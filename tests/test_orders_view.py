from __future__ import annotations

from pathlib import Path

import pytest

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load, load_configuration
from simulator.entities import OrderBar, OvercookedState
from simulator.view import (
    RecipeStep,
    and_list,
    orders_view,
    recipe_expression,
    recipe_steps,
    scene_layers,
)
from simulator.visualisation.panels.orders import orders_panel

LEVELS = Path(__file__).resolve().parents[1] / "levels"

LAYERED_FOOD = {
    "kind": "food",
    "name": "catalog/food/layered",
    "sprite": [
        {"x": 1, "y": 2, "sheet": "first.png"},
        {"x": 3, "y": 4, "shift_x": 2, "shift_y": 1, "sheet": "second.png"},
    ],
}


def _environment(**overrides: object):
    payload: dict[str, object] = {"layout": "| |"}
    payload.update(overrides)
    return load(Configuration.from_dict(payload))


def test_one_card_per_visible_order_in_queue_order() -> None:
    environment = _environment(
        state={"orders": ["catalog/food/layered", "catalog/food/layered"]},
        legend={"foods": [LAYERED_FOOD]},
    )

    view = orders_view(environment)

    assert len(view.cards) == 2
    assert [card.name for card in view.cards] == [
        "catalog/food/layered",
        "catalog/food/layered",
    ]
    assert view.cards[0].label == "Layered"


def test_card_sprite_layers_food_over_a_plate() -> None:
    environment = _environment(
        state={"orders": ["catalog/food/layered"]},
        legend={"foods": [LAYERED_FOOD]},
    )

    parts = orders_view(environment).cards[0].sprite.loop_cycle_animation[0].parts

    assert [part.sheet for part in parts] == [
        "interiors.png",
        "first.png",
        "second.png",
    ]
    # The plate takes the cell, the dish stands three pixels above it, and the
    # food's own shifts survive on top of that. A ticket that composed the two
    # flat would print a dish squarely over its plate, which is not how the
    # kitchen ever draws one.
    assert [(part.shift_x, part.shift_y) for part in parts] == [
        (0, 0),
        (0, -3),
        (2, -2),
    ]


def test_food_without_a_sprite_yields_only_the_plate() -> None:
    environment = _environment(
        state={"orders": ["catalog/food/plain"]},
        legend={"foods": [{"kind": "food", "name": "catalog/food/plain"}]},
    )

    parts = orders_view(environment).cards[0].sprite.loop_cycle_animation[0].parts

    assert [part.sheet for part in parts] == ["interiors.png"]


def test_expiry_is_a_fraction_and_a_step_count() -> None:
    environment = _environment(
        state={"orders": ["catalog/food/layered"]},
        legend={"foods": [LAYERED_FOOD]},
        rules={"default_order_time_limit": 100},
    )

    card = orders_view(environment).cards[0]
    assert card.remaining_steps == 100
    assert (card.remaining_fraction or 0.0) == pytest.approx(1.0)

    stepped = environment.copy_with(timestep=75)
    card = orders_view(stepped).cards[0]
    assert card.remaining_steps == 25
    assert (card.remaining_fraction or 0.0) == pytest.approx(0.25)


def test_expiry_is_absent_without_a_time_limit() -> None:
    environment = _environment(
        state={"orders": ["catalog/food/layered"]},
        legend={"foods": [LAYERED_FOOD]},
    )

    card = orders_view(environment).cards[0]

    assert card.remaining_fraction is None
    assert card.remaining_steps is None


def test_queue_label_reflects_reveal_and_generator() -> None:
    legend = {"foods": [LAYERED_FOOD]}
    state = {"orders": ["catalog/food/layered"]}

    assert (
        orders_view(_environment(state=state, legend=legend)).queue_label == "Any order"
    )
    assert (
        orders_view(
            _environment(
                state=state, legend=legend, rules={"order_reveal": "sequential"}
            )
        ).queue_label
        == "Sequential"
    )
    assert (
        orders_view(
            _environment(state=state, legend=legend, rules={"infinite_orders": True})
        ).queue_label
        == "Endless"
    )


def test_first_order_is_marked_next_only_when_ordering_matters() -> None:
    legend = {"foods": [LAYERED_FOOD]}
    state = {"orders": ["catalog/food/layered", "catalog/food/layered"]}

    loose = orders_view(_environment(state=state, legend=legend))
    assert not any(card.is_next for card in loose.cards)

    strict = orders_view(
        _environment(state=state, legend=legend, rules={"strict_ordering": True})
    )
    assert strict.cards[0].is_next
    assert not strict.cards[1].is_next


def _state(**overrides: object) -> OvercookedState:
    state = _environment(**overrides).get_first_entity_of_type(OvercookedState)
    assert state is not None
    return state


def _cook(ingredient: str, equipment: str, output: str) -> dict[str, str]:
    return {
        "ingredient": f"catalog/food/{ingredient}",
        "with": f"catalog/equipment/{equipment}",
        "to_make": f"catalog/food/{output}",
    }


def _combine(first: str, second: str, output: str) -> dict[str, object]:
    return {
        "ingredients": [f"catalog/food/{first}", f"catalog/food/{second}"],
        "to_make": f"catalog/food/{output}",
    }


def _expression(state: OvercookedState, dish: str) -> str:
    return recipe_expression(recipe_steps(state, f"catalog/food/{dish}"))


CHICKEN_AND_CHIPS = {
    "cook": [
        _cook("chicken", "oven", "oven_chicken"),
        _cook("potato", "cutboard", "chopped_potato"),
        _cook("chopped_potato", "deep_fryer", "chips"),
    ],
    "combine": [_combine("oven_chicken", "chips", "chicken_and_chips")],
}

CHEESEBURGER = {
    "cook": [
        _cook("cheese", "cutboard", "sliced_cheese"),
        _cook("meat", "pan", "grilled_meat"),
    ],
    "combine": [
        _combine("bun", "sliced_cheese", "bun_cheese"),
        _combine("bun", "grilled_meat", "hamburger"),
        _combine("sliced_cheese", "grilled_meat", "patty_cheese"),
        _combine("bun_cheese", "grilled_meat", "cheeseburger"),
        _combine("hamburger", "sliced_cheese", "cheeseburger"),
        _combine("patty_cheese", "bun", "cheeseburger"),
    ],
}


def test_a_run_of_stations_is_one_item_passing_through_them() -> None:
    state = _state(
        state={"orders": ["catalog/food/chicken_and_chips"]}, recipes=CHICKEN_AND_CHIPS
    )

    # The potato keeps one slot across both stations, because a potato on its
    # way to being chips is a potato the whole time. Nothing is bracketed: there
    # is no "+" inside either half for a bracket to disambiguate.
    assert (
        _expression(state, "chicken_and_chips")
        == "[Potato](Cutboard)(Deep fryer) + [Chicken](Oven)"
    )


def test_interchangeable_orders_collapse_to_what_you_actually_fetch() -> None:
    state = _state(
        state={"orders": ["catalog/food/cheeseburger"]}, recipes=CHEESEBURGER
    )

    # Three recipes make a cheeseburger, and all three are the same three things
    # stacked in a different order. None of the half-built stacks survive.
    assert (
        _expression(state, "cheeseburger") == "[Bun] + [Meat](Pan) + [Cheese](Cutboard)"
    )


def test_a_base_that_has_to_go_down_first_is_printed_first() -> None:
    state = _state(
        state={"orders": ["catalog/food/plate_salad"]},
        recipes={
            "cook": [_cook("tomato", "cutboard", "chopped_tomato")],
            "combine": [
                {
                    "ingredients": [
                        "catalog/food/chopped_tomato",
                        "catalog/equipment/plate",
                    ],
                    "to_make": "catalog/food/plate_tomato",
                },
                _combine("plate_tomato", "lettuce", "plate_salad"),
            ],
        },
    )

    # Tomato and lettuce never meet each other, only the plate, so the plate
    # cannot be anywhere but the front of the line.
    assert (
        _expression(state, "plate_salad") == "[Plate] + [Tomato](Cutboard) + [Lettuce]"
    )


def test_a_sub_assembly_comes_before_what_gets_added_to_it() -> None:
    state = _state(
        state={"orders": ["catalog/food/sushi"]},
        recipes={
            "cook": [
                _cook("rice", "pot", "cooked_rice"),
                _cook("fish", "cutboard", "sliced_fish"),
            ],
            "combine": [
                _combine("cooked_rice", "sliced_fish", "nigiri"),
                _combine("nigiri", "nori", "sushi"),
            ],
        },
    )

    # Nigiri is forced rather than incidental, so its two halves stay, but it
    # has to be built before the nori joins and so it leads.
    assert _expression(state, "sushi") == "[Rice](Pot) + [Fish](Cutboard) + [Nori]"


def test_a_station_fed_by_a_group_gets_one_pair_of_brackets() -> None:
    state = _state(
        state={"orders": ["catalog/food/cake"]},
        recipes={
            "cook": [
                _cook("batter_ingredients", "mixing_bowl", "batter"),
                _cook("batter", "oven", "cake"),
            ],
            "combine": [
                _combine("egg", "flour", "egg_flour"),
                _combine("egg", "cream", "egg_cream"),
                _combine("cream", "flour", "cream_flour"),
                _combine("egg_flour", "cream", "batter_ingredients"),
                _combine("egg_cream", "flour", "batter_ingredients"),
                _combine("cream_flour", "egg", "batter_ingredients"),
            ],
        },
    )

    # The bowl takes all three, so they need holding together. The oven then
    # takes what the bowl produced, which is a single thing already, so it does
    # not get a second pair.
    assert (
        _expression(state, "cake") == "([Cream] + [Egg] + [Flour])(Mixing bowl)(Oven)"
    )


def test_a_station_prints_the_word_for_what_it_does() -> None:
    state = _state(
        state={"orders": ["catalog/food/chips"]},
        legend={
            "equipment": [
                {
                    "kind": "equipment",
                    "symbol": "/",
                    "name": "catalog/equipment/cutboard",
                    "verb": "Chop",
                },
                {
                    "kind": "equipment",
                    "symbol": "D",
                    "name": "catalog/equipment/deep_fryer",
                    "verb": "Fry",
                },
            ]
        },
        recipes={
            "cook": [
                _cook("potato", "cutboard", "chopped_potato"),
                _cook("chopped_potato", "deep_fryer", "chips"),
            ]
        },
    )

    assert _expression(state, "chips") == "[Potato](Chop)(Fry)"

    # Both stations hang off the one potato rather than becoming steps of their
    # own, and each keeps the name of the station it stands for.
    potato = recipe_steps(state, "catalog/food/chips")
    assert potato is not None
    assert not potato.parts
    assert [station.name for station in potato.stations] == [
        "catalog/equipment/cutboard",
        "catalog/equipment/deep_fryer",
    ]


def test_a_run_of_stations_is_read_out_as_a_list() -> None:
    assert and_list([]) == ""
    assert and_list(["Chop"]) == "Chop"
    assert and_list(["Chop", "Fry"]) == "Chop & Fry"
    assert and_list(["Mix", "Bake", "Chop"]) == "Mix, Bake & Chop"
    assert and_list(["Mix", "Bake", "Chop", "Fry"]) == "Mix, Bake, Chop & Fry"


def test_a_station_with_no_word_falls_back_to_its_name() -> None:
    state = _state(
        state={"orders": ["catalog/food/chopped_potato"]},
        recipes={"cook": [_cook("potato", "deep_fryer", "chopped_potato")]},
    )

    # Nothing in this kitchen says what a deep fryer does, and the step still
    # has to print something.
    assert _expression(state, "chopped_potato") == "[Potato](Deep fryer)"


def test_equipment_named_in_a_recipe_is_drawn_rather_than_left_blank() -> None:
    state = _state(
        state={"orders": ["catalog/food/plate_tomato"]},
        recipes={
            "combine": [
                {
                    "ingredients": [
                        "catalog/food/tomato",
                        "catalog/equipment/plate",
                    ],
                    "to_make": "catalog/food/plate_tomato",
                }
            ]
        },
    )

    steps = recipe_steps(state, "catalog/food/plate_tomato")
    assert steps is not None
    plate = next(part for part in steps.parts if part.name == "catalog/equipment/plate")

    assert plate.sprite.loop_cycle_animation


def test_a_raw_ingredient_prints_nothing() -> None:
    state = _state(
        state={"orders": ["catalog/food/layered"]}, legend={"foods": [LAYERED_FOOD]}
    )

    assert recipe_steps(state, "catalog/food/layered") is None


def test_recipes_that_feed_themselves_do_not_hang() -> None:
    state = _state(
        state={"orders": ["catalog/food/soup"]},
        recipes={"combine": [_combine("soup", "salt", "soup")]},
    )

    # A level can describe a loop. The ticket has to stop somewhere, so a name
    # already open further up the branch is treated as something you pick up.
    assert _expression(state, "soup") == "[Soup] + [Salt]"


def _make(state: OvercookedState, step: RecipeStep) -> str:
    """Build a recipe expression by applying each step."""
    if step.parts:
        held = _make(state, step.parts[0])
        for part in step.parts[1:]:
            added = _make(state, part)
            merged = state.get_combine_output(held, added)
            assert merged is not None, f"{held} does not combine with {added}"
            held = merged
    else:
        held = step.name
    for station in step.stations:
        cooked = state.get_cook_output(held, station.name)
        assert cooked is not None, f"{held} does not go in {station.name}"
        held = cooked
    return held


@pytest.mark.parametrize(
    "level", sorted(LEVELS.rglob("*.yaml")), ids=lambda path: path.stem
)
def test_every_level_prints_a_build_order_that_works(level: Path) -> None:
    state = load(load_configuration(level)).get_first_entity_of_type(OvercookedState)
    assert state is not None

    queue = state.order_queue
    for entry in [*queue.visible, *queue.pending]:
        steps = recipe_steps(state, entry.name)
        if steps is None:
            continue
        assert _make(state, steps) == entry.name, (
            f"{recipe_expression(steps)} does not make {entry.name}"
        )


@pytest.mark.parametrize(
    "level",
    [
        # Brackets, a chain of stations, and a station the kitchen never got.
        "demos/black_forest_cake.yaml",
        "demos/chicken_and_chips.yaml",
        "0_i_can_cook/0_coconut_juice_finished_on_counter.yaml",
    ],
)
def test_the_rail_draws_every_kind_of_mark(level: str) -> None:
    view = orders_view(load(load_configuration(LEVELS / level)))

    orders_panel(view)

    assert any(card.recipe for card in view.cards)


def test_loading_no_longer_creates_an_order_bar() -> None:
    environment = _environment()

    assert environment.get_first_entity_of_type(OrderBar) is None


def test_scene_never_renders_an_order_bar() -> None:
    # The class survives so old recordings deserialise, but a recording that
    # still carries one must not draw order cards over the DOM panel.
    environment = _environment().with_entity(OrderBar(id="order_bar", x=0, y=0))

    layers = scene_layers(environment, [])

    rendered = [
        renderable.id
        for renderable in (*layers.background, *layers.shadows, *layers.objects)
    ]
    assert "order_bar" not in rendered

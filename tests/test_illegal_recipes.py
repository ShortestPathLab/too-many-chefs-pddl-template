"""Test illegal recipe handling."""

from __future__ import annotations

import pytest

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.entities import Agent, Food, OvercookedState
from simulator.entities.garbage import (
    DUBIOUS_FOOD,
    GARBAGE_FOOD_NAMES,
    ROCK_HARD_FOOD,
    garbage_food_name,
)
from simulator.entities.sprite import SpriteDefinition, SpriteFramePart
from simulator.environment import Environment
from simulator.mutations import Combine, Cook
from simulator.mutations.mutation import IllegalMutationError

BUN = "catalog/food/bun"
MEAT = "catalog/food/meat"
GRILLED_MEAT = "catalog/food/grilled_meat"
PAN = "catalog/equipment/pan"
STOVE = "catalog/equipment/stove"


def kitchen(
    layout: str,
    *,
    allow_illegal_recipes: bool = True,
    holding: str | None = None,
    on_counter: str | None = None,
    on_plate: str | None = None,
) -> Environment:
    """Build a kitchen with one valid cook recipe and order."""
    return load(
        Configuration.from_dict(
            {
                "layout": layout,
                "state": {"orders": [GRILLED_MEAT]},
                "rules": {"allow_illegal_recipes": allow_illegal_recipes},
                "scoring": {"produce_ordered_item_reward": 7},
                "legend": {
                    "agents": [
                        {
                            "kind": "agent",
                            "symbol": "A",
                            "orientation": "e",
                            **({"held_item": {"name": holding}} if holding else {}),
                        }
                    ],
                    "counters": [
                        {
                            "kind": "counter",
                            "symbol": "-",
                            **(
                                {"held_item": {"name": on_counter}}
                                if on_counter
                                else {}
                            ),
                        }
                    ],
                    "plates": [
                        {
                            "kind": "plate",
                            "symbol": "p",
                            **({"held_item": {"name": on_plate}} if on_plate else {}),
                        }
                    ],
                    "equipment": [
                        {"kind": "equipment", "symbol": "V", "name": STOVE},
                        {"kind": "equipment", "symbol": "R", "name": PAN},
                    ],
                    "foods": [
                        {"kind": "food", "name": name}
                        for name in (BUN, MEAT, GRILLED_MEAT)
                    ],
                },
                "recipes": {
                    "cook": [{"ingredient": MEAT, "with": PAN, "to_make": GRILLED_MEAT}]
                },
            }
        )
    )


def chef(environment: Environment) -> Agent:
    agent = environment.get_first_entity_of_type(Agent)
    assert agent is not None
    return agent


def state_of(environment: Environment) -> OvercookedState:
    state = environment.get_first_entity_of_type(OvercookedState)
    assert state is not None
    return state


def food_names(environment: Environment) -> list[str]:
    return sorted(food.name for food in environment.get_entities_of_type(Food))


def ruin(environment: Environment) -> Environment:
    """Put whatever the chef is holding into the pan and cook it."""
    agent = chef(environment)
    return Cook(agent_id=agent.id).run(Combine(agent_id=agent.id).run(environment))


def test_a_station_refuses_an_ingredient_it_has_no_recipe_for() -> None:
    environment = kitchen("|A|VR|", allow_illegal_recipes=False, holding=BUN)

    with pytest.raises(IllegalMutationError):
        Combine(agent_id=chef(environment).id).run(environment)


def test_two_items_that_make_nothing_stay_two_items() -> None:
    environment = kitchen(
        "|A|-|", allow_illegal_recipes=False, holding=BUN, on_counter=MEAT
    )

    with pytest.raises(IllegalMutationError):
        Combine(agent_id=chef(environment).id).run(environment)


def test_the_rule_is_off_unless_a_level_asks_for_it() -> None:
    silent = load(
        Configuration.from_dict(
            {
                "layout": "|A|",
                "legend": {"agents": [{"kind": "agent", "symbol": "A"}]},
            }
        )
    )

    assert not Configuration().rules.allow_illegal_recipes
    assert not state_of(silent).allow_illegal_recipes
    assert not state_of(
        kitchen("|A|VR|", allow_illegal_recipes=False)
    ).allow_illegal_recipes


def test_a_level_turns_the_rule_on() -> None:
    assert state_of(kitchen("|A|VR|", allow_illegal_recipes=True)).allow_illegal_recipes


def test_cooking_the_wrong_ingredient_ruins_it() -> None:
    environment = ruin(kitchen("|A|VR|", holding=BUN))

    assert len(food_names(environment)) == 1
    assert food_names(environment)[0] in GARBAGE_FOOD_NAMES


def test_combining_on_a_counter_ruins_both_items() -> None:
    environment = kitchen("|A|-|", holding=BUN, on_counter=MEAT)

    combined = Combine(agent_id=chef(environment).id).run(environment)

    assert len(food_names(combined)) == 1
    assert food_names(combined)[0] in GARBAGE_FOOD_NAMES
    assert chef(combined).hands_free


def test_combining_on_a_plate_ruins_the_plated_dish() -> None:
    environment = kitchen("|A|p|", holding=BUN, on_plate=GRILLED_MEAT)

    combined = Combine(agent_id=chef(environment).id).run(environment)

    assert len(food_names(combined)) == 1
    assert food_names(combined)[0] in GARBAGE_FOOD_NAMES


def test_a_recipe_the_book_does_cover_still_wins() -> None:
    environment = ruin(kitchen("|A|VR|", holding=MEAT))

    assert food_names(environment) == [GRILLED_MEAT]


# Stations without cook recipes remain closed.
def test_a_stove_still_wants_its_pan() -> None:
    environment = kitchen("|A|V|", holding=MEAT)

    with pytest.raises(IllegalMutationError):
        Combine(agent_id=chef(environment).id).run(environment)


def test_a_plate_is_not_a_station_so_a_plated_dish_survives_the_cook_key() -> None:
    environment = kitchen("|A|p|", on_plate=GRILLED_MEAT)

    with pytest.raises(IllegalMutationError):
        Cook(agent_id=chef(environment).id).run(environment)


def test_there_are_two_of_them_and_both_turn_up() -> None:
    drawn = {garbage_food_name(BUN, PAN, timestep=timestep) for timestep in range(20)}

    assert drawn == set(GARBAGE_FOOD_NAMES)


def test_the_same_attempt_ruins_the_same_way_twice() -> None:
    environment = kitchen("|A|VR|", holding=BUN)

    assert food_names(ruin(environment)) == food_names(ruin(environment))


def test_it_pays_nothing_where_the_ordered_dish_pays() -> None:
    ruined = ruin(kitchen("|A|VR|", holding=BUN))
    cooked = ruin(kitchen("|A|VR|", holding=MEAT))

    assert state_of(ruined).score == 0
    assert state_of(cooked).score == 7


@pytest.mark.parametrize("name", GARBAGE_FOOD_NAMES)
def test_it_can_be_drawn_by_a_kitchen_that_never_declared_it(name: str) -> None:
    state = state_of(kitchen("|A|VR|"))

    definition = state.get_food_definition(name)
    assert definition is not None
    assert definition.raw
    assert not definition.deliverable
    sprite = state.get_food_sprite(name)
    assert sprite is not None
    assert sprite.parts


def test_a_closed_kitchen_knows_nothing_about_it() -> None:
    state = state_of(kitchen("|A|VR|", allow_illegal_recipes=False))

    assert state.get_food_definition(DUBIOUS_FOOD) is None
    assert state.get_food_sprite(ROCK_HARD_FOOD) is None


def test_a_level_can_draw_it_itself() -> None:
    own_art = SpriteDefinition(
        parts=[SpriteFramePart(x=0, y=0, width=16, height=16, sheet="custom.png")]
    )
    state = OvercookedState(
        allow_illegal_recipes=True,
        food_sprites={DUBIOUS_FOOD: own_art},
    )

    assert state.get_food_sprite(DUBIOUS_FOOD) == own_art

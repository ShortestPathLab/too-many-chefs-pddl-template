"""Test equipment sprite variants."""

from __future__ import annotations

from simulator.configuration.load import load
from simulator.mutations.cook import Cook
from simulator.mutations.interact import Interact
from simulator.mutations.pick_up import PickUp
from simulator.mutations.place import Place
from simulator.view import CALLOUT_SUFFIX, OVERLAY_DRAW_LIFT, scene_layers
from tests.pan_kitchens import (
    COOK_TOMATO_IN_PAN,
    COOKED_TOMATO,
    TOMATO,
    TOMATO_NAME,
    chef_pan_and_state,
    draws_poof,
    pan_kitchen,
    reload_pan,
)


def test_equipment_food_in_can_render_callout_and_init_animation() -> None:
    environment = load(
        pan_kitchen(
            foods=[TOMATO],
            display_food="callout",
            on_food_in={
                "sprite": [
                    {
                        "x": 100,
                        "y": 200,
                        "width": 8,
                        "height": 10,
                        "shift_x": -1,
                        "shift_y": -2,
                        "sheet": "animated.png",
                    }
                ],
                "frames": 3,
            },
        )
    )
    agent, equipment, state = chef_pan_and_state(environment)

    food = state.create_food(TOMATO_NAME, x=equipment.x, y=equipment.y)
    assert food is not None
    environment = environment.with_entity(food).replace_entity(
        agent.copy_with(held_item_id=None),
        equipment.copy_with(held_item_id=food.id),
    )

    sprite = reload_pan(environment, equipment).sprite(
        environment, [Place(agent_id=agent.id)]
    )

    assert len(sprite.init_animation) == 3
    assert [frame.parts[1].x for frame in sprite.init_animation] == [100, 108, 116]
    # The station draws itself and its animation. The bubble is not here: it
    # goes out as its own renderable so it can clear anything drawn over the
    # station, which is what a stand mixer needs over its bowl.
    assert [part.sheet for part in sprite.init_animation[0].parts] == [
        "interiors.png",
        "animated.png",
    ]
    assert not draws_poof(sprite)
    assert [part.sheet for part in sprite.loop_cycle_animation[0].parts] == [
        "interiors.png"
    ]


def test_a_callout_draws_as_its_own_renderable_over_the_station() -> None:
    environment = load(pan_kitchen(foods=[TOMATO], display_food="callout"))
    agent, equipment, state = chef_pan_and_state(environment)

    food = state.create_food(TOMATO_NAME, x=equipment.x, y=equipment.y)
    assert food is not None
    environment = environment.with_entity(food).replace_entity(
        agent.copy_with(held_item_id=None),
        equipment.copy_with(held_item_id=food.id),
    )

    objects = {
        renderable.id: renderable for renderable in scene_layers(environment).objects
    }
    callout = objects[f"{equipment.id}{CALLOUT_SUFFIX}"]

    assert callout.z > objects[equipment.id].z + OVERLAY_DRAW_LIFT
    assert [part.sheet for part in callout.sprite.loop_cycle_animation[0].parts] == [
        "ui.png",
        "ui.png",
        "food.png",
    ]


def test_a_station_holding_nothing_has_no_callout() -> None:
    environment = load(pan_kitchen(foods=[TOMATO], display_food="callout"))

    ids = [renderable.id for renderable in scene_layers(environment).objects]
    assert [id for id in ids if id.endswith(CALLOUT_SUFFIX)] == []


def test_equipment_food_out_can_render_init_animation() -> None:
    environment = load(
        pan_kitchen(
            foods=[TOMATO],
            on_food_out={
                "sprite": [{"x": 40, "y": 60, "sheet": "animated.png"}],
                "frames": 2,
            },
        )
    )
    agent, equipment, state = chef_pan_and_state(environment)

    food = state.create_food(TOMATO_NAME, x=None, y=None)
    assert food is not None
    environment = environment.with_entity(food).replace_entity(
        agent.copy_with(held_item_id=food.id),
        equipment.copy_with(held_item_id=None),
    )

    sprite = reload_pan(environment, equipment).sprite(
        environment, [PickUp(agent_id=agent.id)]
    )

    assert len(sprite.init_animation) == 2
    assert [frame.parts[-1].x for frame in sprite.init_animation] == [40, 56]
    assert not draws_poof(sprite)


# Cooking always includes the generic puff.
def test_equipment_cook_renders_poof_animation() -> None:
    environment = load(
        pan_kitchen(
            foods=[TOMATO, COOKED_TOMATO],
            recipes=COOK_TOMATO_IN_PAN,
            on_cook={
                "sprite": [{"x": 40, "y": 60, "sheet": "animated.png"}],
                "frames": 2,
            },
        )
    )
    agent, equipment, state = chef_pan_and_state(environment)

    food = state.create_food(TOMATO_NAME, x=equipment.x, y=equipment.y)
    assert food is not None
    environment = environment.with_entity(food).replace_entity(
        equipment.copy_with(held_item_id=food.id),
    )
    cook = Cook(agent_id=agent.id)
    environment = cook.run(environment)

    sprite = reload_pan(environment, equipment).sprite(environment, [cook])

    assert len(sprite.init_animation) == 5
    assert draws_poof(sprite)


def test_equipment_interact_cook_renders_poof_animation() -> None:
    environment = load(
        pan_kitchen(
            foods=[TOMATO, COOKED_TOMATO],
            recipes=COOK_TOMATO_IN_PAN,
        )
    )
    agent, equipment, state = chef_pan_and_state(environment)

    food = state.create_food(TOMATO_NAME, x=equipment.x, y=equipment.y)
    assert food is not None
    environment = environment.with_entity(food).replace_entity(
        equipment.copy_with(held_item_id=food.id),
    )
    interact = Interact(agent_id=agent.id)
    environment = interact.run(environment)

    sprite = reload_pan(environment, equipment).sprite(environment, [interact])

    assert len(sprite.init_animation) == 5
    assert draws_poof(sprite)

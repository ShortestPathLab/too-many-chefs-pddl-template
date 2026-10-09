"""Kitchens and step helpers shared by the audio cue tests."""

from __future__ import annotations

from typing import Any

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.entities import Agent, Counter, Food, OrderEntry, Plate
from simulator.environment import Environment
from simulator.mutations import Interact, MoveAgentForward, Mutation
from simulator.view import cues_for_step, equipment_cue_name

CUTBOARD_CUE = equipment_cue_name("catalog/equipment/cutboard")

# A kitchen with one of each audio-producing station.
KITCHEN: dict[str, Any] = {
    "layout": (
        "| T | 1 | / | O | X | * | p |\n"
        "|   |   |   |   |   |   |   |\n"
        "| - | - | - | - | - | - | - |"
    ),
    "legend": {
        "agents": [{"symbol": "1", "orientation": "w"}],
        "counters": [{"symbol": "-"}],
        "plates": [{"symbol": "p"}],
        "bins": [{"symbol": "X"}],
        "deliveries": [{"symbol": "*"}],
        "storages": [{"symbol": "T", "food_name": "catalog/food/tomato"}],
        "equipment": [
            # The board names its own sound; the oven deliberately does not, so
            # the fallback is covered too.
            {
                "symbol": "/",
                "name": "catalog/equipment/cutboard",
                "sound": ["chop.ogg", "knifeSlice.ogg"],
            },
            {"symbol": "O", "name": "catalog/equipment/oven"},
        ],
        "foods": [
            {"name": "catalog/food/tomato", "raw": True},
            {"name": "catalog/food/chopped_tomato"},
            {"name": "catalog/food/baked_tomato"},
        ],
    },
    "recipes": {
        "cook": [
            {
                "ingredient": "catalog/food/tomato",
                "with": "catalog/equipment/cutboard",
                "to_make": "catalog/food/chopped_tomato",
            },
            {
                "ingredient": "catalog/food/chopped_tomato",
                "with": "catalog/equipment/oven",
                "to_make": "catalog/food/baked_tomato",
            },
        ]
    },
}

MINIMAL = {"layout": "|1|", "legend": {"agents": [{"symbol": "1"}]}}

SALAD = "catalog/food/salad"

# A server and a second chef with separate movement paths.
PASS: dict[str, Any] = {
    "layout": "| A | * |\n| B |   |",
    "state": {"orders": [SALAD]},
    "legend": {
        "agents": [
            {"symbol": "A", "orientation": "e"},
            {"symbol": "B", "orientation": "e"},
        ],
        "deliveries": [{"symbol": "*"}],
        "foods": [{"name": SALAD}],
    },
}

# Four chefs with clear floor for simultaneous movement.
CREW: dict[str, Any] = {
    "layout": "| 1 | 2 | 3 | 4 |\n|   |   |   |   |",
    "legend": {
        "agents": [
            {"symbol": symbol, "orientation": "s"} for symbol in ("1", "2", "3", "4")
        ]
    },
}


def kitchen() -> Environment:
    return load(Configuration.from_dict(KITCHEN))


def minimal() -> Environment:
    return load(Configuration.from_dict(MINIMAL))


def crew() -> Environment:
    return load(Configuration.from_dict(CREW))


def pass_kitchen() -> tuple[Environment, Agent, Agent]:
    """Return a server holding a plated salad and a second chef."""
    environment = load(Configuration.from_dict(PASS))
    server, runner = sorted(
        environment.get_entities_of_type(Agent), key=lambda agent: agent.y or 0
    )
    food = Food(name=SALAD, x=None, y=None)
    plate = Plate(x=None, y=None, held_item_id=food.id)
    return (
        environment.with_entity(food)
        .with_entity(plate)
        .replace_entity(server.copy_with(held_item_id=plate.id)),
        server,
        runner,
    )


def agent_id(environment: Environment) -> str:
    return environment.get_entities_of_type(Agent)[0].id


def with_cutboard_sound(sound: object) -> dict[str, Any]:
    """Return the kitchen with a replacement cutboard sound."""
    equipment = [
        {**entry, "sound": sound} if "cutboard" in entry["name"] else entry
        for entry in KITCHEN["legend"]["equipment"]
    ]
    return {
        **KITCHEN,
        "legend": {**KITCHEN["legend"], "equipment": equipment},
    }


def step(
    environment: Environment, *mutations: Mutation
) -> tuple[Environment, list[str]]:
    """Run a step and return its generated cues."""
    updated = environment.step(list(mutations))
    return updated, cues_for_step(environment, updated, list(mutations))


def face(environment: Environment, orientation: str) -> Environment:
    agent = environment.get_entities_of_type(Agent)[0]
    return environment.replace_entity(agent.copy_with(orientation=orientation))


def turn_away(environment: Environment, chef_id: str) -> Environment:
    """Face one chef south before the next action."""
    agent = environment.get_entity_as(chef_id, Agent)
    assert agent is not None
    return environment.replace_entity(agent.copy_with(orientation="s"))


def holding_a_tomato() -> tuple[Environment, str]:
    """Return a chef holding a tomato near the counter row."""
    environment = kitchen()
    chef_id = agent_id(environment)
    environment, _ = step(environment, Interact(agent_id=chef_id))
    environment = face(environment, "s")
    environment, _ = step(environment, MoveAgentForward(agent_id=chef_id))
    return environment, chef_id


def plate_on_counter(environment: Environment, x: int, y: int) -> Environment:
    """Place a clean plate on the counter at ``x``, ``y``."""
    counter = next(
        counter
        for counter in environment.get_entities_of_type(Counter)
        if counter.is_at(x, y)
    )
    plate = Plate(x=x, y=y)
    return environment.with_entity(plate).replace_entity(
        counter.copy_with(held_item_id=plate.id)
    )


def order(name: str) -> OrderEntry:
    return OrderEntry(name=name)

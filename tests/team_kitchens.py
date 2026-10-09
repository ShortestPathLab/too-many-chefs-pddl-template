"""Two-chef kitchens, shared by the per-agent and per-team scoring tests."""

from __future__ import annotations

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.entities import Agent, OvercookedState
from simulator.environment import Environment
from simulator.view import badge_order
from tests.scoring_states import CHOPPED_TOMATO, SALAD, TOMATO

CUTBOARD = "catalog/equipment/cutboard"

# Two chefs with separate work and distinct rewards.
TWO_CHEF_KITCHEN = {
    "layout": "|1|T|C|2|",
    "state": {"orders": [CHOPPED_TOMATO]},
    "scoring": {
        "retrieve_order_component_reward": 2,
        "produce_ordered_item_reward": 5,
    },
    "legend": {
        "agents": [
            {"symbol": "1", "orientation": "e"},
            {"symbol": "2", "orientation": "w"},
        ],
        "storages": [{"symbol": "T", "food_name": TOMATO}],
        "equipment": [{"symbol": "C", "name": CUTBOARD, "held_item": {"name": TOMATO}}],
        "foods": [{"name": TOMATO}, {"name": CHOPPED_TOMATO}],
    },
    "recipes": {
        "cook": [{"ingredient": TOMATO, "with": CUTBOARD, "to_make": CHOPPED_TOMATO}]
    },
}

# The same kitchen with named chefs.
NAMED_CHEF_KITCHEN = {
    **TWO_CHEF_KITCHEN,
    "legend": {
        **TWO_CHEF_KITCHEN["legend"],
        "agents": [
            {"symbol": "1", "orientation": "e", "name": "Alfred"},
            {"symbol": "2", "orientation": "w", "name": "Bruno"},
        ],
    },
}

# Both chefs face their own crate so teams can do identical work.
MIRRORED_KITCHEN = {
    **TWO_CHEF_KITCHEN,
    "layout": "|1|T|T|2|",
    "legend": {
        **TWO_CHEF_KITCHEN["legend"],
        "equipment": [],
    },
}

DELIVERY_KITCHEN = {
    "layout": "|1| |2|*|",
    "state": {"orders": [SALAD]},
    "legend": {
        "agents": [
            {"symbol": "1", "orientation": "e"},
            {"symbol": "2", "orientation": "e"},
        ],
        "deliveries": [{"symbol": "*"}],
        "foods": [{"name": SALAD}],
    },
}


def kitchen(level: dict, **overrides: object) -> Environment:
    return load(Configuration.from_dict({**level, **overrides}))


def two_chefs(level: dict, **overrides: object) -> tuple[Environment, Agent, Agent]:
    environment = kitchen(level, **overrides)
    first, second = badge_order(environment)
    return environment, first, second


def state_of(environment: Environment) -> OvercookedState:
    state = environment.get_first_entity_of_type(OvercookedState)
    assert state is not None
    return state

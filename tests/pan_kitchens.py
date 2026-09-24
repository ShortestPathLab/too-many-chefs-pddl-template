"""Fixtures for pan sprite tests."""

from __future__ import annotations

from typing import Any

from simulator.configuration.configuration import Configuration
from simulator.entities import Agent, Equipment, OvercookedState, Sprite
from simulator.environment import Environment

PAN = "catalog/equipment/pan"
TOMATO_NAME = "catalog/food/tomato"
COOKED_TOMATO_NAME = "catalog/food/cooked_tomato"

PAN_SPRITE = [{"x": 16, "y": 32, "sheet": "interiors.png"}]
TOMATO = {
    "kind": "food",
    "name": TOMATO_NAME,
    "sprite": [{"x": 0, "y": 0, "sheet": "food.png"}],
}
COOKED_TOMATO = {
    "kind": "food",
    "name": COOKED_TOMATO_NAME,
    "sprite": [{"x": 16, "y": 0, "sheet": "food.png"}],
}
COOK_TOMATO_IN_PAN = {
    "cook": [
        {
            "ingredient": TOMATO_NAME,
            "with": PAN,
            "to_make": COOKED_TOMATO_NAME,
        }
    ]
}


def pan_kitchen(
    *,
    foods: list[dict[str, Any]],
    recipes: dict[str, Any] | None = None,
    **pan: Any,
) -> Configuration:
    """Build ``|A|P|`` with the supplied food, recipe, and equipment options."""
    configuration: dict[str, Any] = {
        "layout": "|A|P|",
        "legend": {
            "agents": [{"kind": "agent", "symbol": "A", "orientation": "e"}],
            "equipment": [
                {
                    "kind": "equipment",
                    "symbol": "P",
                    "name": PAN,
                    "sprite": PAN_SPRITE,
                    **pan,
                }
            ],
            "foods": foods,
        },
    }
    if recipes is not None:
        configuration["recipes"] = recipes
    return Configuration.from_dict(configuration)


def chef_pan_and_state(
    environment: Environment,
) -> tuple[Agent, Equipment, OvercookedState]:
    agent = environment.get_first_entity_of_type(Agent)
    equipment = environment.get_first_entity_of_type(Equipment)
    state = environment.get_first_entity_of_type(OvercookedState)
    assert agent is not None
    assert equipment is not None
    assert state is not None
    return agent, equipment, state


def reload_pan(environment: Environment, equipment: Equipment) -> Equipment:
    """Return the current pan after an environment update."""
    updated = environment.get_entity_as(equipment.id, Equipment)
    assert updated is not None
    return updated


def draws_poof(sprite: Sprite) -> bool:
    """Return whether the one-shot animation includes the generic puff."""
    return any(
        part.sheet == "poof.png"
        for frame in sprite.init_animation
        for part in frame.parts
    )

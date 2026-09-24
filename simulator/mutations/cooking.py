"""Cooking steps shared by the Cook action and stations that cook by themselves."""

from __future__ import annotations

from typing import TYPE_CHECKING

from simulator.entities import Equipment, Food, OvercookedState
from simulator.entities.equipment import CookingTimer
from simulator.entities.garbage import is_garbage_food
from simulator.entities.teams import team_of
from simulator.utils import required

if TYPE_CHECKING:
    from simulator.environment import Environment


def has_required_support(environment: Environment, equipment: Equipment) -> bool:
    """Return whether a station stands on the station it needs, if any.

    A pan needs a stove below it. Equipment in a chef's hands has no support.
    """
    if not equipment.requires:
        return True
    if equipment.x is None or equipment.y is None:
        return False
    return any(
        other.name == equipment.requires
        for other in environment.get_entities_of_type(Equipment)
        if other.is_at(equipment.x, equipment.y)
    )


def held_food(environment: Environment, equipment: Equipment) -> Food | None:
    if not equipment.held_item_id:
        return None
    return environment.get_entity_as(equipment.held_item_id, Food)


def cooks_gradually(equipment: Equipment) -> bool:
    """Return whether cooking at a station shows progress before it finishes.

    That is a station that cooks by itself, or one that needs more than one
    press of Cook.
    """
    return equipment.cooks_by_itself or equipment.cook_time > 1


def current_timer(equipment: Equipment, food: Food) -> CookingTimer | None:
    """Return the station's timer if it belongs to this food."""
    if equipment.cooking is None or equipment.cooking.food_id != food.id:
        return None
    return equipment.cooking


def cook_output_name(
    environment: Environment,
    state: OvercookedState,
    equipment: Equipment,
    food: Food,
) -> str | None:
    """Return what a station's food cooks into, if the station can cook it."""
    # Garbage cooks into garbage, so a station cooking it would never stop.
    if not equipment.can_process_food or is_garbage_food(food.name):
        return None
    return state.resolve_cook_output(
        food.name,
        equipment.name,
        timestep=environment.timestep,
    )


def cooking_progress(environment: Environment, equipment: Equipment) -> float | None:
    """Return how far a station's food has cooked, from 0 up to 1.

    Return None for stations that finish in one press, and when the food in the
    station has nothing to cook into here. Progress is still reported while a
    station is paused.
    """
    state = environment.get_first_entity_of_type(OvercookedState)
    food = held_food(environment, equipment)
    if not cooks_gradually(equipment) or state is None or food is None:
        return None
    if cook_output_name(environment, state, equipment, food) is None:
        return None
    timer = current_timer(equipment, food)
    elapsed = timer.elapsed if timer is not None else 0
    return min(1.0, elapsed / equipment.cook_time)


def cook_presses_left(environment: Environment, equipment: Equipment) -> int:
    """Return how many Cook presses the food in a station still needs.

    A station holding no food, or food with no progress yet, needs its full
    cook time.
    """
    food = held_food(environment, equipment)
    timer = current_timer(equipment, food) if food is not None else None
    elapsed = timer.elapsed if timer is not None else 0
    return max(1, equipment.cook_time - elapsed)


def replace_with_cooked_food(
    environment: Environment,
    state: OvercookedState,
    equipment: Equipment,
    food: Food,
    output_name: str,
    *,
    agent_id: str | None,
) -> Environment:
    """Swap the food in a station for what it cooks into and score it."""
    cooked_food = required(
        state.create_food(output_name, x=food.x, y=food.y),
        message=f"Missing food definition for {output_name}",
    )
    return (
        environment.without_entity(food.id)
        .with_entity(cooked_food)
        .replace_entity(
            equipment.copy_with(held_item_id=cooked_food.id),
            state.notify_item_prepared(
                output_name,
                agent_id=agent_id,
                team=team_of(environment, agent_id),
            ),
        )
    )

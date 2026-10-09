from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities import Equipment, OvercookedState
from simulator.entities.equipment import CookingTimer
from simulator.mutations.cooking import (
    cook_output_name,
    current_timer,
    has_required_support,
    held_food,
    replace_with_cooked_food,
)
from simulator.mutations.tick_mutation import TickMutation
from simulator.utils import RequiredValueError

if TYPE_CHECKING:
    from simulator.environment import Environment


class AdvanceCooking(TickMutation):
    """Cook food in stations that cook by themselves, one timestep at a time.

    Food put into such a station during step ``t`` has cooked by the end of
    step ``t + cook_time - 1``, so a chef can take it out during step
    ``t + cook_time``. Each station uses its own ``cook_time``. A station
    pauses while a chef holds it or while it is off the station it needs, and
    starts again when food is taken out or replaced.
    """

    kind: Literal["advance_cooking"] = "advance_cooking"

    def describe(self, environment: Environment) -> str:
        return "stations cook"

    def run(self, environment: Environment) -> Environment:
        equipment_ids = sorted(
            equipment.id
            for equipment in environment.get_entities_of_type(Equipment)
            if equipment.cooks_by_itself
        )
        for equipment_id in equipment_ids:
            environment = self._advance(environment, equipment_id)
        return environment

    def pending(self, environment: Environment) -> bool:
        return any(
            cooking_output(environment, equipment) is not None
            for equipment in environment.get_entities_of_type(Equipment)
        )

    def _advance(self, environment: Environment, equipment_id: str) -> Environment:
        equipment = environment.get_entity_as(equipment_id, Equipment)
        state = environment.get_first_entity_of_type(OvercookedState)
        if equipment is None or state is None:
            return environment

        food = held_food(environment, equipment)
        if (
            food is None
            or cook_output_name(environment, state, equipment, food) is None
        ):
            if equipment.cooking is None:
                return environment
            return environment.replace_entity(equipment.copy_with(cooking=None))

        output_name = cooking_output(environment, equipment)
        if output_name is None:
            return environment

        timer = current_timer(equipment, food) or CookingTimer(food_id=food.id)
        timer = timer.copy_with(elapsed=timer.elapsed + 1)
        if timer.elapsed < equipment.cook_time:
            return environment.replace_entity(equipment.copy_with(cooking=timer))

        try:
            cooked = replace_with_cooked_food(
                environment,
                state,
                equipment.copy_with(
                    cooking=None,
                    last_cooked_at=environment.timestep,
                ),
                food,
                output_name,
                agent_id=timer.started_by,
            )
        except RequiredValueError:
            return environment
        return _continue_cooking(cooked, equipment_id, started_by=timer.started_by)


def cooking_output(environment: Environment, equipment: Equipment) -> str | None:
    """Return what a station's food turns into if it cooks by itself this step.

    Return None when the station does not cook by itself, holds nothing it can
    cook, is in a chef's hands, or is off its support.
    """
    state = environment.get_first_entity_of_type(OvercookedState)
    food = held_food(environment, equipment)
    if not equipment.cooks_by_itself or state is None or food is None:
        return None
    if equipment.x is None or equipment.y is None:
        return None
    if not has_required_support(environment, equipment):
        return None
    return cook_output_name(environment, state, equipment, food)


def start_timers_for_new_food(
    before: Environment,
    after: Environment,
    *,
    agent_id: str,
) -> Environment:
    """Credit a chef with any food they just put into a station that cooks it.

    Stations whose contents did not change keep their timers.
    """
    state = after.get_first_entity_of_type(OvercookedState)
    if state is None:
        return after

    updates: list[Equipment] = []
    for equipment in after.get_entities_of_type(Equipment):
        if not equipment.cooks_by_itself:
            continue
        previous = before.get_entity_as(equipment.id, Equipment)
        if previous is not None and previous.held_item_id == equipment.held_item_id:
            continue
        food = held_food(after, equipment)
        if food is None or cook_output_name(after, state, equipment, food) is None:
            continue
        updates.append(
            equipment.copy_with(
                cooking=CookingTimer(food_id=food.id, started_by=agent_id)
            )
        )
    return after.replace_entity(*updates)


def _continue_cooking(
    environment: Environment,
    equipment_id: str,
    *,
    started_by: str | None,
) -> Environment:
    """Start a new timer when cooked food can cook again in the same station."""
    equipment = environment.get_entity_as(equipment_id, Equipment)
    state = environment.get_first_entity_of_type(OvercookedState)
    if equipment is None or state is None:
        return environment
    food = held_food(environment, equipment)
    if food is None or cook_output_name(environment, state, equipment, food) is None:
        return environment
    return environment.replace_entity(
        equipment.copy_with(
            cooking=CookingTimer(food_id=food.id, started_by=started_by)
        )
    )

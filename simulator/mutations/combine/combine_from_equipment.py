from __future__ import annotations

from typing import TYPE_CHECKING

from simulator.entities import Agent, Equipment, OvercookedState
from simulator.mutations.mutation import expected_matches

from .combine_equipment_into_equipment import combine_equipment_into_equipment
from .combine_facing_equipment_into_held_equipment import (
    combine_facing_equipment_into_held_equipment,
)
from .combine_food_into_held_equipment import combine_food_into_held_equipment
from .common import (
    get_facing_food,
    get_top_equipment_at,
    held_food,
)

if TYPE_CHECKING:
    from simulator.environment import Environment


def combine_from_equipment(
    environment: Environment,
    state: OvercookedState,
    agent: Agent,
    held_equipment: Equipment,
    target_x: int,
    target_y: int,
    *,
    expected_target_food_name: str | None,
    expected_target_equipment_name: str | None,
    expected_target_equipment_contents_name: str | None,
    expected_output_name: str | None,
) -> Environment | None:
    target_equipment = get_top_equipment_at(environment, target_x, target_y)
    if target_equipment:
        output_environment = place_equipment_on_equipment(
            environment,
            agent,
            held_equipment=held_equipment,
            target_equipment=target_equipment,
            expected_target_equipment_name=expected_target_equipment_name,
            expected_output_name=expected_output_name,
        )
        if output_environment:
            return output_environment

        output_environment = combine_equipment_into_equipment(
            environment,
            state,
            source_equipment=held_equipment,
            target_equipment=target_equipment,
            expected_target_equipment_name=expected_target_equipment_name,
            expected_target_equipment_contents_name=expected_target_equipment_contents_name,
            expected_output_name=expected_output_name,
        )
        if output_environment:
            return output_environment

        output_environment = combine_facing_equipment_into_held_equipment(
            environment,
            state,
            held_equipment=held_equipment,
            facing_equipment=target_equipment,
            expected_target_equipment_name=expected_target_equipment_name,
            expected_target_equipment_contents_name=expected_target_equipment_contents_name,
            expected_output_name=expected_output_name,
        )
        if output_environment:
            return output_environment

    facing_food = get_facing_food(environment, target_x, target_y)
    if not facing_food:
        return None

    target_food, counter = facing_food
    if not expected_matches(expected_target_food_name, target_food.name):
        return None
    return combine_food_into_held_equipment(
        environment,
        state,
        held_equipment=held_equipment,
        source_food=target_food,
        counter=counter,
        expected_output_name=expected_output_name,
    )


def place_equipment_on_equipment(
    environment: Environment,
    agent: Agent,
    *,
    held_equipment: Equipment,
    target_equipment: Equipment,
    expected_target_equipment_name: str | None,
    expected_output_name: str | None,
) -> Environment | None:
    if (
        not held_equipment.requires
        or held_equipment.requires != target_equipment.name
        or held_equipment.id == target_equipment.id
    ):
        return None
    if not expected_matches(expected_target_equipment_name, target_equipment.name):
        return None
    held_equipment_food = held_food(environment, held_equipment)
    output_name = held_equipment_food.name if held_equipment_food else None
    if not expected_matches(expected_output_name, output_name):
        return None

    updates = [
        agent.copy_with(held_item_id=None),
        held_equipment.copy_with(x=target_equipment.x, y=target_equipment.y),
    ]
    if held_equipment_food:
        updates.append(
            held_equipment_food.copy_with(x=target_equipment.x, y=target_equipment.y)
        )
    return environment.replace_entity(*updates)

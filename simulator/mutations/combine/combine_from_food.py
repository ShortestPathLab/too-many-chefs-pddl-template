from __future__ import annotations

from typing import TYPE_CHECKING

from simulator.entities import Agent, Food, OvercookedState
from simulator.mutations.mutation import expected_matches
from simulator.utils import required

from .combine_food_into_equipment import combine_food_into_equipment
from .combine_food_into_hand import combine_food_into_hand
from .common import get_equipments_at, get_facing_food

if TYPE_CHECKING:
    from simulator.entities import EntityModel
    from simulator.environment import Environment


def combine_from_food(
    environment: Environment,
    state: OvercookedState,
    agent: Agent,
    held_food: Food,
    target_x: int,
    target_y: int,
    *,
    expected_target_food_name: str | None,
    expected_target_equipment_name: str | None,
    expected_target_equipment_contents_name: str | None,
    expected_output_name: str | None,
) -> Environment | None:
    equipments = get_equipments_at(environment, target_x, target_y)
    for equipment in reversed(equipments):
        output_environment = combine_food_into_equipment(
            environment,
            state,
            held_food,
            equipment,
            on_success=[agent.copy_with(held_item_id=None)],
            expected_target_equipment_name=expected_target_equipment_name,
            expected_target_equipment_contents_name=expected_target_equipment_contents_name,
            expected_output_name=expected_output_name,
        )
        if output_environment:
            return output_environment
    for equipment in reversed(equipments):
        output_environment = combine_food_into_hand(
            environment,
            state,
            equipment,
            agent,
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
    output_name = state.resolve_combine_output(
        held_food.name,
        target_food.name,
        timestep=environment.timestep,
    )
    if not output_name:
        return None
    if not expected_matches(expected_target_food_name, target_food.name):
        return None
    if not expected_matches(expected_output_name, output_name):
        return None

    output_food = required(
        state.create_food(output_name, x=target_food.x, y=target_food.y),
        message=f"Missing food definition for {output_name}",
    )
    # Only raw food may be placed directly on a counter.
    if counter and not output_food.raw:
        return None

    environment = (
        environment.without_entity(held_food.id)
        .without_entity(target_food.id)
        .with_entity(output_food)
    )
    updates: list[EntityModel] = [agent.copy_with(held_item_id=None)]
    if counter:
        updates.append(counter.copy_with(held_item_id=output_food.id))
    return environment.replace_entity(*updates)

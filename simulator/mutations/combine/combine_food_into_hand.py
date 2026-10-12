from __future__ import annotations

from typing import TYPE_CHECKING

from simulator.entities import Agent, Equipment, Food, OvercookedState
from simulator.mutations.mutation import expected_matches
from simulator.utils import RequiredValueError, required

from .common import matches_equipment_expectations, resolve_output_name

if TYPE_CHECKING:
    from simulator.environment import Environment


def combine_food_into_hand(
    environment: Environment,
    state: OvercookedState,
    equipment: Equipment,
    agent: Agent,
    *,
    expected_target_equipment_name: str | None,
    expected_target_equipment_contents_name: str | None,
    expected_output_name: str | None,
) -> Environment | None:
    try:
        agent_held_item_id = required(agent.held_item_id)
        held_food = required(environment.get_entity_as(agent_held_item_id, Food))
        equipment_held_item_id = required(equipment.held_item_id)
        equipment_food = required(
            environment.get_entity_as(equipment_held_item_id, Food)
        )
        output_name = required(
            resolve_output_name(
                environment,
                state,
                incoming_food=equipment_food,
                existing_food=held_food,
            )
        )
        if not matches_equipment_expectations(
            equipment=equipment,
            expected_equipment_name=expected_target_equipment_name,
            expected_contents_name=expected_target_equipment_contents_name,
            contents_name=equipment_food.name,
        ):
            return None
        if not expected_matches(expected_output_name, output_name):
            return None
        output_food = required(
            state.create_food(output_name),
            message=f"Missing food definition for {output_name}",
        )

        if equipment_food:
            environment = environment.without_entity(equipment_food.id)
        return (
            environment.with_entity(output_food)
            .without_entity(equipment_held_item_id)
            .without_entity(agent_held_item_id)
            .replace_entity(
                agent.copy_with(held_item_id=output_food.id),
                equipment.copy_with(held_item_id=None),
            )
        )
    except RequiredValueError:
        return None

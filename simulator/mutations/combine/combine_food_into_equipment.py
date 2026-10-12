from __future__ import annotations

from typing import TYPE_CHECKING

from simulator.entities import Equipment, Food, OvercookedState
from simulator.mutations.mutation import expected_matches
from simulator.utils import required

from .common import matches_equipment_expectations, resolve_output_name

if TYPE_CHECKING:
    from simulator.entities import EntityModel
    from simulator.environment import Environment


def combine_food_into_equipment(
    environment: Environment,
    state: OvercookedState,
    incoming_food: Food,
    equipment: Equipment,
    *,
    on_success: list[EntityModel],
    expected_target_equipment_name: str | None,
    expected_target_equipment_contents_name: str | None,
    expected_output_name: str | None,
) -> Environment | None:
    existing_food = (
        environment.get_entity_as(equipment.held_item_id, Food)
        if equipment.held_item_id
        else None
    )
    output_name = resolve_output_name(
        environment,
        state,
        incoming_food=incoming_food,
        equipment=equipment,
        existing_food=existing_food,
    )
    if not output_name:
        return None
    if not matches_equipment_expectations(
        equipment=equipment,
        expected_equipment_name=expected_target_equipment_name,
        expected_contents_name=expected_target_equipment_contents_name,
        contents_name=existing_food.name if existing_food else None,
    ):
        return None
    if not expected_matches(expected_output_name, output_name):
        return None

    output_food = required(
        state.create_food(output_name, x=equipment.x, y=equipment.y),
        message=f"Missing food definition for {output_name}",
    )

    environment = environment.without_entity(incoming_food.id)
    if existing_food:
        environment = environment.without_entity(existing_food.id)
    return environment.with_entity(output_food).replace_entity(
        *on_success,
        equipment.copy_with(held_item_id=output_food.id),
    )

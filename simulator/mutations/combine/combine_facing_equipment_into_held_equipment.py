from __future__ import annotations

from typing import TYPE_CHECKING

from simulator.entities import Equipment, OvercookedState

from .combine_food_into_held_equipment import combine_food_into_held_equipment
from .common import held_food, matches_equipment_expectations

if TYPE_CHECKING:
    from simulator.environment import Environment


def combine_facing_equipment_into_held_equipment(
    environment: Environment,
    state: OvercookedState,
    *,
    held_equipment: Equipment,
    facing_equipment: Equipment,
    expected_target_equipment_name: str | None,
    expected_target_equipment_contents_name: str | None,
    expected_output_name: str | None,
) -> Environment | None:
    source_food = held_food(environment, facing_equipment)
    if not source_food:
        return None
    if not matches_equipment_expectations(
        equipment=facing_equipment,
        expected_equipment_name=expected_target_equipment_name,
        expected_contents_name=expected_target_equipment_contents_name,
        contents_name=source_food.name,
    ):
        return None

    output_environment = combine_food_into_held_equipment(
        environment,
        state,
        held_equipment=held_equipment,
        source_food=source_food,
        counter=None,
        expected_output_name=expected_output_name,
    )
    if not output_environment:
        return None
    return output_environment.replace_entity(
        facing_equipment.copy_with(held_item_id=None)
    )

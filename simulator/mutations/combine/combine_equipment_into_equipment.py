from __future__ import annotations

from typing import TYPE_CHECKING

from simulator.entities import Equipment, OvercookedState

from .combine_food_into_equipment import combine_food_into_equipment
from .common import held_food

if TYPE_CHECKING:
    from simulator.environment import Environment


def combine_equipment_into_equipment(
    environment: Environment,
    state: OvercookedState,
    *,
    source_equipment: Equipment,
    target_equipment: Equipment,
    expected_target_equipment_name: str | None,
    expected_target_equipment_contents_name: str | None,
    expected_output_name: str | None,
) -> Environment | None:
    incoming_food = held_food(environment, source_equipment)
    if not incoming_food:
        return None

    return combine_food_into_equipment(
        environment,
        state,
        incoming_food,
        target_equipment,
        # The chef keeps hold of the emptied equipment. Nothing else refers to
        # it while it is in hand, so letting go of it here would lose it.
        on_success=[source_equipment.copy_with(held_item_id=None)],
        expected_target_equipment_name=expected_target_equipment_name,
        expected_target_equipment_contents_name=expected_target_equipment_contents_name,
        expected_output_name=expected_output_name,
    )

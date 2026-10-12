from __future__ import annotations

from typing import TYPE_CHECKING

from simulator.entities import Counter, Equipment, Food, OvercookedState
from simulator.mutations.mutation import expected_matches
from simulator.utils import required

from .common import resolve_output_name

if TYPE_CHECKING:
    from simulator.environment import Environment


def combine_food_into_held_equipment(
    environment: Environment,
    state: OvercookedState,
    *,
    held_equipment: Equipment,
    source_food: Food,
    counter: Counter | None,
    expected_output_name: str | None,
) -> Environment | None:
    existing_food = (
        environment.get_entity_as(held_equipment.held_item_id, Food)
        if held_equipment.held_item_id
        else None
    )
    output_name = resolve_output_name(
        environment,
        state,
        incoming_food=source_food,
        equipment=held_equipment,
        existing_food=existing_food,
    )
    if not output_name:
        return None
    if not expected_matches(expected_output_name, output_name):
        return None

    output_food = required(
        state.create_food(output_name, x=None, y=None),
        message=f"Missing food definition for {output_name}",
    )

    if counter:
        environment = environment.replace_entity(counter.copy_with(held_item_id=None))
    environment = environment.without_entity(source_food.id)
    if existing_food:
        environment = environment.without_entity(existing_food.id)
    return environment.with_entity(output_food).replace_entity(
        held_equipment.copy_with(x=None, y=None, held_item_id=output_food.id)
    )

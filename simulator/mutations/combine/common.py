from __future__ import annotations

from typing import TYPE_CHECKING

from simulator.entities import (
    Counter,
    Equipment,
    Food,
    OvercookedState,
    Plate,
    get_first_game_object_of_type_at,
    get_game_objects_of_type_at,
)
from simulator.mutations.mutation import expected_matches

if TYPE_CHECKING:
    from simulator.environment import Environment


def get_top_equipment_at(environment: Environment, x: int, y: int) -> Equipment | None:
    equipment = get_game_objects_of_type_at(environment, x, y, Equipment)
    if not equipment:
        return None
    return equipment[-1]


def get_equipments_at(environment: Environment, x: int, y: int) -> list[Equipment]:
    return get_game_objects_of_type_at(environment, x, y, Equipment)


def get_counter_item(
    environment: Environment,
    x: int,
    y: int,
) -> tuple[Counter, Food | Equipment] | None:
    counter = get_first_game_object_of_type_at(environment, x, y, Counter)
    if not counter or not counter.held_item_id:
        return None

    item = environment.get_entity(counter.held_item_id)
    if isinstance(item, (Food, Equipment)):
        return (counter, item)
    return None


def get_facing_food(
    environment: Environment,
    x: int,
    y: int,
) -> tuple[Food, Counter | None] | None:
    counter_item = get_counter_item(environment, x, y)
    if counter_item:
        counter, item = counter_item
        if isinstance(item, Food):
            return (item, counter)

    if get_top_equipment_at(environment, x, y):
        return None

    food = get_first_game_object_of_type_at(environment, x, y, Food)
    if not food:
        return None
    return (food, None)


def can_put_in(
    environment: Environment,
    food: Food,
    equipment: Equipment,
) -> bool:
    if isinstance(equipment, Plate):
        # A used plate must be washed before it can hold another item.
        return not equipment.dirty
    state = environment.get_first_entity_of_type(OvercookedState)
    if not state:
        return False
    return state.equipment_accepts(food.name, equipment.name)


def resolve_output_name(
    environment: Environment,
    state: OvercookedState,
    *,
    incoming_food: Food,
    equipment: Equipment | None = None,
    existing_food: Food | None,
) -> str | None:
    if isinstance(equipment, Plate):
        if equipment.dirty:
            return None
        if not existing_food:
            return (
                incoming_food.name
                if can_put_in(environment, incoming_food, equipment)
                else None
            )
        return state.resolve_combine_output(
            incoming_food.name,
            existing_food.name,
            timestep=environment.timestep,
        )
    if not equipment and existing_food:
        return state.resolve_combine_output(
            incoming_food.name,
            existing_food.name,
            timestep=environment.timestep,
        )

    if not existing_food and equipment:
        return (
            incoming_food.name
            if can_put_in(environment, incoming_food, equipment)
            else None
        )

    output_name = (
        state.resolve_combine_output(
            incoming_food.name,
            existing_food.name,
            timestep=environment.timestep,
        )
        if existing_food
        else None
    )
    if not output_name:
        return None
    if equipment:
        return (
            output_name
            if state.equipment_accepts(output_name, equipment.name)
            else None
        )
    return None


def matches_equipment_expectations(
    *,
    equipment: Equipment,
    expected_equipment_name: str | None,
    expected_contents_name: str | None,
    contents_name: str | None,
) -> bool:
    return expected_matches(
        expected_equipment_name, equipment.name
    ) and expected_matches(
        expected_contents_name,
        contents_name,
    )


def held_food(environment: Environment, equipment: Equipment) -> Food | None:
    if not equipment.held_item_id:
        return None
    return environment.get_entity_as(equipment.held_item_id, Food)

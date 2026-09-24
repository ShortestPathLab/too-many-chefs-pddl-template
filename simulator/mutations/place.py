from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities import (
    Agent,
    Counter,
    Equipment,
    Food,
    get_first_game_object_of_type_at,
    get_game_objects_of_type_at,
)
from simulator.mutations.agent_mutation import AgentMutation
from simulator.mutations.mutation import IllegalMutationError, expected_matches
from simulator.mutations.virtual_input import VirtualInput

if TYPE_CHECKING:
    from simulator.environment import Environment


class Place(AgentMutation):
    kind: Literal["place"] = "place"

    def describe(self, environment: Environment) -> str:
        return f"{self.agent_id} places item"

    def virtual_input(self, environment: Environment) -> VirtualInput | None:
        return "b"

    def run(self, environment: Environment) -> Environment:
        agent = environment.get_entity_as(self.agent_id, Agent)
        if not agent or not agent.held_item_id:
            raise IllegalMutationError()

        target_x, target_y = agent.looking_at
        held_food = environment.get_entity_as(agent.held_item_id, Food)
        if held_food:
            if not expected_matches(self.expected_held_food, held_food.name):
                raise IllegalMutationError()
            placed_environment = _place_food(
                environment, agent, held_food, target_x, target_y
            )
            if placed_environment:
                return placed_environment
            raise IllegalMutationError()

        held_equipment = environment.get_entity_as(agent.held_item_id, Equipment)
        if held_equipment and held_equipment.portable:
            if not expected_matches(
                self.expected_held_equipment_name, held_equipment.name
            ):
                raise IllegalMutationError()
            held_food = _held_food(environment, held_equipment)
            if not expected_matches(
                self.expected_held_equipment_contents_name,
                held_food.name if held_food else None,
            ):
                raise IllegalMutationError()
            placed_environment = _place_equipment(
                environment, agent, held_equipment, target_x, target_y
            )
            if placed_environment:
                return placed_environment
            raise IllegalMutationError()

        raise IllegalMutationError()


def _place_food(
    environment: Environment,
    agent: Agent,
    held_food: Food,
    target_x: int,
    target_y: int,
) -> Environment | None:
    counter = get_first_game_object_of_type_at(environment, target_x, target_y, Counter)
    if counter and counter.empty(environment) and held_food.raw:
        return environment.replace_entity(
            agent.copy_with(held_item_id=None),
            counter.copy_with(held_item_id=held_food.id),
            held_food.copy_with(x=counter.x, y=counter.y),
        )

    return None


def _place_equipment(
    environment: Environment,
    agent: Agent,
    held_equipment: Equipment,
    target_x: int,
    target_y: int,
) -> Environment | None:
    counter = get_first_game_object_of_type_at(environment, target_x, target_y, Counter)
    if (
        counter
        and counter.empty(environment)
        and counter.x is not None
        and counter.y is not None
    ):
        return _place_equipment_entities(
            environment,
            agent,
            held_equipment,
            target_x=counter.x,
            target_y=counter.y,
            counter=counter,
        )

    if _can_place_on_required_support(environment, held_equipment, target_x, target_y):
        return _place_equipment_entities(
            environment,
            agent,
            held_equipment,
            target_x=target_x,
            target_y=target_y,
        )

    return None


def _place_equipment_entities(
    environment: Environment,
    agent: Agent,
    held_equipment: Equipment,
    *,
    target_x: int,
    target_y: int,
    counter: Counter | None = None,
) -> Environment:
    updates = [
        agent.copy_with(held_item_id=None),
        held_equipment.copy_with(x=target_x, y=target_y),
    ]
    if counter:
        updates.append(counter.copy_with(held_item_id=held_equipment.id))
    held_food = _held_food(environment, held_equipment)
    if held_food:
        updates.append(held_food.copy_with(x=target_x, y=target_y))
    return environment.replace_entity(*updates)


def _can_place_on_required_support(
    environment: Environment,
    held_equipment: Equipment,
    target_x: int,
    target_y: int,
) -> bool:
    if not held_equipment.requires:
        return False

    equipment = get_game_objects_of_type_at(environment, target_x, target_y, Equipment)
    if not equipment:
        return False

    top_equipment = equipment[-1]
    return (
        top_equipment.name == held_equipment.requires
        and top_equipment.id != held_equipment.id
    )


def _held_food(environment: Environment, equipment: Equipment) -> Food | None:
    if not equipment.held_item_id:
        return None
    return environment.get_entity_as(equipment.held_item_id, Food)

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities import (
    Agent,
    Equipment,
    Food,
)
from simulator.mutations.agent_mutation import AgentMutation
from simulator.mutations.combine import get_counter_item, get_top_equipment_at
from simulator.mutations.mutation import IllegalMutationError, expected_matches
from simulator.mutations.virtual_input import VirtualInput

if TYPE_CHECKING:
    from simulator.environment import Environment


class PickUp(AgentMutation):
    kind: Literal["pick_up"] = "pick_up"

    def describe(self, environment: Environment) -> str:
        return f"{self.agent_id} picks up item"

    def virtual_input(self, environment: Environment) -> VirtualInput | None:
        return "b"

    def run(self, environment: Environment) -> Environment:
        agent = environment.get_entity_as(self.agent_id, Agent)
        if not agent or not agent.hands_free:
            raise IllegalMutationError()

        target_x, target_y = agent.looking_at
        counter_item = get_counter_item(environment, target_x, target_y)
        if counter_item:
            counter, item = counter_item
            if isinstance(item, Equipment) and item.portable:
                if not expected_matches(self.expected_held_equipment_name, item.name):
                    raise IllegalMutationError()
                held_food = _get_held_food(environment, item)
                if not expected_matches(
                    self.expected_held_equipment_contents_name,
                    held_food.name if held_food else None,
                ):
                    raise IllegalMutationError()
                updates = [
                    agent.copy_with(held_item_id=item.id),
                    counter.copy_with(held_item_id=None),
                    item.copy_with(x=None, y=None),
                ]
                if held_food:
                    updates.append(held_food.copy_with(x=None, y=None))
                return environment.replace_entity(*updates)
            if isinstance(item, Food):
                if not expected_matches(self.expected_input_name, item.name):
                    raise IllegalMutationError()
                if not expected_matches(self.expected_output_name, item.name):
                    raise IllegalMutationError()
                return environment.replace_entity(
                    agent.copy_with(held_item_id=item.id),
                    counter.copy_with(held_item_id=None),
                    item.copy_with(x=None, y=None),
                )

        equipment = get_top_equipment_at(environment, target_x, target_y)
        if equipment and equipment.portable:
            if not expected_matches(self.expected_held_equipment_name, equipment.name):
                raise IllegalMutationError()
            held_food = _get_held_food(environment, equipment)
            if not expected_matches(
                self.expected_held_equipment_contents_name,
                held_food.name if held_food else None,
            ):
                raise IllegalMutationError()
            updates = [
                agent.copy_with(held_item_id=equipment.id),
                equipment.copy_with(x=None, y=None),
            ]
            if held_food:
                updates.append(held_food.copy_with(x=None, y=None))
            return environment.replace_entity(*updates)
        if equipment and equipment.held_item_id:
            item = environment.get_entity_as(equipment.held_item_id, Food)
            if not item:
                raise IllegalMutationError()
            if not expected_matches(self.expected_input_name, item.name):
                raise IllegalMutationError()
            if not expected_matches(self.expected_output_name, item.name):
                raise IllegalMutationError()
            return environment.replace_entity(
                agent.copy_with(held_item_id=item.id),
                equipment.copy_with(held_item_id=None),
                item.copy_with(x=None, y=None),
            )

        loose_food = _get_loose_food(environment, target_x, target_y)
        if loose_food:
            if not expected_matches(self.expected_input_name, loose_food.name):
                raise IllegalMutationError()
            if not expected_matches(self.expected_output_name, loose_food.name):
                raise IllegalMutationError()
            updated_agent = agent.copy_with(held_item_id=loose_food.id)
            return environment.replace_entity(
                updated_agent,
                loose_food.copy_with(x=None, y=None),
            )

        raise IllegalMutationError()


def _get_held_food(environment: Environment, equipment: Equipment) -> Food | None:
    if not equipment.held_item_id:
        return None
    return environment.get_entity_as(equipment.held_item_id, Food)


def _get_loose_food(environment: Environment, x: int, y: int) -> Food | None:
    equipment = get_top_equipment_at(environment, x, y)
    if equipment:
        return None

    counter_item = get_counter_item(environment, x, y)
    if counter_item:
        return None

    return next(
        (
            food
            for food in environment.get_entities_of_type(Food)
            if food.x == x and food.y == y
        ),
        None,
    )

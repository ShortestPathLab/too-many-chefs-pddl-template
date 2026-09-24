from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities import Agent, Equipment, Food
from simulator.mutations.agent_mutation import AgentMutation
from simulator.mutations.mutation import IllegalMutationError
from simulator.mutations.virtual_input import VirtualInput

if TYPE_CHECKING:
    from simulator.environment import Environment


class Discard(AgentMutation):
    kind: Literal["discard"] = "discard"

    def describe(self, environment: Environment) -> str:
        return f"{self.agent_id} discards held item"

    def virtual_input(self, environment: Environment) -> VirtualInput | None:
        return "a"

    def run(self, environment: Environment) -> Environment:
        agent = environment.get_entity_as(self.agent_id, Agent)
        if not agent or not agent.held_item_id:
            raise IllegalMutationError()

        held_food = environment.get_entity_as(agent.held_item_id, Food)
        if held_food:
            return environment.without_entity(held_food.id).replace_entity(
                agent.copy_with(held_item_id=None)
            )

        held_equipment = environment.get_entity_as(agent.held_item_id, Equipment)
        if not held_equipment or not held_equipment.held_item_id:
            raise IllegalMutationError()

        equipment_food = environment.get_entity_as(held_equipment.held_item_id, Food)
        if not equipment_food:
            raise IllegalMutationError()

        return environment.without_entity(equipment_food.id).replace_entity(
            held_equipment.copy_with(held_item_id=None)
        )

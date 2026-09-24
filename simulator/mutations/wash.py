from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities import (
    Agent,
    Plate,
    Sink,
    get_first_game_object_of_type_at,
)
from simulator.mutations.agent_mutation import AgentMutation
from simulator.mutations.mutation import IllegalMutationError, expected_matches
from simulator.mutations.virtual_input import VirtualInput

if TYPE_CHECKING:
    from simulator.environment import Environment


class Wash(AgentMutation):
    """Clean the held plate at the sink the agent is facing."""

    kind: Literal["wash"] = "wash"

    def describe(self, environment: Environment) -> str:
        return f"{self.agent_id} washes a plate"

    def virtual_input(self, environment: Environment) -> VirtualInput | None:
        return "a"

    def run(self, environment: Environment) -> Environment:
        agent = environment.get_entity_as(self.agent_id, Agent)
        if not agent or not agent.held_item_id:
            raise IllegalMutationError()

        target_x, target_y = agent.looking_at
        if not get_first_game_object_of_type_at(environment, target_x, target_y, Sink):
            raise IllegalMutationError()

        plate = environment.get_entity_as(agent.held_item_id, Plate)
        if not plate or not plate.dirty:
            raise IllegalMutationError()
        if not expected_matches(self.expected_held_equipment_name, plate.name):
            raise IllegalMutationError()

        return environment.replace_entity(plate.copy_with(dirty=False))

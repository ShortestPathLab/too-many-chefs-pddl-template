from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities import Agent, Orientation
from simulator.mutations.agent_mutation import AgentMutation
from simulator.mutations.mutation import IllegalMutationError
from simulator.mutations.virtual_input import ORIENTATION_INPUTS, VirtualInput

if TYPE_CHECKING:
    from simulator.environment import Environment


class TurnAgent(AgentMutation):
    kind: Literal["turn_agent"] = "turn_agent"
    orientation: Orientation

    def describe(self, environment: Environment) -> str:
        return f"{self.agent_id} faces {self.orientation.upper()}"

    def virtual_input(self, environment: Environment) -> VirtualInput | None:
        return ORIENTATION_INPUTS.get(self.orientation)

    def run(self, environment: Environment) -> Environment:
        agent = environment.get_entity_as(self.agent_id, Agent)
        if not agent:
            raise IllegalMutationError()

        return environment.replace_entity(agent.copy_with(orientation=self.orientation))

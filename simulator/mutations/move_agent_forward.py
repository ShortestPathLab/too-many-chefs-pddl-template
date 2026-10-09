from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities import ORIENTATION_DELTAS, Agent
from simulator.mutations.agent_mutation import AgentMutation
from simulator.mutations.move_agent import MoveAgent
from simulator.mutations.mutation import IllegalMutationError
from simulator.mutations.virtual_input import ORIENTATION_INPUTS, VirtualInput

if TYPE_CHECKING:
    from simulator.environment import Environment


class MoveAgentForward(AgentMutation):
    kind: Literal["move_agent_forward"] = "move_agent_forward"

    def describe(self, environment: Environment) -> str:
        return f"{self.agent_id} steps forwards"

    def virtual_input(self, environment: Environment) -> VirtualInput | None:
        # Read the direction from the agent.
        agent = environment.get_entity_as(self.agent_id, Agent)
        if agent is None:
            return None
        return ORIENTATION_INPUTS.get(agent.orientation)

    def run(self, environment: Environment) -> Environment:
        agent = environment.get_entity_as(self.agent_id, Agent)
        if not agent:
            raise IllegalMutationError()

        dx, dy = ORIENTATION_DELTAS[agent.orientation]
        return MoveAgent(agent_id=self.agent_id, dx=dx, dy=dy).run(environment)

"""Controllers that take exactly one step, for exercising the run loop."""

from __future__ import annotations

from simulator.context import Context
from simulator.controller import Controller
from simulator.entities import Agent
from simulator.environment import Environment
from simulator.mutations import MoveAgentForward, Mutation

# One chef with a clear tile ahead.
AGENT_LEVEL = {
    "layout": "|A|\n| |",
    "legend": {
        "agents": [{"kind": "agent", "symbol": "A"}],
        "foods": [{"kind": "food", "name": "catalog/food/tomato"}],
    },
}


class StepOnceController(Controller):
    def __init__(self) -> None:
        self._has_stepped = False

    def get_actions(self, environment: Environment, context: Context) -> list[Mutation]:
        if self._has_stepped:
            return []

        agent = environment.get_first_entity_of_type(Agent)
        if not agent:
            return []

        self._has_stepped = True
        return [MoveAgentForward(agent_id=agent.id)]

    def is_busy(self) -> bool:
        return False

    def shutdown(self) -> None:
        pass


class NeverFinishedController(Controller):
    """Walk forever without reporting completion."""

    def get_actions(self, environment: Environment, context: Context) -> list[Mutation]:
        agent = environment.get_first_entity_of_type(Agent)
        if agent is None:
            return []
        return [MoveAgentForward(agent_id=agent.id)]

    def is_busy(self) -> bool:
        return False

    def has_finished(self, environment: Environment) -> bool:
        return False

    def shutdown(self) -> None:
        pass


class TemporarilyIdleController(StepOnceController):
    """Return no actions on the first tick."""

    def __init__(self) -> None:
        super().__init__()
        self._calls = 0

    def get_actions(self, environment: Environment, context: Context) -> list[Mutation]:
        self._calls += 1
        if self._calls == 1:
            return []
        return super().get_actions(environment, context)

    def has_finished(self, environment: Environment) -> bool:
        return self._has_stepped

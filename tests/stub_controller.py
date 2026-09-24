from __future__ import annotations

from simulator.context import Context
from simulator.controller import Controller
from simulator.environment import Environment
from simulator.mutations import Mutation


class StubController(Controller):
    """Controller stub with configurable status and no actions."""

    def __init__(
        self,
        *,
        busy: bool = False,
        finished: bool = False,
        progress: tuple[int, int] | None = None,
    ):
        self._busy = busy
        self._finished = finished
        self._progress = progress

    def get_actions(self, environment: Environment, context: Context) -> list[Mutation]:
        return []

    def is_busy(self) -> bool:
        return self._busy

    def has_finished(self, environment: Environment) -> bool:
        return self._finished

    def plan_progress(self, agent_id: str | None = None) -> tuple[int, int] | None:
        return self._progress

    def shutdown(self) -> None:
        return None

"""Track and enforce controller planning budgets."""

from __future__ import annotations

import time
from collections.abc import Callable, Collection

from simulator.context import Context
from simulator.controller import Controller
from simulator.environment import Environment
from simulator.mutations import Mutation

# Injected so tests can control the clock.
Now = Callable[[], float]


class PlanningClock:
    """Track one controller's planning time.

    Charge time spent in ``get_actions`` and in background workers started by
    that call.

    A budget belongs to the controller, not to an individual agent.
    """

    def __init__(
        self,
        budget_seconds: float | None,
        *,
        now: Now = time.monotonic,
    ) -> None:
        self.budget_seconds = budget_seconds
        self._now = now
        self._spent_seconds = 0.0
        self._thinking_since: float | None = None

    @property
    def limited(self) -> bool:
        """Return whether a finite budget is configured."""
        return self.budget_seconds is not None

    @property
    def thinking(self) -> bool:
        return self._thinking_since is not None

    @property
    def spent_seconds(self) -> float:
        """Return time charged so far, including the current interval."""
        if self._thinking_since is None:
            return self._spent_seconds
        return self._spent_seconds + max(0.0, self._now() - self._thinking_since)

    @property
    def remaining_seconds(self) -> float | None:
        if self.budget_seconds is None:
            return None
        return max(0.0, self.budget_seconds - self.spent_seconds)

    @property
    def exhausted(self) -> bool:
        remaining = self.remaining_seconds
        return remaining is not None and remaining <= 0.0

    def start_thinking(self) -> None:
        """Start timing if the clock is not already running."""
        if self._thinking_since is None:
            self._thinking_since = self._now()

    def stop_thinking(self) -> None:
        """Stop timing and charge the current interval."""
        if self._thinking_since is None:
            return
        self._spent_seconds += max(0.0, self._now() - self._thinking_since)
        self._thinking_since = None


class BudgetedController(Controller):
    """Wrap a controller with a planning budget.

    The wrapper exposes the wrapped controller to the run loop, composite
    controller, and agent inspector. The budget applies to one wrapped
    controller, even when it controls several agents.

    Exhaustion is checked before each call. A call that starts with time left may
    still return its action after the budget expires.
    """

    def __init__(
        self,
        controller: Controller,
        *,
        budget_seconds: float | None,
        now: Now = time.monotonic,
    ) -> None:
        self._controller = controller
        self._clock = PlanningClock(budget_seconds, now=now)

    @property
    def planning_clock(self) -> PlanningClock:
        return self._clock

    @property
    def label(self) -> str:
        return self._controller.label

    def set_controlled_agents(self, agent_ids: Collection[str] | None) -> None:
        super().set_controlled_agents(agent_ids)
        self._controller.set_controlled_agents(agent_ids)

    def get_actions(self, environment: Environment, context: Context) -> list[Mutation]:
        if self._clock.exhausted:
            self._clock.stop_thinking()
            return []

        self._clock.start_thinking()
        try:
            return self._controller.get_actions(environment, context)
        finally:
            # Keep charging while background workers are still running.
            if not self._controller.is_busy():
                self._clock.stop_thinking()

    def is_busy(self) -> bool:
        return self._controller.is_busy()

    def has_finished(self, environment: Environment) -> bool:
        return self._controller.has_finished(environment)

    def plan_progress(self, agent_id: str | None = None) -> tuple[int, int] | None:
        return self._controller.plan_progress(agent_id)

    def child_controllers(self) -> list[Controller]:
        return self._controller.child_controllers()

    def nested_controllers(self) -> list[Controller]:
        return [self._controller]

    def shutdown(self) -> None:
        self._clock.stop_thinking()
        self._controller.shutdown()


def planning_clocks(controller: Controller | None) -> list[PlanningClock]:
    """Return all planning clocks under ``controller``."""
    if controller is None:
        return []
    clocks = [controller.planning_clock] if controller.planning_clock else []
    for child in controller.child_controllers():
        clocks.extend(planning_clocks(child))
    return clocks


def all_budgets_exhausted(controller: Controller | None) -> bool:
    """Return whether every finite planning budget is exhausted.

    Return ``False`` when no finite budgets are configured.
    """
    limited = [clock for clock in planning_clocks(controller) if clock.limited]
    return bool(limited) and all(clock.exhausted for clock in limited)

"""Build controller status data for the agent panel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from simulator.environment import Environment
from simulator.models import FrozenSimulatorModel

if TYPE_CHECKING:
    from simulator.controller import Controller


class ControllerView(FrozenSimulatorModel):
    """Controller status shown in the agent panel.

    Plan fields appear when a controller reports progress. Budget fields appear
    when the run configured a planning clock.
    """

    label: str = "Manual"
    busy: bool = False
    finished: bool = False
    plan_done: int | None = None
    plan_total: int | None = None
    budget_seconds: float | None = None
    budget_remaining_seconds: float | None = None

    @property
    def executing(self) -> bool:
        """Return whether the controller is executing a plan."""
        return bool(self.plan_total) and (self.plan_done or 0) < (self.plan_total or 0)

    @property
    def out_of_time(self) -> bool:
        """Return whether this controller has exhausted its planning budget."""
        return (
            self.budget_seconds is not None
            and (self.budget_remaining_seconds or 0.0) <= 0.0
        )

    @property
    def active(self) -> bool:
        return (self.busy or self.executing) and not self.out_of_time

    @property
    def status_label(self) -> str:
        # Planning and execution are separate states.
        if self.out_of_time:
            return "Out of time"
        if self.finished:
            return "Finished"
        if self.busy:
            return "Planning"
        if self.executing:
            return "Executing"
        return "Idle"

    @property
    def progress(self) -> float | None:
        if not self.plan_total:
            return None
        return min(1.0, max(0.0, (self.plan_done or 0) / self.plan_total))

    @property
    def budget_progress(self) -> float | None:
        """Return the remaining planning budget as a fraction."""
        if self.budget_seconds is None:
            return None
        # A zero-second budget is still a configured budget.
        if not self.budget_seconds:
            return 0.0
        remaining = self.budget_remaining_seconds or 0.0
        return min(1.0, max(0.0, remaining / self.budget_seconds))

    @property
    def budget_label(self) -> str:
        """Return remaining and total budget as text."""
        if self.budget_seconds is None:
            return ""
        remaining = self.budget_remaining_seconds or 0.0
        return f"{remaining:.1f}s / {self.budget_seconds:g}s"


def controller_view(
    controller: Controller | None,
    agent_id: str,
    environment: Environment,
) -> ControllerView | None:
    owner = controller_for_agent(controller, agent_id)
    if owner is None:
        return None

    progress = owner.plan_progress(agent_id)
    clock = owner.planning_clock
    return ControllerView(
        label=owner.label,
        busy=owner.is_busy(),
        finished=owner.has_finished(environment),
        plan_done=progress[0] if progress else None,
        plan_total=progress[1] if progress else None,
        budget_seconds=clock.budget_seconds if clock else None,
        budget_remaining_seconds=clock.remaining_seconds if clock else None,
    )


def controller_for_agent(
    controller: Controller | None,
    agent_id: str,
) -> Controller | None:
    """Return the leaf controller that owns ``agent_id``.

    Check child controllers first because a composite may claim all agents.
    """
    if controller is None:
        return None
    for child in controller.child_controllers():
        found = controller_for_agent(child, agent_id)
        if found is not None:
            return found
    return controller if controller.controls_agent(agent_id) else None

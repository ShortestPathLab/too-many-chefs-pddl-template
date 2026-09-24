from __future__ import annotations

from collections.abc import Sequence
from traceback import format_exception
from typing import Literal

from pydantic import Field

from simulator.entities import Agent, OvercookedState, badge_order, team_scores
from simulator.environment import Environment
from simulator.models import SimulatorModel

from .reason import TerminationReason
from .setup import RunSetup

#: When the exception came. ``import`` means the controller's code would not
#: import, ``build`` that the controller raised while it was built, and ``run``
#: that it raised once the run had started.
ErrorStage = Literal["import", "build", "run"]


class RunError(SimulatorModel):
    """The exception that ended a run."""

    stage: ErrorStage = "run"
    #: The exception's class name, such as ``AgentDeadlockError``.
    type: str
    message: str
    #: The whole traceback. For an exception raised in a planning worker, it
    #: includes the worker's own traceback as well.
    traceback: str

    @classmethod
    def from_exception(
        cls, error: BaseException, *, stage: ErrorStage = "run"
    ) -> RunError:
        return cls(
            stage=stage,
            type=type(error).__name__,
            message=str(error),
            traceback="".join(format_exception(error)),
        )


class SimulationResult(SimulatorModel):
    """Machine-readable summary of a finished run.

    ``run`` says what the run was asked to do and the rest says what came of
    it. ``reason`` identifies why the run ended, including whether a controller
    stopped with orders still pending. ``error`` is set when the reason is
    ``error``.
    """

    # Empty for a run started in code rather than from the command line.
    run: RunSetup | None = None
    reason: TerminationReason
    score: int
    # Every chef in badge order, including chefs with no score.
    score_by_agent: dict[str, int] = Field(default_factory=dict)
    # Scores grouped by team. Empty when the kitchen has no teams.
    score_by_team: dict[str, int] = Field(default_factory=dict)
    timesteps: int
    orders_delivered: int
    orders_remaining: int
    elapsed_seconds: float
    error: RunError | None = None


def build_simulation_result(
    environment: Environment,
    *,
    reason: TerminationReason,
    elapsed_seconds: float,
    agent_order: Sequence[str] | None = None,
    setup: RunSetup | None = None,
    error: RunError | None = None,
) -> SimulationResult:
    """Build a result from the finished environment.

    ``agent_order`` preserves the badge order from run start. Without it, use
    the order in the finished environment. ``setup`` describes the run that
    produced this result, and ``error`` describes the exception that ended it.
    """
    state = environment.get_first_entity_of_type(OvercookedState)
    order_queue = state.order_queue if state is not None else None
    order = (
        list(agent_order)
        if agent_order is not None
        else [agent.id for agent in badge_order(environment)]
    )
    return SimulationResult(
        run=setup,
        reason=reason,
        score=state.score if state is not None else 0,
        score_by_agent={
            agent_id: state.score_for(agent_id) if state is not None else 0
            for agent_id in order
        },
        score_by_team=(
            team_scores(state.scoring, environment.get_entities_of_type(Agent))
            if state is not None
            else {}
        ),
        timesteps=environment.timestep,
        orders_delivered=order_queue.delivered_count if order_queue else 0,
        orders_remaining=(
            len(order_queue.visible) + len(order_queue.pending) if order_queue else 0
        ),
        elapsed_seconds=round(elapsed_seconds, 3),
        error=error,
    )

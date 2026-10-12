"""A finished run, said in words over the numbers it finished with."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import Field

from simulator.models import FrozenSimulatorModel
from simulator.view.teams import TeamScore, to_teams_view

if TYPE_CHECKING:
    from simulator.run.result import SimulationResult, TerminationReason

# Summary text for each termination reason.
ENDINGS: dict[str, tuple[str, str]] = {
    "completed": ("Service over", "The controller had nothing left to do."),
    "gave_up": (
        "Orders left standing",
        "The controller stopped with tickets still on the rail.",
    ),
    "orders_delivered": ("Every order served", "The last ticket on the rail went out."),
    "time_limit": ("Time up", "The run reached its wall-clock limit."),
    "max_timesteps": ("Service over", "The kitchen reached its last timestep."),
    "planning_budget_exhausted": (
        "Out of planning time",
        "Every controller spent its planning budget.",
    ),
    "stopped": ("Kitchen closed", "The run ended before any condition was met."),
    "error": ("Kitchen on fire", "A controller raised an error."),
}


class AgentScore(FrozenSimulatorModel):
    """One chef's share of the takings, under the number their badge shows."""

    number: int
    agent_id: str
    score: int


class SummaryView(FrozenSimulatorModel):
    """What the card at the end of a run shows."""

    headline: str = "Service over"
    reason_label: str = ""
    reason: str = "stopped"
    score: int = 0
    agents: list[AgentScore] = Field(default_factory=list)
    teams: list[TeamScore] = Field(default_factory=list)
    # Empty for an unassigned run or a draw.
    leader: str = ""
    timesteps: int = 0
    delivered: int = 0
    remaining: int = 0
    elapsed_seconds: float = 0.0

    @property
    def elapsed_label(self) -> str:
        return f"{self.elapsed_seconds:.1f}s"

    @property
    def split_worth_showing(self) -> bool:
        """Return whether the card should show per-agent scores."""
        return len(self.agents) > 1

    @property
    def contested(self) -> bool:
        """Return whether the run has multiple teams."""
        return len(self.teams) > 1

    @property
    def winner(self) -> TeamScore | None:
        """The side that took the most, or nothing on a draw."""
        return next((team for team in self.teams if team.name == self.leader), None)

    @property
    def verdict(self) -> str:
        """How a contested run is called, in the words the card uses."""
        if not self.contested:
            return ""
        winner = self.winner
        return f"{winner.label} wins" if winner is not None else "Draw"

    @property
    def served_everything(self) -> bool:
        """Return whether at least one order was delivered and none remain."""
        return self.remaining == 0 and self.delivered > 0


def summary_view(result: SimulationResult) -> SummaryView:
    headline, reason_label = ending_words(result.reason)
    if result.error is not None:
        # The first line says what went wrong; the JSON has the traceback.
        first_line = next(iter(result.error.message.splitlines()), "")
        reason_label = f"{result.error.type}: {first_line}".rstrip(": ")
    sides = to_teams_view(result.score_by_team)
    return SummaryView(
        headline=headline,
        reason_label=reason_label,
        reason=result.reason,
        score=result.score,
        agents=[
            AgentScore(number=number, agent_id=agent_id, score=score)
            for number, (agent_id, score) in enumerate(
                result.score_by_agent.items(), start=1
            )
        ],
        teams=sides.teams,
        leader=sides.leader or "",
        timesteps=result.timesteps,
        delivered=result.orders_delivered,
        remaining=result.orders_remaining,
        elapsed_seconds=result.elapsed_seconds,
    )


def ending_words(reason: TerminationReason | str) -> tuple[str, str]:
    return ENDINGS.get(reason, ENDINGS["stopped"])

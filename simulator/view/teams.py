"""Build team score data for the HUD."""

from __future__ import annotations

from pydantic import Field

from simulator.entities import Agent, OvercookedState, team_label, team_scores
from simulator.environment import Environment
from simulator.models import FrozenSimulatorModel


class TeamScore(FrozenSimulatorModel):
    """Score for one team."""

    name: str
    label: str
    score: int


class TeamsView(FrozenSimulatorModel):
    teams: list[TeamScore] = Field(default_factory=list)

    @property
    def split(self) -> bool:
        """Return whether the view contains a contest between teams."""
        return len(self.teams) > 1

    @property
    def leader(self) -> str | None:
        """Return the leading team, or ``None`` for a draw."""
        if not self.split:
            return None
        ranked = sorted(self.teams, key=lambda team: team.score, reverse=True)
        if ranked[0].score == ranked[1].score:
            return None
        return ranked[0].name


def teams_view(environment: Environment) -> TeamsView:
    state = environment.get_first_entity_of_type(OvercookedState)
    if state is None:
        return TeamsView()
    return to_teams_view(
        team_scores(state.scoring, environment.get_entities_of_type(Agent))
    )


def to_teams_view(scores: dict[str, int]) -> TeamsView:
    """Build a team view from team totals."""
    return TeamsView(
        teams=[
            TeamScore(name=name, label=team_label(name), score=score)
            for name, score in scores.items()
        ]
    )

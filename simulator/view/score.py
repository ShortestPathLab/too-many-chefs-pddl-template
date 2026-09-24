"""Build score data for the HUD."""

from __future__ import annotations

from pydantic import Field

from simulator.entities import OvercookedState
from simulator.environment import Environment
from simulator.models import FrozenSimulatorModel
from simulator.view.teams import TeamScore, teams_view


class ScoreView(FrozenSimulatorModel):
    score: int = 0
    delivered: int = 0
    outstanding: int = 0
    # Team totals. Empty when the kitchen has no teams.
    teams: list[TeamScore] = Field(default_factory=list)


def score_view(environment: Environment) -> ScoreView:
    state = environment.get_first_entity_of_type(OvercookedState)
    if state is None:
        return ScoreView()
    return ScoreView(
        score=state.score,
        delivered=state.order_queue.delivered_count,
        outstanding=len(state.order_queue.visible) + len(state.order_queue.pending),
        teams=teams_view(environment).teams,
    )

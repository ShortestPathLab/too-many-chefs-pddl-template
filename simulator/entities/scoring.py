"""Track kitchen and per-agent scores."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import Field

from simulator.models import FrozenSimulatorModel


class ScoringState(FrozenSimulatorModel):
    retrieve_order_component_reward: int = Field(default=1, ge=0)
    produce_order_component_reward: int = Field(default=1, ge=0)
    produce_ordered_item_reward: int = Field(default=1, ge=0)
    score: int = Field(default=0, ge=0)
    # Score contributions by agent. Team totals are derived from this ledger.
    score_by_agent: dict[str, int] = Field(default_factory=dict)

    def rewarded(self, reward: int, *, agent_id: str | None = None) -> ScoringState:
        """Add a reward to the total and, when provided, to an agent."""
        if reward == 0:
            return self
        if agent_id is None:
            return self.copy_with(score=self.score + reward)
        return self.copy_with(
            score=self.score + reward,
            score_by_agent={
                **self.score_by_agent,
                agent_id: self.score_for(agent_id) + reward,
            },
        )

    def score_for(self, agent_id: str) -> int:
        return self.score_by_agent.get(agent_id, 0)

    def total_for(self, agent_ids: Iterable[str]) -> int:
        """Return the combined score for a group of agents."""
        return sum(self.score_for(agent_id) for agent_id in agent_ids)

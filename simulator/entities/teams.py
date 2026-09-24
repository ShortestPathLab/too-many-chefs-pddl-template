"""Resolve team rosters and team scores.

Teams affect score grouping only. They do not change kitchen rules or recipes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from simulator.entities.agent import Agent
from simulator.entities.scoring import ScoringState

if TYPE_CHECKING:
    from simulator.environment import Environment

# Standard team names, in display order.
TEAM_NAMES: tuple[str, ...] = ("red", "blue", "green", "yellow", "purple", "orange")


def team_label(name: str) -> str:
    """Return the display label for a team."""
    return f"Team {name.replace('_', ' ').title()}"


def resolve_rosters(
    agents: Sequence[Agent],
    rosters: Mapping[str, Sequence[str]],
) -> dict[str, str]:
    """Resolve roster tokens to agent ids.

    Tokens may be agent ids or badge numbers. Badge numbers refer to the order
    in ``agents``.

    An exact agent id takes precedence over a badge number.
    """
    numbers = [str(number) for number in range(1, len(agents) + 1)]
    by_token: dict[str, str] = dict(zip(numbers, (agent.id for agent in agents)))
    by_token.update({agent.id: agent.id for agent in agents})

    team_of: dict[str, str] = {}
    # Preserve the original roster token for duplicate-team errors.
    claimed_as: dict[str, str] = {}
    for name, tokens in rosters.items():
        for token in tokens:
            agent_id = by_token.get(str(token))
            if agent_id is None:
                raise ValueError(
                    f"Team {name!r} names unknown agent {str(token)!r}."
                    f" This level has {len(agents)} chefs, numbered"
                    f" {', '.join(numbers) or 'none'}."
                )
            if agent_id in team_of:
                already = claimed_as[agent_id]
                seen = repr(team_of[agent_id])
                if already != str(token):
                    seen = f"{seen} as {already!r}"
                raise ValueError(
                    f"Chef {str(token)!r} is on more than one team:"
                    f" {seen} and {name!r}."
                )
            team_of[agent_id] = name
            claimed_as[agent_id] = str(token)
    return team_of


def team_of(environment: Environment, agent_id: str | None) -> str | None:
    """Return the team of the chef with ``agent_id``, if it has one."""
    if agent_id is None:
        return None
    agent = environment.get_entity_as(agent_id, Agent)
    return agent.team if agent is not None else None


def team_rosters(agents: Sequence[Agent]) -> dict[str, list[str]]:
    """Return team rosters in agent order."""
    rosters: dict[str, list[str]] = {}
    for agent in agents:
        if agent.team is None:
            continue
        rosters.setdefault(agent.team, []).append(agent.id)
    return rosters


def team_scores(scoring: ScoringState, agents: Sequence[Agent]) -> dict[str, int]:
    """Return scores grouped by team."""
    return {
        name: scoring.total_for(agent_ids)
        for name, agent_ids in team_rosters(agents).items()
    }

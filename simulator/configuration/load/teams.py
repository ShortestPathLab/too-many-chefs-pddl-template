"""Apply configured team rosters to agents."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from simulator.entities import Agent, badge_order, resolve_rosters
from simulator.environment import Environment


def assign_teams(
    environment: Environment,
    rosters: Mapping[str, Sequence[str]],
) -> Environment:
    """Assign each roster's team to its agents.

    Resolve roster tokens against the loaded agents. Unknown agents raise an
    error instead of being ignored.
    """
    if not rosters:
        return environment

    team_of = resolve_rosters(badge_order(environment), rosters)
    for agent in environment.get_entities_of_type(Agent):
        team = team_of.get(agent.id)
        if team is not None:
            environment = environment.replace_entity(agent.copy_with(team=team))
    return environment

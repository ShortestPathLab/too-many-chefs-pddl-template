"""Build team rosters from the command line."""

from __future__ import annotations

import typer

from cli.assignments import parse_assignment
from simulator.configuration import Configuration, load
from simulator.entities import TEAM_NAMES, badge_order, resolve_rosters


def with_teams(configuration: Configuration, *, teams: list[str]) -> Configuration:
    """Apply repeated ``--team`` options to a level configuration.

    Team rosters and controller assignments are independent. A controller can
    own more than one team, and a team can use more than one controller.

    If no teams are supplied, the rosters in the level are kept. Supplying one
    or more teams replaces all rosters from the level.
    """
    if not teams:
        return configuration

    rosters: dict[str, list[str]] = {}
    for spec in teams:
        team_name, tokens = parse_assignment(spec, param_hint="--team", subject="team")
        rosters.setdefault(team_name, []).extend(tokens)

    # Validate the names here so errors identify --team instead of surfacing
    # later while the run loads.
    try:
        resolve_rosters(badge_order(load(configuration)), rosters)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="--team") from None

    return configuration.copy_with(teams=rosters)


def teams_help() -> str:
    return (
        "Assign agents to a team, for example --team red=1 --team blue=2."
        " Use badge numbers or names defined by the level. Repeatable; agents"
        " omitted from every --team are on no side."
        f" Known team colours: {', '.join(TEAM_NAMES)}."
    )

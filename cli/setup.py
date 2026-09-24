"""Describe the run behind a result."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from simulator.configuration import Configuration
from simulator.run import ControllerAssignment, EndConditions, RunSetup


def describe_run(
    configuration: Configuration,
    controllers: Sequence[ControllerAssignment],
    *,
    level: Path,
    end_conditions: EndConditions,
    headless: bool,
    planning_budget: float | None,
) -> RunSetup:
    """Describe a run for the result it will produce.

    Everything here is settled before the first timestep, so a result file can
    say what produced it as well as what came of it. ``controllers`` comes from
    building the run, details included.
    """
    return RunSetup(
        level=str(level),
        controllers=list(controllers),
        teams=dict(configuration.teams),
        headless=headless,
        planning_budget_seconds=planning_budget,
        end_conditions=end_conditions,
    )

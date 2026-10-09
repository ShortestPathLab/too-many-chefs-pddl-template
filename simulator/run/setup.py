"""What a run was asked to do, recorded beside what it did."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from simulator.models import FrozenSimulatorModel

from .end_conditions import EndConditions


class ControllerAssignment(FrozenSimulatorModel):
    """A controller in the run, and the chefs it was given.

    An empty ``agents`` list means the controller took every chef no other
    controller claimed, which without ``--assign`` is the whole kitchen.
    ``details`` is whatever the controller's plugin chose to record, such as
    the planner a PDDL controller plans with.
    """

    controller: str
    agents: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class RunSetup(FrozenSimulatorModel):
    """The level, the controllers, and the limits a run started with.

    A result carries this so a reader can tell two runs apart without the
    command line that produced them.
    """

    #: The level file, as it was named on the command line.
    level: str = ""
    controllers: list[ControllerAssignment] = Field(default_factory=list)
    #: Chefs by side. Empty when the kitchen has no teams.
    teams: dict[str, list[str]] = Field(default_factory=dict)
    headless: bool = False
    #: Planning time each controller was given for the whole run.
    planning_budget_seconds: float | None = None
    end_conditions: EndConditions = Field(default_factory=EndConditions)

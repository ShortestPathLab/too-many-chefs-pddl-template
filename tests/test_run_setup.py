"""Test the run description carried by a result."""

from __future__ import annotations

from pathlib import Path

import pytest

from cli.assignments import build_agent_controller, controller_assignments
from cli.setup import describe_run
from controllers.pddl import PDDLOptions
from controllers.pddl.solvers import available_solvers, solver_type
from simulator.configuration.configuration import Configuration
from simulator.run import (
    ControllerAssignment,
    EndConditions,
    RunSetup,
    SimulationResult,
    run_agent_mode,
)
from tests.run_controllers import AGENT_LEVEL, StepOnceController


def test_a_result_says_nothing_about_a_run_nobody_described() -> None:
    """A run started from code carries no command line to report."""
    assert _run(setup=None).run is None


def test_a_result_carries_the_run_that_produced_it() -> None:
    setup = RunSetup(
        level="levels/demos/burger.yaml",
        controllers=[
            ControllerAssignment(controller="pddl", details={"solver": "pyperplan"})
        ],
    )

    result = _run(setup=setup)

    assert result.run == setup
    assert '"solver":"pyperplan"' in result.to_json()


def test_the_default_controller_owns_a_kitchen_nobody_carved_up() -> None:
    described = controller_assignments(
        _two_chef_configuration(),
        default_controller="open",
        assignments=[],
    )

    assert [(entry.controller, entry.agents) for entry in described] == [("open", [])]


def test_the_default_controller_picks_up_the_chefs_assign_left_over() -> None:
    described = controller_assignments(
        _two_chef_configuration(),
        default_controller="pddl",
        assignments=["open=alfred"],
    )

    assert [(entry.controller, entry.agents) for entry in described] == [
        ("open", ["alfred"]),
        ("pddl", []),
    ]


def test_a_fully_assigned_kitchen_leaves_the_default_controller_out() -> None:
    described = controller_assignments(
        _two_chef_configuration(),
        default_controller="pddl",
        assignments=["open=alfred,bob"],
    )

    assert [entry.controller for entry in described] == ["open"]


def test_a_run_that_never_plans_names_no_solver() -> None:
    run = build_agent_controller(
        _two_chef_configuration(),
        default_controller="open",
        assignments=[],
    )
    try:
        assert _details(run.assignments) == [("open", {})]
    finally:
        run.controller.shutdown()


def test_a_named_solver_is_reported_as_the_one_that_was_asked_for() -> None:
    name = _an_installed_solver()
    run = build_agent_controller(
        _two_chef_configuration(),
        default_controller="pddl",
        assignments=[],
        options={"pddl": PDDLOptions(solver=name)},
    )
    try:
        assert _details(run.assignments) == [
            ("pddl", {"solver": name, "solver_selection": "named"})
        ]
    finally:
        run.controller.shutdown()


def test_an_omitted_solver_is_reported_as_the_one_the_run_will_reach_for() -> None:
    """The run resolves the same way its planning workers do."""
    _an_installed_solver()
    run = build_agent_controller(
        _two_chef_configuration(),
        default_controller="pddl",
        assignments=[],
    )
    try:
        assert _details(run.assignments) == [
            (
                "pddl",
                {"solver": available_solvers()[0], "solver_selection": "automatic"},
            )
        ]
    finally:
        run.controller.shutdown()


def test_a_planner_is_described_before_the_clock_wraps_it() -> None:
    name = _an_installed_solver()
    run = build_agent_controller(
        _two_chef_configuration(),
        default_controller="pddl",
        assignments=[],
        planning_budget=1.0,
        options={"pddl": PDDLOptions(solver=name)},
    )
    try:
        assert _details(run.assignments) == [
            ("pddl", {"solver": name, "solver_selection": "named"})
        ]
    finally:
        run.controller.shutdown()


def test_each_assigned_controller_carries_its_own_details() -> None:
    name = _an_installed_solver()
    run = build_agent_controller(
        _two_chef_configuration(),
        default_controller="pddl",
        assignments=["open=alfred"],
        options={"pddl": PDDLOptions(solver=name)},
    )
    try:
        assert [(entry.controller, entry.agents) for entry in run.assignments] == [
            ("open", ["alfred"]),
            ("pddl", []),
        ]
        assert _details(run.assignments) == [
            ("open", {}),
            ("pddl", {"solver": name, "solver_selection": "named"}),
        ]
    finally:
        run.controller.shutdown()


def test_a_described_run_reports_its_level_teams_and_limits() -> None:
    configuration = _two_chef_configuration().copy_with(teams={"red": ["alfred"]})
    end_conditions = EndConditions(max_timesteps=12, end_on_orders_delivered=True)
    run = build_agent_controller(
        configuration,
        default_controller="open",
        assignments=[],
        planning_budget=3.0,
    )
    try:
        setup = describe_run(
            configuration,
            run.assignments,
            level=Path("levels/demos/burger.yaml"),
            end_conditions=end_conditions,
            headless=True,
            planning_budget=3.0,
        )
    finally:
        run.controller.shutdown()

    assert setup.level == "levels/demos/burger.yaml"
    assert setup.controllers == run.assignments
    assert setup.teams == {"red": ["alfred"]}
    assert setup.headless
    assert setup.planning_budget_seconds == 3.0
    assert setup.end_conditions == end_conditions


def _details(
    assignments: list[ControllerAssignment],
) -> list[tuple[str, dict[str, object]]]:
    return [(entry.controller, entry.details) for entry in assignments]


def _run(*, setup: RunSetup | None) -> SimulationResult:
    """Run one headless step and return the reported result."""
    reported: list[SimulationResult] = []
    run_agent_mode(
        Configuration.from_dict(AGENT_LEVEL),
        StepOnceController(),
        headless=True,
        on_result=reported.append,
        setup=setup,
    )
    assert reported
    return reported[0]


def _two_chef_configuration() -> Configuration:
    return Configuration.from_dict(
        {
            "layout": "| 1 | 2 |",
            "state": {"orders": ["catalog/food/tomato"]},
            "legend": {
                "agents": [
                    {"kind": "agent", "symbol": "1", "name": "alfred"},
                    {"kind": "agent", "symbol": "2", "name": "bob"},
                ],
                "foods": [{"kind": "food", "name": "catalog/food/tomato", "raw": True}],
            },
            "recipes": {"cook": [], "combine": []},
        }
    )


def _an_installed_solver() -> str:
    """Return a planner this machine has, since ``--solver`` refuses the rest."""
    names = available_solvers()
    if not names:
        pytest.skip("No PDDL solver is installed")
    assert solver_type(names[0]).is_available()
    return names[0]

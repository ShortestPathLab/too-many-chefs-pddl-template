"""Solve test problems with an installed planner."""

from __future__ import annotations

import pytest

from controllers.pddl import PDDLPlanStep, PDDLProblem
from controllers.pddl.solvers import (
    Solver,
    SolverUnavailableError,
    resolve_solver,
    solve_problem_with_logging,
)


def installed_solver() -> Solver:
    """Return the available test planner, or skip if none is installed."""
    try:
        return resolve_solver()
    except SolverUnavailableError as error:
        pytest.skip(str(error).splitlines()[0])


def solve_for_test(problem: PDDLProblem) -> list[PDDLPlanStep]:
    return solve_problem_with_logging(problem, solver=installed_solver())

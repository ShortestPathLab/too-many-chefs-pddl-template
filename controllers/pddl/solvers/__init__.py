"""PDDL solver adapters and solver selection.

Importing this package registers every adapter.
"""

from __future__ import annotations

from ..interfaces import PDDLPlanStep, PDDLProblem
from .base import (
    DEFAULT_SOLVER_TIME_LIMIT_SECONDS,
    Solver,
    SolverError,
    SolverTimeoutError,
    SolverUnavailableError,
    SolverUnsolvableError,
)
from .downward import DownwardDriverSolver
from .fast_downward import FastDownwardSolver
from .plan_format import parse_plan_step, parse_sas_plan
from .pyperplan_solver import PyperplanSolver
from .registry import (
    available_solvers,
    known_solvers,
    no_solver_message,
    register_solver,
    resolve_solver,
    solver_type,
    unavailable_message,
)
from .symk import SymKSolver
from .time_limit import time_limit


def solve_problem(problem: PDDLProblem) -> list[PDDLPlanStep]:
    return solve_problem_with_logging(problem, logging=False)


def solve_problem_with_logging(
    problem: PDDLProblem,
    *,
    logging: bool = False,
    time_limit_seconds: float = DEFAULT_SOLVER_TIME_LIMIT_SECONDS,
    solver: Solver | None = None,
) -> list[PDDLPlanStep]:
    """Solve ``problem`` with the selected or automatically chosen solver.

    Both a solver that ran out of resources and one that finished without a
    plan return no plan, so the controller keeps going either way. The two are
    logged apart because only the first is worth another cycle.
    """
    chosen = solver if solver is not None else resolve_solver()
    try:
        return chosen.solve(
            problem,
            time_limit_seconds=time_limit_seconds,
            logging=logging,
        )
    except SolverTimeoutError as error:
        if logging:
            print(f"[PDDLSolver] {error}; giving up this cycle.")
        return []
    except SolverUnsolvableError as error:
        if logging:
            print(f"[PDDLSolver] {error}.")
        return []


# Backward-compatible name for the ``sas_plan`` reader.
parse_fast_downward_plan = parse_sas_plan

__all__ = [
    "DEFAULT_SOLVER_TIME_LIMIT_SECONDS",
    "DownwardDriverSolver",
    "FastDownwardSolver",
    "PyperplanSolver",
    "Solver",
    "SolverError",
    "SolverTimeoutError",
    "SolverUnavailableError",
    "SolverUnsolvableError",
    "SymKSolver",
    "available_solvers",
    "known_solvers",
    "no_solver_message",
    "parse_fast_downward_plan",
    "parse_plan_step",
    "parse_sas_plan",
    "register_solver",
    "resolve_solver",
    "solve_problem",
    "solve_problem_with_logging",
    "solver_type",
    "time_limit",
    "unavailable_message",
]

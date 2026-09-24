"""Adapter for pyperplan.

pyperplan is pure Python and runs in the current process. It is available on
platforms where the compiled planners cannot be installed.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import ClassVar

from ..interfaces import PDDLPlanStep, PDDLProblem
from .base import (
    DEFAULT_SOLVER_TIME_LIMIT_SECONDS,
    Solver,
    SolverUnsolvableError,
)
from .plan_format import parse_plan_step
from .registry import register_solver
from .time_limit import time_limit


@register_solver
@dataclass(frozen=True)
class PyperplanSolver(Solver):
    name: ClassVar[str] = "pyperplan"
    summary: ClassVar[str] = "pyperplan, pure Python; slow but installs anywhere"
    extra: ClassVar[str | None] = "pyperplan"
    priority: ClassVar[int] = 20

    search: str = "gbf"
    heuristic: str = "hff"

    @classmethod
    def is_available(cls) -> bool:
        try:
            return find_spec("pyperplan") is not None
        except ImportError, ValueError:
            return False

    def solve(
        self,
        problem: PDDLProblem,
        *,
        time_limit_seconds: float = DEFAULT_SOLVER_TIME_LIMIT_SECONDS,
        logging: bool = False,
    ) -> list[PDDLPlanStep]:
        from pyperplan.planner import HEURISTICS, SEARCHES, search_plan

        search = SEARCHES[self.search]
        heuristic = HEURISTICS[self.heuristic]

        # pyperplan accepts file paths.
        with tempfile.TemporaryDirectory(
            prefix="too-many-chefs-pyperplan-"
        ) as temp_dir:
            temp_dir_path = Path(temp_dir)
            domain_path = temp_dir_path / "domain.pddl"
            problem_path = temp_dir_path / "problem.pddl"
            domain_path.write_text(problem.domain, encoding="utf-8")
            problem_path.write_text(problem.problem, encoding="utf-8")

            with time_limit(time_limit_seconds):
                solution = search_plan(
                    str(domain_path),
                    str(problem_path),
                    search,
                    heuristic,
                )

        # pyperplan returns ``None`` when its search found no plan, and a
        # list when it did, which is empty when the goal already holds.
        if solution is None:
            raise SolverUnsolvableError(
                f"{self.name}: the search gave up without finding a plan"
            )
        return [
            step
            for step in (parse_plan_step(operator.name) for operator in solution)
            if step is not None
        ]

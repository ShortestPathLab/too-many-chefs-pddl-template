"""Adapters for planners driven by a Fast Downward style script.

Fast Downward and its forks accept the same input and plan-file format, so the
process management is shared here. A planner is a translator, written in
Python, and a compiled search. The driver script runs one after the other, and
an adapter that can find the two runs them itself instead: the driver costs a
Python process of its own on every solve.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from abc import abstractmethod
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import IO, Any

from ..interfaces import PDDLPlanStep, PDDLProblem
from .base import (
    DEFAULT_SOLVER_TIME_LIMIT_SECONDS,
    Solver,
    SolverError,
    SolverTimeoutError,
    SolverUnavailableError,
    SolverUnsolvableError,
)
from .plan_format import parse_sas_plan

# Allow a short grace period after the planner's own limit.
_KILL_GRACE_SECONDS = 5.0

# Runs the translator in place of ``python -m translate``. See the script.
_TRANSLATE_ONCE = Path(__file__).with_name("translate_once.py")

# How much of a failed planner's output an error message repeats.
_OUTPUT_TAIL_LINES = 20

# What the exit codes mean, from https://www.fast-downward.org/ExitCodes. The
# driver passes on its components' codes, so one table serves both ways of
# running a planner. Codes 1 to 3 report a plan found alongside a resource
# limit, so they arrive here with a plan file and never reach the tables.
_NO_PLAN_EXIT_CODES = {
    10: "the translator proved the problem unsolvable",
    11: "the search proved the problem unsolvable",
    12: "the search gave up without finding a plan",
}
_OUT_OF_RESOURCES_EXIT_CODES = {
    20: "the translator ran out of memory",
    21: "the translator ran out of time",
    22: "the search ran out of memory",
    23: "the search ran out of time",
    24: "the search ran out of memory and time",
}
# The planner's own failures. They are errors, not missing plans: another
# attempt at the same domain fails the same way.
_FAILURE_EXIT_CODES = {
    1: "the translator crashed",
    30: "the translator crashed",
    31: "the translator could not read the domain or problem",
    32: "the search crashed",
    33: "the search could not read the translated task",
    34: "the search does not support something in the task",
    35: "the driver crashed",
    36: "the driver was given input it could not use",
    37: "the driver does not support this configuration",
}


@dataclass(frozen=True)
class PlannerComponents:
    """A planner's translator and search, for running without its driver."""

    #: The directory that holds the ``translate`` package.
    translator: Path
    #: The search executable.
    search: Path
    #: Options for the search, ahead of the plan file it is told to write.
    search_options: tuple[str, ...]


class DownwardDriverSolver(Solver):
    """Runs a Fast Downward style planner and reads back its plan file."""

    @classmethod
    @abstractmethod
    def driver_path(cls) -> Path | None:
        """Where this planner's driver script lives, or ``None`` if it is absent."""

    def components(self) -> PlannerComponents | None:
        """Return the translator and search to run in place of the driver.

        ``None``, the default, runs the driver script.
        """
        return None

    def driver_arguments(self, time_limit_seconds: float) -> list[str]:
        """Options for the driver itself, which go ahead of the two files."""
        return [
            "--overall-time-limit",
            f"{max(1, int(time_limit_seconds))}s",
        ]

    def search_arguments(self) -> list[str]:
        """Options for the search, which the driver only reads after the files."""
        return []

    @classmethod
    def is_available(cls) -> bool:
        return cls.driver_path() is not None

    def solve(
        self,
        problem: PDDLProblem,
        *,
        time_limit_seconds: float = DEFAULT_SOLVER_TIME_LIMIT_SECONDS,
        logging: bool = False,
    ) -> list[PDDLPlanStep]:
        driver = self.driver_path()
        if driver is None:
            raise SolverUnavailableError(f"Solver {self.name!r} is not installed")

        with tempfile.TemporaryDirectory(
            prefix=f"too-many-chefs-{self.name}-"
        ) as temp_dir:
            temp_dir_path = Path(temp_dir)
            domain_path = temp_dir_path / "domain.pddl"
            problem_path = temp_dir_path / "problem.pddl"
            plan_path = temp_dir_path / "sas_plan"

            domain_path.write_text(problem.domain, encoding="utf-8")
            problem_path.write_text(problem.problem, encoding="utf-8")

            components = self.components()
            if components is None:
                exit_code, output = self._run_driver(
                    driver,
                    [domain_path, problem_path],
                    plan_path,
                    time_limit_seconds=time_limit_seconds,
                    logging=logging,
                )
            else:
                exit_code, output = self._run_components(
                    components,
                    [domain_path, problem_path],
                    plan_path,
                    time_limit_seconds=time_limit_seconds,
                    logging=logging,
                )

            found_plan = _newest_plan(plan_path)
            if found_plan is not None:
                return parse_sas_plan(found_plan)
            raise self._no_plan(exit_code, output)

    def _run_driver(
        self,
        driver: Path,
        inputs: list[Path],
        plan_path: Path,
        *,
        time_limit_seconds: float,
        logging: bool,
    ) -> tuple[int, str]:
        command = [
            *self._driver_command(driver),
            *self.driver_arguments(time_limit_seconds),
            "--plan-file",
            str(plan_path),
            *map(str, inputs),
            *self.search_arguments(),
        ]
        # Enforce a limit even if the driver ignores its own one.
        return self._run(
            command,
            cwd=plan_path.parent,
            timeout=time_limit_seconds + _KILL_GRACE_SECONDS,
            logging=logging,
        )

    def _run_components(
        self,
        components: PlannerComponents,
        inputs: list[Path],
        plan_path: Path,
        *,
        time_limit_seconds: float,
        logging: bool,
    ) -> tuple[int, str]:
        """Translate, then search, sharing one time limit between them."""
        work = plan_path.parent
        task_path = work / "output.sas"
        deadline = time.monotonic() + time_limit_seconds

        exit_code, output = self._run(
            [
                sys.executable,
                # Keep PYTHONPATH and this directory away from the translator.
                "-I",
                str(_TRANSLATE_ONCE),
                str(components.translator),
                *map(str, inputs),
                "--sas-file",
                str(task_path),
            ],
            cwd=work,
            timeout=time_limit_seconds,
            logging=logging,
        )
        if exit_code != 0:
            return exit_code, output

        with task_path.open("rb") as task:
            return self._run(
                [
                    str(components.search),
                    *components.search_options,
                    "--internal-plan-file",
                    str(plan_path),
                ],
                cwd=work,
                timeout=max(0.0, deadline - time.monotonic()),
                logging=logging,
                stdin=task,
            )

    def _run(
        self,
        command: list[str],
        *,
        cwd: Path,
        timeout: float,
        logging: bool,
        stdin: IO[Any] | None = None,
    ) -> tuple[int, str]:
        """Run one planner process and return its exit code and output.

        With ``logging`` the output goes to the terminal instead, and the
        returned output is empty.
        """
        try:
            completed = subprocess.run(
                command,
                check=False,
                text=True,
                stdin=stdin,
                stdout=None if logging else subprocess.PIPE,
                stderr=None if logging else subprocess.STDOUT,
                # Keep planner scratch files in the temporary directory.
                cwd=cwd,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as error:
            raise SolverTimeoutError(
                f"{self.name} did not finish within {error.timeout:g}s"
            ) from error
        return completed.returncode, completed.stdout or ""

    def _no_plan(self, exit_code: int, output: str) -> SolverError:
        """Explain a run that left no plan file, as the error to raise."""
        if exit_code in _NO_PLAN_EXIT_CODES:
            return SolverUnsolvableError(
                f"{self.name}: {_NO_PLAN_EXIT_CODES[exit_code]}"
            )
        if exit_code in _OUT_OF_RESOURCES_EXIT_CODES:
            return SolverTimeoutError(
                f"{self.name}: {_OUT_OF_RESOURCES_EXIT_CODES[exit_code]}"
            )
        if exit_code == 0:
            return SolverError(f"{self.name} did not produce a plan file")

        meaning = _FAILURE_EXIT_CODES.get(exit_code)
        message = f"{self.name} exited with code {exit_code} without producing a plan"
        if meaning is not None:
            message += f": {meaning}"
        tail = output.strip().splitlines()[-_OUTPUT_TAIL_LINES:]
        if tail:
            message += "\n" + "\n".join(tail)
        return SolverError(message)

    @staticmethod
    def _driver_command(driver: Path) -> list[str]:
        """Return the command used to start the driver.

        Python driver files run under the current interpreter. Executable
        entry points run directly.
        """
        if driver.suffix == ".py":
            return [sys.executable, str(driver)]
        return [str(driver)]


def _newest_plan(plan_path: Path) -> Path | None:
    """Return the newest plan file written by the driver.

    A single-plan search writes ``sas_plan``. Anytime searches may write numbered
    files such as ``sas_plan.1`` and ``sas_plan.2``.
    """
    if plan_path.exists():
        return plan_path

    numbered = [
        (int(candidate.suffix[1:]), candidate)
        for candidate in plan_path.parent.glob(f"{plan_path.name}.*")
        if candidate.suffix[1:].isdigit()
    ]
    if not numbered:
        return None
    return max(numbered)[1]


def packaged_driver(package: str, *relative_parts: str) -> Path | None:
    """Locate a driver script in an installed package without importing it.

    ``find_spec`` resolves the package location without executing its
    ``__init__``.
    """
    try:
        spec = find_spec(package)
    except ImportError, ValueError:
        return None
    if spec is None or spec.origin is None:
        return None
    driver = Path(spec.origin).parent.joinpath(*relative_parts)
    return driver if driver.exists() else None

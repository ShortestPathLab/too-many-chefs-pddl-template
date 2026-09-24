"""The common interface for PDDL planners.

A solver takes a domain and problem and returns a symbolic plan. Adapters hide
the planner-specific details from the controller.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from ..interfaces import PDDLPlanStep, PDDLProblem

# Bound each solve so an unsatisfiable problem cannot keep a controller blocked.
DEFAULT_SOLVER_TIME_LIMIT_SECONDS = 15.0


class SolverError(Exception):
    """Base class for planner errors."""


class SolverTimeoutError(SolverError):
    """Raised when a solver runs out of time or memory before it finishes.

    The problem may still be solvable, so the caller can try again from a
    later state.
    """


class SolverUnsolvableError(SolverError):
    """Raised when a solver finishes and reports that it has no plan.

    The problem may be provably unsolvable, or the search may be incomplete
    and have given up on it. Either way, trying again from the same kitchen
    will not produce a plan.
    """


class SolverUnavailableError(SolverError):
    """Raised when a registered solver is not installed."""


@dataclass(frozen=True)
class Solver(ABC):
    """A PDDL planner adapter.

    Subclasses are frozen dataclasses so instances can be sent to worker
    processes. Unpicklable planner state must be created inside ``solve``.
    """

    #: The name ``--solver`` accepts, and the key in the registry.
    name: ClassVar[str]
    #: One line, shown by ``cook pddl solvers`` and in error messages.
    summary: ClassVar[str]
    #: The project extra that installs the planner.
    extra: ClassVar[str]
    #: Lower wins when nobody asked for a particular solver.
    priority: ClassVar[int] = 50

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Return whether this planner is installed and usable."""

    @abstractmethod
    def solve(
        self,
        problem: PDDLProblem,
        *,
        time_limit_seconds: float = DEFAULT_SOLVER_TIME_LIMIT_SECONDS,
        logging: bool = False,
    ) -> list[PDDLPlanStep]:
        """Solve ``problem``, or raise when the planner returns no plan.

        An empty list means the planner ran and the problem needs no actions.
        Running out of time or memory raises ``SolverTimeoutError``; finishing
        without a plan raises ``SolverUnsolvableError``. The caller handles the
        two separately because only the first is worth retrying.
        """

"""What the PDDL controller expects from the code you write.

A ``ProblemGenerator`` turns the kitchen into a PDDL problem and decides when
to replan. A ``FromPDDL`` turns the solver's plan back into mutations.
``submission/problem_generator.py`` and ``submission/from_pddl.py`` implement
them; see "The Files You Will Edit" in getting-started.md.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Collection
from dataclasses import dataclass

from simulator.environment import Environment
from simulator.mutations import MutationWithLocation


@dataclass(frozen=True)
class PDDLProblem:
    domain: str
    problem: str


@dataclass(frozen=True)
class PDDLPlanStep:
    name: str
    parameters: tuple[str, ...]


class ProblemGenerator(ABC):
    """Build PDDL problems and decide when to replan."""

    @abstractmethod
    def to_pddl(
        self,
        environment: Environment,
        controlled_agent_ids: Collection[str] | None = None,
    ) -> PDDLProblem:
        """Return a PDDL domain and problem for the current environment.

        ``controlled_agent_ids`` limits the agents the plan may move. Other
        agents remain in the environment as obstacles. ``None`` plans for every
        agent. Implementations that omit the parameter remain compatible.
        """

    def should_replan(self, environment: Environment) -> bool:
        """Return whether the controller should discard its plan and replan.

        The controller calls this once per tick when a plan exists and no
        planning task is running. Returning ``True`` starts the full
        ``to_pddl -> solver -> from_pddl`` pipeline again. This method runs in
        the simulator process, so it must be fast and non-blocking.

        The default keeps the initial plan until it is complete.
        """
        return False


class FromPDDL(ABC):
    @abstractmethod
    def from_pddl(self, steps: list[PDDLPlanStep]) -> list[MutationWithLocation]:
        pass

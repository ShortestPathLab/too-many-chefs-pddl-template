from __future__ import annotations

from controllers.navigation import (
    DefaultMutationInterpolationPolicy,
    MutationInterpolationPolicy,
)
from simulator.environment import Environment

from .controller import PDDLController
from .interfaces import FromPDDL, ProblemGenerator
from .solvers import Solver
from .submission.from_pddl import DefaultFromPDDL
from .submission.problem_generator import DefaultProblemGenerator


class DefaultPDDLController(PDDLController):
    def __init__(
        self,
        mutation_interpolation_policy: type[
            MutationInterpolationPolicy
        ] = DefaultMutationInterpolationPolicy,
        *,
        solver: Solver | None = None,
    ) -> None:
        super().__init__(mutation_interpolation_policy, solver=solver)
        self._problem_generator = DefaultProblemGenerator()

    def problem_generator(self) -> ProblemGenerator:
        return self._problem_generator

    def from_pddl(self, environment: Environment) -> FromPDDL:
        return DefaultFromPDDL(environment)

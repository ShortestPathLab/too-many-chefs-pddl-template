"""Plan with PDDL, then carry the plan out.

Each plan runs ``to_pddl``, the solver and ``from_pddl`` in worker processes,
one after another, while the simulator keeps stepping. The finished plan goes
to a ``MutationInterpolationPolicy``, which walks the chefs through it.
"""

from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable
from concurrent.futures import Future
from typing import Any

from controllers.navigation import MutationInterpolationPolicy, Plan
from simulator.context import Context
from simulator.controller import MultiprocessingController
from simulator.entities import Agent, Equipment, OvercookedState, Plate
from simulator.environment import Environment
from simulator.mutations import Mutation, MutationWithLocation
from simulator.mutations.agent_mutation import AgentMutation

from .interfaces import FromPDDL, PDDLPlanStep, PDDLProblem, ProblemGenerator
from .solvers import Solver, solve_problem_with_logging


class PDDLController(
    MultiprocessingController,
    ABC,
):
    def __init__(
        self,
        mutation_interpolation_policy: type[MutationInterpolationPolicy],
        *,
        solver: Solver | None = None,
    ) -> None:
        super().__init__(max_workers=1)
        self._solver = solver
        self._mutation_interpolation_policy_type = mutation_interpolation_policy
        self._mutation_interpolation_policy = mutation_interpolation_policy()
        self._agent_ids: list[str] = []
        self._plans: Plan = {}
        self._plan_totals: dict[str, int] = {}
        self._has_planned = False
        # Set when a replan is due but has to wait for a station to be put down.
        self._replan_due = False
        self._pending_environment: Environment | None = None
        self._pending_log = False
        self._pending_to_pddl_future: Future[PDDLProblem] | None = None
        self._pending_solver_future: Future[list[PDDLPlanStep]] | None = None
        self._pending_from_pddl_future: Future[list[MutationWithLocation]] | None = None

    @property
    def solver(self) -> Solver | None:
        """Return the configured solver, or ``None`` for automatic selection.

        Automatic selection happens in the worker process.
        """
        return self._solver

    def set_solver(self, solver: Solver | None) -> None:
        """Set the solver used for planning.

        The command line sets this after creating the controller from its
        zero-argument factory.
        """
        self._solver = solver

    @abstractmethod
    def problem_generator(self) -> ProblemGenerator:
        """Return the problem generator used for planning and replanning.

        Return the same instance on every call because ``should_replan`` may
        keep state between ticks.
        """

    @abstractmethod
    def from_pddl(self, environment: Environment) -> FromPDDL:
        pass

    def get_actions(self, environment: Environment, context: Context) -> list[Mutation]:
        if self._has_planned and not self.is_busy():
            if self.problem_generator().should_replan(environment):
                self._replan_due = True
            if self._replan_due and not self._carrying_station(environment):
                self._invalidate_plan()

        state = environment.get_first_entity_of_type(OvercookedState)
        if state is not None and not state.visible_orders and not self._has_planned:
            return []

        if not self._has_planned and not self._replan(environment, context):
            return []

        actions, self._plans = self._mutation_interpolation_policy.get_mutations(
            self._plans,
            environment,
            context,
        )
        return actions

    def is_busy(self) -> bool:
        return bool(self.pending_work())

    def pending_work(self) -> list[Future[Any]]:
        return [
            future
            for future in (
                self._pending_to_pddl_future,
                self._pending_solver_future,
                self._pending_from_pddl_future,
            )
            if future is not None
        ]

    def warm_up(self) -> list[Future[Any]]:
        """Start the three planning workers before the first plan needs them.

        The ``to_pddl`` worker also gets the problem generator, so the modules
        it lives in are imported before planning starts.
        """
        return [
            self._submit_to_named_process(
                "to_pddl", worker_ready, self.problem_generator()
            ),
            self._submit_to_process(worker_ready),
            self._submit_to_named_process("from_pddl", worker_ready),
        ]

    def has_finished(self, environment: Environment) -> bool:
        if self.is_busy():
            return False

        state = environment.get_first_entity_of_type(OvercookedState)
        if (
            state is not None
            and not state.visible_orders
            and not state.order_queue.pending
        ):
            return True

        return self._has_planned and all(not plan for plan in self._plans.values())

    def shutdown(self) -> None:
        for pending_future in self.pending_work():
            pending_future.cancel()
        self._mutation_interpolation_policy = self._mutation_interpolation_policy_type()
        self._clear_pending_plan()
        super().shutdown()

    def _replan(self, environment: Environment, context: Context) -> bool:
        if not self.is_busy():
            self._agent_ids = self._controlled_ordered_agent_ids(environment)
            self._pending_environment = environment
            self._pending_log = context.log
            self._pending_to_pddl_future = self._submit_to_pddl(environment)
            return False

        if self._pending_to_pddl_future is not None:
            if not self._pending_to_pddl_future.done():
                return False
            problem = self._pending_to_pddl_future.result()
            self._pending_to_pddl_future = None
            self._pending_solver_future = self._submit_plan_solve(
                problem,
                log=self._pending_log,
            )
            return False

        if self._pending_solver_future is not None:
            if not self._pending_solver_future.done():
                return False
            symbolic_plan = self._pending_solver_future.result()
            self._pending_solver_future = None
            environment = self._require_pending_environment()
            self._pending_from_pddl_future = self._submit_from_pddl(
                environment,
                symbolic_plan,
            )
            return False

        if self._pending_from_pddl_future is None:
            raise ValueError("Missing pending PDDL planning stage")
        if not self._pending_from_pddl_future.done():
            return False

        plan_steps = self._pending_from_pddl_future.result()
        self._plans = group_mutations_by_agent(
            mutations=plan_steps,
            agent_ids=self._agent_ids,
        )
        # Keep the original lengths because plans are consumed in place.
        self._plan_totals = {
            agent_id: len(steps) for agent_id, steps in self._plans.items()
        }
        self._has_planned = True
        self._clear_pending_plan()
        return True

    def plan_progress(self, agent_id: str | None = None) -> tuple[int, int] | None:
        if not self._plan_totals:
            return None
        if agent_id is not None:
            total = self._plan_totals.get(agent_id)
            if not total:
                return None
            return (total - len(self._plans.get(agent_id, [])), total)

        total = sum(self._plan_totals.values())
        if not total:
            return None
        remaining = sum(len(steps) for steps in self._plans.values())
        return (total - remaining, total)

    def _build_plan(
        self,
        environment: Environment,
        agent_ids: list[str],
        context: Context,
    ) -> Plan:
        problem = self._submit_to_pddl(environment).result()
        symbolic_plan = self._submit_plan_solve(problem, log=context.log).result()
        plan_steps = self._submit_from_pddl(environment, symbolic_plan).result()
        return group_mutations_by_agent(
            mutations=plan_steps,
            agent_ids=agent_ids,
        )

    def _submit_to_pddl(
        self,
        environment: Environment,
    ) -> Future[PDDLProblem]:
        controlled_agent_ids = (
            None
            if self._controlled_agent_ids is None
            else sorted(self._controlled_agent_ids)
        )
        return self._submit_to_named_process(
            "to_pddl",
            to_pddl_worker,
            self.problem_generator(),
            environment,
            controlled_agent_ids,
        )

    def _controlled_ordered_agent_ids(self, environment: Environment) -> list[str]:
        agent_ids = self.ordered_agent_ids(environment)
        if self._controlled_agent_ids is None:
            return agent_ids
        return [
            agent_id for agent_id in agent_ids if agent_id in self._controlled_agent_ids
        ]

    def _submit_plan_solve(
        self,
        problem: PDDLProblem,
        *,
        log: bool,
    ) -> Future[list[PDDLPlanStep]]:
        return self._submit_to_process(
            solve_problem_worker,
            problem,
            log,
            self._solver,
        )

    def _submit_from_pddl(
        self,
        environment: Environment,
        symbolic_plan: list[PDDLPlanStep],
    ) -> Future[list[MutationWithLocation]]:
        return self._submit_to_named_process(
            "from_pddl",
            from_pddl_worker,
            self.from_pddl(environment),
            symbolic_plan,
        )

    def _require_pending_environment(self) -> Environment:
        if self._pending_environment is None:
            raise ValueError("Missing environment for pending PDDL plan")
        return self._pending_environment

    def _clear_pending_plan(self) -> None:
        self._pending_environment = None
        self._pending_log = False
        self._pending_to_pddl_future = None
        self._pending_solver_future = None
        self._pending_from_pddl_future = None

    def _carrying_station(self, environment: Environment) -> bool:
        """Return whether one of this controller's chefs holds a pot, pan or bowl.

        The provided domain cannot describe a chef holding a station, so a plan
        made now would treat the chef as empty-handed and drop the step that
        puts the station back. Replanning waits until it is down.
        """
        for agent in self.controllable_agents(environment):
            if agent.held_item_id is None:
                continue
            held_item = environment.get_entity(agent.held_item_id)
            if isinstance(held_item, Equipment) and not isinstance(held_item, Plate):
                return True
        return False

    def _invalidate_plan(self) -> None:
        for future in self.pending_work():
            future.cancel()
        self._clear_pending_plan()
        self._plans = {}
        self._plan_totals = {}
        self._has_planned = False
        self._replan_due = False
        self._mutation_interpolation_policy = self._mutation_interpolation_policy_type()

    @staticmethod
    def ordered_agent_ids(environment: Environment) -> list[str]:
        return [
            agent.id
            for agent in sorted(
                environment.get_entities_of_type(Agent),
                key=lambda agent: (
                    agent.y if agent.y is not None else -1,
                    agent.x if agent.x is not None else -1,
                    agent.id,
                ),
            )
        ]


def group_mutations_by_agent(
    *,
    mutations: list[MutationWithLocation],
    agent_ids: list[str],
) -> Plan:
    plans_by_agent: Plan = {agent_id: [] for agent_id in agent_ids}

    for index, mutation_with_location in enumerate(mutations):
        agent_id = _require_agent_id(mutation_with_location)
        if agent_id not in plans_by_agent:
            plans_by_agent[agent_id] = []
        plans_by_agent[agent_id].append((index, mutation_with_location))

    return plans_by_agent


def _require_agent_id(mutation_with_location: MutationWithLocation) -> str:
    if not isinstance(mutation_with_location.mutation, AgentMutation):
        raise TypeError(
            "Expected agent mutation, got "
            f"{type(mutation_with_location.mutation).__name__}"
        )
    return mutation_with_location.mutation.agent_id


# The functions below run in the worker processes. They sit at module
# level so they can be pickled.


def worker_ready(*_loaded: object) -> None:
    """Return at once. Warm-up submits this to make a worker import its code.

    Unpickling the function imports this module and the controller package,
    and unpickling the arguments imports the modules their classes live in.
    """


def to_pddl_worker(
    problem_generator: ProblemGenerator,
    environment: Environment,
    controlled_agent_ids: list[str] | None = None,
) -> PDDLProblem:
    if controlled_agent_ids is not None and _accepts_controlled_agents(
        problem_generator.to_pddl
    ):
        return problem_generator.to_pddl(
            environment, controlled_agent_ids=controlled_agent_ids
        )
    return problem_generator.to_pddl(environment)


def from_pddl_worker(
    from_pddl: FromPDDL,
    symbolic_plan: list[PDDLPlanStep],
) -> list[MutationWithLocation]:
    return from_pddl.from_pddl(symbolic_plan)


def solve_problem_worker(
    problem: PDDLProblem,
    log: bool,
    solver: Solver | None = None,
) -> list[PDDLPlanStep]:
    """Run one solve in the worker process.

    Resolve an omitted solver in the worker so selection happens where the solve
    runs.
    """
    return solve_problem_with_logging(problem, logging=log, solver=solver)


def _accepts_controlled_agents(to_pddl: Callable[..., PDDLProblem]) -> bool:
    """Return whether ``to_pddl`` accepts ``controlled_agent_ids``.

    Older generators receive the full environment for compatibility.
    """
    parameters = inspect.signature(to_pddl).parameters
    if "controlled_agent_ids" in parameters:
        return True
    return any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )

from __future__ import annotations

import atexit
import ctypes
import multiprocessing
import os
import signal
import sys
import time
import weakref
from abc import ABC, abstractmethod
from collections.abc import Callable, Collection, Iterator
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, wait
from multiprocessing.context import BaseContext
from typing import TYPE_CHECKING, Any, TypeVar

from simulator.context import Context
from simulator.entities import Agent
from simulator.environment import Environment
from simulator.mutations import Mutation

if TYPE_CHECKING:
    from simulator.planning_budget import PlanningClock

ResultT = TypeVar("ResultT")


class Controller(ABC):
    """Controller for one or more agents.

    By default a controller owns every agent. ``set_controlled_agents`` can
    restrict it to a subset when controllers share a level.
    """

    #: ``None`` means every agent. Otherwise, the ids owned by this controller.
    _controlled_agent_ids: frozenset[str] | None = None

    def set_controlled_agents(self, agent_ids: Collection[str] | None) -> None:
        """Restrict this controller to the given agents (``None`` = all agents)."""
        self._controlled_agent_ids = None if agent_ids is None else frozenset(agent_ids)

    @property
    def controlled_agent_ids(self) -> frozenset[str] | None:
        return self._controlled_agent_ids

    def controls_agent(self, agent_id: str) -> bool:
        """Return whether ``agent_id`` is owned by this controller."""
        return (
            self._controlled_agent_ids is None or agent_id in self._controlled_agent_ids
        )

    def controllable_agents(self, environment: Environment) -> list[Agent]:
        """Return the agents this controller is responsible for."""
        agents = environment.get_entities_of_type(Agent)
        if self._controlled_agent_ids is None:
            return agents
        return [agent for agent in agents if agent.id in self._controlled_agent_ids]

    @property
    def label(self) -> str:
        """Return the controller name shown in the agent inspector.

        The ``Controller`` suffix is omitted to keep the label short.
        """
        name = type(self).__name__
        return name.removesuffix("Controller") or name

    def plan_progress(self, agent_id: str | None = None) -> tuple[int, int] | None:
        """Return optional ``(done, total)`` plan progress.

        With an agent id, return progress for that agent. Without one, return
        progress across all controlled agents. The base controller has no plan.
        """
        return None

    def child_controllers(self) -> list[Controller]:
        """Return nested controllers, if this controller delegates."""
        return []

    def nested_controllers(self) -> list[Controller]:
        """Return the controllers inside this one, wrappers included.

        ``child_controllers`` answers what the agent inspector should look
        through, where a budget wrapper hides the controller it times so the
        budget stays on screen. This answers what the run is made of instead.
        """
        return self.child_controllers()

    @property
    def planning_clock(self) -> PlanningClock | None:
        """Return this controller's planning clock, if it has one.

        The run adds a clock by wrapping the controller in a
        ``BudgetedController``.
        """
        return None

    @abstractmethod
    def get_actions(self, environment: Environment, context: Context) -> list[Mutation]:
        pass

    @abstractmethod
    def is_busy(self) -> bool:
        pass

    def has_finished(self, environment: Environment) -> bool:
        return not self.is_busy()

    @abstractmethod
    def shutdown(self) -> None:
        pass

    def warm_up(self) -> list[Future[Any]]:
        """Start anything slow to start, such as worker processes.

        Return futures that finish once it is ready. A run calls this before
        its clock starts, so neither a planning budget nor a time limit pays
        for the start-up. Nested controllers are warmed up separately, by
        ``warm_up_controllers``.
        """
        return []

    def pending_work(self) -> list[Future[Any]]:
        """Return background work this controller is waiting on.

        A headless run waits on these between steps instead of polling, so it
        continues as soon as one finishes.
        """
        return []


def every_controller(controller: Controller | None) -> Iterator[Controller]:
    """Yield ``controller`` and every controller nested inside it."""
    if controller is None:
        return
    yield controller
    for nested in controller.nested_controllers():
        yield from every_controller(nested)


def warm_up_controllers(controller: Controller | None) -> None:
    """Warm up every controller under ``controller`` and wait until all are ready.

    Every controller starts before any is waited on, so their workers start
    in parallel.
    """
    ready = [
        future for nested in every_controller(controller) for future in nested.warm_up()
    ]
    for future in ready:
        future.result()


def wait_for_controllers(controller: Controller | None, timeout: float) -> None:
    """Wait until some controller's background work finishes, or ``timeout``.

    Finished work that a controller has not collected yet is skipped, so a
    controller that stopped collecting, such as one out of budget, cannot turn
    the wait into a busy loop.
    """
    pending = {
        future
        for nested in every_controller(controller)
        for future in nested.pending_work()
        if not future.done()
    }
    if pending:
        wait(pending, timeout=timeout, return_when=FIRST_COMPLETED)
    else:
        time.sleep(timeout)


class MultiprocessingController(Controller, ABC):
    """Controller base class with reusable worker-process executors."""

    def __init__(self, *, max_workers: int = 1) -> None:
        self._max_workers = max_workers
        self._process_executor: ProcessPoolExecutor | None = None
        self._named_process_executors: dict[str, ProcessPoolExecutor] = {}
        atexit.register(_shutdown_controller_from_ref, weakref.ref(self))

    def shutdown(self) -> None:
        process_executor = self._process_executor
        if process_executor is not None:
            process_executor.shutdown(wait=False, cancel_futures=True)
        self._process_executor = None
        for named_process_executor in self._named_process_executors.values():
            named_process_executor.shutdown(wait=False, cancel_futures=True)
        self._named_process_executors.clear()

    def _submit_to_process(
        self,
        fn: Callable[..., ResultT],
        /,
        *args: Any,
    ) -> Future[ResultT]:
        process_executor = self._ensure_process_executor()
        return process_executor.submit(fn, *args)

    def _submit_to_named_process(
        self,
        name: str,
        fn: Callable[..., ResultT],
        /,
        *args: Any,
    ) -> Future[ResultT]:
        process_executor = self._ensure_named_process_executor(name)
        return process_executor.submit(fn, *args)

    def _ensure_process_executor(self) -> ProcessPoolExecutor:
        if self._process_executor is None:
            self._process_executor = self._create_process_executor()
        return self._process_executor

    def _ensure_named_process_executor(self, name: str) -> ProcessPoolExecutor:
        process_executor = self._named_process_executors.get(name)
        if process_executor is None:
            process_executor = self._create_process_executor()
            self._named_process_executors[name] = process_executor
        return process_executor

    def _create_process_executor(self) -> ProcessPoolExecutor:
        context = _multiprocessing_context()
        return ProcessPoolExecutor(
            max_workers=self._max_workers,
            initializer=_initialise_worker_process,
            initargs=(_worker_parent_pid(context),),
            mp_context=context,
        )


def _shutdown_controller_from_ref(
    controller_ref: weakref.ReferenceType[MultiprocessingController],
) -> None:
    controller = controller_ref()
    if controller is None:
        return
    controller.shutdown()


def _initialise_worker_process(parent_pid: int | None) -> None:
    _set_parent_death_signal(parent_pid)


def _set_parent_death_signal(parent_pid: int | None) -> None:
    """Stop this worker when the process that started it dies.

    The kernel only signals a death that happens after ``prctl``. A parent
    that died first has already left this worker to be adopted by another
    process, so a parent pid other than ``parent_pid`` means it is gone.
    Checking for a parent of 1 instead would kill every worker of a parent
    that is itself PID 1, as a container's first process is, and would miss
    an orphan adopted by a subreaper.
    """
    if sys.platform != "linux":
        return

    pr_set_pdeathsig = 1
    libc = ctypes.CDLL("libc.so.6", use_errno=True)
    result = libc.prctl(pr_set_pdeathsig, signal.SIGTERM, 0, 0, 0)
    if result != 0:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno))

    if parent_pid is not None and os.getppid() != parent_pid:
        os.kill(os.getpid(), signal.SIGTERM)


def _worker_parent_pid(context: BaseContext | None) -> int | None:
    """Return the pid a new worker's parent will have, if it is this process.

    A fork server starts workers itself, so under one the parent is not
    known here and the worker skips the check.
    """
    method = (
        context.get_start_method()
        if context is not None
        else multiprocessing.get_start_method()
    )
    return os.getpid() if method in ("spawn", "fork") else None


def _multiprocessing_context() -> BaseContext | None:
    available_methods = multiprocessing.get_all_start_methods()
    if "spawn" in available_methods:
        return multiprocessing.get_context("spawn")
    if "forkserver" in available_methods:
        return multiprocessing.get_context("forkserver")
    if "fork" in available_methods:
        return multiprocessing.get_context("fork")
    return None

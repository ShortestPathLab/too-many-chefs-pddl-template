"""Test that a run starts controllers before its clock and waits on their work."""

from __future__ import annotations

import threading
import time
from concurrent.futures import Future
from typing import Any

from simulator.configuration import Configuration
from simulator.context import Context
from simulator.controller import wait_for_controllers
from simulator.environment import Environment
from simulator.mutations import Mutation
from simulator.planning_budget import BudgetedController
from simulator.run import SimulationResult, run_agent_mode
from tests.run_controllers import AGENT_LEVEL
from tests.stub_controller import StubController

WARM_UP_SECONDS = 0.3


def finishes_after(seconds: float) -> Future[Any]:
    future: Future[Any] = Future()
    threading.Timer(seconds, future.set_result, args=(None,)).start()
    return future


class SlowToStartController(StubController):
    """Takes a while to warm up, then has nothing to do."""

    def __init__(self) -> None:
        super().__init__(finished=True)
        self.calls: list[str] = []

    def warm_up(self) -> list[Future[Any]]:
        self.calls.append("warm_up")
        return [finishes_after(WARM_UP_SECONDS)]

    def get_actions(self, environment: Environment, context: Context) -> list[Mutation]:
        self.calls.append("get_actions")
        return []


class WaitingController(StubController):
    """Busy with one piece of background work."""

    def __init__(self, work: Future[Any]) -> None:
        super().__init__(busy=True)
        self._work = work

    def pending_work(self) -> list[Future[Any]]:
        return [self._work]


def run_headless(controller: StubController | BudgetedController) -> SimulationResult:
    results: list[SimulationResult] = []
    run_agent_mode(
        Configuration.from_dict(AGENT_LEVEL),
        controller,
        headless=True,
        on_result=results.append,
    )
    return results[0]


def test_a_run_warms_its_controller_up_before_the_clock_starts() -> None:
    controller = SlowToStartController()

    result = run_headless(controller)

    assert controller.calls == ["warm_up", "get_actions"]
    assert result.elapsed_seconds < WARM_UP_SECONDS


def test_warming_up_is_not_charged_to_a_planning_budget() -> None:
    inner = SlowToStartController()
    budget = WARM_UP_SECONDS / 2
    controller = BudgetedController(inner, budget_seconds=budget)

    result = run_headless(controller)

    assert inner.calls[0] == "warm_up"
    assert result.reason != "planning_budget_exhausted"
    assert controller.planning_clock.spent_seconds < budget


def test_waiting_ends_as_soon_as_background_work_finishes() -> None:
    controller = BudgetedController(
        WaitingController(finishes_after(0.05)), budget_seconds=None
    )

    started = time.monotonic()
    wait_for_controllers(controller, timeout=30)

    assert time.monotonic() - started < 10


def test_finished_work_left_uncollected_does_not_cut_the_wait_short() -> None:
    # A controller out of budget stops collecting its finished work. Waiting
    # on that work would return at once and spin the run loop.
    done: Future[Any] = Future()
    done.set_result(None)

    started = time.monotonic()
    wait_for_controllers(WaitingController(done), timeout=0.1)

    assert time.monotonic() - started >= 0.09

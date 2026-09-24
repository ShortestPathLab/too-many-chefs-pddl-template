from __future__ import annotations

import pytest

from simulator.composite_controller import CompositeController
from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.context import Context
from simulator.controller import Controller
from simulator.entities import Agent
from simulator.environment import Environment
from simulator.mutations import MoveAgentForward, Mutation
from simulator.planning_budget import (
    BudgetedController,
    PlanningClock,
    all_budgets_exhausted,
    planning_clocks,
)
from simulator.view import controller_for_agent, controller_view
from tests.run_controllers import AGENT_LEVEL
from tests.status_levels import LEVEL
from tests.stub_controller import StubController


class FakeClock:
    """A manually controlled test clock."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class SlowController(Controller):
    """Advance the fake clock during each call."""

    def __init__(
        self,
        clock: FakeClock,
        *,
        seconds_per_call: float = 0.0,
        busy: bool = False,
    ) -> None:
        self._clock = clock
        self._seconds_per_call = seconds_per_call
        self.busy = busy
        self.calls = 0

    def get_actions(self, environment: Environment, context: Context) -> list[Mutation]:
        self.calls += 1
        self._clock.advance(self._seconds_per_call)
        agent = environment.get_first_entity_of_type(Agent)
        if agent is None:
            return []
        return [MoveAgentForward(agent_id=agent.id)]

    def is_busy(self) -> bool:
        return self.busy

    def has_finished(self, environment: Environment) -> bool:
        return False

    def shutdown(self) -> None:
        return None


def agent_environment() -> Environment:
    return load(Configuration.from_dict(AGENT_LEVEL))


def test_an_unlimited_clock_never_runs_out() -> None:
    clock = FakeClock()
    planning = PlanningClock(None, now=clock)

    planning.start_thinking()
    clock.advance(1000)

    assert not planning.limited
    assert planning.remaining_seconds is None
    assert not planning.exhausted
    assert planning.spent_seconds == 1000


def test_time_is_only_charged_while_thinking() -> None:
    clock = FakeClock()
    planning = PlanningClock(10, now=clock)

    clock.advance(3)
    planning.start_thinking()
    clock.advance(2)
    planning.stop_thinking()
    clock.advance(4)

    assert planning.spent_seconds == 2
    assert planning.remaining_seconds == 8


def test_a_running_clock_reads_live() -> None:
    clock = FakeClock()
    planning = PlanningClock(10, now=clock)

    planning.start_thinking()
    clock.advance(6)

    assert planning.remaining_seconds == 4
    assert planning.thinking


def test_remaining_time_stops_at_zero() -> None:
    clock = FakeClock()
    planning = PlanningClock(2, now=clock)

    planning.start_thinking()
    clock.advance(30)

    assert planning.remaining_seconds == 0
    assert planning.exhausted


def test_thinking_inside_the_call_is_charged() -> None:
    clock = FakeClock()
    controller = BudgetedController(
        SlowController(clock, seconds_per_call=2),
        budget_seconds=5,
        now=clock,
    )

    controller.get_actions(agent_environment(), Context())

    assert controller.planning_clock is not None
    assert controller.planning_clock.remaining_seconds == 3


def test_a_worker_left_running_is_charged_between_calls() -> None:
    clock = FakeClock()
    inner = SlowController(clock, busy=True)
    controller = BudgetedController(inner, budget_seconds=10, now=clock)
    environment = agent_environment()

    controller.get_actions(environment, Context())
    clock.advance(4)

    # Still solving in the background, so the clock is still running and the
    # interface can watch it drain.
    assert controller.planning_clock.remaining_seconds == 6

    inner.busy = False
    controller.get_actions(environment, Context())

    assert controller.planning_clock.remaining_seconds == 6


def test_a_controller_out_of_time_stops_acting() -> None:
    clock = FakeClock()
    inner = SlowController(clock, seconds_per_call=2)
    controller = BudgetedController(inner, budget_seconds=1.5, now=clock)
    environment = agent_environment()

    # The first call started with time left, so the move it came back with
    # stands even though it went over.
    first = controller.get_actions(environment, Context())
    second = controller.get_actions(environment, Context())

    assert len(first) == 1
    assert second == []
    assert inner.calls == 1


def test_agents_and_progress_reach_the_controller_underneath() -> None:
    inner = StubController(busy=True, progress=(2, 6))
    controller = BudgetedController(inner, budget_seconds=5)

    controller.set_controlled_agents(["chef-1"])

    assert inner.controlled_agent_ids == frozenset({"chef-1"})
    assert controller.controls_agent("chef-1")
    assert not controller.controls_agent("chef-2")
    assert controller.plan_progress() == (2, 6)
    assert controller.label == "Stub"
    assert controller.is_busy()


def test_shutting_down_reaches_the_controller_underneath() -> None:
    clock = FakeClock()
    inner = SlowController(clock, busy=True)
    controller = BudgetedController(inner, budget_seconds=5, now=clock)

    controller.get_actions(agent_environment(), Context())
    clock.advance(2)
    controller.shutdown()
    clock.advance(2)

    assert controller.planning_clock.spent_seconds == 2


def test_a_controller_off_the_clock_reports_none() -> None:
    assert planning_clocks(StubController()) == []
    assert not all_budgets_exhausted(StubController())


def test_a_run_with_no_clocks_cannot_run_out_of_them() -> None:
    composite = CompositeController([(StubController(), ["chef-1"])])

    assert not all_budgets_exhausted(composite)


def test_one_controller_with_time_left_keeps_the_kitchen_open() -> None:
    clock = FakeClock()
    spent = BudgetedController(StubController(), budget_seconds=0, now=clock)
    fresh = BudgetedController(StubController(), budget_seconds=5, now=clock)
    composite = CompositeController([(spent, ["chef-1"]), (fresh, ["chef-2"])])

    assert len(planning_clocks(composite)) == 2
    assert not all_budgets_exhausted(composite)


def test_every_budget_spent_ends_the_wait() -> None:
    clock = FakeClock()
    composite = CompositeController(
        [
            (BudgetedController(StubController(), budget_seconds=0), ["chef-1"]),
            (
                BudgetedController(StubController(), budget_seconds=0, now=clock),
                ["chef-2"],
            ),
        ]
    )

    assert all_budgets_exhausted(composite)


def test_the_panel_reads_the_clock_of_the_controller_driving_an_agent() -> None:
    clock = FakeClock()
    environment = load(Configuration.from_dict(LEVEL))
    agent_id = environment.get_entities_of_type(Agent)[0].id
    controller = BudgetedController(
        SlowController(clock, seconds_per_call=6),
        budget_seconds=8,
        now=clock,
    )

    controller.get_actions(environment, Context())
    view = controller_view(controller, agent_id, environment)

    assert view is not None
    assert controller_for_agent(controller, agent_id) is controller
    assert view.label == "Slow"
    assert view.budget_seconds == 8
    assert view.budget_remaining_seconds == 2
    assert view.budget_label == "2.0s / 8s"
    assert (view.budget_progress or 0) == pytest.approx(0.25)
    assert not view.out_of_time


def test_a_controller_out_of_time_says_so() -> None:
    environment = load(Configuration.from_dict(LEVEL))
    agent_id = environment.get_entities_of_type(Agent)[0].id
    controller = BudgetedController(StubController(progress=(1, 4)), budget_seconds=0)

    view = controller_view(controller, agent_id, environment)

    assert view is not None
    assert view.out_of_time
    assert view.status_label == "Out of time"
    assert not view.active
    assert view.budget_progress == 0.0


def test_a_run_without_a_budget_shows_no_clock() -> None:
    environment = load(Configuration.from_dict(LEVEL))
    agent_id = environment.get_entities_of_type(Agent)[0].id

    view = controller_view(StubController(), agent_id, environment)

    assert view is not None
    assert view.budget_seconds is None
    assert view.budget_progress is None
    assert view.budget_label == ""

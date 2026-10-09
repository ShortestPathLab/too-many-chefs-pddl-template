from __future__ import annotations

import pytest
import typer

from cli.end_conditions import build_end_conditions
from simulator.configuration.configuration import Configuration
from simulator.entities import OrderEntry, OrderQueue, OvercookedState
from simulator.environment import Environment
from simulator.planning_budget import BudgetedController
from simulator.run import EndConditions, SimulationResult, run_agent_mode
from tests.run_controllers import AGENT_LEVEL, NeverFinishedController
from tests.stub_controller import StubController
from tests.test_planning_budget import FakeClock, SlowController, agent_environment

SALAD = "catalog/food/salad"


def queued(
    *,
    visible: list[OrderEntry] | None = None,
    pending: list[OrderEntry] | None = None,
    delivered_count: int = 0,
    expired_count: int = 0,
) -> Environment:
    """Return a kitchen with the given order queue."""
    return Environment().with_entity(
        OvercookedState(
            order_queue=OrderQueue(
                visible=visible or [],
                pending=pending or [],
                delivered_count=delivered_count,
                expired_count=expired_count,
            )
        ),
    )


def infinite_configuration() -> Configuration:
    return Configuration.from_dict(
        {
            "layout": "|A|\n| |",
            "state": {"orders": [SALAD]},
            "rules": {"infinite_orders": True},
            "legend": {
                "agents": [{"kind": "agent", "symbol": "A"}],
                "foods": [{"kind": "food", "name": SALAD}],
            },
        }
    )


def test_a_headless_run_stops_at_the_last_timestep() -> None:
    results: list[SimulationResult] = []

    recording = run_agent_mode(
        Configuration.from_dict(AGENT_LEVEL),
        NeverFinishedController(),
        headless=True,
        end_conditions=EndConditions(max_timesteps=3),
        on_result=results.append,
    )

    assert results[0].reason == "max_timesteps"
    assert results[0].timesteps == 3
    assert recording.environments[-1].timestep == 3


def test_a_run_of_no_timesteps_ends_before_it_starts() -> None:
    results: list[SimulationResult] = []

    run_agent_mode(
        Configuration.from_dict(AGENT_LEVEL),
        NeverFinishedController(),
        headless=True,
        end_conditions=EndConditions(max_timesteps=0),
        on_result=results.append,
    )

    assert results[0].reason == "max_timesteps"
    assert results[0].timesteps == 0


def test_an_emptied_queue_ends_the_run() -> None:
    conditions = EndConditions(end_on_orders_delivered=True)

    reason = conditions.reached(
        queued(delivered_count=2),
        StubController(),
        elapsed_seconds=0,
    )

    assert reason == "orders_delivered"


def test_orders_still_on_the_rail_keep_the_run_going() -> None:
    conditions = EndConditions(end_on_orders_delivered=True)

    reason = conditions.reached(
        queued(visible=[OrderEntry(name=SALAD)]),
        StubController(),
        elapsed_seconds=0,
    )

    assert reason is None


def test_orders_yet_to_be_revealed_keep_the_run_going() -> None:
    conditions = EndConditions(end_on_orders_delivered=True)

    reason = conditions.reached(
        queued(pending=[OrderEntry(name=SALAD)]),
        StubController(),
        elapsed_seconds=0,
    )

    assert reason is None


def test_a_ticket_that_ran_out_is_not_a_ticket_served() -> None:
    conditions = EndConditions(end_on_orders_delivered=True)

    reason = conditions.reached(
        queued(delivered_count=1, expired_count=1),
        StubController(),
        elapsed_seconds=0,
    )

    assert reason is None


def test_the_condition_is_off_unless_asked_for() -> None:
    reason = EndConditions().reached(
        queued(delivered_count=2),
        StubController(),
        elapsed_seconds=0,
    )

    assert reason is None


def test_expiring_an_order_is_counted() -> None:
    queue = OrderQueue(visible=[OrderEntry(name=SALAD, time_limit=2)])

    assert queue.advance_to_timestep(1).expired_count == 0
    assert queue.advance_to_timestep(9).expired_count == 1


def test_a_run_ends_once_every_controller_is_out_of_planning_time() -> None:
    clock = FakeClock()
    controller = BudgetedController(
        SlowController(clock, seconds_per_call=0.6),
        budget_seconds=1,
        now=clock,
    )
    results: list[SimulationResult] = []

    run_agent_mode(
        Configuration.from_dict(AGENT_LEVEL),
        controller,
        headless=True,
        on_result=results.append,
    )

    assert results[0].reason == "planning_budget_exhausted"
    assert results[0].timesteps == 2


def test_the_run_carries_on_when_told_to() -> None:
    conditions = EndConditions(
        time_limit_seconds=0.05,
        end_on_budget_exhausted=False,
    )
    controller = BudgetedController(NeverFinishedController(), budget_seconds=0)
    results: list[SimulationResult] = []

    run_agent_mode(
        Configuration.from_dict(AGENT_LEVEL),
        controller,
        headless=True,
        end_conditions=conditions,
        on_result=results.append,
    )

    # A kitchen where nobody is allowed to plan takes no steps at all, so
    # leaving this condition off needs a wall clock behind it.
    assert results[0].reason == "time_limit"
    assert results[0].timesteps == 0


def test_the_wall_clock_is_reported_over_the_simulation_clock() -> None:
    conditions = EndConditions(time_limit_seconds=5, max_timesteps=1)

    reason = conditions.reached(
        agent_environment().copy_with(timestep=1),
        StubController(),
        elapsed_seconds=9,
    )

    assert reason == "time_limit"


def test_nothing_set_never_ends_a_run() -> None:
    reason = EndConditions().reached(
        agent_environment().copy_with(timestep=10_000),
        StubController(),
        elapsed_seconds=10_000,
    )

    assert reason is None


def options(**overrides: object) -> EndConditions:
    arguments: dict[str, object] = {
        "headless": True,
        "time_limit": None,
        "max_timesteps": None,
        "planning_budget": None,
        "end_on_orders_delivered": False,
        "end_on_budget_exhausted": True,
    }
    arguments.update(overrides)
    return build_end_conditions(infinite_configuration(), **arguments)  # type: ignore[arg-type]


def test_an_endless_level_needs_something_to_stop_it() -> None:
    with pytest.raises(typer.BadParameter):
        options()


def test_a_timestep_limit_bounds_an_endless_level() -> None:
    assert options(max_timesteps=50).max_timesteps == 50


def test_a_planning_budget_bounds_an_endless_level() -> None:
    conditions = options(planning_budget=30)

    assert conditions.end_on_budget_exhausted


def test_a_budget_nobody_is_stopped_by_bounds_nothing() -> None:
    with pytest.raises(typer.BadParameter):
        options(planning_budget=30, end_on_budget_exhausted=False)


def test_serving_every_order_bounds_nothing_on_an_endless_level() -> None:
    with pytest.raises(typer.BadParameter):
        options(end_on_orders_delivered=True)


def test_a_visual_run_is_stopped_by_closing_the_window() -> None:
    conditions = options(headless=False)

    assert conditions.max_timesteps is None

from __future__ import annotations

import pytest

from simulator.configuration.configuration import Configuration
from simulator.configuration.load.state import build_overcooked_state
from simulator.context import Context
from simulator.entities import (
    OrderEntry,
    OrderGenerator,
    OrderQueue,
    OvercookedState,
)
from simulator.environment import Environment
from simulator.mutations import Mutation
from simulator.run import EndConditions, SimulationResult, run_agent_mode
from tests.run_controllers import NeverFinishedController


def infinite_configuration(**rules: object) -> Configuration:
    return Configuration.from_dict(
        {
            "layout": "|A|\n| |",
            "state": {
                "orders": ["catalog/food/tomato", "catalog/food/potato"],
            },
            "rules": {"infinite_orders": True, **rules},
            "legend": {
                "agents": [{"kind": "agent", "symbol": "A"}],
                "foods": [
                    {"kind": "food", "name": "catalog/food/tomato"},
                    {"kind": "food", "name": "catalog/food/potato"},
                ],
            },
        }
    )


def test_generator_fills_visible_orders_up_to_max_visible() -> None:
    generator = OrderGenerator(
        pool=[OrderEntry(name="catalog/food/tomato")],
        seed=7,
        max_visible=3,
    )

    queue = OrderQueue.from_orders([], generator=generator)

    assert queue.generator is not None
    assert len(queue.visible) == 3
    assert queue.generator.generated_count == 3


def test_delivery_refills_visible_orders_deterministically() -> None:
    generator = OrderGenerator(
        pool=[
            OrderEntry(name="catalog/food/tomato"),
            OrderEntry(name="catalog/food/potato"),
        ],
        seed=7,
        max_visible=2,
    )
    queue = OrderQueue.from_orders([], generator=generator)

    first, reward = queue.delivered(queue.visible[0].name, timestep=4)
    second, _ = queue.delivered(queue.visible[0].name, timestep=4)

    assert reward is not None
    assert first == second
    assert len(first.visible) == 2
    assert first.delivered_count == 1
    assert first.revision == queue.revision + 1
    assert first.visible[-1].revealed_at == 5


def test_expiry_refills_visible_orders() -> None:
    generator = OrderGenerator(
        pool=[OrderEntry(name="catalog/food/tomato")],
        seed=1,
        max_visible=1,
    )
    queue = OrderQueue(
        visible=[OrderEntry(name="catalog/food/tomato", time_limit=3)],
        generator=generator,
    )

    advanced = queue.advance_to_timestep(10)

    assert len(advanced.visible) == 1
    assert advanced.visible[0].revealed_at == 10
    assert advanced.revision == queue.revision + 1


def test_rules_build_an_order_generator() -> None:
    state = build_overcooked_state(
        infinite_configuration(order_seed=3, max_visible_orders=1)
    )

    generator = state.order_queue.generator
    assert generator is not None
    assert generator.seed == 3
    assert generator.max_visible == 1
    assert len(state.order_queue.visible) == 1


def test_infinite_orders_default_max_visible_is_pool_size() -> None:
    state = build_overcooked_state(infinite_configuration())

    generator = state.order_queue.generator
    assert generator is not None
    assert generator.max_visible == 2


def test_infinite_orders_requires_an_order_pool() -> None:
    configuration = infinite_configuration()
    configuration = configuration.copy_with(
        state=configuration.state.copy_with(orders=[])
    )

    with pytest.raises(ValueError):
        build_overcooked_state(configuration)


def test_time_limit_terminates_headless_run_and_reports_result() -> None:
    results: list[SimulationResult] = []

    recording = run_agent_mode(
        infinite_configuration(max_visible_orders=1),
        NeverFinishedController(),
        headless=True,
        end_conditions=EndConditions(time_limit_seconds=0.2),
        on_result=results.append,
    )

    assert len(results) == 1
    result = results[0]
    assert result.reason == "time_limit"
    assert result.elapsed_seconds >= 0.2
    assert result.timesteps == recording.environments[-1].timestep
    assert result.orders_remaining == 1


def test_completed_run_reports_result_with_score() -> None:
    configuration = Configuration.from_dict(
        {
            "layout": "|A|\n| |",
            "legend": {
                "agents": [{"kind": "agent", "symbol": "A"}],
                "foods": [{"kind": "food", "name": "catalog/food/tomato"}],
            },
        }
    )

    class _StepOnce(NeverFinishedController):
        def __init__(self) -> None:
            self._stepped = False

        def get_actions(
            self, environment: Environment, context: Context
        ) -> list[Mutation]:
            if self._stepped:
                return []
            self._stepped = True
            return super().get_actions(environment, context)

        def has_finished(self, environment: Environment) -> bool:
            return self._stepped

    results: list[SimulationResult] = []
    run_agent_mode(
        configuration,
        _StepOnce(),
        headless=True,
        on_result=results.append,
    )

    assert len(results) == 1
    assert results[0].reason == "completed"
    assert results[0].timesteps == 1
    assert results[0].orders_delivered == 0


def test_infinite_level_keeps_generating_orders_during_run() -> None:
    results: list[SimulationResult] = []
    recording = run_agent_mode(
        infinite_configuration(max_visible_orders=2),
        NeverFinishedController(),
        headless=True,
        end_conditions=EndConditions(time_limit_seconds=0.2),
        on_result=results.append,
    )

    state = recording.environments[-1].get_first_entity_of_type(OvercookedState)
    assert state is not None
    assert state is not None
    assert len(state.order_queue.visible) == 2

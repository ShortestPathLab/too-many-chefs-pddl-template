from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from unittest.mock import patch

from simulator.configuration.configuration import Configuration
from simulator.context import Context
from simulator.controller import Controller
from simulator.entities import Agent
from simulator.environment import Environment
from simulator.mutations import Mutation
from simulator.run import SimulationResult, run_agent_mode, run_play_mode
from tests.pddl_levels import coconut_juice_configuration
from tests.run_controllers import (
    AGENT_LEVEL,
    StepOnceController,
    TemporarilyIdleController,
)


def test_agent_mode_headless_records_each_environment() -> None:
    configuration = Configuration.from_dict(AGENT_LEVEL)

    recording = run_agent_mode(
        configuration,
        StepOnceController(),
        headless=True,
    )

    assert len(recording.environments) == 2
    assert recording.environments[0].timestep == 0
    assert recording.environments[1].timestep == 1

    first_agent = recording.environments[0].get_first_entity_of_type(Agent)
    second_agent = recording.environments[1].get_first_entity_of_type(Agent)
    assert first_agent is not None
    assert second_agent is not None
    assert first_agent is not None
    assert second_agent is not None
    assert (first_agent.x, first_agent.y) == (0, 0)
    assert (second_agent.x, second_agent.y) == (0, 1)


def test_agent_mode_does_not_finish_during_temporary_idle_tick() -> None:
    configuration = Configuration.from_dict(AGENT_LEVEL)

    recording = run_agent_mode(
        configuration,
        TemporarilyIdleController(),
        headless=True,
    )

    assert len(recording.environments) == 2
    moved_agent = recording.environments[-1].get_first_entity_of_type(Agent)
    assert moved_agent is not None
    assert (moved_agent.x, moved_agent.y) == (0, 1)


def test_visual_agent_mode_stays_running_during_temporary_idle_tick() -> None:
    configuration = Configuration.from_dict(AGENT_LEVEL)

    def run_two_ticks(
        environment: Environment,
        *,
        key_handler: Callable[..., object],
        tick_handler: Callable[..., object],
        **_: object,
    ) -> None:
        refresh_scene = lambda environment, mutations: None
        key_handler(
            SimpleNamespace(
                action=SimpleNamespace(keydown=True),
                key=SimpleNamespace(code="Space"),
            ),
            refresh_scene,
        )
        tick_handler(refresh_scene)
        tick_handler(refresh_scene)

    with patch("simulator.visualisation.launch", side_effect=run_two_ticks):
        recording = run_agent_mode(
            configuration,
            TemporarilyIdleController(),
        )

    assert len(recording.environments) == 2


def test_play_mode_launches_visualiser() -> None:
    configuration = Configuration.from_dict(
        {
            "layout": "|A|",
            "legend": {
                "agents": [{"kind": "agent", "symbol": "A"}],
                "foods": [{"kind": "food", "name": "catalog/food/tomato"}],
            },
        }
    )

    with patch("simulator.run.play.launch") as mock_launch:
        recording = run_play_mode(configuration)

    assert len(recording.environments) == 1
    mock_launch.assert_called_once()


class _GivesUpController(Controller):
    """Return no actions and report that planning stopped."""

    def get_actions(self, environment: Environment, context: Context) -> list[Mutation]:
        return []

    def is_busy(self) -> bool:
        return False

    def has_finished(self, environment: Environment) -> bool:
        return True

    def shutdown(self) -> None:
        pass


def test_a_controller_that_stops_with_orders_outstanding_has_not_completed() -> None:
    reported: list[SimulationResult] = []

    run_agent_mode(
        coconut_juice_configuration(),
        _GivesUpController(),
        headless=True,
        on_result=reported.append,
    )

    assert [result.reason for result in reported] == ["gave_up"]
    assert reported[0].orders_remaining == 1


def test_a_controller_that_stops_with_nothing_outstanding_has_completed() -> None:
    reported: list[SimulationResult] = []

    run_agent_mode(
        Configuration.from_dict(AGENT_LEVEL),
        _GivesUpController(),
        headless=True,
        on_result=reported.append,
    )

    assert [result.reason for result in reported] == ["completed"]

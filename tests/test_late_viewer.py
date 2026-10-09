"""Test what a page shows when it is opened after the run has moved on."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock, patch

from nicegui import ui

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.environment import Environment
from simulator.visualisation import launch
from tests.run_controllers import AGENT_LEVEL


def test_a_page_opened_mid_run_draws_the_kitchen_as_it_is_now() -> None:
    # A paused or finished run takes no further step, so nothing would ever
    # redraw a kitchen that started out stale.
    start = load(Configuration.from_dict(AGENT_LEVEL))
    later = start.copy_with(timestep=7)
    ticks: list[Callable[[], None]] = []
    drawn: list[Environment] = []

    def stack(environment: Environment, *_: object, **__: object) -> MagicMock:
        drawn.append(environment)
        return MagicMock()

    def two_viewers(build_root: Callable[[], None], **_: object) -> None:
        build_root()
        # The first viewer's timer moves the run on before the second arrives.
        ticks[0]()
        build_root()

    with (
        patch("simulator.visualisation.launch.serve", side_effect=two_viewers),
        patch(
            "simulator.visualisation.launch.ui.timer",
            side_effect=lambda interval, callback: ticks.append(callback),
        ),
        patch("simulator.visualisation.launch.world_stack", side_effect=stack),
        # Redrawing a panel needs a running event loop, which a test lacks.
        patch.object(ui.refreshable, "refresh"),
    ):
        launch(
            start,
            tick_handler=lambda refresh_scene: refresh_scene(later),
            tick_interval_ms=100,
            sound=False,
        )

    assert [environment.timestep for environment in drawn] == [0, 7]

from __future__ import annotations

from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.controller import Controller
from simulator.environment import Environment
from simulator.mutations import Mutation
from simulator.recording import Recording
from simulator.run import EndConditions, SimulationResult, run_agent_mode
from simulator.view import ending_words, summary_view
from simulator.visualisation import launch
from tests.run_controllers import AGENT_LEVEL, NeverFinishedController


def space() -> SimpleNamespace:
    return SimpleNamespace(
        action=SimpleNamespace(keydown=True),
        key=SimpleNamespace(code="Space"),
    )


def noop(environment: Environment, mutations: Sequence[Mutation] | None = None) -> None:
    return None


def drive_visual_run(
    controller: Controller,
    *,
    conditions: EndConditions | None = None,
    ticks: int = 6,
    press_space_after: bool = False,
) -> tuple[Recording, list[SimulationResult], dict[str, Any]]:
    """Run a visual agent session and inspect its ending card."""
    results: list[SimulationResult] = []
    seen: dict[str, Any] = {}

    def fake_launch(
        environment: Environment,
        *,
        key_handler: Any,
        tick_handler: Any,
        summary: Any = None,
        on_quit: Any = None,
        timeline: Any = None,
        **_: object,
    ) -> None:
        seen["card_before_start"] = summary()
        key_handler(space(), noop)
        seen["card_while_running"] = summary()
        seen["status_while_running"] = timeline(environment).status
        for _tick in range(ticks):
            tick_handler(noop)
        seen["card_at_end"] = summary()
        seen["status_at_end"] = timeline(environment).status
        # Taken before the window closes, so a card reported only on the way out
        # would show up as an empty list here.
        seen["reported_before_close"] = list(results)
        if press_space_after:
            key_handler(space(), noop)
            for _tick in range(ticks):
                tick_handler(noop)
        seen["on_quit"] = on_quit

    with patch("simulator.visualisation.launch", side_effect=fake_launch):
        recording = run_agent_mode(
            Configuration.from_dict(AGENT_LEVEL),
            controller,
            end_conditions=conditions,
            on_result=results.append,
        )
    return recording, results, seen


def test_the_card_appears_when_a_condition_ends_the_run() -> None:
    recording, _, seen = drive_visual_run(
        NeverFinishedController(),
        conditions=EndConditions(max_timesteps=2),
    )

    assert seen["card_before_start"] is None
    assert seen["card_while_running"] is None
    card = seen["card_at_end"]
    assert card is not None
    assert card.reason == "max_timesteps"
    assert card.headline == "Service over"
    assert card.timesteps == 2
    assert recording.environments[-1].timestep == 2


def test_the_result_is_reported_when_the_run_ends_not_when_it_closes() -> None:
    _, results, seen = drive_visual_run(
        NeverFinishedController(),
        conditions=EndConditions(max_timesteps=2),
    )

    assert len(seen["reported_before_close"]) == 1
    assert len(results) == 1
    assert results[0].reason == "max_timesteps"


def test_the_card_shows_the_numbers_that_were_reported() -> None:
    _, results, seen = drive_visual_run(
        NeverFinishedController(),
        conditions=EndConditions(max_timesteps=3),
    )

    assert seen["card_at_end"] == summary_view(results[0])


def test_the_timeline_says_the_run_is_finished() -> None:
    _, _, seen = drive_visual_run(
        NeverFinishedController(),
        conditions=EndConditions(max_timesteps=2),
    )

    assert seen["status_while_running"] == "Running"
    assert seen["status_at_end"] == "Finished"


def test_a_finished_run_cannot_be_started_again() -> None:
    recording, results, seen = drive_visual_run(
        NeverFinishedController(),
        conditions=EndConditions(max_timesteps=2),
        press_space_after=True,
    )

    assert recording.environments[-1].timestep == 2
    assert len(results) == 1
    assert seen["card_at_end"] is not None


def test_quitting_brings_the_app_down() -> None:
    with patch("simulator.visualisation.request_shutdown") as shutdown:
        _, _, seen = drive_visual_run(
            NeverFinishedController(),
            conditions=EndConditions(max_timesteps=1),
        )

        seen["on_quit"]()

    shutdown.assert_called_once_with()


def test_a_window_closed_early_reports_once_and_shows_no_card() -> None:
    _, results, seen = drive_visual_run(NeverFinishedController(), ticks=2)

    assert seen["card_at_end"] is None
    assert seen["reported_before_close"] == []
    assert len(results) == 1
    assert results[0].reason == "stopped"


def test_a_controller_finishing_on_its_own_also_ends_the_run() -> None:
    _, results, seen = drive_visual_run(_IdleController())

    card = seen["card_at_end"]
    assert card is not None
    assert card.reason == "completed"
    assert len(results) == 1


# Build the page as the browser would.
def build_page(card: Any) -> Any:
    environment = load(Configuration.from_dict(AGENT_LEVEL))

    with (
        patch(
            "simulator.visualisation.launch.serve",
            side_effect=lambda build_root, **_: build_root(),
        ),
        patch("simulator.visualisation.launch.summary_panel") as panel,
    ):
        launch(
            environment,
            title="Too Many Chefs - Agent",
            summary=lambda: card,
            on_quit=lambda: None,
            mode="Agent mode",
            show_info=False,
        )
    return panel


def test_a_running_page_draws_no_card() -> None:
    assert build_page(None).call_count == 0


def test_a_finished_page_draws_the_card_over_everything_else() -> None:
    card = summary_view(
        SimulationResult(
            reason="orders_delivered",
            score=50,
            timesteps=9,
            orders_delivered=1,
            orders_remaining=0,
            elapsed_seconds=1.5,
        )
    )

    panel = build_page(card)

    panel.assert_called_once()
    assert panel.call_args.args[0] is card


def result(**overrides: Any) -> SimulationResult:
    fields: dict[str, Any] = {
        "reason": "completed",
        "score": 120,
        "timesteps": 30,
        "orders_delivered": 2,
        "orders_remaining": 0,
        "elapsed_seconds": 4.25,
    }
    fields.update(overrides)
    return SimulationResult(**fields)


def test_every_reason_has_words_of_its_own() -> None:
    reasons = [
        "completed",
        "orders_delivered",
        "time_limit",
        "max_timesteps",
        "planning_budget_exhausted",
        "stopped",
    ]

    headlines = {reason: ending_words(reason) for reason in reasons}

    assert len(set(headlines.values())) == len(reasons)
    for headline, explanation in headlines.values():
        assert headline and explanation


def test_a_reason_nobody_wrote_words_for_reads_as_stopped() -> None:
    assert ending_words("something_else") == ending_words("stopped")


def test_the_card_carries_the_numbers_across() -> None:
    card = summary_view(result(reason="orders_delivered"))

    assert card.headline == "Every order served"
    assert card.score == 120
    assert card.delivered == 2
    assert card.remaining == 0
    assert card.timesteps == 30
    assert card.elapsed_label == "4.2s"
    assert card.served_everything


def test_a_rail_with_orders_left_on_it_is_not_a_clean_service() -> None:
    card = summary_view(result(reason="time_limit", orders_remaining=2))

    assert card.headline == "Time up"
    assert not card.served_everything


def test_delivering_nothing_is_not_a_clean_service() -> None:
    card = summary_view(result(orders_delivered=0, orders_remaining=0))

    assert not card.served_everything


class _IdleController(NeverFinishedController):
    """Return no actions and report completion."""

    def get_actions(self, environment: Environment, context: Any) -> list[Mutation]:
        return []

    def has_finished(self, environment: Environment) -> bool:
        return True


def test_a_run_that_ends_in_an_error_says_so_on_its_card() -> None:
    from tests.test_run_errors import FailingController

    _, results, seen = drive_visual_run(FailingController(calls=1))

    card = seen["card_at_end"]
    assert card is not None
    assert card.reason == "error"
    assert card.reason_label == "ControllerError: the controller broke"
    assert results[0].error is not None

"""Test watching a kitchen that something else steps."""

from __future__ import annotations

import threading
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from simulator.configuration import load
from simulator.configuration.configuration import Configuration
from simulator.entities import Agent
from simulator.environment import Environment
from simulator.mutations import MoveAgentForward, Mutation
from simulator.recording import Recording
from simulator.run import Episode, LiveFeed, LiveFrame, LiveViewer, run_live_mode
from simulator.visualisation import server
from tests.run_controllers import AGENT_LEVEL

WAIT = 5.0


def kitchen() -> Environment:
    return load(Configuration.from_dict(AGENT_LEVEL))


def walk(episode: Episode, steps: int) -> None:
    agent = episode.environment.get_first_entity_of_type(Agent)
    assert agent is not None
    for _ in range(steps):
        episode.advance([MoveAgentForward(agent_id=agent.id)])


def watching(viewers: list[int]) -> Callable[[], bool]:
    return lambda: viewers[0] > 0


def publish_in_background(
    feed: LiveFeed, recording: Recording, *, paced: bool
) -> threading.Thread:
    thread = threading.Thread(
        target=feed.publish, args=(recording,), kwargs={"paced": paced}, daemon=True
    )
    thread.start()
    return thread


def test_the_feed_holds_the_newest_step_of_the_newest_episode() -> None:
    feed = LiveFeed(has_viewers=lambda: True)
    first = Episode(kitchen(), on_step=feed.publish)
    walk(first, 1)

    assert feed.latest() == LiveFrame(episode=1, index=1, recording=first.recording)

    second = Episode(kitchen(), on_step=feed.publish)

    frame = feed.latest()
    assert frame is not None
    assert (frame.episode, frame.index, frame.recording) == (2, 0, second.recording)


def test_nothing_is_there_to_draw_before_the_first_step() -> None:
    assert LiveFeed(has_viewers=lambda: True).latest() is None


def test_a_paced_kitchen_waits_until_its_step_is_drawn() -> None:
    feed = LiveFeed(has_viewers=lambda: True, poll_seconds=0.01)
    recording = Recording(environments=[kitchen()], mutations=[[]])

    publisher = publish_in_background(feed, recording, paced=True)
    publisher.join(0.1)
    assert publisher.is_alive()

    frame = feed.latest()
    assert frame is not None
    feed.shown(frame)
    publisher.join(WAIT)
    assert not publisher.is_alive()


def test_a_paced_kitchen_stops_waiting_when_the_last_viewer_leaves() -> None:
    viewers = [1]
    feed = LiveFeed(has_viewers=watching(viewers), poll_seconds=0.01)
    recording = Recording(environments=[kitchen()], mutations=[[]])

    publisher = publish_in_background(feed, recording, paced=True)
    publisher.join(0.1)
    assert publisher.is_alive()

    viewers[0] = 0
    publisher.join(WAIT)
    assert not publisher.is_alive()


def test_closing_the_feed_releases_a_waiting_kitchen() -> None:
    feed = LiveFeed(has_viewers=lambda: True, poll_seconds=10)
    recording = Recording(environments=[kitchen()], mutations=[[]])

    publisher = publish_in_background(feed, recording, paced=True)
    publisher.join(0.1)
    feed.close()
    publisher.join(WAIT)

    assert not publisher.is_alive()
    assert feed.closed


def test_an_unpaced_kitchen_never_waits() -> None:
    feed = LiveFeed(has_viewers=lambda: True)

    episode = Episode(kitchen(), on_step=feed.publish)
    walk(episode, 3)

    frame = feed.latest()
    assert frame is not None
    assert frame.index == 3


class _Page:
    """Capture the handlers a run mode gives the visualiser."""

    def __init__(self) -> None:
        self.tick: Callable[[Any], None] | None = None
        self.key: Callable[[Any, Any], None] | None = None
        self.draws: list[tuple[int, list[Mutation]]] = []
        # A real page keeps one refresh function for its lifetime, and the
        # live mode tracks each page by it.
        self.refresh = self._refresh

    def launch(self, environment: Environment, **kwargs: Any) -> None:
        self.tick = kwargs["tick_handler"]
        self.key = kwargs["key_handler"]
        self.timeline = kwargs["timeline"]
        assert kwargs["background"] is True

    def _refresh(self, environment: Environment, mutations: list[Mutation]) -> None:
        self.draws.append((environment.timestep, list(mutations)))

    def press_space(self) -> None:
        assert self.key is not None
        event = SimpleNamespace(
            action=SimpleNamespace(keydown=True), key=SimpleNamespace(code="Space")
        )
        self.key(event, self.refresh)


def open_page(feed: LiveFeed, environment: Environment) -> _Page:
    page = _Page()
    with patch("simulator.run.live.launch", side_effect=page.launch):
        run_live_mode(feed, environment, background=True)
    return page


def test_the_page_animates_a_step_that_follows_the_last_one_it_drew() -> None:
    feed = LiveFeed(has_viewers=lambda: True)
    episode = Episode(kitchen(), on_step=feed.publish)
    page = open_page(feed, episode.environment)
    assert page.tick is not None

    page.tick(page.refresh)
    walk(episode, 1)
    page.tick(page.refresh)

    assert [timestep for timestep, _ in page.draws] == [0, 1]
    assert len(page.draws[1][1]) == 1


def test_the_page_jumps_over_steps_it_had_no_time_to_draw() -> None:
    feed = LiveFeed(has_viewers=lambda: True)
    episode = Episode(kitchen(), on_step=feed.publish)
    page = open_page(feed, episode.environment)
    assert page.tick is not None

    page.tick(page.refresh)
    walk(episode, 3)
    page.tick(page.refresh)

    assert page.draws[-1] == (3, [])


def test_a_new_episode_is_drawn_without_animation() -> None:
    feed = LiveFeed(has_viewers=lambda: True)
    episode = Episode(kitchen(), on_step=feed.publish)
    page = open_page(feed, episode.environment)
    assert page.tick is not None
    walk(episode, 1)
    page.tick(page.refresh)

    Episode(kitchen(), on_step=feed.publish)
    page.tick(page.refresh)

    assert page.draws[-1] == (0, [])
    assert "Episode 2" in page.timeline(kitchen()).rate_label


def test_a_paused_page_draws_nothing_and_holds_a_paced_kitchen() -> None:
    feed = LiveFeed(has_viewers=lambda: True, poll_seconds=0.01)
    recording = Recording(environments=[kitchen()], mutations=[[]])
    page = open_page(feed, recording.environments[0])
    assert page.tick is not None

    page.press_space()
    publisher = publish_in_background(feed, recording, paced=True)
    page.tick(page.refresh)
    publisher.join(0.1)

    assert publisher.is_alive()
    assert page.timeline(kitchen()).status == "Paused"

    page.press_space()
    page.tick(page.refresh)
    publisher.join(WAIT)
    assert not publisher.is_alive()


def test_the_viewer_refuses_a_kitchen_of_another_level(
    capsys: pytest.CaptureFixture[str],
) -> None:
    viewer = LiveViewer(kitchen())
    other = load(
        Configuration.from_dict(
            {
                "layout": "|A| |",
                "legend": {"agents": [{"kind": "agent", "symbol": "A"}]},
            }
        )
    )

    assert viewer._accepts(kitchen())
    assert not viewer._accepts(other)
    assert not viewer._accepts(other)
    assert capsys.readouterr().out.count("ANOTHER LEVEL IS SHOWING") == 1


def test_a_background_visualiser_leaves_signals_to_the_main_thread() -> None:
    with (
        patch.object(server, "install_shutdown_signal_handlers") as install,
        patch.object(server, "restore_signal_handlers") as restore,
        patch.object(server, "_claim_port", return_value=8080),
        patch.object(server.ui, "run"),
    ):
        server.serve(lambda: None, title="Live", open_window=False, background=True)

    install.assert_not_called()
    restore.assert_not_called()

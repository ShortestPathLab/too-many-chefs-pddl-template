"""Watch a kitchen that something else is stepping.

The other run modes own their clock: the visualiser's timer decides when the
kitchen steps. A training loop owns its own clock and steps when it is ready.
``LiveFeed`` carries its steps across threads, ``run_live_mode`` shows them
with the usual panels, and ``LiveViewer`` runs that visualiser on a background
thread, once per process, for any kitchen that asks to be watched.

A paced kitchen waits for the visualiser to draw each step before it takes the
next, so every step animates and pausing the visualiser pauses the kitchen. An
unpaced kitchen never waits. The visualiser then draws the newest step on each
tick, and a chef that moved several tiles since the last one it drew jumps
there instead of walking.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar, cast
from weakref import WeakKeyDictionary

from nicegui.events import KeyEventArguments

from simulator import console
from simulator.entities import Agent, Bounds
from simulator.environment import Environment
from simulator.mutations import Mutation
from simulator.recording import Recording
from simulator.view import ActionsView, actions_view, badge_order, timeline_view
from simulator.visualisation import RefreshScene, launch
from simulator.visualisation.server import count_viewers

from .common import LIVE_CONTROLS, VISUAL_STEP_INTERVAL_MS

# How long a paced kitchen waits for someone to open the visualiser at first.
FIRST_VIEWER_TIMEOUT = 60.0

# Where a frame sits: which episode, and which environment in it.
Position = tuple[int, int]


@dataclass(frozen=True)
class LiveFrame:
    """One published step, read from the episode's recording."""

    #: Counts the episodes published to the feed, from 1.
    episode: int
    index: int
    recording: Recording
    #: The timestep the episode ends at, when there is a limit.
    total: int | None = None

    @property
    def position(self) -> Position:
        return (self.episode, self.index)

    @property
    def environment(self) -> Environment:
        return self.recording.environments[self.index]

    @property
    def mutations(self) -> list[Mutation]:
        return cast(list[Mutation], self.recording.mutations[self.index])


class LiveFeed:
    """Hand steps from a kitchen on one thread to a visualiser on another.

    The kitchen calls ``publish`` with its recording after every step, as an
    ``Episode`` listener. A new recording starts a new episode. The visualiser
    reads the newest step with ``latest`` and reports each one it drew with
    ``shown``. ``has_viewers`` tells a paced kitchen whether anyone is left to
    wait for.
    """

    def __init__(
        self,
        *,
        has_viewers: Callable[[], bool],
        poll_seconds: float = 0.25,
    ) -> None:
        self._has_viewers = has_viewers
        self._poll_seconds = poll_seconds
        self._condition = threading.Condition()
        self._recording: Recording | None = None
        self._episode = 0
        self._index = -1
        self._total: int | None = None
        self._shown: Position = (0, -1)
        self._closed = False

    def publish(
        self,
        recording: Recording,
        *,
        paced: bool = False,
        total: int | None = None,
    ) -> None:
        """Make the recording's newest step the one to draw.

        A paced publish returns once a visualiser has drawn the step, the last
        viewer has gone, or the feed has closed.
        """
        with self._condition:
            if self._closed:
                return
            if recording is not self._recording:
                self._recording = recording
                self._episode += 1
            self._index = len(recording.environments) - 1
            self._total = total
            position = (self._episode, self._index)
            self._condition.notify_all()
            while (
                paced
                and not self._closed
                and self._shown < position
                and self._has_viewers()
            ):
                self._condition.wait(self._poll_seconds)

    def latest(self) -> LiveFrame | None:
        """Return the newest published step, or ``None`` before the first."""
        with self._condition:
            if self._recording is None:
                return None
            return LiveFrame(
                episode=self._episode,
                index=self._index,
                recording=self._recording,
                total=self._total,
            )

    def shown(self, frame: LiveFrame) -> None:
        """Record that a visualiser drew ``frame``, releasing a paced kitchen."""
        with self._condition:
            if frame.position > self._shown:
                self._shown = frame.position
                self._condition.notify_all()

    def close(self) -> None:
        """Stop accepting steps and release any kitchen waiting on one."""
        with self._condition:
            self._closed = True
            self._condition.notify_all()

    @property
    def closed(self) -> bool:
        return self._closed


def run_live_mode(
    feed: LiveFeed,
    environment: Environment,
    *,
    level_label: str = "",
    open_window: bool = True,
    background: bool = False,
) -> None:
    """Show whatever ``feed`` publishes until the visualiser stops.

    ``environment`` is the level's first environment. It sets the kitchen's
    size and the chefs the panels list, so the feed should carry that level.
    """
    following = True
    # The newest frame any viewer drew, for the panels.
    drawn: LiveFrame | None = None
    # Each viewer's page has its own refresh function and may lag the others.
    shown_by_page: WeakKeyDictionary[RefreshScene, Position] = WeakKeyDictionary()
    agent_order = [agent.id for agent in badge_order(environment)]

    def current_environment() -> Environment:
        return drawn.environment if drawn is not None else environment

    def tick(refresh_scene: RefreshScene) -> None:
        nonlocal drawn
        if not following:
            return
        frame = feed.latest()
        if frame is None:
            return
        before = shown_by_page.get(refresh_scene)
        if before == frame.position:
            return
        # Animate only a step that follows the last one this page drew.
        follows = before == (frame.episode, frame.index - 1)
        shown_by_page[refresh_scene] = frame.position
        drawn = frame
        refresh_scene(frame.environment, frame.mutations if follows else [])
        feed.shown(frame)

    def handle_key(event: KeyEventArguments, refresh_scene: RefreshScene) -> None:
        nonlocal following
        if not event.action.keydown or event.key.code != "Space":
            return
        following = not following
        refresh_scene(current_environment(), [])

    def actions(active: Environment) -> ActionsView:
        if drawn is None:
            return ActionsView()
        return actions_view(drawn.recording, active, order=agent_order)

    def status() -> str:
        if not following:
            return "Paused"
        return "Following" if drawn is not None else "Waiting"

    launch(
        environment,
        key_handler=handle_key,
        tick_handler=tick,
        tick_interval_ms=VISUAL_STEP_INTERVAL_MS,
        title="Too Many Chefs - Live",
        controls=LIVE_CONTROLS,
        actions=actions,
        timeline=lambda active: timeline_view(
            active,
            total=drawn.total if drawn is not None else None,
            rate_label=f"Episode {drawn.episode}" if drawn is not None else "",
            status=status(),
        ),
        mode="Live mode",
        level_label=level_label,
        show_info=False,
        open_window=open_window,
        background=background,
    )


class LiveViewer:
    """A live visualiser on a background thread, shared by the whole process.

    NiceGUI serves one app per process, so the first kitchen that asks to be
    watched starts the viewer and later kitchens publish to the same one. The
    page is built for the first kitchen's level. A kitchen with a different
    size or different chefs is not shown.

    Closing the window leaves the process running. The viewer keeps serving,
    so its link still works, and a paced kitchen stops waiting once nobody is
    connected.
    """

    _shared: ClassVar[LiveViewer | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(
        self,
        environment: Environment,
        *,
        level_label: str = "",
        open_window: bool = True,
    ) -> None:
        self.feed = LiveFeed(has_viewers=lambda: count_viewers() > 0)
        self._environment = environment
        self._layout = _layout(environment)
        self._level_label = level_label
        self._open_window = open_window
        self._waited_for_viewer = False
        self._refused: set[tuple[object, ...]] = set()
        self._thread = threading.Thread(
            target=self._run,
            name="too-many-chefs-live-viewer",
            daemon=True,
        )

    @classmethod
    def for_environment(
        cls,
        environment: Environment,
        *,
        level_label: str = "",
        open_window: bool = True,
    ) -> LiveViewer | None:
        """Return the process's viewer, starting it for this level if needed.

        Returns ``None``, after a warning, when the viewer already shows a
        different level or has stopped.
        """
        with cls._lock:
            if cls._shared is None:
                cls._shared = cls(
                    environment,
                    level_label=level_label,
                    open_window=open_window,
                )
                cls._shared._thread.start()
            viewer = cls._shared
        return viewer if viewer._accepts(environment) else None

    def wait_for_first_viewer(self, timeout: float = FIRST_VIEWER_TIMEOUT) -> bool:
        """Wait, once per viewer, for someone to open the visualiser.

        A paced kitchen calls this before its first step, so the start of the
        episode is not over before the window has loaded. Returns whether
        anyone is watching.
        """
        if self._waited_for_viewer:
            return count_viewers() > 0
        self._waited_for_viewer = True
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not self.feed.closed:
            if count_viewers() > 0:
                return True
            time.sleep(0.1)
        console.warn(
            f"Nobody opened the visualiser within {timeout:.0f} seconds, so the"
            " kitchen is carrying on without waiting. Open the link to watch"
            " from wherever it has got to.",
            title="NOBODY IS WATCHING",
        )
        return False

    def _accepts(self, environment: Environment) -> bool:
        if self.feed.closed:
            return False
        layout = _layout(environment)
        if layout == self._layout:
            return True
        if layout not in self._refused:
            self._refused.add(layout)
            console.warn(
                "The live visualiser is showing a different level, and one"
                " process can only show one. This kitchen will not be drawn."
                " Watch it from a separate process, or save its recording for"
                " cook replay.",
                title="ANOTHER LEVEL IS SHOWING",
            )
        return False

    def _run(self) -> None:
        try:
            run_live_mode(
                self.feed,
                self._environment,
                level_label=self._level_label,
                open_window=self._open_window,
                background=True,
            )
        except Exception as error:  # noqa: BLE001 - training must outlive its viewer
            console.warn(str(error), title="THE LIVE VISUALISER STOPPED")
        finally:
            self.feed.close()


def _layout(environment: Environment) -> tuple[object, ...]:
    """What the page was built around: the kitchen's size and its chefs."""
    bounds = environment.get_first_entity_of_type(Bounds)
    size = (bounds.width, bounds.height) if bounds is not None else None
    chefs = tuple(sorted(agent.id for agent in environment.get_entities_of_type(Agent)))
    return (size, chefs)

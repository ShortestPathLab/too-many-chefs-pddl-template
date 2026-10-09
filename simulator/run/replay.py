from __future__ import annotations

from typing import cast

from nicegui.events import KeyEventArguments

from simulator.mutations import Mutation
from simulator.recording import Recording
from simulator.view import actions_view, badge_order, timeline_view
from simulator.visualisation import RefreshScene, launch

from .common import (
    REPLAY_CONTROLS,
    VISUAL_STEP_INTERVAL_MS,
)


def run_replay_mode(
    recording: Recording,
    *,
    level_label: str = "",
    open_window: bool = True,
) -> None:
    if not recording.environments:
        raise ValueError("Cannot replay an empty recording")

    environment_index = 0
    is_playing = False
    playback_started = False

    def render_environment(index: int, refresh_scene: RefreshScene) -> None:
        mutations = (
            recording.mutations[index] if index < len(recording.mutations) else []
        )
        refresh_scene(
            recording.environments[index],
            cast(list[Mutation], mutations),
        )

    def tick(refresh_scene: RefreshScene) -> None:
        nonlocal environment_index, is_playing
        if not playback_started or not is_playing:
            return
        if environment_index >= len(recording.environments) - 1:
            is_playing = False
            render_environment(environment_index, refresh_scene)
            return

        environment_index += 1
        render_environment(environment_index, refresh_scene)

    def handle_key(event: KeyEventArguments, refresh_scene: RefreshScene) -> None:
        nonlocal environment_index, is_playing, playback_started
        if not event.action.keydown:
            return

        if event.key.code == "Space":
            playback_started = True
            is_playing = not is_playing
            render_environment(environment_index, refresh_scene)
            return

        if event.key.code == "ArrowRight":
            playback_started = True
            is_playing = False
            if environment_index >= len(recording.environments) - 1:
                return
            environment_index += 1
            render_environment(environment_index, refresh_scene)
            return

        if event.key.code == "ArrowLeft":
            playback_started = True
            is_playing = False
            if environment_index <= 0:
                return
            environment_index -= 1
            render_environment(environment_index, refresh_scene)

    launch(
        recording.environments[0],
        key_handler=handle_key,
        tick_handler=tick,
        tick_interval_ms=VISUAL_STEP_INTERVAL_MS,
        title="Too Many Chefs - Replay",
        controls=REPLAY_CONTROLS,
        actions=lambda current_environment: actions_view(
            recording,
            current_environment,
            order=[agent.id for agent in badge_order(recording.environments[0])],
        ),
        timeline=lambda current_environment: timeline_view(
            current_environment,
            total=recording.environments[-1].timestep,
            rate_label=f"{VISUAL_STEP_INTERVAL_MS}ms / step",
            status="Playing" if is_playing else "Paused",
        ),
        mode="Replay mode",
        level_label=level_label,
        show_info=False,
        open_window=open_window,
    )

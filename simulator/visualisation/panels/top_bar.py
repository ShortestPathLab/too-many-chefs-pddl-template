"""Render the top bar and timeline."""

from __future__ import annotations

from nicegui import ui

from simulator.view import ScoreView, TimelineView
from simulator.visualisation.panels.common import counter
from simulator.visualisation.panels.score import score_panel
from simulator.visualisation.theme import (
    ACCENT_INK,
    CENTRE,
    CHIP,
    COUNTER_DIGITS,
    COUNTER_TEXT,
    INK_FAINT,
    PALETTE,
    PANEL,
    SPACER,
    STEEL,
    SURFACE_GROOVE,
    TEXT_SMALL,
    TRACK_FILL_TO_HANDLE,
    TRACK_SHAPE,
)


def top_bar(*, timeline: TimelineView, score: ScoreView | None = None) -> None:
    # The left rail runs the full height beside this bar, and the score takes
    # the same width on the right, so the timeline stays centred.
    with ui.row().classes("w-full items-start gap-2 flex-nowrap"):
        timeline_panel(timeline)

        with ui.column().classes(SPACER):
            if score is not None:
                score_panel(score)


def timeline_panel(timeline: TimelineView) -> None:
    with (
        ui.row().classes("flex-1 min-w-0"),
        ui.row().classes(
            f"{PANEL} {STEEL} {CENTRE} items-center gap-2 flex-nowrap min-w-0"
        ),
    ):
        counter(timeline.timestep, digits=COUNTER_DIGITS, classes=COUNTER_TEXT)
        with ui.column().classes("flex-1 gap-1 min-w-0"):
            # The marker stands proud of the track, so the track's clipped
            # corners belong to a layer of their own beneath it.
            with ui.element("div").classes("relative w-full h-1.5"):
                ui.element("div").classes(
                    f"{TRACK_SHAPE} {SURFACE_GROOVE} absolute inset-0"
                )
                # Use a dim fill when the run has no known end.
                fill = "bg-sky-900" if timeline.live else "bg-sky-400"
                ui.element("div").classes(
                    f"{TRACK_FILL_TO_HANDLE} absolute inset-y-0 left-0 {fill}"
                ).style(
                    f"width: {timeline.progress * 100:.2f}%;"
                    " transition: width 160ms linear"
                )
                # The handle stands proud of the track by the same amount
                # above and below.
                ui.element("div").classes(
                    f"absolute -top-1 w-1 h-3.5 bg-[{PALETTE.ink}]"
                ).style(
                    f"left: {timeline.progress * 100:.2f}%;"
                    " transition: left 160ms linear"
                )
            with ui.row().classes(
                f"w-full justify-between {TEXT_SMALL} {INK_FAINT} flex-nowrap"
            ):
                ui.label("T 0")
                ui.label(timeline.rate_label)
                ui.label(timeline.position_label)
        # Show status for modes that can be started or stopped.
        if timeline.status:
            ui.label(timeline.status).classes(f"{CHIP} {ACCENT_INK} shrink-0")

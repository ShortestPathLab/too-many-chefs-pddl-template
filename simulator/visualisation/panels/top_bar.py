"""Render the top bar and timeline."""

from __future__ import annotations

from nicegui import ui

from simulator.view import ScoreView, TimelineView
from simulator.visualisation.panels.common import counter
from simulator.visualisation.panels.score import score_panel
from simulator.visualisation.theme import (
    ACCENT_EDGE,
    ACCENT_INK,
    CENTRE,
    CHIP,
    COUNTER_DIGITS,
    COUNTER_TEXT,
    INK_DIM,
    INK_FAINT,
    PALETTE,
    PANEL,
    RAIL,
    SPACER,
    TEXT_SMALL,
    TITLE,
    TRACK,
    TRACK_FILL,
)


def top_bar(
    *,
    level_label: str,
    level_name: str | None = None,
    description: str | None = None,
    timeline: TimelineView,
    score: ScoreView | None = None,
) -> None:
    # Reserve both rail widths so the timeline stays centered.
    with ui.row().classes("w-full items-stretch gap-2 flex-nowrap"):
        with (
            ui.row().classes(
                f"{PANEL} {RAIL} shrink-0 items-center justify-between flex-nowrap"
            ),
            ui.column().classes("gap-0 min-w-0"),
        ):
            ui.label((level_name or "").strip() or level_label).classes(
                f"{TITLE} leading-tight break-words"
            )
            if description and description.strip():
                ui.label(description.strip()).classes(
                    f"{TEXT_SMALL} {INK_DIM} leading-snug break-words mt-1"
                )

        timeline_panel(timeline)

        with ui.column().classes(f"{SPACER} self-start"):
            if score is not None:
                score_panel(score)


def timeline_panel(timeline: TimelineView) -> None:
    with (
        ui.row().classes("flex-1 min-w-0"),
        ui.row().classes(f"{PANEL} {CENTRE} items-center gap-2 flex-nowrap min-w-0"),
    ):
        counter(timeline.timestep, digits=COUNTER_DIGITS, classes=COUNTER_TEXT)
        with ui.column().classes("flex-1 gap-1 min-w-0"):
            with ui.element("div").classes(TRACK):
                # Use a dim fill when the run has no known end.
                fill = "bg-sky-900" if timeline.live else "bg-sky-400"
                ui.element("div").classes(
                    f"{TRACK_FILL} absolute inset-y-0 left-0 {fill}"
                ).style(
                    f"width: {timeline.progress * 100:.2f}%;"
                    " transition: width 160ms linear"
                )
                # Extend the position marker beyond the track.
                ui.element("div").classes(
                    f"absolute -top-1 w-1 h-4 bg-[{PALETTE.ink}]"
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
            ui.label(timeline.status).classes(
                f"{CHIP} {ACCENT_EDGE} {ACCENT_INK} shrink-0"
            )

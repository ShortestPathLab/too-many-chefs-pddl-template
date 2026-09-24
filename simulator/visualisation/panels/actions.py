"""The action log, along the bottom of the screen."""

from __future__ import annotations

from nicegui import ui

from simulator.view import ActionLine, ActionsView
from simulator.visualisation.panels.common import panel_head
from simulator.visualisation.theme import (
    CENTRE,
    INK,
    INK_FAINT,
    INK_GHOST,
    PANEL_FRAME,
    RULE,
    TEXT,
)


def actions_panel(view: ActionsView) -> None:
    # Set to the same measure as the timeline directly above it, so the two
    # panels that belong to neither rail read as one column down the middle.
    with ui.column().classes(f"{PANEL_FRAME} {CENTRE} min-w-0 overflow-x-auto"):
        panel_head("Actions")
        # Reverse the list so new lines remain at the bottom.
        with ui.element("div").classes(
            "w-full min-w-max flex flex-col-reverse px-2 py-1 overflow-y-auto"
        ):
            if not view.lines:
                ui.label(view.empty_label).classes(f"{TEXT} {INK_GHOST} py-0.5")
            for line in reversed(view.lines):
                _action_line(line)


def _action_line(line: ActionLine) -> None:
    step_tone = "text-amber-400" if line.current else INK_GHOST
    text_tone = INK if line.current else INK_FAINT
    with ui.row().classes(
        f"w-full items-baseline gap-2 flex-nowrap py-0.5 border-b-2 {RULE}"
    ):
        ui.label(f"T{line.step}").classes(
            f"{TEXT} tabular-nums w-12 shrink-0 {step_tone}"
        )
        ui.label(line.text).classes(f"{TEXT} break-words min-w-0 {text_tone}")

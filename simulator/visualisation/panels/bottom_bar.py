"""The log along the bottom, and the stack of panels down the right.

Each panel is passed the view it should show, or ``None`` to leave it out, so
the decision about what a run mode displays stays with the caller and the
layout stays here.
"""

from __future__ import annotations

from nicegui import ui

from simulator.view import ActionsView, AgentsView
from simulator.visualisation.panels.actions import actions_panel
from simulator.visualisation.panels.agents import agents_panel
from simulator.visualisation.panels.common import controls_panel, value_panel
from simulator.visualisation.theme import ACCENT_EDGE, ACCENT_INK, CHIP, RAIL
from simulator.visualisation.types import HudSection


def bottom_bar(
    *,
    actions: ActionsView | None,
    agents: AgentsView | None,
    info: HudSection | None,
) -> None:
    with ui.row().classes("w-full items-end gap-2 flex-nowrap"):
        with ui.row().classes("flex-1 min-w-0"):
            if actions is not None:
                actions_panel(actions)
        if info is not None or agents is not None:
            right_rail(agents=agents, info=info)


def right_rail(
    *,
    agents: AgentsView | None,
    info: HudSection | None,
) -> None:
    # Keep mode information and agent details above the keyboard hints.
    with ui.column().classes(f"{RAIL} shrink-0 gap-2 items-end ml-auto"):
        if info is not None:
            value_panel(info)
        if agents is not None:
            agents_panel(agents)


def controls_bar(*, mode: str, controls: HudSection | None) -> None:
    """A viewport-wide footer with the mode on the left and hints on the right."""
    with ui.row().classes("w-full shrink-0 items-center gap-x-6 gap-y-2 flex-nowrap"):
        ui.label(mode).classes(
            f"{CHIP} {ACCENT_EDGE} {ACCENT_INK}  shrink-0 [text-shadow:_1px_1px_0px_rgba(0,0,0,0.3)]"
        )
        with ui.column().classes("flex-1 min-w-0"):
            if controls is not None:
                controls_panel(controls)

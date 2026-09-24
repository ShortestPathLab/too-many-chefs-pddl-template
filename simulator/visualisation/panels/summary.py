"""Render the ending summary card."""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

from simulator.view import SummaryView
from simulator.visualisation.panels.common import panel_head, row
from simulator.visualisation.theme import (
    BUTTON,
    CHIP,
    DISPLAY,
    INK,
    INK_DIM,
    INK_FAINT,
    PANEL_BODY,
    PANEL_FRAME,
    RULE,
    RULE_LIGHT,
    SCRIM,
    TEXT,
    TITLE,
    team_ink,
)


def summary_panel(view: SummaryView, *, on_quit: Callable[[], None]) -> None:
    """Render the ending card over the kitchen."""

    def handle_quit():
        on_quit()

    with (
        ui.element("div").classes(SCRIM),
        ui.column().classes(PANEL_FRAME + " w-80"),
    ):
        panel_head("Run over")
        with ui.column().classes(PANEL_BODY + " gap-1.5 py-2"):
            headline = "text-amber-300" if view.served_everything else INK
            ui.label(view.headline).classes(f"{DISPLAY} {headline}")
            # Show the contest result before the end reason.
            if view.contested:
                winner = view.winner
                ui.label(view.verdict).classes(
                    f"{TITLE} {team_ink(winner.name) if winner else INK}"
                )
            ui.label(view.reason_label).classes(f"{TEXT} {INK_DIM} break-words")
            with ui.element("div").classes(f"w-full border-t-2 {RULE} my-0.5"):
                pass
            row("Tips", str(view.score))
            for team in view.teams:
                row(team.label, str(team.score))
            if view.split_worth_showing:
                for agent in view.agents:
                    row(f"Chef {agent.number}", str(agent.score))
            row("Delivered", str(view.delivered))
            row("Left on the rail", str(view.remaining))
            row("Timesteps", str(view.timesteps))
            row("Elapsed", view.elapsed_label)
            with ui.row().classes("w-full items-center justify-between gap-2 pt-1"):
                ui.label(view.reason).classes(
                    f"{CHIP} {RULE_LIGHT} {INK_FAINT} truncate"
                )
                # Let the theme control the button radius.
                ui.button("Quit", on_click=lambda: handle_quit()).classes(BUTTON).props(
                    "flat dense no-caps"
                )

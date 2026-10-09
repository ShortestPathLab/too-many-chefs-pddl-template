"""Render the ending summary: a receipt for the run, printed over the kitchen."""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

from simulator.view import SummaryView
from simulator.visualisation.panels.common import fringe
from simulator.visualisation.theme import (
    BUTTON,
    RECEIPT,
    RECEIPT_BODY,
    RECEIPT_CAPTION,
    RECEIPT_HEADLINE,
    RECEIPT_LEADER,
    RECEIPT_LINE,
    RECEIPT_ROW,
    RECEIPT_RULE,
    SCRIM,
    team_paper_ink,
)


def summary_panel(view: SummaryView, *, on_quit: Callable[[], None]) -> None:
    """Render the ending slip over the kitchen."""

    def handle_quit():
        on_quit()

    with ui.element("div").classes(SCRIM):
        with ui.column().classes(RECEIPT):
            fringe()
            with ui.column().classes(RECEIPT_BODY):
                ui.label("Run over").classes(RECEIPT_CAPTION)
                _outcome(view)
                _rule()
                _row("Tips", str(view.score))
                for team in view.teams:
                    _row(team.label, str(team.score))
                if view.split_worth_showing:
                    for agent in view.agents:
                        _row(f"Chef {agent.number}", str(agent.score))
                _rule()
                _row("Delivered", str(view.delivered))
                _row("Left on the rail", str(view.remaining))
                _row("Timesteps", str(view.timesteps))
                _row("Elapsed", view.elapsed_label)
                _rule()
                # The name the result file gives this ending.
                ui.label(view.reason).classes(RECEIPT_CAPTION)
            fringe()
        # Let the theme control the button radius.
        ui.button("Quit", on_click=lambda: handle_quit()).classes(BUTTON).props(
            "flat dense no-caps"
        )


def _outcome(view: SummaryView) -> None:
    """Say how the run came out, then why it stopped.

    A contest leads with who won, in their colour. How the run ended is the
    smaller line under it.
    """
    if view.contested:
        winner = view.winner
        tone = team_paper_ink(winner.name) if winner else ""
        ui.label(view.verdict).classes(f"{RECEIPT_HEADLINE} {tone}")
        ui.label(view.headline).classes(RECEIPT_LINE)
    else:
        ui.label(view.headline).classes(RECEIPT_HEADLINE)
    ui.label(view.reason_label).classes(RECEIPT_LINE)


def _rule() -> None:
    ui.element("div").classes(RECEIPT_RULE)


def _row(label: str, value: str) -> None:
    with ui.row().classes(RECEIPT_ROW):
        ui.label(label)
        ui.element("div").classes(RECEIPT_LEADER)
        ui.label(value)

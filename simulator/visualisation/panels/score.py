"""Render the score panel."""

from __future__ import annotations

from nicegui import ui

from simulator.view import ScoreView, TeamScore
from simulator.visualisation.theme import (
    CHIP,
    DISPLAY,
    INK_DIM,
    LABEL,
    PANEL,
    TEXT,
    team_tone,
)


def score_panel(view: ScoreView) -> None:
    """Render the kitchen total and team totals."""
    with ui.row().classes(
        f"{PANEL} w-1/2 self-end items-center justify-between flex-wrap"
    ):
        with ui.column().classes("gap-0"):
            ui.label("Tips").classes(LABEL)
        # Show team totals beside the kitchen total.
        with ui.column().classes("gap-0 items-end min-w-0"):
            ui.label(str(view.score)).classes(f"{DISPLAY} text-amber-300")
            ui.label(f"{view.delivered} delivered").classes(f"{TEXT} {INK_DIM}")
            for team in view.teams:
                team_tally(team)


def team_tally(team: TeamScore) -> None:
    """Render one team total."""
    with ui.row().classes("items-center gap-1 flex-nowrap"):
        ui.label(team.label).classes(f"{CHIP} {team_tone(team.name)} truncate")
        ui.label(str(team.score)).classes(f"{TEXT} tabular-nums")

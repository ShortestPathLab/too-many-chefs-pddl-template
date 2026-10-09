"""Render the tips board, or one board for each team in a contest."""

from __future__ import annotations

from nicegui import ui

from simulator.view import ScoreView, TeamScore
from simulator.visualisation.theme import (
    BOARD,
    BOARD_LABEL,
    BOARD_SOLO,
    BOARD_TEAM,
    BOARDS,
    CHALK_DIM,
    CHALK_GOLD,
    DISPLAY,
    TEXT,
    team_ink,
)


def score_panel(view: ScoreView) -> None:
    """Chalk up the kitchen's tips, or each team's when teams compete.

    In a contest the kitchen's total says nothing about who is ahead, so it
    gives way to a board for each team.
    """
    with ui.row().classes(BOARDS):
        if view.contested:
            for team in view.teams:
                _team_board(team)
        else:
            _tips_board(view)


def _tips_board(view: ScoreView) -> None:
    with ui.row().classes(
        f"{BOARD} {BOARD_SOLO} items-start justify-between flex-nowrap"
    ):
        ui.label("Tips").classes(f"{BOARD_LABEL} text-[{CHALK_DIM}]")
        with ui.column().classes("gap-0 items-end min-w-0"):
            ui.label(str(view.score)).classes(f"{DISPLAY} text-[{CHALK_GOLD}]")
            ui.label(f"{view.delivered} delivered").classes(
                f"{TEXT} text-[{CHALK_DIM}]"
            )
            # A lone team, with no other to race.
            for team in view.teams:
                _tally(team)


def _team_board(team: TeamScore) -> None:
    """One team's board, written in the team's own colour."""
    tone = team_ink(team.name)
    with ui.column().classes(f"{BOARD} {BOARD_TEAM}"):
        ui.label(team.label).classes(f"{BOARD_LABEL} {tone} w-full")
        ui.label(str(team.score)).classes(f"{DISPLAY} {tone} self-end")


def _tally(team: TeamScore) -> None:
    with ui.row().classes("items-center gap-1 flex-nowrap"):
        ui.label(team.label).classes(f"{TEXT} {team_ink(team.name)} truncate")
        ui.label(str(team.score)).classes(f"{TEXT} tabular-nums")

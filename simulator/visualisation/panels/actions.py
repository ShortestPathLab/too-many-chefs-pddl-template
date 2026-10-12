"""The action history, along the bottom of the screen."""

from __future__ import annotations

from nicegui import ui

from simulator.view import ActionLane, ActionsView, LaneSegment, sprite_icon
from simulator.visualisation.panels.common import panel_head
from simulator.visualisation.theme import (
    CENTRE,
    INK_GHOST,
    IRON,
    LANE,
    LANE_ACT,
    LANE_IDLE,
    LANE_INSET,
    LANE_PAD,
    LANE_SEGMENT,
    LANE_SERVE,
    LANE_STEP,
    LANE_STEP_NOW,
    LANE_TRACK,
    LANE_WALK,
    LANE_WORK,
    PANEL_BODY,
    PANEL_FRAME,
    TAB_IDLE,
    TAB_SELECTED,
    TEXT,
)

# Boxes by what they hold.
BOXES = {"act": LANE_ACT, "work": LANE_WORK, "serve": LANE_SERVE}


def actions_panel(view: ActionsView, *, selected_agent_id: str | None = None) -> None:
    """One lane per chef, with the step the kitchen is showing on the right."""
    # Set to the same measure as the timeline directly above it, so the two
    # panels that belong to neither rail read as one column down the middle.
    with ui.column().classes(f"{PANEL_FRAME} {IRON} {CENTRE} min-w-0"):
        panel_head("Actions")
        with ui.column().classes(PANEL_BODY):
            if not view.lanes:
                ui.label(view.empty_label).classes(f"{TEXT} {INK_GHOST} py-0.5")
                return
            for lane in view.lanes:
                _lane(lane, view, selected=lane.agent_id == selected_agent_id)
            _steps(view)


def _columns(view: ActionsView) -> str:
    return f"grid-template-columns: repeat({view.window}, minmax(0, 1fr))"


def _padding(view: ActionsView) -> int:
    """Return how many columns stand empty to the left of the first step.

    The step the kitchen is showing sits in the last column, so a run younger
    than the window leaves its spare columns on the left.
    """
    return view.window - (view.current_step - view.first_step + 1)


def _lane(lane: ActionLane, view: ActionsView, *, selected: bool) -> None:
    with ui.row().classes(LANE):
        ui.label(str(lane.number)).classes(TAB_SELECTED if selected else TAB_IDLE)
        with ui.element("div").classes(LANE_TRACK).style(_columns(view)):
            _pad(view)
            for segment in lane.segments:
                _segment(segment, view)


def _pad(view: ActionsView) -> None:
    """Dot the columns the run has not reached back to."""
    padding = _padding(view)
    if padding <= 0:
        return
    with (
        ui.element("div")
        .classes(LANE_SEGMENT)
        .style(f"grid-column: 1 / span {padding}")
    ):
        ui.element("div").classes(LANE_PAD)


def _segment(segment: LaneSegment, view: ActionsView) -> None:
    box = BOXES.get(segment.kind, "")
    cell = ui.element("div").classes(f"{LANE_SEGMENT} {box}")
    column = _padding(view) + segment.first - view.first_step + 1
    cell.style(f"grid-column: {column} / span {segment.steps}")
    cell.props["title"] = _title(segment)
    with cell:
        if segment.kind == "idle":
            ui.element("div").classes(LANE_IDLE)
        elif segment.kind == "walk":
            if segment.sprite is not None:
                sprite_icon(segment.sprite)
            ui.element("div").classes(LANE_WALK)
        elif segment.sprite is not None:
            # One step is too narrow for a word, so the item says what it was
            # and the mark says which way it went.
            if segment.mark:
                ui.label(segment.mark)
            sprite_icon(segment.sprite)
        else:
            ui.label(segment.label)


def _title(segment: LaneSegment) -> str:
    when = (
        f"Step {segment.first}"
        if segment.steps == 1
        else f"Steps {segment.first} to {segment.last}"
    )
    return f"{when}: {segment.detail}"


def _steps(view: ActionsView) -> None:
    """Name the first and the current step under the columns they sit in."""
    with ui.element("div").classes(f"w-full grid {LANE_INSET}").style(_columns(view)):
        if view.first_step < view.current_step:
            ui.label(f"T{view.first_step}").classes(LANE_STEP).style(
                f"grid-area: 1 / {_padding(view) + 1}"
            )
        ui.label(f"T{view.current_step}").classes(LANE_STEP_NOW).style(
            f"grid-area: 1 / {view.window}"
        )

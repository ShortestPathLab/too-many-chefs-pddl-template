"""Test how the action history is drawn."""

from __future__ import annotations

from nicegui import ui

from simulator.view import ActionLane, ActionsView, LaneSegment
from simulator.visualisation.panels.actions import actions_panel
from simulator.visualisation.theme import LANE_PAD, LANE_WALK


def _drawn(view: ActionsView) -> list[ui.element]:
    with ui.column() as container:
        actions_panel(view)
    elements = list(container.descendants())
    container.delete()
    return elements


def _labels(elements: list[ui.element]) -> list[str]:
    return [element.text for element in elements if isinstance(element, ui.label)]


def _columns(elements: list[ui.element], classes: str) -> list[str | None]:
    """Return the columns held by whatever is drawn with ``classes``."""
    return [
        element.parent_slot.parent._style.get("grid-column")
        for element in elements
        if set(classes.split()) <= set(element._classes)
        and element.parent_slot is not None
    ]


def _view(current_step: int, *, window: int = 14) -> ActionsView:
    first = max(1, current_step - window + 1)
    segments = (
        [LaneSegment(first=first, last=current_step, kind="walk", detail="walks")]
        if current_step
        else []
    )
    return ActionsView(
        lanes=[
            ActionLane(number=1, agent_id="a", segments=segments),
            ActionLane(number=2, agent_id="b", segments=segments),
        ],
        first_step=first,
        current_step=current_step,
        window=window,
    )


def test_an_untouched_run_dots_every_lane_from_end_to_end() -> None:
    view = _view(0)

    elements = _drawn(view)

    assert _columns(elements, LANE_PAD) == ["1 / span 14", "1 / span 14"]
    assert view.empty_label not in _labels(elements)
    assert "T0" in _labels(elements)


def test_a_young_run_sits_at_the_right_with_dots_to_its_left() -> None:
    # What has just happened is always at the right edge, whether the run is
    # three steps old or three hundred.
    elements = _drawn(_view(3))

    assert _columns(elements, LANE_PAD) == ["1 / span 11", "1 / span 11"]
    assert _columns(elements, LANE_WALK) == ["12 / span 3", "12 / span 3"]


def test_a_full_history_leaves_nothing_to_dot() -> None:
    elements = _drawn(_view(20))

    assert _columns(elements, LANE_PAD) == []
    assert _columns(elements, LANE_WALK) == ["1 / span 14", "1 / span 14"]


def test_the_step_labels_stand_under_the_steps_they_name() -> None:
    elements = _drawn(_view(3))

    placed = {
        element.text: element._style.get("grid-area")
        for element in elements
        if isinstance(element, ui.label) and element.text.startswith("T")
    }
    assert placed == {"T1": "1 / 12", "T3": "1 / 14"}

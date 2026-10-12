"""Detect interface-only audio cues."""

from __future__ import annotations

from typing import Any

from simulator.view import TimelineView


def interface_cues(
    last: dict[str, Any],
    timeline: TimelineView,
    selected: str | None,
) -> list[str]:
    """Return cues for interface actions that do not change the environment.

    The first refresh is silent because there is no previous view to compare.
    """
    cues: list[str] = []
    if last["seen"]:
        if timeline.status != last["status"]:
            cues.append("toggle_run")
        if selected != last["selected"]:
            cues.append("select_agent")
    last["seen"] = True
    last["status"] = timeline.status
    last["selected"] = selected
    return cues

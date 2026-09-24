"""Render agent badge labels."""

from __future__ import annotations

from nicegui import ui

from simulator.view import WorldAnchor
from simulator.visualisation.theme import (
    BADGE_DROP_CELLS,
    BADGE_IDLE,
    BADGE_SELECTED,
)


class AgentBadges:
    """DOM labels that track interpolated agent positions."""

    def __init__(self, agent_order: list[str], *, selected_agent_id: str | None):
        self._labels: dict[str, ui.label] = {}
        for number, agent_id in enumerate(agent_order, start=1):
            with WorldAnchor(
                track_id=agent_id,
                offset_cells_x=0.5,
                offset_cells_y=BADGE_DROP_CELLS,
                origin_y=0.0,
            ):
                # Match the initial inspector selection.
                self._labels[agent_id] = ui.label(str(number)).classes(
                    BADGE_SELECTED if agent_id == selected_agent_id else BADGE_IDLE
                )

    def select(self, agent_id: str | None) -> None:
        for badge_agent_id, label in self._labels.items():
            label.classes(
                replace=BADGE_SELECTED if badge_agent_id == agent_id else BADGE_IDLE
            )

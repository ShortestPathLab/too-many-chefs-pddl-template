"""Build timeline data for the interface."""

from __future__ import annotations

from simulator.environment import Environment
from simulator.models import FrozenSimulatorModel


class TimelineView(FrozenSimulatorModel):
    """Timeline and playback status.

    ``total`` is ``None`` for runs with no known end. Replay supplies a total and
    can show a position within the recording.
    """

    timestep: int = 0
    total: int | None = None
    rate_label: str = ""
    status: str = ""

    @property
    def live(self) -> bool:
        """Return whether the run has no known end."""
        return self.total is None

    @property
    def progress(self) -> float:
        if not self.total:
            return 1.0
        return min(1.0, max(0.0, self.timestep / self.total))

    @property
    def position_label(self) -> str:
        if self.total is None:
            return "Live"
        return f"{self.timestep} / {self.total}"


def timeline_view(
    environment: Environment,
    *,
    total: int | None = None,
    rate_label: str = "",
    status: str = "",
) -> TimelineView:
    return TimelineView(
        timestep=environment.timestep,
        total=total,
        rate_label=rate_label,
        status=status,
    )

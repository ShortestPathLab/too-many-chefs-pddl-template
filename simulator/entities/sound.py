from __future__ import annotations

from simulator.models import FrozenSimulatorModel


class SoundDefinition(FrozenSimulatorModel):
    """Sound settings for an equipment action.

    The renderer applies the gain and jitter values when present.
    """

    clips: tuple[str, ...] = ()
    gain: float | None = None
    jitter: float | None = None


class SoundtrackDefinition(FrozenSimulatorModel):
    """Music settings stored with a level and its recordings."""

    tracks: tuple[str, ...] = ()
    gain: float | None = None

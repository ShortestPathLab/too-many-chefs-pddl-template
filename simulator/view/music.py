from __future__ import annotations

from simulator.assets import asset_url
from simulator.entities import OvercookedState, SoundtrackDefinition
from simulator.environment import Environment
from simulator.view.audio import AUDIO_DIRECTORY

# Track files live in a dedicated directory and levels store file stems.
SOUNDTRACK_DIRECTORY = AUDIO_DIRECTORY / "soundtrack"
SOUNDTRACK_SUFFIX = ".mp3"

# Default soundtrack volume, below action cues.
DEFAULT_SOUNDTRACK_GAIN = 0.18


def soundtrack(environment: Environment | None = None) -> SoundtrackDefinition:
    """Return the level soundtrack, or an empty soundtrack."""
    state = (
        environment.get_first_entity_of_type(OvercookedState)
        if environment is not None
        else None
    )
    return state.soundtrack if state is not None else SoundtrackDefinition()


def track_url(name: str) -> str:
    return asset_url(SOUNDTRACK_DIRECTORY / f"{name}{SOUNDTRACK_SUFFIX}")


def track_urls(environment: Environment | None = None) -> list[str]:
    """Return soundtrack URLs in playback order."""
    return [track_url(name) for name in soundtrack(environment).tracks]


def soundtrack_gain(environment: Environment | None = None) -> float:
    gain = soundtrack(environment).gain
    return gain if gain is not None else DEFAULT_SOUNDTRACK_GAIN


def missing_tracks(environment: Environment | None = None) -> list[str]:
    """Return soundtrack names whose files are missing."""
    return sorted(
        {
            name
            for name in soundtrack(environment).tracks
            if not (SOUNDTRACK_DIRECTORY / f"{name}{SOUNDTRACK_SUFFIX}").exists()
        }
    )

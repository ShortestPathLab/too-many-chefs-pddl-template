"""Map simulator events to sound cues."""

from __future__ import annotations

from simulator.assets import AUDIO_DIRECTORY, asset_url
from simulator.entities import OvercookedState
from simulator.environment import Environment
from simulator.models import FrozenSimulatorModel


class Cue(FrozenSimulatorModel):
    """Sound settings for one event.

    ``clips`` contains interchangeable audio files. ``jitter`` varies playback
    pitch. ``repeats`` and ``spread`` control repeated samples for one event.
    """

    name: str
    clips: tuple[str, ...]
    gain: float = 1.0
    jitter: float = 0.0
    repeats: int = 1
    spread: float = 0.09


def _takes(stem: str, count: int = 5, start: int = 0) -> tuple[str, ...]:
    """The numbered variants of a sample family, e.g. ``impactTin_medium_003``."""
    return tuple(f"{stem}_{index:03d}.ogg" for index in range(start, start + count))


# Cues are listed in priority order. Gains reflect how often each cue plays.
CUES: tuple[Cue, ...] = (
    # Run outcomes.
    Cue(
        name="deliver",
        clips=("confirmation_003.ogg",),
        gain=0.5,
        jitter=0.02,
    ),
    # Play under the delivery cue.
    Cue(name="tip", clips=("handleCoins.ogg",), gain=0.28, jitter=0.04),
    Cue(name="order_expired", clips=("error_004.ogg",), gain=0.45),
    Cue(
        name="order_revealed",
        clips=("bookFlip1.ogg", "bookFlip2.ogg", "bookFlip3.ogg"),
        gain=0.3,
        jitter=0.05,
    ),
    # Generic equipment cues. Levels may provide equipment-specific cues.
    Cue(name="cook", clips=("metalClick.ogg", "metalLatch.ogg"), gain=0.4, jitter=0.05),
    Cue(name="combine", clips=_takes("impactGeneric_light"), gain=0.4, jitter=0.06),
    Cue(name="discard", clips=_takes("impactWood_light"), gain=0.4, jitter=0.06),
    # Washing used plates.
    Cue(name="wash", clips=_takes("impactGlass_light"), gain=0.35, jitter=0.08),
    # Picking up and placing items.
    Cue(name="take_from_storage", clips=("bookOpen.ogg",), gain=0.5, jitter=0.06),
    Cue(
        name="pick_up",
        clips=("handleSmallLeather.ogg", "handleSmallLeather2.ogg"),
        gain=0.4,
        jitter=0.05,
    ),
    Cue(name="pick_up_plate", clips=_takes("impactWood_light"), gain=0.36, jitter=0.05),
    Cue(
        name="pick_up_equipment",
        clips=_takes("impactMetal_light"),
        gain=0.3,
        jitter=0.05,
    ),
    Cue(name="place", clips=_takes("impactWood_light"), gain=0.45, jitter=0.06),
    Cue(name="place_plate", clips=_takes("impactWood_light"), gain=0.4, jitter=0.05),
    Cue(
        name="place_equipment",
        clips=_takes("impactMetal_medium"),
        gain=0.36,
        jitter=0.05,
    ),
    # Movement. Two samples cover the walk animation.
    Cue(
        name="move",
        clips=_takes("footstep_concrete"),
        gain=0.22,
        jitter=0.09,
        repeats=2,
        spread=0.5,
    ),
    Cue(
        name="turn",
        clips=("cloth2.ogg", "cloth3.ogg", "cloth4.ogg"),
        gain=0.1,
        jitter=0.06,
    ),
    # An action that had no effect.
    Cue(name="blocked", clips=_takes("impactWood_light"), gain=0.2, jitter=0.06),
    # Interface sounds.
    Cue(name="select_agent", clips=("click_002.ogg",), gain=0.3),
    Cue(name="toggle_run", clips=("click_002.ogg",), gain=0.35),
)

CUES_BY_NAME: dict[str, Cue] = {cue.name: cue for cue in CUES}

# Equipment cues use a separate namespace.
EQUIPMENT_CUE_PREFIX = "equipment:"

# Default cue used by equipment-specific sounds.
EQUIPMENT_DEFAULT_CUE = "cook"


def equipment_cue_name(equipment_name: str) -> str:
    return f"{EQUIPMENT_CUE_PREFIX}{equipment_name}"


def equipment_cues(environment: Environment | None) -> tuple[Cue, ...]:
    """Return equipment-specific cues defined by the level.

    Missing gain and jitter values use the generic equipment cue.
    """
    state = (
        environment.get_first_entity_of_type(OvercookedState)
        if environment is not None
        else None
    )
    if state is None:
        return ()

    default = CUES_BY_NAME[EQUIPMENT_DEFAULT_CUE]
    return tuple(
        Cue(
            name=equipment_cue_name(name),
            clips=tuple(sound.clips),
            gain=sound.gain if sound.gain is not None else default.gain,
            jitter=sound.jitter if sound.jitter is not None else default.jitter,
            spread=default.spread,
        )
        for name, sound in sorted(state.equipment_sounds.items())
        if sound.clips
    )


def all_cues(environment: Environment | None = None) -> tuple[Cue, ...]:
    return CUES + equipment_cues(environment)


def cue_urls(environment: Environment | None = None) -> dict[str, list[str]]:
    """Cue name to its variant URLs, for preloading in the browser."""
    return {
        cue.name: [asset_url(AUDIO_DIRECTORY / clip) for clip in cue.clips]
        for cue in all_cues(environment)
    }


def cue_gains(environment: Environment | None = None) -> dict[str, float]:
    return {cue.name: cue.gain for cue in all_cues(environment)}


def cue_jitters(environment: Environment | None = None) -> dict[str, float]:
    return {cue.name: cue.jitter for cue in all_cues(environment)}


def cue_repeats(environment: Environment | None = None) -> dict[str, int]:
    return {cue.name: cue.repeats for cue in all_cues(environment)}


def cue_spreads(environment: Environment | None = None) -> dict[str, float]:
    return {cue.name: cue.spread for cue in all_cues(environment)}


def missing_clips(environment: Environment | None = None) -> list[str]:
    """Clips that are not on disk. Cheap guard against a typo in a clip name."""
    return sorted(
        {
            clip
            for cue in all_cues(environment)
            for clip in cue.clips
            if not (AUDIO_DIRECTORY / clip).exists()
        }
    )

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load, load_configuration
from simulator.entities import OvercookedState
from simulator.environment import Environment
from simulator.view import (
    DEFAULT_SOUNDTRACK_GAIN,
    SOUNDTRACK_DIRECTORY,
    SOUNDTRACK_SUFFIX,
    cue_gains,
    missing_tracks,
    soundtrack,
    soundtrack_gain,
    track_urls,
)

CHILL = "low-key-cooking-side-a"
HEAT = "turning-up-the-heat"

# Minimal kitchen for soundtrack tests.
GALLEY: dict[str, Any] = {
    "layout": "|1|",
    "legend": {"agents": [{"symbol": "1"}]},
}


def _level(soundtrack_value: object) -> Environment:
    return load(Configuration.from_dict({**GALLEY, "soundtrack": soundtrack_value}))


def _levels() -> list[Path]:
    return sorted(Path("levels").rglob("*.yaml"))


def test_a_level_with_no_music_plays_none() -> None:
    environment = load(Configuration.from_dict(GALLEY))

    assert track_urls(environment) == []
    assert missing_tracks(environment) == []


def test_there_is_nothing_to_play_without_a_level() -> None:
    assert track_urls() == []
    assert soundtrack_gain() == DEFAULT_SOUNDTRACK_GAIN


def test_one_track_is_shorthand_for_a_playlist_of_one() -> None:
    assert soundtrack(_level(CHILL)).tracks == (CHILL,)


def test_a_playlist_is_played_in_the_order_it_is_written() -> None:
    # The order is the level's decision, so nothing here may sort or
    # deduplicate it.
    tracks = [HEAT, CHILL, HEAT]

    assert soundtrack(_level(tracks)).tracks == tuple(tracks)


def test_tracks_are_served_from_the_soundtrack_folder() -> None:
    assert track_urls(_level([CHILL])) == [
        f"/assets/audio/soundtrack/{CHILL}{SOUNDTRACK_SUFFIX}"
    ]


def test_a_level_can_say_how_loud_its_music_sits() -> None:
    environment = _level({"tracks": [HEAT], "gain": 0.4})

    assert soundtrack_gain(environment) == 0.4


def test_a_level_that_says_nothing_about_level_inherits_it() -> None:
    assert soundtrack_gain(_level([HEAT])) == DEFAULT_SOUNDTRACK_GAIN


def test_the_music_sits_under_the_kitchen() -> None:
    # The music plays continuously and the cues do not, so a footstep has to
    # be able to cut through it.
    assert DEFAULT_SOUNDTRACK_GAIN < cue_gains()["move"]


def test_a_typo_in_a_playlist_is_reported() -> None:
    environment = _level(["low-key-cookin"])

    assert missing_tracks(environment) == ["low-key-cookin"]


def test_a_replay_is_scored_the_way_the_run_was() -> None:
    # The playlist rides on the state rather than being handed to the
    # visualiser, which is what lets a recording replay to its own music.
    environment = _level([CHILL, HEAT])

    restored = Environment.from_dict(environment.to_dict())

    assert track_urls(restored) == track_urls(environment)


def test_the_state_carries_the_playlist_rather_than_the_urls() -> None:
    # A track is named by stem in the level and stays that way in the state:
    # where the files live and what format they are in is the view's business.
    state = _level([CHILL]).get_first_entity_of_type(OvercookedState)

    assert state is not None
    assert state.soundtrack.tracks == (CHILL,)


@pytest.mark.parametrize("path", _levels(), ids=Path.as_posix)
def test_every_level_is_scored(path: Path) -> None:
    # A level with no music is legal, but a shipped one having none is an
    # oversight rather than a decision.
    assert track_urls(load(load_configuration(path)))


@pytest.mark.parametrize("path", _levels(), ids=Path.as_posix)
def test_every_track_a_level_names_exists(path: Path) -> None:
    assert missing_tracks(load(load_configuration(path))) == []


def test_no_track_in_the_folder_goes_unused() -> None:
    # The other direction: music that was written for the game and then never
    # reached a level.
    played = {
        name
        for path in _levels()
        for name in soundtrack(load(load_configuration(path))).tracks
    }
    on_disk = {path.stem for path in SOUNDTRACK_DIRECTORY.glob(f"*{SOUNDTRACK_SUFFIX}")}

    assert on_disk - played == set()

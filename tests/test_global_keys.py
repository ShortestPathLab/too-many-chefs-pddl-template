"""Test the keys the visualiser handles for every run mode."""

from __future__ import annotations

from simulator.visualisation.keys import with_global_keys

CONTROLS = {"title": "Controls", "items": [{"key": "Space", "action": "Start / stop"}]}


def test_a_silent_visualiser_offers_no_music_key() -> None:
    section = with_global_keys(CONTROLS, agent_cycling=False, sound=False)

    assert [item["key"] for item in section["items"]] == ["Space", "H"]


def test_the_music_key_reads_as_the_state_the_music_is_in() -> None:
    audible = with_global_keys(CONTROLS, agent_cycling=False, sound=True, muted=False)
    silenced = with_global_keys(CONTROLS, agent_cycling=False, sound=True, muted=True)

    assert _hint(audible, "M") == "Music: on"
    assert _hint(silenced, "M") == "Music: off"


def test_a_one_chef_kitchen_has_nothing_to_cycle_through() -> None:
    section = with_global_keys(CONTROLS, agent_cycling=False, sound=True)

    assert "A" not in [item["key"] for item in section["items"]]


def test_the_mode_keeps_its_own_keys_first() -> None:
    section = with_global_keys(CONTROLS, agent_cycling=True, sound=True)

    assert [item["key"] for item in section["items"]] == ["Space", "A", "M", "H"]


def _hint(section: dict, key: str) -> str:
    return next(item["action"] for item in section["items"] if item["key"] == key)

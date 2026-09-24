from pathlib import Path

import pytest
from nicegui import ui

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load, load_configuration
from simulator.entities import OvercookedState
from simulator.recording import (
    Recording,
    create_recording_sink,
    load_recording,
    save_recording,
)
from simulator.view import TimelineView
from simulator.visualisation.panels.top_bar import top_bar


@pytest.mark.parametrize("metadata", [{}, {"name": None, "description": None}])
def test_metadata_is_optional(metadata: dict) -> None:
    configuration = Configuration.from_dict({"layout": "| |", **metadata})
    state = load(configuration).get_first_entity_of_type(OvercookedState)
    assert state is not None
    assert state.name is None
    assert state.description is None


@pytest.mark.parametrize("streaming", [False, True])
def test_metadata_survives_recording_round_trip(
    tmp_path: Path, streaming: bool
) -> None:
    configuration = Configuration.from_dict(
        {
            "layout": "| |",
            "name": "The BBQ kitchen",
            "description": "Grill, plate, and serve.",
        }
    )
    recording = Recording(environments=[load(configuration)])
    path = tmp_path / "recording.yaml"
    if streaming:
        create_recording_sink(path)(recording)
    else:
        save_recording(recording, path)
    state = (
        load_recording(path).environments[0].get_first_entity_of_type(OvercookedState)
    )
    assert state is not None
    assert state.name == configuration.name
    assert state.description == configuration.description


@pytest.mark.parametrize("name", [None, "", "   ", "The BBQ kitchen"])
@pytest.mark.parametrize(
    "description", [None, "", "   ", "Chop & serve <fresh> fruit."]
)
def test_top_bar_displays_metadata_and_filename_fallback(name, description) -> None:
    with ui.column() as container:
        top_bar(
            level_label="burger_2p.yaml",
            level_name=name,
            description=description,
            timeline=TimelineView(),
        )
    labels = [
        element.text
        for element in container.descendants()
        if isinstance(element, ui.label)
    ]
    assert labels[0] == ((name or "").strip() or "burger_2p.yaml")
    if description and description.strip():
        assert labels[1] == description
    else:
        assert "Play mode" not in labels
    container.delete()


@pytest.mark.parametrize("path", sorted(Path("levels").rglob("*.yaml")), ids=str)
def test_bundled_levels_have_metadata(path: Path) -> None:
    configuration = load_configuration(path)
    assert configuration.name and configuration.name.strip()
    assert configuration.description and configuration.description.strip()
    state = load(configuration).get_first_entity_of_type(OvercookedState)
    assert state is not None
    assert state.name == configuration.name
    assert state.description == configuration.description

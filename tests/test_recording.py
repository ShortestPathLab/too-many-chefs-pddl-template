from __future__ import annotations

import tempfile
from pathlib import Path

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.recording import Recording, create_recording_sink, load_recording
from simulator.run import run_agent_mode
from tests.run_controllers import AGENT_LEVEL, StepOnceController


def test_yaml_recording_round_trip_restores_environment_history() -> None:
    configuration = Configuration.from_dict(AGENT_LEVEL)
    environment = load(configuration)
    recording = Recording(environments=[environment, environment.copy_with(timestep=1)])
    with tempfile.TemporaryDirectory() as temp_dir:
        recording_path = Path(temp_dir) / "recording.yaml"
        create_recording_sink(recording_path)(recording)
        restored = load_recording(recording_path)

    assert len(restored.environments) == 2
    assert restored.environments[1].timestep == 1


def test_yaml_recording_sink_streams_each_environment() -> None:
    configuration = Configuration.from_dict(AGENT_LEVEL)

    with tempfile.TemporaryDirectory() as temp_dir:
        recording_path = Path(temp_dir) / "recording.yaml"
        run_agent_mode(
            configuration,
            StepOnceController(),
            headless=True,
            on_step=create_recording_sink(recording_path),
        )

        restored = load_recording(recording_path)

    assert len(restored.environments) == 2
    assert restored.environments[0].timestep == 0
    assert restored.environments[1].timestep == 1


# These recordings are used by the README examples. Keep them valid when the
# recording schema changes.
EXAMPLES_DIRECTORY = Path(__file__).resolve().parent.parent / "examples"


def test_every_shipped_recording_still_loads() -> None:
    recordings = sorted(EXAMPLES_DIRECTORY.glob("*.yaml"))

    assert recordings, f"No recordings found in {EXAMPLES_DIRECTORY}"
    for path in recordings:
        restored = load_recording(path)
        assert restored.environments, f"{path.name} restored no environments"

from __future__ import annotations

import gzip
from collections.abc import Callable
from pathlib import Path

import yaml
from pydantic import Field

from simulator.environment import Environment
from simulator.models import SimulatorModel
from simulator.mutations import MutationModel

RecordingSink = Callable[["Recording"], None]


class Recording(SimulatorModel):
    environments: list[Environment] = Field(default_factory=list)
    mutations: list[list[MutationModel]] = Field(default_factory=list)


def load_recording(path: str | Path) -> Recording:
    """Load a recording, gzipped when its name ends in ``.gz``."""
    recording_path = Path(path)
    data = recording_path.read_bytes()
    if recording_path.suffix == ".gz":
        data = gzip.decompress(data)
    documents = [
        document
        for document in yaml.safe_load_all(data.decode("utf-8"))
        if document is not None
    ]
    if (
        len(documents) == 1
        and isinstance(documents[0], dict)
        and "environments" in documents[0]
    ):
        recording = Recording.from_dict(documents[0])
        return _normalise_recording(recording)

    if all(
        isinstance(document, dict) and "environment" in document
        for document in documents
    ):
        recording = Recording(
            environments=[
                Environment.from_dict(document["environment"])
                for document in documents
                if isinstance(document, dict)
            ],
            mutations=[
                document.get("mutations", [])
                for document in documents
                if isinstance(document, dict)
            ],
        )
        return _normalise_recording(recording)

    recording = Recording(
        environments=[Environment.from_dict(document) for document in documents]
    )
    return _normalise_recording(recording)


def save_recording(recording: Recording, path: str | Path) -> Path:
    """Save a recording, gzipped when ``path`` ends in ``.gz``.

    A recording repeats the whole kitchen every timestep, so it compresses to
    about a hundredth of its size.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = yaml.safe_dump(
        recording.to_dict(),
        sort_keys=False,
    ).encode("utf-8")
    if output_path.suffix == ".gz":
        serialized = gzip.compress(serialized)

    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary_path.write_bytes(serialized)
    temporary_path.replace(output_path)
    return output_path


def create_recording_sink(path: str | Path) -> RecordingSink:
    return _YamlRecordingSink(Path(path))


class _YamlRecordingSink:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._written_count = 0
        self._initialized = False

    def __call__(self, recording: Recording) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._initialized:
            self._path.write_text("", encoding="utf-8")
            self._initialized = True

        new_environments = recording.environments[self._written_count :]
        if not new_environments:
            return

        with self._path.open("a", encoding="utf-8") as file:
            for offset, environment in enumerate(new_environments):
                mutations = (
                    recording.mutations[self._written_count + offset]
                    if self._written_count + offset < len(recording.mutations)
                    else []
                )
                yaml.safe_dump(
                    {
                        "environment": environment.to_dict(),
                        "mutations": [mutation.to_dict() for mutation in mutations],
                    },
                    file,
                    explicit_start=True,
                    sort_keys=False,
                )

        self._written_count = len(recording.environments)


def _normalise_recording(recording: Recording) -> Recording:
    missing_mutation_sets = len(recording.environments) - len(recording.mutations)
    if missing_mutation_sets <= 0:
        return recording

    return recording.copy_with(
        mutations=[*recording.mutations, *([] for _ in range(missing_mutation_sets))]
    )

"""Where a run writes its recording and its result."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4


def generate_run_id() -> str:
    return uuid4().hex[:6]


def resolve_recording_output(
    *,
    record: bool,
    recording_out_file: Path | None,
) -> Path | None:
    if recording_out_file is not None:
        return recording_out_file
    if not record:
        return None
    return Path(f"{generate_run_id()}-recording.yaml")


def resolve_run_outputs(
    *,
    record: bool,
    recording_out_file: Path | None,
    result: bool,
    result_out_file: Path | None,
) -> tuple[Path | None, Path | None]:
    """Resolve recording and result output paths.

    Auto-named recording and result files share a random run id, such as
    ``abc123-recording.yaml`` and ``abc123-result.json``.
    """
    run_id: str | None = None

    def shared_run_id() -> str:
        nonlocal run_id
        if run_id is None:
            run_id = generate_run_id()
        return run_id

    if recording_out_file is not None:
        recording_path: Path | None = recording_out_file
    elif record:
        recording_path = Path(f"{shared_run_id()}-recording.yaml")
    else:
        recording_path = None

    if result_out_file is not None:
        result_path: Path | None = result_out_file
    elif result:
        result_path = Path(f"{shared_run_id()}-result.json")
    else:
        result_path = None

    return recording_path, result_path

"""Test how planning worker processes follow the process that started them."""

from __future__ import annotations

import shutil
import signal
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

linux_only = pytest.mark.skipif(
    sys.platform != "linux", reason="parent death signals are Linux only"
)

UNSHARE = ["unshare", "--user", "--pid", "--fork", "--map-root-user"]


def can_run_as_pid_1() -> bool:
    if shutil.which("unshare") is None:
        return False
    try:
        return (
            subprocess.run([*UNSHARE, "true"], check=False, timeout=30).returncode == 0
        )
    except OSError, subprocess.TimeoutExpired:
        return False


def run_python(script: str, *, prefix: list[str] | None = None):
    return subprocess.run(
        [*(prefix or []), sys.executable, "-c", script],
        check=False,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


# A container's first process is PID 1, and so are the workers' parent.
@linux_only
@pytest.mark.skipif(not can_run_as_pid_1(), reason="needs unshare with user namespaces")
def test_a_worker_whose_parent_is_pid_1_keeps_working() -> None:
    result = run_python(
        """
import os
import signal
from simulator.controller import MultiprocessingController

# unshare starts us with SIGTERM ignored, and workers would inherit that. A
# container's first process has it at the default, so it can stop a worker.
signal.signal(signal.SIGTERM, signal.SIG_DFL)

class Probe(MultiprocessingController):
    def get_actions(self, environment, context):
        return []

    def is_busy(self):
        return False

assert os.getpid() == 1
probe = Probe()
try:
    print(probe._submit_to_process(os.getppid).result(timeout=60))
finally:
    probe.shutdown()
""",
        prefix=UNSHARE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "1"


@linux_only
def test_a_worker_with_the_parent_that_started_it_carries_on() -> None:
    result = run_python(
        """
import os
from simulator.controller import _set_parent_death_signal

_set_parent_death_signal(os.getppid())
print("running")
"""
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "running"


# An orphan has a new parent, which the check has to notice.
@linux_only
def test_a_worker_whose_parent_is_already_gone_stops() -> None:
    result = run_python(
        """
import os
from simulator.controller import _set_parent_death_signal

_set_parent_death_signal(os.getppid() + 1)
print("running")
"""
    )

    assert result.returncode == -signal.SIGTERM
    assert result.stdout == ""

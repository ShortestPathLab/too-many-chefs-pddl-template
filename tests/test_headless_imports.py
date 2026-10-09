"""Test what a headless run leaves unimported.

The visualiser pulls in NiceGUI and its web server, which take most of a
second to import. Every planning worker process pays for what the command line
imports, so a headless run keeps all of it out. The students' modules load
only when a run builds the controller that uses them.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HEADLESS_RUN = """
import sys

import main
from simulator.configuration import Configuration
from simulator.run import run_agent_mode
from tests.run_controllers import AGENT_LEVEL
from tests.stub_controller import StubController

run_agent_mode(
    Configuration.from_dict(AGENT_LEVEL),
    StubController(finished=True),
    headless=True,
)
print("\\n".join(sys.modules))
"""


def modules_after_a_headless_run() -> list[str]:
    result = subprocess.run(
        [sys.executable, "-c", HEADLESS_RUN],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    return result.stdout.split()


def test_a_headless_run_does_not_import_the_visualiser() -> None:
    loaded = modules_after_a_headless_run()

    visual = [
        module
        for module in loaded
        if module == "nicegui"
        or module.startswith(("nicegui.", "simulator.view", "simulator.visualisation"))
    ]
    assert visual == []


def test_the_command_line_does_not_import_the_students_modules() -> None:
    loaded = modules_after_a_headless_run()

    student_code = [
        module for module in loaded if module.startswith("controllers.pddl.submission")
    ]
    assert student_code == []

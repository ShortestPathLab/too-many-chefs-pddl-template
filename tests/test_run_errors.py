"""Test that an error during an agent run still ends it with a result."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Iterator
from concurrent.futures import Future
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

import main
from controllers import ControllerPlugin, OpenController
from controllers.registry import _registry, register_controller
from simulator.configuration import Configuration
from simulator.context import Context
from simulator.entities import Agent
from simulator.environment import Environment
from simulator.mutations import Mutation, TurnAgent
from simulator.run import Episode, SimulationResult, run_agent_mode
from tests.run_controllers import AGENT_LEVEL
from tests.stub_controller import StubController


class ControllerError(RuntimeError):
    pass


class FailingController(StubController):
    """Turns its chef on each call, then raises once it has had ``calls``."""

    def __init__(self, *, calls: int = 0, error: BaseException | None = None) -> None:
        super().__init__()
        self._calls_left = calls
        self._error = error or ControllerError("the controller broke")
        self.shut_down = False

    def get_actions(self, environment: Environment, context: Context) -> list[Mutation]:
        if self._calls_left <= 0:
            raise self._error
        self._calls_left -= 1
        agent = environment.get_first_entity_of_type(Agent)
        assert agent is not None
        return [TurnAgent(agent_id=agent.id, orientation="s")]

    def shutdown(self) -> None:
        self.shut_down = True


def run_headless(controller: StubController) -> SimulationResult:
    results: list[SimulationResult] = []
    run_agent_mode(
        Configuration.from_dict(AGENT_LEVEL),
        controller,
        headless=True,
        on_result=results.append,
    )
    assert len(results) == 1
    return results[0]


def test_an_error_from_the_controller_ends_the_run_with_a_result() -> None:
    controller = FailingController(calls=2)

    result = run_headless(controller)

    assert result.reason == "error"
    # The steps taken before the error still count.
    assert result.timesteps == 2
    assert result.error is not None
    assert result.error.stage == "run"
    assert result.error.type == "ControllerError"
    assert result.error.message == "the controller broke"
    assert "in get_actions" in result.error.traceback
    assert controller.shut_down


def test_a_controller_calling_sys_exit_still_gets_a_result() -> None:
    result = run_headless(FailingController(error=SystemExit(3)))

    assert result.reason == "error"
    assert result.error is not None
    assert result.error.type == "SystemExit"


def test_an_error_in_a_step_ends_the_run_with_a_result() -> None:
    with patch.object(Episode, "advance", side_effect=ValueError("no such chef")):
        result = run_headless(FailingController(calls=1))

    assert result.reason == "error"
    assert result.error is not None
    assert result.error.message == "no such chef"


class FailsToWarmUp(FailingController):
    def warm_up(self) -> list[Future[Any]]:
        failed: Future[Any] = Future()
        failed.set_exception(ControllerError("the worker would not start"))
        return [failed]


def test_an_error_while_warming_up_ends_the_run_before_it_starts() -> None:
    controller = FailsToWarmUp(calls=5)

    result = run_headless(controller)

    assert result.reason == "error"
    assert result.timesteps == 0
    assert result.error is not None
    assert result.error.message == "the worker would not start"
    assert controller.shut_down


def test_an_error_while_reporting_the_result_is_not_swallowed() -> None:
    def report(result: SimulationResult) -> None:
        raise OSError("disk full")

    with pytest.raises(OSError, match="disk full"):
        run_agent_mode(
            Configuration.from_dict(AGENT_LEVEL),
            FailingController(calls=1),
            headless=True,
            on_result=report,
        )


def test_a_controller_that_fails_to_build_still_prints_a_result() -> None:
    with patch(
        "controllers.open.submission.controller.OpenController.__init__",
        side_effect=ControllerError("could not start"),
    ):
        outcome = CliRunner().invoke(
            main.app,
            [
                "agent",
                "--level",
                "levels/demos/coconut_juice_tiny.yaml",
                "--controller",
                "open",
                "--headless",
                "--quiet",
            ],
        )

    assert outcome.exit_code == 0, outcome.output
    result = json.loads(outcome.stdout)
    assert result["reason"] == "error"
    assert result["timesteps"] == 0
    assert result["error"]["stage"] == "build"
    assert result["error"]["message"] == "could not start"
    assert result["run"]["controllers"][0]["controller"] == "open"


def fail_to_import() -> None:
    raise ModuleNotFoundError("No module named 'student_helpers'")


UNIMPORTABLE = ControllerPlugin(
    name="unimportable",
    summary="A controller whose code will not import.",
    create=lambda options: OpenController(),
    load=fail_to_import,
)


@pytest.fixture
def unimportable_plugin() -> Iterator[ControllerPlugin]:
    saved = dict(_registry)
    register_controller(UNIMPORTABLE)
    try:
        yield UNIMPORTABLE
    finally:
        _registry.clear()
        _registry.update(saved)


def test_a_controller_whose_code_will_not_import_still_prints_a_result(
    unimportable_plugin: ControllerPlugin,
) -> None:
    outcome = CliRunner().invoke(
        main.app,
        [
            "agent",
            "--level",
            "levels/demos/coconut_juice_tiny.yaml",
            "--controller",
            "unimportable",
            "--headless",
            "--quiet",
        ],
    )

    assert outcome.exit_code == 0, outcome.output
    result = json.loads(outcome.stdout)
    assert result["reason"] == "error"
    assert result["error"]["stage"] == "import"
    assert result["error"]["type"] == "ModuleNotFoundError"


# A fresh interpreter, so the missing module does not leak into other tests.
BROKEN_STUDENT_MODULE = """
import sys

sys.modules["controllers.pddl.submission.problem_generator"] = None
import main

main.app(
    ["agent", "--level", "levels/demos/coconut_juice_tiny.yaml", "--headless", "--quiet"],
    standalone_mode=False,
)
"""


def test_a_student_module_that_will_not_import_ends_the_pddl_run() -> None:
    outcome = subprocess.run(
        [sys.executable, "-c", BROKEN_STUDENT_MODULE],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    assert outcome.returncode == 0, outcome.stderr
    result = json.loads(outcome.stdout)
    assert result["reason"] == "error"
    assert result["error"]["stage"] == "import"
    assert "submission.problem_generator" in result["error"]["message"]

"""Run a controller for one match seat and respond to the host.

Usage: python -m controllers.open.seat --connect PATH [--submission DIR | --example]

The seat connects to the host's socket, then imports the controller from
``controllers/open/submission``, ``--submission DIR``, or the example selected
by ``--example``. A separate submission directory allows four students'
controllers to run on one machine. Each game uses a new controller instance,
which supplies actions for each tick. If a response misses the host's
deadline, the seat skips pending ticks and processes the latest one.

Controller output is written to the seat's output stream. Communication with
the host uses only the socket.
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from collections.abc import Callable
from pathlib import Path

from simulator.context import Context
from simulator.controller import Controller
from simulator.environment import Environment
from simulator.match.protocol import Connection, ConnectionClosed, connect
from simulator.run import RUN_ERRORS
from simulator.run.result import ErrorStage, RunError

SUBMISSION = "controllers.open.submission"

Factory = Callable[[], Controller]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m controllers.open.seat")
    parser.add_argument("--connect", required=True, help="The host's socket.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--submission", type=Path, help="A submission folder to play.")
    source.add_argument("--example", action="store_true", help="Play the example.")
    parser.add_argument(
        "--wait", type=float, default=30.0, help="Seconds to wait for the host."
    )
    args = parser.parse_args(argv)

    connection = connect(args.connect, wait_seconds=args.wait)
    try:
        factory = load_controller(submission=args.submission, example=args.example)
    except RUN_ERRORS as error:
        _report(connection, error, "import")
        return 1
    try:
        connection.send({"type": "hello"})
        return serve(connection, factory)
    except ConnectionClosed:
        # The host has disconnected, so no further result can be reported.
        return 0
    finally:
        connection.close()


def load_controller(
    *, submission: Path | None = None, example: bool = False
) -> Factory:
    """Import the seat controller and return its factory."""
    if example:
        from controllers.open.example import ExampleController

        return ExampleController
    if submission is not None:
        _mount_submission(submission)
    from controllers.open.submission.controller import OpenController

    return OpenController


def serve(connection: Connection, factory: Factory) -> int:
    """Run games requested by the host until it closes the session."""
    context = Context()
    controller: Controller | None = None
    game: int | None = None
    try:
        while True:
            messages = connection.receive(None)
            ticks = [message for message in messages if message["type"] == "tick"]
            newest = ticks[-1] if ticks else None
            for message in messages:
                kind = message["type"]
                if kind == "start":
                    _shut_down(controller)
                    controller = None
                    game = message["game"]
                    try:
                        controller = factory()
                        controller.set_controlled_agents({message["chef"]})
                    except RUN_ERRORS as error:
                        _report(connection, error, "build")
                        return 1
                    connection.send({"type": "ready", "game": game})
                elif kind == "tick":
                    # Discard ticks whose response deadlines have passed.
                    if (
                        message is not newest
                        or controller is None
                        or message["game"] != game
                    ):
                        continue
                    try:
                        environment = Environment.from_dict(message["environment"])
                        actions = controller.get_actions(environment, context)
                        answer = [action.to_dict() for action in actions]
                    except RUN_ERRORS as error:
                        _report(connection, error, "run")
                        return 1
                    connection.send(
                        {
                            "type": "actions",
                            "game": game,
                            "timestep": message["timestep"],
                            "actions": answer,
                        }
                    )
                elif kind == "end":
                    _shut_down(controller)
                    controller = None
                elif kind == "bye":
                    return 0
    finally:
        _shut_down(controller)


def _mount_submission(folder: Path) -> None:
    """Make ``controllers.open.submission`` import from ``folder``.

    The package is configured before import so that both absolute and relative
    imports in student code resolve to the submission files.
    """
    import importlib.util
    import types

    import controllers.open

    folder = folder.resolve()
    init = folder / "__init__.py"
    if init.is_file():
        spec = importlib.util.spec_from_file_location(
            SUBMISSION, init, submodule_search_locations=[str(folder)]
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot import a submission from {folder}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[SUBMISSION] = module
        spec.loader.exec_module(module)
    else:
        module = types.ModuleType(SUBMISSION)
        module.__path__ = [str(folder)]
        sys.modules[SUBMISSION] = module
    vars(controllers.open)["submission"] = module


def _report(connection: Connection, error: BaseException, stage: ErrorStage) -> None:
    try:
        connection.send(
            {
                "type": "error",
                "error": RunError.from_exception(error, stage=stage).to_dict(),
            }
        )
    except ConnectionClosed:
        pass


def _shut_down(controller: Controller | None) -> None:
    if controller is None:
        return
    # The game has ended; controller shutdown failures cannot affect its result.
    with contextlib.suppress(*RUN_ERRORS):
        controller.shutdown()


if __name__ == "__main__":
    sys.exit(main())

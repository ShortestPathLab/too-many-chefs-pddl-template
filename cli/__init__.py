"""Argument handling for the ``cook`` command."""

from cli.assignments import (
    RunControllers,
    build_agent_controller,
    controller_assignments,
    import_controllers,
)
from cli.controller_options import (
    controller_listing,
    parse_controller_options,
    with_controller_options,
)
from cli.end_conditions import build_end_conditions
from cli.outputs import resolve_recording_output, resolve_run_outputs
from cli.setup import describe_run
from cli.teams import teams_help, with_teams

__all__ = [
    "RunControllers",
    "build_agent_controller",
    "build_end_conditions",
    "controller_assignments",
    "controller_listing",
    "describe_run",
    "import_controllers",
    "parse_controller_options",
    "resolve_recording_output",
    "resolve_run_outputs",
    "teams_help",
    "with_controller_options",
    "with_teams",
]

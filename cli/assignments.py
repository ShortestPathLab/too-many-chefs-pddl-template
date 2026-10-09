"""Build controllers from the command-line assignments."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

import typer

from controllers import (
    ControllerOptionError,
    ControllerOptions,
    ControllerPlugin,
    ControllerUnavailableError,
    available_controllers,
    controller_plugin,
)
from simulator.composite_controller import CompositeController
from simulator.configuration import Configuration, load
from simulator.controller import Controller
from simulator.entities import Agent
from simulator.planning_budget import BudgetedController
from simulator.run import ControllerAssignment


@dataclass(frozen=True)
class RunControllers:
    """The controller a run steps, and the assignments that describe it."""

    controller: Controller
    assignments: list[ControllerAssignment] = field(default_factory=list)


def build_agent_controller(
    configuration: Configuration,
    *,
    default_controller: str,
    assignments: list[str],
    planning_budget: float | None = None,
    options: Mapping[str, ControllerOptions] | None = None,
) -> RunControllers:
    """Build the controller for a run.

    Without ``--assign``, ``default_controller`` owns every agent. With
    ``--assign``, each named controller owns its listed agents and the default
    controller owns any remaining agents.

    Each controller gets its own planning budget. ``options`` holds each
    plugin's validated options by plugin name; a plugin left out gets its
    defaults.
    """
    plugin_options = dict(options or {})

    def build(name: str) -> tuple[Controller, dict]:
        plugin = plugin_or_fail(name)
        chosen = plugin_options.get(name, plugin.options())
        controller = create_or_fail(plugin, chosen)
        details = plugin.describe(controller) if plugin.describe else {}
        return on_a_clock(controller, planning_budget), details

    described = controller_assignments(
        configuration,
        default_controller=default_controller,
        assignments=assignments,
    )
    built = [(entry, *build(entry.controller)) for entry in described]
    assignments_with_details = [
        entry.copy_with(details=details) for entry, _, details in built
    ]

    if not assignments:
        (_, controller, _), *_ = built
        return RunControllers(controller, assignments_with_details)

    explicit = [
        (controller, entry.agents) for entry, controller, _ in built if entry.agents
    ]
    fallback = next(
        (controller for entry, controller, _ in built if not entry.agents),
        None,
    )
    return RunControllers(
        CompositeController(explicit, fallback=fallback),
        assignments_with_details,
    )


def controller_assignments(
    configuration: Configuration,
    *,
    default_controller: str,
    assignments: list[str],
) -> list[ControllerAssignment]:
    """Return each controller in the run and the chefs it was given.

    An entry with no chefs is the ``--controller`` default, which takes
    whatever ``--assign`` left over. Without ``--assign`` that is the only
    entry and it owns the kitchen.
    """
    if not assignments:
        return [ControllerAssignment(controller=default_controller)]

    known_agent_ids = {
        agent.id for agent in load(configuration).get_entities_of_type(Agent)
    }

    described: list[ControllerAssignment] = []
    claimed: set[str] = set()
    for spec in assignments:
        controller_name, agent_ids = parse_assignment(spec)
        for agent_id in agent_ids:
            if agent_id not in known_agent_ids:
                raise typer.BadParameter(
                    f"Unknown agent {agent_id!r}."
                    f" Level agents: {', '.join(sorted(known_agent_ids)) or 'none'}",
                    param_hint="--assign",
                )
            if agent_id in claimed:
                raise typer.BadParameter(
                    f"Agent {agent_id!r} is assigned to more than one controller.",
                    param_hint="--assign",
                )
            claimed.add(agent_id)
        described.append(
            ControllerAssignment(controller=controller_name, agents=agent_ids)
        )

    if not claimed >= known_agent_ids:
        described.append(ControllerAssignment(controller=default_controller))
    return described


def on_a_clock(controller: Controller, budget_seconds: float | None) -> Controller:
    """Wrap a controller with a planning budget when one was set."""
    if budget_seconds is None:
        return controller
    return BudgetedController(controller, budget_seconds=budget_seconds)


def parse_assignment(
    spec: str,
    *,
    param_hint: str = "--assign",
    subject: str = "controller",
) -> tuple[str, list[str]]:
    """Parse a ``name=agent,agent`` assignment.

    ``--assign`` uses the name for a controller and ``--team`` uses it for a
    side. Both options use the same format.
    """
    name, separator, agents = spec.partition("=")
    name = name.strip()
    if not separator or not name:
        raise typer.BadParameter(
            f"Expected '{subject}=agent,agent', got {spec!r}.",
            param_hint=param_hint,
        )
    agent_ids = [agent_id.strip() for agent_id in agents.split(",") if agent_id.strip()]
    if not agent_ids:
        raise typer.BadParameter(
            f"{param_hint} {spec!r} names no agents.",
            param_hint=param_hint,
        )
    return name, agent_ids


def import_controllers(names: Iterable[str]) -> None:
    """Import the code of each named controller that puts it off.

    The PDDL plugin leaves the students' modules unimported until a run needs
    them. Importing them here, before any controller is built, lets the
    command line tell a module that will not import from a controller that
    raises while it is built.
    """
    for name in dict.fromkeys(names):
        plugin = plugin_or_fail(name)
        if plugin.load is not None:
            plugin.load()


def plugin_or_fail(name: str) -> ControllerPlugin:
    try:
        return controller_plugin(name)
    except KeyError:
        raise typer.BadParameter(
            f"Unknown controller {name!r}."
            f" Available controllers: {', '.join(available_controllers())}",
            param_hint="--controller",
        ) from None


def create_or_fail(plugin: ControllerPlugin, options: ControllerOptions) -> Controller:
    """Check the plugin can run here, then build it.

    A controller that cannot run here stops the command with its install
    instructions. A bad option value is reported against its flag.
    """
    from cli.controller_options import option_flag

    try:
        if plugin.check is not None:
            plugin.check(options)
        return plugin.create(options)
    except ControllerUnavailableError as unavailable:
        typer.echo(str(unavailable), err=True)
        raise typer.Exit(code=1) from None
    except ControllerOptionError as error:
        field = plugin.options.model_fields.get(error.field)
        raise typer.BadParameter(
            str(error),
            param_hint=(
                option_flag(plugin, error.field, field)
                if field is not None
                else f"--controller {plugin.name}"
            ),
        ) from None

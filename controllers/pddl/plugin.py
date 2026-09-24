"""The PDDL controller's command-line plugin.

Everything the ``cook`` command line knows about planners lives here: the
``--solver`` option, the check that a planner is installed, the planner named
in a result, and the ``cook pddl solvers`` listing.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

import typer
from pydantic import Field

from controllers.registry import (
    ControllerOptionError,
    ControllerOptions,
    ControllerPlugin,
    ControllerUnavailableError,
)
from simulator.controller import Controller

from .controller import PDDLController
from .solvers import (
    Solver,
    SolverUnavailableError,
    available_solvers,
    known_solvers,
    no_solver_message,
    resolve_solver,
    solver_type,
)


def solver_help() -> str:
    """Return the ``--solver`` help, which spells out the selection order."""
    return (
        "PDDL solver to plan with. Left out, these are tried in order and the"
        f" first one installed here does the planning: {solver_order()}."
        f"{missing_solver_hint()}"
        " Run `cook pddl solvers` for what each one does."
    )


def solver_order() -> str:
    """Return the solvers in selection order, marking the installed ones."""
    return ", ".join(
        f"{name} (installed)" if solver_type(name).is_available() else name
        for name in known_solvers()
    )


def missing_solver_hint() -> str:
    """Return how to install a solver this machine lacks, or nothing.

    Naming one that is actually missing keeps the example runnable.
    """
    missing = [name for name in known_solvers() if not solver_type(name).is_available()]
    if not missing:
        return ""
    extra = solver_type(missing[0]).extra
    return f" The rest come from a project extra: uv sync --extra {extra}."


def solver_listing() -> str:
    """Return known solvers in selection order, one per line.

    Uninstalled solvers include the extra needed to install them.
    """
    installed = available_solvers()
    default = installed[0] if installed else None
    lines = [
        "Tried in this order. The first one installed here does the planning.",
        "",
    ]
    for name in known_solvers():
        found = solver_type(name)
        if not found.is_available():
            state = f"not installed (uv sync --extra {found.extra})"
        elif name == default:
            state = "installed, used by default"
        else:
            state = "installed"
        lines.append(f"{name:<14} {state:<46} {found.summary}")
    return "\n".join(lines)


class PDDLOptions(ControllerOptions):
    solver: str | None = Field(
        default=None,
        description=solver_help(),
        json_schema_extra={"flag": "--solver"},
    )


def load() -> None:
    """Import the default controller, and with it the students' modules."""
    import_module(".default_controller", __package__)


def create(options: ControllerOptions) -> Controller:
    assert isinstance(options, PDDLOptions)
    from .default_controller import DefaultPDDLController

    return DefaultPDDLController(solver=resolve_solver_or_fail(options.solver))


def check(options: ControllerOptions) -> None:
    """Fail early when nothing can plan.

    A named solver is checked when it is resolved. Without one, any installed
    solver will do.
    """
    assert isinstance(options, PDDLOptions)
    if options.solver is not None or available_solvers():
        return
    raise ControllerUnavailableError(no_solver_message())


def describe(controller: Controller) -> dict[str, Any]:
    """Name the planner a controller plans with, and how it was chosen.

    An omitted ``--solver`` is resolved the way the planning workers resolve
    it, by taking the first installed solver in priority order.
    """
    if not isinstance(controller, PDDLController):
        return {}
    if controller.solver is not None:
        return {"solver": controller.solver.name, "solver_selection": "named"}
    return {"solver": resolve_solver().name, "solver_selection": "automatic"}


def resolve_solver_or_fail(name: str | None) -> Solver | None:
    """Resolve a named solver or report how to install it."""
    if name is None:
        return None
    try:
        return resolve_solver(name)
    except KeyError:
        raise ControllerOptionError(
            f"Unknown solver {name!r}. Known solvers: {', '.join(known_solvers())}",
            field="solver",
        ) from None
    except SolverUnavailableError:
        raise ControllerOptionError(
            f"Solver {name!r} is not installed."
            f" Installed solvers: {', '.join(available_solvers())}."
            f" Install it with: uv sync --extra {solver_type(name).extra}",
            field="solver",
        ) from None


commands = typer.Typer(help="PDDL planner commands.", no_args_is_help=True)


@commands.command()
def solvers() -> None:
    """List the available PDDL solvers."""
    typer.echo(solver_listing())


PDDL_PLUGIN = ControllerPlugin(
    name="pddl",
    summary="Plans with a PDDL solver and replans when the kitchen changes.",
    create=create,
    load=load,
    options=PDDLOptions,
    check=check,
    describe=describe,
    commands=commands,
    default=True,
)

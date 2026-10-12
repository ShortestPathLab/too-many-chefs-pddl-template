"""Register and select PDDL solvers."""

from __future__ import annotations

from .base import Solver, SolverUnavailableError

_registry: dict[str, type[Solver]] = {}


def register_solver[SolverT: Solver](solver_type: type[SolverT]) -> type[SolverT]:
    """Register a solver class under its ``name``."""
    name = solver_type.name
    existing = _registry.get(name)
    if existing is not None and existing is not solver_type:
        raise ValueError(f"Solver {name!r} is already registered")
    _registry[name] = solver_type
    return solver_type


def known_solvers() -> list[str]:
    """Return all registered solvers in priority order."""
    return [solver_type.name for solver_type in _ordered()]


def available_solvers() -> list[str]:
    """Return installed solvers in priority order."""
    return [
        solver_type.name for solver_type in _ordered() if solver_type.is_available()
    ]


def solver_type(name: str) -> type[Solver]:
    """The class registered under ``name``."""
    found = _registry.get(name)
    if found is None:
        raise KeyError(
            f"Unknown solver {name!r}."
            f" Known solvers: {', '.join(known_solvers()) or 'none'}"
        )
    return found


def resolve_solver(name: str | None = None) -> Solver:
    """Return the requested solver or the best installed solver.

    An explicitly named but unavailable solver raises an error instead of being
    replaced by another solver.
    """
    if name is not None:
        found = solver_type(name)
        if not found.is_available():
            raise SolverUnavailableError(unavailable_message(found))
        return found()

    for candidate in _ordered():
        if candidate.is_available():
            return candidate()
    raise SolverUnavailableError(no_solver_message())


def unavailable_message(solver_type: type[Solver]) -> str:
    """Return an installation message for an unavailable solver."""
    return (
        f"Solver {solver_type.name!r} is not installed."
        f" Install it with: uv sync --extra {solver_type.extra}"
    )


def no_solver_message() -> str:
    """Return the message shown when no solver is installed."""
    lines = ["No PDDL solver is installed, so nothing can plan.", ""]
    lines += [
        f"    uv sync --extra {entry.extra:<14} {entry.summary}" for entry in _ordered()
    ]
    lines += [
        "",
        "Any one of them is enough. `cook pddl solvers` lists them again later.",
    ]
    return "\n".join(lines)


def _ordered() -> list[type[Solver]]:
    return sorted(_registry.values(), key=lambda entry: (entry.priority, entry.name))

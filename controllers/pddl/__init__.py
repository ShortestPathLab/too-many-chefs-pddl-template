"""The PDDL controller.

Implement the interfaces defined in ``interfaces.py`` under ``submission/``.
``problem_builder.py`` generates PDDL problem text. ``controller.py`` runs
the planning pipeline, and ``default_controller.py`` supplies the two
submission classes. ``plugin.py`` defines the command-line interface, while
``solvers/`` provides planner adapters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .controller import PDDLController
from .interfaces import FromPDDL, PDDLPlanStep, PDDLProblem, ProblemGenerator
from .plugin import PDDL_PLUGIN, PDDLOptions
from .problem_builder import ProblemBuilder

if TYPE_CHECKING:
    from .default_controller import DefaultPDDLController
    from .submission.from_pddl import DefaultFromPDDL
    from .submission.problem_generator import DefaultProblemGenerator

# Load student modules on first use. Import failures are then reported in
# the affected run results without preventing other commands from starting.
_STUDENT_CODE = {
    "DefaultFromPDDL": ".submission.from_pddl",
    "DefaultPDDLController": ".default_controller",
    "DefaultProblemGenerator": ".submission.problem_generator",
}


def __getattr__(name: str) -> Any:
    module = _STUDENT_CODE.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    return getattr(import_module(module, __name__), name)


__all__ = [
    "PDDL_PLUGIN",
    "DefaultFromPDDL",
    "DefaultPDDLController",
    "DefaultProblemGenerator",
    "FromPDDL",
    "PDDLController",
    "PDDLOptions",
    "PDDLPlanStep",
    "PDDLProblem",
    "ProblemBuilder",
    "ProblemGenerator",
]

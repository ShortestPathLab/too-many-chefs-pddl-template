"""The PDDL controller.

Your code goes in ``submission/``, and ``interfaces.py`` is the contract it
meets. ``controller.py`` runs the planning pipeline, ``default_controller.py``
plugs your two classes into it, ``plugin.py`` is everything the command line
knows about it, and ``solvers/`` holds the planners.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .controller import PDDLController
from .interfaces import FromPDDL, PDDLPlanStep, PDDLProblem, ProblemGenerator
from .plugin import PDDL_PLUGIN, PDDLOptions

if TYPE_CHECKING:
    from .default_controller import DefaultPDDLController
    from .submission.from_pddl import DefaultFromPDDL
    from .submission.problem_generator import DefaultProblemGenerator

# These live in the modules students write. They load on first use, so a
# module that will not import ends the runs that use it, with a result that
# says so, instead of stopping every command before it starts.
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
    "ProblemGenerator",
]

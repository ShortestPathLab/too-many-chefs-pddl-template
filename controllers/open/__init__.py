"""The open controller, which Part 4's 2v2 competition runs.

Your code goes in ``submission/``, starting from ``submission/controller.py``.
``example.py`` is a sparring partner for ``cook match``, ``seat.py`` runs one
controller in a match, and ``plugin.py`` is what the command line knows about
it, as ``--controller open``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .plugin import OPEN_PLUGIN

if TYPE_CHECKING:
    from .submission.controller import OpenController


def __getattr__(name: str) -> Any:
    # The controller is the students' code, so it loads on first use, as the
    # PDDL controller's does. A module that will not import then ends the runs
    # that use it instead of every command.
    if name == "OpenController":
        from .submission.controller import OpenController

        return OpenController
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["OPEN_PLUGIN", "OpenController"]

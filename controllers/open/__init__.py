"""The open controller for Part 4's 2v2 competition.

Implement the controller in ``submission/``, starting with
``submission/controller.py``. ``example.py`` provides a test opponent for
``cook match``, ``seat.py`` runs a controller in a match, and ``plugin.py``
registers the command-line interface as ``--controller open``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .plugin import OPEN_PLUGIN

if TYPE_CHECKING:
    from .submission.controller import OpenController


def __getattr__(name: str) -> Any:
    # Load the student controller on first use, as with the PDDL controller.
    # Import failures then affect only runs that use it.
    if name == "OpenController":
        from .submission.controller import OpenController

        return OpenController
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["OPEN_PLUGIN", "OpenController"]

"""The open controller's command-line plugin, ``--controller open``."""

from __future__ import annotations

from importlib import import_module

from controllers.registry import ControllerOptions, ControllerPlugin
from simulator.controller import Controller


def load() -> None:
    """Import the students' controller."""
    import_module(".submission.controller", __package__)


def create(options: ControllerOptions) -> Controller:
    from .submission.controller import OpenController

    return OpenController()


OPEN_PLUGIN = ControllerPlugin(
    name="open",
    summary="Your Part 4 controller: any technique, one chef each in a match.",
    create=create,
    load=load,
)

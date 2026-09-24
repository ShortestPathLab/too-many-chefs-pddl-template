"""The controllers ``--controller`` can name, and the code they share.

Each controller is a plugin, declared with ``registry.py`` and registered
below. ``pddl/`` is the PDDL controller for Parts 1 to 3 and ``open/`` is the
open controller for Part 4's competition. ``navigation/`` walks chefs to where
a plan says to act, for any controller that wants it.
"""

from typing import TYPE_CHECKING, Any

from controllers.open import OPEN_PLUGIN
from controllers.pddl import PDDL_PLUGIN
from controllers.registry import (
    ControllerOptionError,
    ControllerOptions,
    ControllerPlugin,
    ControllerUnavailableError,
    available_controllers,
    controller_plugin,
    controller_plugins,
    create_controller,
    default_controller_name,
    register_controller,
)

if TYPE_CHECKING:
    from controllers.open import OpenController
    from controllers.pddl import DefaultPDDLController

register_controller(PDDL_PLUGIN)
register_controller(OPEN_PLUGIN)


def __getattr__(name: str) -> Any:
    # Both controllers import the students' modules, so they load on first
    # use. See ``controllers.pddl`` and ``controllers.open``.
    if name == "DefaultPDDLController":
        import controllers.pddl

        return controllers.pddl.DefaultPDDLController
    if name == "OpenController":
        import controllers.open

        return controllers.open.OpenController
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ControllerOptionError",
    "ControllerOptions",
    "ControllerPlugin",
    "ControllerUnavailableError",
    "DefaultPDDLController",
    "OpenController",
    "available_controllers",
    "controller_plugin",
    "controller_plugins",
    "create_controller",
    "default_controller_name",
    "register_controller",
]

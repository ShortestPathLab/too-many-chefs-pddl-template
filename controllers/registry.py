"""Register controllers and the command-line options they take.

A controller joins the ``cook`` command line by registering a plugin. The
plugin says how to build the controller, which options it accepts, how to
check that it can run here, and what to record about it in a result. The
command line reads all of that from the registry, so it needs no knowledge of
any one controller.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from simulator.controller import Controller

if TYPE_CHECKING:
    import typer


class ControllerOptions(BaseModel):
    """Options a controller takes from the command line.

    Subclass this with one field per option. Each field becomes a flag named
    ``--<plugin>-<field>``, or the flag named in the field's
    ``json_schema_extra["flag"]``. The field description is its help text.
    """

    model_config = ConfigDict(extra="forbid")


class ControllerOptionError(ValueError):
    """Raised when an option value cannot be used.

    ``field`` names the option, so the command line can point at the flag.
    """

    def __init__(self, message: str, *, field: str) -> None:
        super().__init__(message)
        self.field = field


class ControllerUnavailableError(RuntimeError):
    """Raised by a plugin's ``check`` when the controller cannot run here.

    The message should say what to install.
    """


Load = Callable[[], object]
Create = Callable[[ControllerOptions], Controller]
Check = Callable[[ControllerOptions], None]
Describe = Callable[[Controller], dict[str, Any]]


@dataclass(frozen=True)
class ControllerPlugin:
    """Everything the command line needs to offer a controller."""

    #: The ``--controller`` name.
    name: str
    #: One line for ``cook controllers``.
    summary: str
    #: Build the controller from validated options.
    create: Create
    #: Import the code the controller runs, when the plugin leaves that until
    #: a run needs it. A module that will not import then ends only the runs
    #: that use it, and the command line reports it apart from ``create``.
    load: Load | None = None
    #: The options model. The base class takes no options.
    options: type[ControllerOptions] = ControllerOptions
    #: Fail before the run starts when the controller cannot run here.
    check: Check | None = None
    #: Details for the result JSON, such as which planner was chosen.
    describe: Describe | None = None
    #: Commands mounted under ``cook <name>``.
    commands: typer.Typer | None = field(default=None, repr=False)
    #: Whether ``--controller`` picks this plugin when left out.
    default: bool = False


_registry: dict[str, ControllerPlugin] = {}


def register_controller(plugin: ControllerPlugin) -> ControllerPlugin:
    """Register a plugin under its name."""
    existing = _registry.get(plugin.name)
    if existing is not None and existing is not plugin:
        raise ValueError(f"Controller {plugin.name!r} is already registered")
    _registry[plugin.name] = plugin
    return plugin


def controller_plugin(name: str) -> ControllerPlugin:
    """Return the plugin registered under ``name``."""
    plugin = _registry.get(name)
    if plugin is None:
        raise KeyError(
            f"Unknown controller {name!r}."
            f" Available controllers: {', '.join(available_controllers()) or 'none'}"
        )
    return plugin


def controller_plugins() -> list[ControllerPlugin]:
    """Return every registered plugin, by name."""
    return [_registry[name] for name in available_controllers()]


def create_controller(
    name: str,
    options: ControllerOptions | None = None,
) -> Controller:
    """Create the controller registered under ``name``.

    Without ``options``, the plugin's defaults apply.
    """
    plugin = controller_plugin(name)
    return plugin.create(options if options is not None else plugin.options())


def available_controllers() -> list[str]:
    return sorted(_registry)


def default_controller_name() -> str:
    """Return the controller ``--controller`` picks when left out.

    That is the plugin registered as the default, or the first by name.
    """
    for plugin in controller_plugins():
        if plugin.default:
            return plugin.name
    names = available_controllers()
    if not names:
        raise LookupError("No controllers are registered")
    return names[0]

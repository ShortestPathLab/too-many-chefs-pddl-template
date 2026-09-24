"""Put each controller plugin's options on the ``agent`` command.

Typer builds a command from a function's signature. A plugin registered
later cannot add a parameter to that signature by ordinary means, so
``with_controller_options`` rewrites the signature of ``agent`` to include one
keyword parameter per plugin option before Typer reads it. The values arrive in
the function's ``**controller_options`` and ``parse_controller_options`` turns
them back into one options model per plugin.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from typing import Annotated, Any

import typer
from pydantic import ValidationError
from pydantic.fields import FieldInfo

from controllers import (
    ControllerOptions,
    ControllerPlugin,
    controller_plugins,
)


def with_controller_options(func: Callable[..., Any]) -> Callable[..., Any]:
    """Add every registered plugin option to ``func``'s signature.

    ``func`` must accept ``**controller_options``. Apply this below
    ``@app.command()`` so Typer sees the rewritten signature.
    """
    # Evaluate string annotations so Typer sees the real ``Annotated`` types.
    signature = inspect.signature(func, eval_str=True)
    parameters = [
        parameter
        for parameter in signature.parameters.values()
        if parameter.kind is not inspect.Parameter.VAR_KEYWORD
    ]
    if len(parameters) == len(signature.parameters):
        name = getattr(func, "__name__", "The command")
        raise TypeError(f"{name} must accept **controller_options")
    parameters.extend(controller_option_parameters())
    func.__signature__ = signature.replace(parameters=parameters)  # ty: ignore[unresolved-attribute]
    return func


def controller_option_parameters() -> list[inspect.Parameter]:
    """Return one keyword parameter per registered plugin option."""
    parameters: list[inspect.Parameter] = []
    flags: dict[str, str] = {}
    for plugin in controller_plugins():
        for field_name, field in plugin.options.model_fields.items():
            flag = option_flag(plugin, field_name, field)
            owner = flags.setdefault(flag, plugin.name)
            if owner != plugin.name:
                raise ValueError(
                    f"Controllers {owner!r} and {plugin.name!r} both define {flag}"
                )
            parameters.append(
                inspect.Parameter(
                    parameter_name(plugin, field_name),
                    inspect.Parameter.KEYWORD_ONLY,
                    default=field.default,
                    annotation=Annotated[
                        field.annotation,
                        typer.Option(flag, help=field.description or ""),
                    ],
                )
            )
    return parameters


def parse_controller_options(
    values: Mapping[str, Any],
) -> dict[str, ControllerOptions]:
    """Validate the collected option values, one model per plugin.

    ``values`` is keyed the way ``controller_option_parameters`` named them.
    """
    options: dict[str, ControllerOptions] = {}
    for plugin in controller_plugins():
        fields = {
            field_name: values[parameter_name(plugin, field_name)]
            for field_name in plugin.options.model_fields
            if parameter_name(plugin, field_name) in values
        }
        try:
            options[plugin.name] = plugin.options.model_validate(fields)
        except ValidationError as error:
            first = error.errors()[0]
            field_name = str(first["loc"][0]) if first["loc"] else ""
            field = plugin.options.model_fields.get(field_name)
            raise typer.BadParameter(
                first["msg"],
                param_hint=(
                    option_flag(plugin, field_name, field)
                    if field is not None
                    else f"--controller {plugin.name}"
                ),
            ) from None
    return options


def option_flag(plugin: ControllerPlugin, field_name: str, field: FieldInfo) -> str:
    """Return the flag for a plugin option.

    A field can name its own flag in ``json_schema_extra["flag"]``. Otherwise the
    flag is the plugin name and the field name joined with dashes.
    """
    extra = field.json_schema_extra
    flag = extra.get("flag") if isinstance(extra, dict) else None
    if isinstance(flag, str):
        return flag
    return f"--{plugin.name}-{field_name}".replace("_", "-")


def parameter_name(plugin: ControllerPlugin, field_name: str) -> str:
    return f"{plugin.name}_{field_name}".replace("-", "_")


def controller_listing() -> str:
    """Return every controller with its summary and options, one per line."""
    lines = []
    for plugin in controller_plugins():
        suffix = " (default)" if plugin.default else ""
        lines.append(f"{plugin.name}{suffix}")
        lines.append(f"    {plugin.summary}")
        for field_name, field in plugin.options.model_fields.items():
            flag = option_flag(plugin, field_name, field)
            lines.append(f"    {flag}: {field.description or ''}".rstrip(": "))
    return "\n".join(lines)

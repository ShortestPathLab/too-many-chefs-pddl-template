"""Test how controller plugins put their options on the command line."""

from __future__ import annotations

import inspect
from collections.abc import Iterator
from typing import Annotated, Any

import pytest
import typer
from pydantic import Field
from typer.testing import CliRunner

from cli.controller_options import (
    controller_listing,
    controller_option_parameters,
    parse_controller_options,
    with_controller_options,
)
from controllers import (
    ControllerOptions,
    ControllerPlugin,
    ControllerUnavailableError,
    registry,
)
from controllers.open import OpenController
from simulator.controller import Controller


class _StubOptions(ControllerOptions):
    depth: int = Field(default=3, description="How far to look ahead.")
    greedy: bool = Field(
        default=False,
        description="Take the first order.",
        json_schema_extra={"flag": "--greedy"},
    )


class _StubController(OpenController):
    def __init__(self, depth: int) -> None:
        super().__init__()
        self.depth = depth


def _create(options: ControllerOptions) -> Controller:
    assert isinstance(options, _StubOptions)
    return _StubController(options.depth)


def _check(options: ControllerOptions) -> None:
    assert isinstance(options, _StubOptions)
    if options.depth > 10:
        raise ControllerUnavailableError("Install a bigger computer.")


STUB_PLUGIN = ControllerPlugin(
    name="stub",
    summary="A controller for these tests.",
    create=_create,
    options=_StubOptions,
    check=_check,
)


@pytest.fixture
def stub_plugin() -> Iterator[ControllerPlugin]:
    saved = dict(registry._registry)
    registry.register_controller(STUB_PLUGIN)
    try:
        yield STUB_PLUGIN
    finally:
        registry._registry.clear()
        registry._registry.update(saved)


def test_each_option_becomes_a_flag_named_after_its_plugin(
    stub_plugin: ControllerPlugin,
) -> None:
    # In ``Annotated`` form, Typer keeps the first flag in ``default``.
    flags = {
        parameter.name: parameter.annotation.__metadata__[0].default
        for parameter in controller_option_parameters()
    }

    assert flags["stub_depth"] == "--stub-depth"
    assert flags["stub_greedy"] == "--greedy"
    assert flags["pddl_solver"] == "--solver"


def test_two_plugins_cannot_share_a_flag(stub_plugin: ControllerPlugin) -> None:
    rival = ControllerPlugin(
        name="rival",
        summary="Wants --greedy too.",
        create=_create,
        options=_StubOptions,
    )
    registry.register_controller(
        ControllerPlugin(
            name="rival",
            summary=rival.summary,
            create=rival.create,
            options=type(
                "_RivalOptions",
                (ControllerOptions,),
                {
                    "__annotations__": {"greedy": bool},
                    "greedy": Field(
                        default=False, json_schema_extra={"flag": "--greedy"}
                    ),
                },
            ),
        )
    )

    with pytest.raises(ValueError, match="--greedy"):
        controller_option_parameters()


def test_the_rewritten_signature_keeps_the_original_options(
    stub_plugin: ControllerPlugin,
) -> None:
    @with_controller_options
    def command(
        level: Annotated[str, typer.Option(help="A level.")],
        **controller_options: Any,
    ) -> None:
        pass

    names = list(inspect.signature(command).parameters)

    assert names[0] == "level"
    assert "stub_depth" in names
    assert "controller_options" not in names


def test_a_command_without_a_catch_all_is_refused() -> None:
    def command(level: str) -> None:
        pass

    with pytest.raises(TypeError):
        with_controller_options(command)


def test_typer_parses_the_injected_flags(stub_plugin: ControllerPlugin) -> None:
    app = typer.Typer()
    seen: dict[str, Any] = {}

    @app.command()
    @with_controller_options
    def run(**controller_options: Any) -> None:
        seen.update(parse_controller_options(controller_options))

    result = CliRunner().invoke(app, ["--stub-depth", "7", "--greedy"])

    assert result.exit_code == 0, result.output
    assert seen["stub"] == _StubOptions(depth=7, greedy=True)
    assert seen["pddl"].solver is None


def test_a_bad_value_is_reported_against_its_flag(
    stub_plugin: ControllerPlugin,
) -> None:
    with pytest.raises(typer.BadParameter) as error:
        parse_controller_options({"stub_depth": "deep"})

    assert error.value.param_hint == "--stub-depth"


def test_the_listing_names_each_controller_and_its_flags(
    stub_plugin: ControllerPlugin,
) -> None:
    listing = controller_listing()

    assert "stub" in listing
    assert "--stub-depth: How far to look ahead." in listing
    assert "--greedy: Take the first order." in listing
    assert "pddl (default)" in listing

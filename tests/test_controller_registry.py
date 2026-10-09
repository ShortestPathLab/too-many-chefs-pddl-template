from __future__ import annotations

import pytest

from controllers import (
    ControllerPlugin,
    DefaultPDDLController,
    OpenController,
    available_controllers,
    create_controller,
    default_controller_name,
    register_controller,
    registry,
)
from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.context import Context


def open_kitchen_configuration() -> Configuration:
    return Configuration.from_dict(
        {
            "layout": "| 1 |   |\n|   |   |",
            "state": {"orders": ["catalog/food/tomato"]},
            "legend": {
                "agents": [{"kind": "agent", "symbol": "1", "orientation": "s"}],
                "foods": [{"kind": "food", "name": "catalog/food/tomato"}],
            },
        }
    )


def test_built_in_controllers_are_registered() -> None:
    assert "pddl" in available_controllers()
    assert "open" in available_controllers()


def test_create_controller_returns_registered_types() -> None:
    pddl_controller = create_controller("pddl")
    open_controller = create_controller("open")
    try:
        assert isinstance(pddl_controller, DefaultPDDLController)
        assert isinstance(open_controller, OpenController)
    finally:
        pddl_controller.shutdown()
        open_controller.shutdown()


def test_create_controller_rejects_unknown_names() -> None:
    with pytest.raises(KeyError):
        create_controller("does-not-exist")


def test_the_pddl_controller_is_the_default() -> None:
    assert default_controller_name() == "pddl"


def test_registering_two_plugins_under_one_name_is_refused() -> None:
    impostor = ControllerPlugin(
        name="open",
        summary="Not the open controller",
        create=lambda options: OpenController(),
    )

    with pytest.raises(ValueError):
        register_controller(impostor)


def test_registering_the_same_plugin_twice_is_harmless() -> None:
    plugin = registry.controller_plugin("open")

    assert register_controller(plugin) is plugin


def test_returns_a_mutation_per_agent_each_tick() -> None:
    environment = load(open_kitchen_configuration())
    controller = OpenController()

    actions = controller.get_actions(environment, Context())

    assert len(actions) == 1
    controller.shutdown()


def test_finishes_only_when_no_orders_remain() -> None:
    environment = load(open_kitchen_configuration())
    controller = OpenController()

    assert not controller.has_finished(environment)
    controller.shutdown()

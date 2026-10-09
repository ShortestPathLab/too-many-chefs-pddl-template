"""Test actions on cells that hold more than one piece of equipment.

An action tries the equipment in a cell from the top down, portable equipment
first, and uses the first piece it can. Picking up takes food out of a station
before it lifts a portable one.
"""

from __future__ import annotations

import pytest

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.entities import Agent, Equipment, Food
from simulator.entities.agent import Orientation
from simulator.environment import Environment
from simulator.mutations import (
    Combine,
    Cook,
    Interact,
    PickUp,
    PickUpOrPlace,
    Place,
    TurnAgent,
)
from simulator.mutations.agent_mutation import AgentMutation
from simulator.mutations.mutation import IllegalMutationError

MEAT = "catalog/food/meat"
GRILLED_MEAT = "catalog/food/grilled_meat"
CHICKEN = "catalog/food/chicken"
OVEN_CHICKEN = "catalog/food/oven_chicken"
STOVE = "catalog/equipment/stove"
PAN = "catalog/equipment/pan"
OVEN = "catalog/equipment/oven"


def kitchen(layout: str, *, allow_illegal_recipes: bool = False) -> Environment:
    """Build a kitchen whose chef ``A`` starts facing west.

    ``V`` is a stove, ``R`` a pan, ``O`` an empty oven, ``C`` an oven holding
    oven-cooked chicken, and ``T`` a meat storage.
    """
    return load(
        Configuration.from_dict(
            {
                "layout": layout,
                "state": {"orders": [GRILLED_MEAT]},
                "rules": {"allow_illegal_recipes": allow_illegal_recipes},
                "legend": {
                    "agents": [{"kind": "agent", "symbol": "A", "orientation": "w"}],
                    "counters": [{"kind": "counter", "symbol": "-"}],
                    "storages": [{"kind": "storage", "symbol": "T", "food_name": MEAT}],
                    "equipment": [
                        {"kind": "equipment", "symbol": "V", "name": STOVE},
                        {
                            "kind": "equipment",
                            "symbol": "R",
                            "name": PAN,
                            "requires": STOVE,
                            "can_pick_up": True,
                        },
                        {"kind": "equipment", "symbol": "O", "name": OVEN},
                        {
                            "kind": "equipment",
                            "symbol": "C",
                            "name": OVEN,
                            "held_item": {"name": OVEN_CHICKEN, "raw": False},
                        },
                    ],
                    "foods": [
                        {"kind": "food", "name": name}
                        for name in (MEAT, GRILLED_MEAT, CHICKEN, OVEN_CHICKEN)
                    ],
                },
                "recipes": {
                    "cook": [
                        {"ingredient": MEAT, "with": PAN, "to_make": GRILLED_MEAT},
                        {"ingredient": CHICKEN, "with": OVEN, "to_make": OVEN_CHICKEN},
                    ]
                },
            }
        )
    )


def chef(environment: Environment) -> Agent:
    agent = environment.get_first_entity_of_type(Agent)
    assert agent is not None
    return agent


def act(
    environment: Environment, *steps: type[AgentMutation] | Orientation
) -> Environment:
    """Apply each step as the chef. A direction such as ``"s"`` turns it."""
    agent_id = chef(environment).id
    for step in steps:
        if isinstance(step, str):
            mutation: AgentMutation = TurnAgent(agent_id=agent_id, orientation=step)
        else:
            mutation = step(agent_id=agent_id)
        environment = mutation.run(environment)
    return environment


def equipment_named(environment: Environment, name: str) -> list[Equipment]:
    return [e for e in environment.get_entities_of_type(Equipment) if e.name == name]


def contents(environment: Environment, equipment: Equipment) -> str | None:
    if equipment.held_item_id is None:
        return None
    food = environment.get_entity_as(equipment.held_item_id, Food)
    assert food is not None
    return food.name


# The oven may come before or after the stove in the cell; neither order may
# hide the stove.
CELLS = ["OV", "VO"]


@pytest.mark.parametrize("cell", CELLS)
@pytest.mark.parametrize("set_down", [Place, PickUpOrPlace, Combine])
def test_a_pan_goes_on_a_stove_that_shares_its_cell_with_an_oven(
    cell: str, set_down: type[AgentMutation]
) -> None:
    environment = kitchen(f"| -R| A |\n|   | {cell}|")

    environment = act(environment, PickUp, "s", set_down)

    (pan,) = equipment_named(environment, PAN)
    assert (pan.x, pan.y) == (1, 1)
    assert chef(environment).hands_free


@pytest.mark.parametrize("cell", CELLS)
def test_a_pan_of_meat_goes_on_the_stove_rather_than_into_the_oven(
    cell: str,
) -> None:
    # With illegal recipes on, the oven would take the meat and spoil it.
    environment = kitchen(
        f"| -R| A | T |\n|   | {cell}|   |", allow_illegal_recipes=True
    )

    environment = act(environment, PickUp, "e", Interact, "s", Combine)

    (pan,) = equipment_named(environment, PAN)
    (oven,) = equipment_named(environment, OVEN)
    assert (pan.x, pan.y) == (1, 1)
    assert contents(environment, pan) == MEAT
    assert contents(environment, oven) is None


@pytest.mark.parametrize("set_down", [Place, Combine])
def test_a_stove_with_a_pan_on_it_takes_no_second_pan(
    set_down: type[AgentMutation],
) -> None:
    environment = act(kitchen("| -R| A |\n|   | VR|"), PickUp, "s")

    with pytest.raises(IllegalMutationError):
        act(environment, set_down)


@pytest.mark.parametrize("cell", ["CV", "VC"])
def test_food_comes_out_of_an_oven_that_shares_its_cell_with_a_stove(
    cell: str,
) -> None:
    environment = act(kitchen(f"| A |\n| {cell}|"), "s", PickUp)

    held = environment.get_entity_as(chef(environment).held_item_id or "", Food)
    assert held is not None
    assert held.name == OVEN_CHICKEN


def test_a_pan_set_on_a_stove_from_an_earlier_row_can_be_lifted_again() -> None:
    # The pan is listed before the stove, but it still sits on top of it.
    environment = kitchen("| -R| A | T |\n|   | V |   |")

    environment = act(
        environment, PickUp, "s", Place, "e", Interact, "s", Combine, Cook, PickUp
    )

    (pan,) = equipment_named(environment, PAN)
    assert chef(environment).held_item_id == pan.id
    assert contents(environment, pan) == GRILLED_MEAT


# A cooker: an oven holding chicken, with a stove and an empty pan on top.
COOKER = "| A |\n|CVR|"


def test_food_comes_out_of_the_oven_before_the_pan_above_it_is_lifted() -> None:
    environment = act(kitchen(COOKER), "s", PickUp)

    held = environment.get_entity_as(chef(environment).held_item_id or "", Food)
    assert held is not None
    assert held.name == OVEN_CHICKEN


def test_a_pickup_that_expects_the_pan_lifts_it_over_the_oven_food() -> None:
    environment = act(kitchen(COOKER), "s")

    environment = PickUp(
        agent_id=chef(environment).id, expected_held_equipment_name=PAN
    ).run(environment)

    (pan,) = equipment_named(environment, PAN)
    assert chef(environment).held_item_id == pan.id


def test_a_pickup_waiting_for_food_leaves_a_pan_without_it() -> None:
    environment = act(kitchen("| A |\n|OVR|"), "s")

    with pytest.raises(IllegalMutationError):
        PickUp(agent_id=chef(environment).id, expected_input_name=GRILLED_MEAT).run(
            environment
        )

from __future__ import annotations

import pytest

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.entities import (
    Agent,
    Counter,
    Equipment,
    Food,
    OvercookedState,
    Plate,
)
from simulator.mutations import Interact, PickUpOrPlace, TurnAgent
from simulator.mutations.mutation import IllegalMutationError


def test_interact_threads_expectations_to_storage_action() -> None:
    environment = load(
        Configuration.from_dict(
            {
                "layout": "| A | T |",
                "legend": {
                    "agents": [{"kind": "agent", "symbol": "A", "orientation": "e"}],
                    "storages": [
                        {
                            "kind": "storage",
                            "symbol": "T",
                            "food_name": "catalog/food/tomato",
                        }
                    ],
                    "foods": [
                        {
                            "kind": "food",
                            "name": "catalog/food/tomato",
                            "raw": True,
                        }
                    ],
                },
            }
        )
    )
    agent = environment.get_first_entity_of_type(Agent)
    assert agent is not None
    assert agent is not None

    updated_environment = Interact(
        agent_id=agent.id,
        expected_input_name="catalog/food/tomato",
        expected_output_name="catalog/food/tomato",
    ).run(environment)

    updated_agent = updated_environment.get_entity_as(agent.id, Agent)
    assert updated_agent is not None
    assert updated_agent is not None
    held_food = updated_environment.get_entity_as(
        updated_agent.held_item_id or "", Food
    )
    assert held_food is not None
    assert held_food is not None
    assert held_food.name == "catalog/food/tomato"

    with pytest.raises(IllegalMutationError):
        Interact(
            agent_id=agent.id,
            expected_input_name="catalog/food/onion",
        ).run(environment)


def test_pick_up_or_place_combines_held_food_into_target_equipment() -> None:
    environment = load(
        Configuration.from_dict(
            {
                "layout": "| A | p |",
                "legend": {
                    "agents": [{"kind": "agent", "symbol": "A", "orientation": "e"}],
                    "plates": [{"kind": "plate", "symbol": "p"}],
                    "foods": [
                        {
                            "kind": "food",
                            "name": "catalog/food/tomato",
                            "raw": True,
                        }
                    ],
                },
            }
        )
    )
    agent = environment.get_first_entity_of_type(Agent)
    state = environment.get_first_entity_of_type(OvercookedState)
    plate = environment.get_first_entity_of_type(Plate)
    assert agent is not None
    assert state is not None
    assert plate is not None
    assert agent is not None
    assert state is not None
    assert plate is not None

    food = state.create_food("catalog/food/tomato", x=None, y=None)
    assert food is not None
    assert food is not None
    environment = environment.with_entity(food).replace_entity(
        agent.copy_with(held_item_id=food.id)
    )

    updated_environment = PickUpOrPlace(
        agent_id=agent.id,
        expected_held_food="catalog/food/tomato",
        expected_target_equipment_name="catalog/equipment/plate",
        expected_output_name="catalog/food/tomato",
    ).run(environment)

    updated_agent = updated_environment.get_entity_as(agent.id, Agent)
    updated_plate = updated_environment.get_entity_as(plate.id, Plate)
    assert updated_agent is not None
    assert updated_plate is not None
    assert updated_agent is not None
    assert updated_plate is not None
    assert updated_agent.held_item_id is None
    plated_food = updated_environment.get_entity_as(
        updated_plate.held_item_id or "",
        Food,
    )
    assert plated_food is not None
    assert plated_food is not None
    assert plated_food.name == "catalog/food/tomato"


def test_pick_up_or_place_places_held_food_when_not_facing_combine_target() -> None:
    environment = load(
        Configuration.from_dict(
            {
                "layout": "| A | - |",
                "legend": {
                    "agents": [{"kind": "agent", "symbol": "A", "orientation": "e"}],
                    "counters": [{"kind": "counter", "symbol": "-"}],
                    "foods": [
                        {
                            "kind": "food",
                            "name": "catalog/food/tomato",
                            "raw": True,
                        }
                    ],
                },
            }
        )
    )
    agent = environment.get_first_entity_of_type(Agent)
    state = environment.get_first_entity_of_type(OvercookedState)
    counter = environment.get_first_entity_of_type(Counter)
    assert agent is not None
    assert state is not None
    assert counter is not None
    assert agent is not None
    assert state is not None
    assert counter is not None

    food = state.create_food("catalog/food/tomato", x=None, y=None)
    assert food is not None
    assert food is not None
    environment = environment.with_entity(food).replace_entity(
        agent.copy_with(held_item_id=food.id)
    )

    updated_environment = PickUpOrPlace(
        agent_id=agent.id,
        expected_held_food="catalog/food/tomato",
    ).run(environment)

    updated_agent = updated_environment.get_entity_as(agent.id, Agent)
    updated_counter = updated_environment.get_entity_as(counter.id, Counter)
    updated_food = updated_environment.get_entity_as(food.id, Food)
    assert updated_agent is not None
    assert updated_counter is not None
    assert updated_food is not None
    assert updated_agent is not None
    assert updated_counter is not None
    assert updated_food is not None
    assert updated_agent.held_item_id is None
    assert updated_counter.held_item_id == food.id
    assert (updated_food.x, updated_food.y) == (counter.x, counter.y)


def test_pouring_a_held_pan_onto_a_plate_leaves_the_pan_in_hand() -> None:
    environment = load(
        Configuration.from_dict(
            {
                "layout": "| -p| A | VP|",
                "legend": {
                    "agents": [{"symbol": "A", "orientation": "e"}],
                    "counters": [{"symbol": "-"}],
                    "plates": [{"symbol": "p"}],
                    "equipment": [
                        {"symbol": "V", "name": "catalog/equipment/stove"},
                        {
                            "symbol": "P",
                            "name": "catalog/equipment/pan",
                            "requires": "catalog/equipment/stove",
                            "can_pick_up": True,
                            "held_item": {"name": "catalog/food/grilled_meat"},
                        },
                    ],
                    "foods": [{"name": "catalog/food/grilled_meat", "raw": False}],
                },
            }
        )
    )
    agent = environment.get_first_entity_of_type(Agent)
    plate = environment.get_first_entity_of_type(Plate)
    pan = next(
        equipment
        for equipment in environment.get_entities_of_type(Equipment)
        if equipment.name == "catalog/equipment/pan"
    )
    assert agent is not None
    assert plate is not None

    lifted = PickUpOrPlace(agent_id=agent.id).run(environment)
    turned = TurnAgent(agent_id=agent.id, orientation="w").run(lifted)
    poured = PickUpOrPlace(agent_id=agent.id).run(turned)

    poured_agent = poured.get_entity_as(agent.id, Agent)
    poured_pan = poured.get_entity_as(pan.id, Equipment)
    poured_plate = poured.get_entity_as(plate.id, Plate)
    assert poured_agent is not None
    assert poured_pan is not None
    assert poured_plate is not None
    assert poured_agent.held_item_id == pan.id
    assert poured_pan.held_item_id is None
    plated = poured.get_entity_as(poured_plate.held_item_id or "", Food)
    assert plated is not None
    assert plated.name == "catalog/food/grilled_meat"

    turned_back = TurnAgent(agent_id=agent.id, orientation="e").run(poured)
    put_back = PickUpOrPlace(agent_id=agent.id).run(turned_back)

    returned_pan = put_back.get_entity_as(pan.id, Equipment)
    assert returned_pan is not None
    assert (returned_pan.x, returned_pan.y) == (pan.x, pan.y)

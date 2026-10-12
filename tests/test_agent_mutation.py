from __future__ import annotations

from simulator.mutations import PickUpOrPlace


def test_get_expected_args_excludes_kind_and_keeps_agent_id() -> None:
    mutation = PickUpOrPlace(agent_id="agent-1")

    expected_args = mutation.agent_mutation_args

    assert "kind" not in expected_args
    assert expected_args["agent_id"] == "agent-1"


def test_get_expected_args_includes_all_expected_defaults() -> None:
    mutation = PickUpOrPlace(agent_id="agent-1")

    expected_args = mutation.agent_mutation_args

    assert expected_args == {
        "agent_id": "agent-1",
        "expected_held_food": None,
        "expected_input_name": None,
        "expected_output_name": None,
        "expected_held_equipment_name": None,
        "expected_held_equipment_contents_name": None,
        "expected_target_food_name": None,
        "expected_target_equipment_name": None,
        "expected_target_equipment_contents_name": None,
    }


def test_get_expected_args_preserves_explicit_expectations() -> None:
    mutation = PickUpOrPlace(
        agent_id="agent-1",
        expected_held_food="catalog/food/tomato",
        expected_input_name="catalog/equipment/pan",
        expected_output_name="catalog/food/cooked_tomato",
        expected_held_equipment_name="catalog/equipment/plate",
        expected_held_equipment_contents_name="catalog/food/lettuce",
        expected_target_food_name="catalog/food/onion",
        expected_target_equipment_name="catalog/equipment/cutboard",
        expected_target_equipment_contents_name="catalog/food/chopped_onion",
    )

    expected_args = mutation.agent_mutation_args

    assert expected_args == {
        "agent_id": "agent-1",
        "expected_held_food": "catalog/food/tomato",
        "expected_input_name": "catalog/equipment/pan",
        "expected_output_name": "catalog/food/cooked_tomato",
        "expected_held_equipment_name": "catalog/equipment/plate",
        "expected_held_equipment_contents_name": "catalog/food/lettuce",
        "expected_target_food_name": "catalog/food/onion",
        "expected_target_equipment_name": "catalog/equipment/cutboard",
        "expected_target_equipment_contents_name": "catalog/food/chopped_onion",
    }

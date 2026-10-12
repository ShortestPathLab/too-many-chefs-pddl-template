"""Test station cooking under ``rules.timed_cooking``."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from simulator.configuration import configuration_from_dict, load_configuration
from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.configuration.load.catalog import load_equipment_catalog
from simulator.entities import Agent, Equipment, Food, Orientation, OvercookedState
from simulator.entities.garbage import is_garbage_food
from simulator.environment import Environment
from simulator.mutations import (
    AdvanceCooking,
    Combine,
    Cook,
    Mutation,
    PickUp,
    Place,
)
from simulator.mutations.cooking import cooking_progress
from simulator.mutations.mutation import IllegalMutationError, can_apply_mutation
from simulator.recording import Recording
from simulator.run import run_agent_mode
from simulator.run.end_conditions import EndConditions
from simulator.run.result import SimulationResult
from tests.stub_controller import StubController

STOVE = "catalog/equipment/stove"
PAN = "catalog/equipment/pan"
CUTBOARD = "catalog/equipment/cutboard"
MEAT = "catalog/food/meat"
GRILLED_MEAT = "catalog/food/grilled_meat"
BURNT_MEAT = "catalog/food/burnt_meat"
TOMATO = "catalog/food/tomato"
CHOPPED_TOMATO = "catalog/food/chopped_tomato"


def kitchen(**options: Any) -> Environment:
    """Build ``|C|1|VP|``: a cutboard, a chef, then a pan on a stove."""
    return load(kitchen_configuration(**options))


def kitchen_configuration(
    *,
    timed: bool = True,
    pan_time: int = 3,
    chops: int = 3,
    board_cooks_by_itself: bool = False,
    pan_cooks_by_itself: bool = True,
    chef_holds: str | None = MEAT,
    chef_faces: Orientation = "e",
    pan_holds: str | None = None,
    board_holds: str | None = None,
    extra_recipes: list[dict[str, str]] | None = None,
    allow_illegal_recipes: bool = False,
) -> Configuration:
    def holding(name: str | None) -> dict[str, Any]:
        return {"held_item": {"name": name}} if name else {}

    return Configuration.from_dict(
        {
            "layout": "|C|1|VP|",
            "state": {"orders": [GRILLED_MEAT]},
            "rules": {
                "timed_cooking": timed,
                "allow_illegal_recipes": allow_illegal_recipes,
            },
            "scoring": {"produce_ordered_item_reward": 5},
            "legend": {
                "agents": [
                    {"symbol": "1", "orientation": chef_faces, **holding(chef_holds)}
                ],
                "equipment": [
                    {"symbol": "V", "name": STOVE},
                    {
                        "symbol": "P",
                        "name": PAN,
                        "requires": STOVE,
                        "can_pick_up": True,
                        "cook_time": pan_time,
                        "cooks_by_itself": pan_cooks_by_itself,
                        **holding(pan_holds),
                    },
                    {
                        "symbol": "C",
                        "name": CUTBOARD,
                        "cook_time": chops,
                        "cooks_by_itself": board_cooks_by_itself,
                        **holding(board_holds),
                    },
                ],
                "foods": [
                    {"name": MEAT},
                    {"name": GRILLED_MEAT, "raw": False},
                    {"name": BURNT_MEAT, "raw": False},
                    {"name": TOMATO},
                    {"name": CHOPPED_TOMATO, "raw": False},
                ],
            },
            "recipes": {
                "cook": [
                    {"ingredient": MEAT, "with": PAN, "to_make": GRILLED_MEAT},
                    {
                        "ingredient": TOMATO,
                        "with": CUTBOARD,
                        "to_make": CHOPPED_TOMATO,
                    },
                    *(extra_recipes or []),
                ]
            },
        }
    )


def chef(environment: Environment) -> Agent:
    agent = environment.get_first_entity_of_type(Agent)
    assert agent is not None
    return agent


def station(environment: Environment, name: str) -> Equipment:
    equipment = next(
        equipment
        for equipment in environment.get_entities_of_type(Equipment)
        if equipment.name == name
    )
    return equipment


def contents(environment: Environment, name: str) -> str | None:
    equipment = station(environment, name)
    if equipment.held_item_id is None:
        return None
    food = environment.get_entity_as(equipment.held_item_id, Food)
    assert food is not None
    return food.name


def steps(environment: Environment, *mutations: Sequence[Mutation]) -> Environment:
    for step_mutations in mutations:
        environment = environment.step(step_mutations)
    return environment


def idle(environment: Environment, count: int) -> Environment:
    return steps(environment, *([] for _ in range(count)))


def presses(environment: Environment, count: int) -> Environment:
    agent_id = chef(environment).id
    return steps(environment, *([Cook(agent_id=agent_id)] for _ in range(count)))


def score_by_agent(environment: Environment) -> dict[str, int]:
    state = environment.get_first_entity_of_type(OvercookedState)
    assert state is not None
    return state.score_by_agent


def settings(environment: Environment, name: str) -> tuple[int, bool]:
    equipment = station(environment, name)
    return (equipment.cook_time, equipment.cooks_by_itself)


# The rule and station settings


def test_without_the_rule_every_station_cooks_in_one_press() -> None:
    environment = kitchen(timed=False, pan_time=4, chops=3)

    assert settings(environment, PAN) == (1, False)
    assert settings(environment, CUTBOARD) == (1, False)
    assert environment.tick_mutations == []


def test_the_rule_gives_each_station_its_own_settings() -> None:
    environment = kitchen(pan_time=4, chops=3)

    assert settings(environment, PAN) == (4, True)
    assert settings(environment, CUTBOARD) == (3, False)
    assert settings(environment, STOVE) == (1, False)
    assert environment.tick_mutations == [AdvanceCooking()]


def test_a_timed_kitchen_with_nothing_cooking_by_itself_has_no_tick_mutations() -> None:
    environment = kitchen(pan_cooks_by_itself=False)

    assert environment.tick_mutations == []


def catalog_level(rules: dict[str, Any], pan: dict[str, Any]) -> Environment:
    configuration = configuration_from_dict(
        {
            "layout": "|R|",
            "rules": rules,
            "legend": {"equipment": [{"symbol": "R", "name": PAN, **pan}]},
        },
        equipment_catalog=load_equipment_catalog(Path("catalog/equipment.yaml")),
    )
    return load(configuration)


def test_catalog_settings_apply_only_under_the_rule() -> None:
    assert settings(catalog_level({}, {}), PAN) == (1, False)
    assert settings(catalog_level({"timed_cooking": True}, {}), PAN) == (4, True)


def test_a_level_can_retune_a_catalog_station() -> None:
    slower = catalog_level({"timed_cooking": True}, {"cook_time": 10})
    by_hand = catalog_level({"timed_cooking": True}, {"cooks_by_itself": False})

    assert settings(slower, PAN) == (10, True)
    assert settings(by_hand, PAN) == (4, False)


def test_stations_sharing_a_name_must_agree_on_cooking_by_themselves() -> None:
    with pytest.raises(ValueError, match="cooks_by_itself"):
        configuration_from_dict(
            {
                "layout": "|P|Q|",
                "rules": {"timed_cooking": True},
                "legend": {
                    "equipment": [
                        {"symbol": "P", "name": PAN, "cooks_by_itself": True},
                        {"symbol": "Q", "name": PAN, "cooks_by_itself": False},
                    ]
                },
            }
        )


def test_the_timed_burger_demo_grills_by_itself_and_chops_by_hand() -> None:
    environment = load(load_configuration(Path("levels/demos/burger_timed.yaml")))

    assert settings(environment, PAN) == (4, True)
    assert settings(environment, CUTBOARD) == (3, False)


# Stations that cook by themselves


def test_food_is_ready_cook_time_steps_after_it_goes_in() -> None:
    environment = kitchen(pan_time=3)
    agent_id = chef(environment).id

    put_in = environment.step([Combine(agent_id=agent_id)])
    almost = idle(put_in, 1)
    ready = idle(almost, 1)

    assert contents(put_in, PAN) == MEAT
    assert contents(almost, PAN) == MEAT
    assert contents(ready, PAN) == GRILLED_MEAT


def test_a_chef_can_take_cooked_food_out_on_the_step_it_is_ready() -> None:
    environment = kitchen(pan_time=2)
    agent_id = chef(environment).id
    take_grilled_meat = PickUp(
        agent_id=agent_id,
        expected_held_equipment_name=PAN,
        expected_held_equipment_contents_name=GRILLED_MEAT,
    )

    put_in = environment.step([Combine(agent_id=agent_id)])
    ready = idle(put_in, 1)

    assert not can_apply_mutation(put_in, take_grilled_meat)
    assert can_apply_mutation(ready, take_grilled_meat)


def test_the_cook_action_is_refused_at_a_station_that_cooks_by_itself() -> None:
    environment = kitchen(chef_holds=None, pan_holds=MEAT)

    with pytest.raises(IllegalMutationError, match="cooks by itself"):
        Cook(agent_id=chef(environment).id).run(environment)


def test_manual_kitchens_do_not_cook_food_left_in_a_station() -> None:
    environment = kitchen(timed=False, chef_holds=None, pan_holds=MEAT)

    assert contents(idle(environment, 10), PAN) == MEAT


def test_a_pan_lifted_off_the_stove_keeps_its_progress() -> None:
    environment = kitchen(pan_time=3)
    agent_id = chef(environment).id

    put_in = environment.step([Combine(agent_id=agent_id)])
    lifted = steps(put_in, [PickUp(agent_id=agent_id)], [], [], [])
    back = lifted.step([Place(agent_id=agent_id)])

    assert contents(lifted, PAN) == MEAT
    assert cooking_progress(lifted, station(lifted, PAN)) == 1 / 3
    assert contents(back, PAN) == MEAT
    assert contents(idle(back, 1), PAN) == GRILLED_MEAT


def test_taking_food_out_of_a_station_that_cooks_by_itself_starts_it_over() -> None:
    environment = kitchen(board_cooks_by_itself=True, chef_holds=TOMATO, chef_faces="w")
    agent_id = chef(environment).id

    put_in = steps(environment, [Combine(agent_id=agent_id)], [])
    taken_out = put_in.step([PickUp(agent_id=agent_id)])
    put_back = taken_out.step([Combine(agent_id=agent_id)])

    assert cooking_progress(put_in, station(put_in, CUTBOARD)) == 2 / 3
    assert cooking_progress(put_back, station(put_back, CUTBOARD)) == 1 / 3
    assert contents(idle(put_back, 1), CUTBOARD) == TOMATO
    assert contents(idle(put_back, 2), CUTBOARD) == CHOPPED_TOMATO


def test_the_chef_who_put_the_food_in_is_credited() -> None:
    environment = kitchen(pan_time=2)
    agent_id = chef(environment).id

    cooked = steps(environment, [Combine(agent_id=agent_id)], [])

    assert score_by_agent(cooked) == {agent_id: 5}


def test_food_a_level_starts_with_cooks_for_the_kitchen_only() -> None:
    environment = kitchen(pan_time=2, chef_holds=None, pan_holds=MEAT)

    cooked = idle(environment, 2)
    state = cooked.get_first_entity_of_type(OvercookedState)

    assert contents(cooked, PAN) == GRILLED_MEAT
    assert state is not None
    assert state.score == 5
    assert state.score_by_agent == {}


def test_cooked_food_with_its_own_recipe_keeps_cooking() -> None:
    environment = kitchen(
        pan_time=2,
        extra_recipes=[
            {"ingredient": GRILLED_MEAT, "with": PAN, "to_make": BURNT_MEAT}
        ],
    )
    agent_id = chef(environment).id

    grilled = steps(environment, [Combine(agent_id=agent_id)], [])
    burnt = idle(grilled, 2)
    timer = station(grilled, PAN).cooking

    assert contents(grilled, PAN) == GRILLED_MEAT
    assert timer is not None
    assert timer.started_by == agent_id
    assert contents(burnt, PAN) == BURNT_MEAT


def test_with_illegal_recipes_food_left_to_cook_turns_to_garbage() -> None:
    environment = kitchen(pan_time=2, allow_illegal_recipes=True)
    agent_id = chef(environment).id

    grilled = steps(environment, [Combine(agent_id=agent_id)], [])
    spoiled = idle(grilled, 2)
    spoiled_name = contents(spoiled, PAN)

    assert contents(grilled, PAN) == GRILLED_MEAT
    assert spoiled_name is not None and is_garbage_food(spoiled_name)
    assert station(spoiled, PAN).cooking is None
    assert contents(idle(spoiled, 5), PAN) == spoiled_name


def test_finishing_records_the_step_it_happened_in() -> None:
    environment = kitchen(pan_time=1, chef_holds=None, pan_holds=MEAT)

    cooked = environment.step([])

    assert station(cooked, PAN).last_cooked_at == environment.timestep
    assert station(cooked, PAN).cooking is None


def test_pending_effects_follow_food_that_cooks_by_itself() -> None:
    cooking = kitchen(pan_time=3, chef_holds=None, pan_holds=MEAT)
    empty = kitchen(chef_holds=None)
    manual = kitchen(timed=False, chef_holds=None, pan_holds=MEAT)
    board_only = kitchen(chef_holds=None, board_holds=TOMATO)

    assert cooking.has_pending_effects()
    assert not idle(cooking, 3).has_pending_effects()
    assert not empty.has_pending_effects()
    assert not manual.has_pending_effects()
    assert not board_only.has_pending_effects()


def test_a_held_pan_has_nothing_pending() -> None:
    environment = kitchen(chef_holds=None, pan_holds=MEAT)
    agent_id = chef(environment).id

    lifted = environment.step([PickUp(agent_id=agent_id)])

    assert not lifted.has_pending_effects()


def test_recordings_keep_the_kitchen_tick_mutations() -> None:
    environment = kitchen(chef_holds=None, pan_holds=MEAT)
    recording = Recording(
        environments=[environment, environment.step([])], mutations=[[], []]
    )

    restored = Recording.from_dict(recording.to_dict())

    assert restored.environments[0].tick_mutations == [AdvanceCooking()]
    assert station(restored.environments[1], PAN) == station(
        recording.environments[1], PAN
    )


# Stations cooked by hand


def chopping_board(chops: int = 3) -> Environment:
    return kitchen(chops=chops, chef_holds=None, chef_faces="w", board_holds=TOMATO)


def test_a_board_needs_one_press_per_chop() -> None:
    environment = chopping_board(chops=3)

    two_chops = presses(environment, 2)
    three_chops = presses(two_chops, 1)

    assert contents(two_chops, CUTBOARD) == TOMATO
    assert cooking_progress(two_chops, station(two_chops, CUTBOARD)) == 2 / 3
    assert contents(three_chops, CUTBOARD) == CHOPPED_TOMATO
    assert station(three_chops, CUTBOARD).cooking is None


def test_a_board_that_needs_one_press_chops_at_once() -> None:
    environment = kitchen(
        timed=False, chef_holds=None, chef_faces="w", board_holds=TOMATO
    )

    assert contents(presses(environment, 1), CUTBOARD) == CHOPPED_TOMATO


def test_chops_stay_on_the_board_while_the_chef_is_away() -> None:
    environment = chopping_board(chops=3)

    chopped_once = presses(environment, 1)
    later = idle(chopped_once, 5)

    assert cooking_progress(later, station(later, CUTBOARD)) == 1 / 3
    assert contents(presses(later, 2), CUTBOARD) == CHOPPED_TOMATO


def test_taking_food_off_the_board_loses_its_chops() -> None:
    environment = chopping_board(chops=3)
    agent_id = chef(environment).id

    chopped_twice = presses(environment, 2)
    put_back = steps(
        chopped_twice, [PickUp(agent_id=agent_id)], [Combine(agent_id=agent_id)]
    )

    assert cooking_progress(put_back, station(put_back, CUTBOARD)) == 0
    assert contents(presses(put_back, 2), CUTBOARD) == TOMATO
    assert contents(presses(put_back, 3), CUTBOARD) == CHOPPED_TOMATO


def test_a_board_cooked_by_hand_never_cooks_by_itself() -> None:
    environment = chopping_board(chops=3)

    assert contents(idle(presses(environment, 1), 10), CUTBOARD) == TOMATO


# Agent mode


def run_idle_controller(
    controller: StubController,
    end_conditions: EndConditions,
) -> tuple[list[SimulationResult], Environment]:
    results: list[SimulationResult] = []
    recording = run_agent_mode(
        kitchen_configuration(pan_time=2, chef_holds=None, pan_holds=MEAT),
        controller,
        headless=True,
        end_conditions=end_conditions,
        on_result=results.append,
    )
    return results, recording.environments[-1]


def test_time_passes_for_a_controller_waiting_on_food() -> None:
    results, final = run_idle_controller(
        StubController(),
        EndConditions(max_timesteps=2, time_limit_seconds=5),
    )

    assert results[0].reason == "max_timesteps"
    assert contents(final, PAN) == GRILLED_MEAT


def test_time_stops_again_once_nothing_is_cooking() -> None:
    results, final = run_idle_controller(
        StubController(),
        EndConditions(max_timesteps=10, time_limit_seconds=0.2),
    )

    assert results[0].reason == "time_limit"
    assert final.timestep == 2


def test_a_controller_that_is_still_planning_costs_no_timesteps() -> None:
    results, final = run_idle_controller(
        StubController(busy=True),
        EndConditions(max_timesteps=10, time_limit_seconds=0.2),
    )

    assert results[0].reason == "time_limit"
    assert final.timestep == 0
    assert contents(final, PAN) == MEAT

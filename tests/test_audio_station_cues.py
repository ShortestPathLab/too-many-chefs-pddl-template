from __future__ import annotations

from simulator.mutations import (
    Deliver,
    Interact,
    MoveAgentForward,
    PickUpOrPlace,
    TurnAgent,
)
from simulator.view import EQUIPMENT_DEFAULT_CUE
from tests.audio_kitchens import (
    CUTBOARD_CUE,
    agent_id,
    face,
    holding_a_tomato,
    kitchen,
    pass_kitchen,
    plate_on_counter,
    step,
    turn_away,
)


def test_taking_from_a_hatch_sounds_like_a_hatch() -> None:
    environment = kitchen()
    chef_id = agent_id(environment)

    _, cues = step(environment, Interact(agent_id=chef_id))

    assert cues == ["take_from_storage"]


def test_a_chopping_board_chops() -> None:
    environment = kitchen()
    chef_id = agent_id(environment)
    environment, _ = step(environment, Interact(agent_id=chef_id))
    environment = face(environment, "e")

    # Put the tomato on the board, then work it.
    environment, placed = step(environment, PickUpOrPlace(agent_id=chef_id))
    _, cooked = step(environment, Interact(agent_id=chef_id))

    assert placed == ["combine"]
    assert cooked == [CUTBOARD_CUE]


def test_a_station_with_no_sound_of_its_own_falls_back() -> None:
    environment = kitchen()
    chef_id = agent_id(environment)
    environment, _ = step(environment, Interact(agent_id=chef_id))

    # Chop, collect, carry east, then load the oven.
    environment = face(environment, "e")
    environment, _ = step(environment, PickUpOrPlace(agent_id=chef_id))
    environment, _ = step(environment, Interact(agent_id=chef_id))
    environment, picked = step(environment, PickUpOrPlace(agent_id=chef_id))
    environment = face(environment, "s")
    environment, _ = step(environment, MoveAgentForward(agent_id=chef_id))
    environment = face(environment, "e")
    for _ in range(2):
        environment, _ = step(environment, MoveAgentForward(agent_id=chef_id))
    environment = face(environment, "n")
    environment, loaded = step(environment, PickUpOrPlace(agent_id=chef_id))
    _, baked = step(environment, Interact(agent_id=chef_id))

    assert picked == ["pick_up"]
    assert loaded == ["combine"]
    assert baked == [EQUIPMENT_DEFAULT_CUE]


def test_a_bin_sounds_like_a_bin_rather_than_a_stove() -> None:
    # Interact is an umbrella mutation: the same keypress cooks, bins,
    # serves or opens a hatch depending on what the chef is facing.
    environment = kitchen()
    chef_id = agent_id(environment)
    environment, _ = step(environment, Interact(agent_id=chef_id))

    environment = face(environment, "s")
    environment, _ = step(environment, MoveAgentForward(agent_id=chef_id))
    environment = face(environment, "e")
    for _ in range(3):
        environment, _ = step(environment, MoveAgentForward(agent_id=chef_id))
    environment = face(environment, "n")

    _, cues = step(environment, Interact(agent_id=chef_id))

    assert cues == ["discard"]


def test_an_interaction_that_achieves_nothing_is_a_bump() -> None:
    environment = face(kitchen(), "n")
    chef_id = agent_id(environment)

    _, cues = step(environment, Interact(agent_id=chef_id))

    assert cues == ["blocked"]


def test_food_onto_a_counter_thuds_and_comes_back_off_as_a_grab() -> None:
    environment = kitchen()
    chef_id = agent_id(environment)
    environment, _ = step(environment, Interact(agent_id=chef_id))
    environment = face(environment, "s")
    environment, _ = step(environment, MoveAgentForward(agent_id=chef_id))

    environment, placed = step(environment, PickUpOrPlace(agent_id=chef_id))
    _, retrieved = step(environment, PickUpOrPlace(agent_id=chef_id))

    assert placed == ["place"]
    assert retrieved == ["pick_up"]


def test_a_plate_is_set_down_as_ceramic_rather_than_as_food() -> None:
    environment = kitchen()
    chef_id = agent_id(environment)
    environment = face(environment, "s")
    environment, _ = step(environment, MoveAgentForward(agent_id=chef_id))
    environment = face(environment, "e")
    for _ in range(5):
        environment, _ = step(environment, MoveAgentForward(agent_id=chef_id))
    environment = face(environment, "n")
    environment, _ = step(environment, PickUpOrPlace(agent_id=chef_id))

    environment = face(environment, "s")
    _, cues = step(environment, PickUpOrPlace(agent_id=chef_id))

    assert cues == ["place_plate"]


def test_a_plate_is_picked_up_as_ceramic() -> None:
    environment = kitchen()
    chef_id = agent_id(environment)
    environment = face(environment, "s")
    environment, _ = step(environment, MoveAgentForward(agent_id=chef_id))
    environment = face(environment, "e")
    for _ in range(5):
        environment, _ = step(environment, MoveAgentForward(agent_id=chef_id))
    environment = face(environment, "n")

    _, cues = step(environment, PickUpOrPlace(agent_id=chef_id))

    assert cues == ["pick_up_plate"]


# Cues for a step that turns before interacting.
def test_food_going_onto_a_plate_is_heard_when_the_chef_turned_to_it() -> None:
    environment, chef_id = holding_a_tomato()
    environment = plate_on_counter(environment, 1, 2)
    environment = face(environment, "e")

    _, cues = step(
        environment,
        TurnAgent(agent_id=chef_id, orientation="s"),
        PickUpOrPlace(agent_id=chef_id),
    )

    assert cues == ["combine"]


def test_a_bin_is_heard_when_the_chef_turned_to_it() -> None:
    # A hand emptying into a bin looks like a hand emptying anywhere else,
    # so the bin is claimed off the tile the chef faced.
    environment, chef_id = holding_a_tomato()
    environment = face(environment, "e")
    for _ in range(3):
        environment, _ = step(environment, MoveAgentForward(agent_id=chef_id))

    _, cues = step(
        environment,
        TurnAgent(agent_id=chef_id, orientation="n"),
        Interact(agent_id=chef_id),
    )

    # The swivel is still reported beside it: only a station cue silences a
    # turn, and a bin is not a station.
    assert cues == ["discard", "turn"]


def test_the_server_who_turned_to_the_hatch_is_still_the_server() -> None:
    # Nothing but the outcome is worth hearing from the chef who served, and
    # working out which chef that was means knowing which tile they faced.
    environment, server, _ = pass_kitchen()
    environment = turn_away(environment, server.id)

    _, cues = step(
        environment,
        TurnAgent(agent_id=server.id, orientation="e"),
        Deliver(agent_id=server.id),
    )

    assert cues == ["deliver", "tip"]

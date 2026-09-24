from __future__ import annotations

from simulator.entities import Agent
from simulator.mutations import MoveAgentForward, TurnAgent
from tests.audio_kitchens import agent_id, crew, kitchen, step


def test_a_move_that_lands_is_a_footstep() -> None:
    environment = kitchen()
    chef_id = agent_id(environment)

    _, cues = step(
        environment,
        TurnAgent(agent_id=chef_id, orientation="s"),
        MoveAgentForward(agent_id=chef_id),
    )

    assert cues == ["move"]


def test_a_move_into_a_wall_is_a_bump_rather_than_a_footstep() -> None:
    # Play mode queues a turn and a move for one arrow key. Hearing a
    # footstep for a step the chef never took is the tell that the cue was
    # read off the mutation instead of the result.
    environment = kitchen()
    chef_id = agent_id(environment)

    _, cues = step(
        environment,
        TurnAgent(agent_id=chef_id, orientation="w"),
        MoveAgentForward(agent_id=chef_id),
    )

    assert cues == ["blocked"]


def test_turning_on_the_spot_is_a_turn() -> None:
    environment = kitchen()
    chef_id = agent_id(environment)

    _, cues = step(environment, TurnAgent(agent_id=chef_id, orientation="n"))

    assert cues == ["turn"]


def test_one_chef_asked_to_walk_twice_takes_one_step() -> None:
    environment = kitchen()
    chef_id = agent_id(environment)

    _, cues = step(
        environment,
        TurnAgent(agent_id=chef_id, orientation="s"),
        MoveAgentForward(agent_id=chef_id),
        MoveAgentForward(agent_id=chef_id),
    )

    assert cues == ["move"]


def test_four_chefs_moving_play_one_footstep() -> None:
    # A brigade crossing the kitchen together is one footstep, not a
    # stampede. What that footstep sounds like is the cue's business.
    environment = crew()
    agents = environment.get_entities_of_type(Agent)

    _, cues = step(
        environment,
        *[MoveAgentForward(agent_id=agent.id) for agent in agents],
    )

    assert cues == ["move"]


def test_a_chef_turning_is_heard_beside_a_chef_walking() -> None:
    # One chef's footstep is not a reason to drop another chef's turn.
    environment = crew()
    walker, turner, *_ = environment.get_entities_of_type(Agent)

    _, cues = step(
        environment,
        MoveAgentForward(agent_id=walker.id),
        TurnAgent(agent_id=turner.id, orientation="e"),
    )

    assert cues == ["move", "turn"]


def test_a_chef_walking_into_a_wall_is_heard_beside_one_who_gets_through() -> None:
    environment = crew()
    walker, blocked, *_ = environment.get_entities_of_type(Agent)

    _, cues = step(
        environment,
        MoveAgentForward(agent_id=walker.id),
        TurnAgent(agent_id=blocked.id, orientation="n"),
        MoveAgentForward(agent_id=blocked.id),
    )

    assert cues == ["move", "blocked"]

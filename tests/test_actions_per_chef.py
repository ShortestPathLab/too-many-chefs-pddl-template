"""Each step a chef can turn once and make ``actions_per_step`` moves or actions."""

from __future__ import annotations

import pytest

from simulator.configuration import Configuration, load
from simulator.entities import Agent, Bounds
from simulator.environment import Environment
from simulator.mutations import (
    Interact,
    MoveAgent,
    MoveAgentForward,
    Mutation,
    TurnAgent,
    limit_actions_per_chef,
)
from simulator.run.episode import Episode

EAST = MoveAgent(agent_id="alfred", dx=1, dy=0)
WEST = MoveAgent(agent_id="alfred", dx=-1, dy=0)
FACE_EAST = TurnAgent(agent_id="alfred", orientation="e")
FACE_SOUTH = TurnAgent(agent_id="alfred", orientation="s")
BOB_FACES_EAST = TurnAgent(agent_id="bob", orientation="e")


def kitchen() -> Environment:
    """Two chefs facing north in an empty room three tiles wide."""
    return (
        Environment()
        .with_entity(Bounds(id="bounds", x=0, y=0, width=3, height=2))
        .with_entity(Agent(id="alfred", x=0, y=0, orientation="n"))
        .with_entity(Agent(id="bob", x=0, y=1, orientation="n"))
    )


def chef(environment: Environment, agent_id: str) -> Agent:
    agent = environment.get_entity_as(agent_id, Agent)
    assert agent is not None
    return agent


def test_a_chef_can_turn_and_move_in_one_step() -> None:
    stepped = kitchen().step([FACE_EAST, MoveAgentForward(agent_id="alfred")])

    alfred = chef(stepped, "alfred")
    assert (alfred.x, alfred.y, alfred.orientation) == (1, 0, "e")


def test_a_turn_sent_after_a_move_still_comes_first() -> None:
    # Facing north, stepping forward first would walk out of the room.
    stepped = kitchen().step([MoveAgentForward(agent_id="alfred"), FACE_EAST])

    alfred = chef(stepped, "alfred")
    assert (alfred.x, alfred.y, alfred.orientation) == (1, 0, "e")


def test_every_chef_gets_its_own_turn_and_action() -> None:
    stepped = kitchen().step(
        [
            FACE_EAST,
            MoveAgentForward(agent_id="alfred"),
            BOB_FACES_EAST,
            MoveAgentForward(agent_id="bob"),
        ]
    )

    assert (chef(stepped, "alfred").x, chef(stepped, "bob").x) == (1, 1)


@pytest.mark.parametrize(
    ("sent", "limit", "kept"),
    [
        ([EAST, EAST], 1, [EAST]),
        ([EAST, Interact(agent_id="alfred")], 1, [EAST]),
        ([FACE_EAST, FACE_SOUTH], 1, [FACE_EAST]),
        ([EAST, BOB_FACES_EAST, FACE_EAST], 1, [BOB_FACES_EAST, FACE_EAST, EAST]),
        ([EAST, EAST, EAST], 2, [EAST, EAST]),
    ],
)
def test_each_chef_keeps_its_first_turn_and_first_actions(
    sent: list[Mutation], limit: int, kept: list[Mutation]
) -> None:
    assert limit_actions_per_chef(sent, limit) == kept


def test_a_step_drops_a_chefs_second_move() -> None:
    stepped = kitchen().step([EAST, EAST])

    assert chef(stepped, "alfred").x == 1


def test_a_spare_action_does_not_replace_an_illegal_one() -> None:
    episode = Episode(kitchen())

    step = episode.advance([WEST, EAST])

    assert chef(step.current, "alfred").x == 0
    assert step.mutations == []


def test_a_kitchen_without_a_limit_runs_every_mutation() -> None:
    stepped = kitchen().copy_with(actions_per_step=None).step([EAST, EAST])

    assert chef(stepped, "alfred").x == 2


@pytest.mark.parametrize(
    ("rules", "limit"),
    [({}, 1), ({"actions_per_step": 2}, 2), ({"actions_per_step": None}, None)],
)
def test_a_level_sets_the_limit_in_its_rules(
    rules: dict[str, int | None], limit: int | None
) -> None:
    level = {
        "layout": "| 1 |",
        "legend": {"agents": [{"symbol": "1"}]},
        "rules": rules,
    }

    assert load(Configuration.from_dict(level)).actions_per_step == limit

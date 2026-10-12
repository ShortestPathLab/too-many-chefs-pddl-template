from __future__ import annotations

import pytest

from simulator.entities import Agent, Bounds, Counter
from simulator.environment import Environment, filter_legal_actions
from simulator.mutations.move_agent import MoveAgent, reachable_walkable_positions


def test_filter_legal_actions_applies_mutations_in_sequence() -> None:
    first_agent = Agent(id="agent-1", x=0, y=0)
    second_agent = Agent(id="agent-2", x=1, y=0)
    environment = (
        Environment()
        .with_entity(Bounds(id="bounds", x=0, y=0, width=3, height=1))
        .with_entity(first_agent)
        .with_entity(second_agent)
    )
    mutations = [
        MoveAgent(agent_id=second_agent.id, dx=1, dy=0),
        MoveAgent(agent_id=first_agent.id, dx=1, dy=0),
    ]

    legal_actions = filter_legal_actions(environment, mutations)

    assert legal_actions == mutations


@pytest.mark.parametrize(
    ("dx", "dy", "facing"), [(0, -1, "n"), (0, 1, "s"), (1, 0, "e"), (-1, 0, "w")]
)
def test_moving_turns_the_agent_the_way_it_went(dx: int, dy: int, facing: str) -> None:
    agent = Agent(id="agent-1", x=1, y=1, orientation="n")
    environment = (
        Environment()
        .with_entity(Bounds(id="bounds", x=0, y=0, width=3, height=3))
        .with_entity(agent)
    )

    moved = MoveAgent(agent_id=agent.id, dx=dx, dy=dy).run(environment)

    moved_agent = moved.get_entity_as(agent.id, Agent)
    assert moved_agent is not None
    assert (moved_agent.x, moved_agent.y) == (1 + dx, 1 + dy)
    assert moved_agent.orientation == facing


def test_next_position_returns_destination() -> None:
    agent = Agent(id="agent-1", x=2, y=3)
    environment = Environment().with_entity(agent)
    mutation = MoveAgent(agent_id="agent-1", dx=-1, dy=0)

    assert mutation.next_position(environment) == (1, 3)


def test_returns_shortest_path_costs_around_blocked_positions() -> None:
    agent = Agent(id="agent-1", x=0, y=0)
    environment = (
        Environment()
        .with_entity(Bounds(id="bounds", x=0, y=0, width=3, height=3))
        .with_entity(agent)
        .with_entity(Counter(id="counter", x=1, y=0))
    )

    costs = reachable_walkable_positions(
        environment,
        start=(0, 0),
        ignore_entity_id=agent.id,
    )

    assert costs == {
        (0, 0): 0,
        (0, 1): 1,
        (0, 2): 2,
        (1, 1): 2,
        (1, 2): 3,
        (2, 1): 3,
        (2, 2): 4,
        (2, 0): 4,
    }

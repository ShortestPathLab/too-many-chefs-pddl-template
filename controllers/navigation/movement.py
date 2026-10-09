"""Build movement mutations for agents."""

from __future__ import annotations

from simulator.entities import ORIENTATION_DELTAS, Agent, Orientation
from simulator.environment import Environment
from simulator.mutations import MoveAgentForward, Mutation, TurnAgent
from simulator.mutations.move_agent import MoveAgent
from simulator.types import Location


def direct_movement_mutation(
    mutation: Mutation,
    environment: Environment,
) -> Mutation | None:
    """Return a queued movement mutation in executable form.

    Movement mutations do not need a target location or pathfinding.
    """
    if isinstance(mutation, MoveAgentForward):
        agent = require_agent(environment, mutation.agent_id)
        dx, dy = ORIENTATION_DELTAS[agent.orientation]
        return MoveAgent(agent_id=mutation.agent_id, dx=dx, dy=dy)
    if isinstance(mutation, (TurnAgent, MoveAgent)):
        return mutation
    return None


def orient_and_wrap(
    *,
    agent_id: str,
    start: Location,
    destination: Location,
    mutation: Mutation,
) -> list[Mutation]:
    """Return a turn followed by ``mutation``."""
    return [
        TurnAgent(
            agent_id=agent_id,
            orientation=orientation_between(start, destination),
        ),
        mutation,
    ]


def orientation_between(
    start: Location,
    destination: Location,
) -> Orientation:
    dx = destination[0] - start[0]
    dy = destination[1] - start[1]
    for orientation, delta in ORIENTATION_DELTAS.items():
        if delta == (dx, dy):
            return orientation
    raise ValueError(f"Cannot orient from {start} to {destination}")


def is_next_to_target(agent: Agent, target_location: Location) -> bool:
    agent_x, agent_y = require_agent_location(agent)
    return abs(agent_x - target_location[0]) + abs(agent_y - target_location[1]) == 1


def require_agent_location(agent: Agent) -> Location:
    if agent.x is None or agent.y is None:
        raise ValueError(f"Agent {agent.id} has no position")
    return (agent.x, agent.y)


def require_agent(environment: Environment, agent_id: str) -> Agent:
    agent = environment.get_entity_as(agent_id, Agent)
    if not agent:
        raise ValueError(f"Unknown agent {agent_id}")
    return agent

"""Prevent agents from moving into the same tile in one tick.

Agents are interpolated in priority order. Earlier agents reserve their current
and destination tiles; later agents route around those reservations.
"""

from __future__ import annotations

from controllers.navigation.movement import orient_and_wrap, require_agent_location
from simulator.entities import ORIENTATION_DELTAS, Agent
from simulator.environment import Environment
from simulator.mutations import Mutation
from simulator.mutations.agent_mutation import AgentMutation
from simulator.mutations.move_agent import MoveAgent, is_walkable
from simulator.types import Location


class AgentDeadlockError(RuntimeError):
    """Raised when agent traffic cannot be resolved."""


def get_reserved_positions(
    *,
    committed_mutations: list[Mutation],
    committed_agent_ids: set[str],
    environment: Environment,
) -> set[Location]:
    """Return tiles reserved by higher-priority agents this tick."""
    higher_priority_agent_ids = {
        mutation.agent_id
        for mutation in committed_mutations
        if isinstance(mutation, AgentMutation)
    } | committed_agent_ids
    higher_priority_agents = (
        environment.get_entity_as(agent_id, Agent)
        for agent_id in higher_priority_agent_ids
    )
    return {
        *{
            mutation.next_position(environment)
            for mutation in committed_mutations
            if isinstance(mutation, MoveAgent)
        },
        *{
            require_agent_location(higher_priority_agent)
            for higher_priority_agent in higher_priority_agents
            if higher_priority_agent is not None
        },
    }


def get_escape_mutation(
    *,
    agent: Agent,
    current_location: Location,
    committed_mutations: list[Mutation],
    committed_agent_ids: set[str],
    reserved_positions: set[Location],
    environment: Environment,
) -> list[Mutation] | None:
    """Return a step aside when another agent is moving into this tile.

    Only lower-priority agents can be ignored while looking for an escape tile.
    """
    if current_location not in reserved_positions:
        return None
    x, y = current_location

    higher_priority_agent_ids = {
        mutation.agent_id
        for mutation in committed_mutations
        if isinstance(mutation, AgentMutation)
    } | committed_agent_ids

    lower_priority_agents = {
        other_agent.id for other_agent in environment.get_entities_of_type(Agent)
    } - higher_priority_agent_ids

    for dx, dy in ORIENTATION_DELTAS.values():
        next_x, next_y = (x + dx, y + dy)
        if (next_x, next_y) in reserved_positions:
            continue

        if is_walkable(
            environment,
            next_x,
            next_y,
            ignore_entity_id=lower_priority_agents,
        ):
            return orient_and_wrap(
                agent_id=agent.id,
                start=(x, y),
                destination=(next_x, next_y),
                mutation=MoveAgent(agent_id=agent.id, dx=dx, dy=dy),
            )

    raise AgentDeadlockError("Agents entered an unresolvable deadlock.")


def insert_before_move_into_agent(
    *,
    actions: list[Mutation],
    mutations_to_queue: list[Mutation],
    agent_id: str,
    environment: Environment,
) -> None:
    """Insert this agent's step before a move into its current tile.

    This lets the occupant leave before the next agent moves in.
    """
    agent = environment.get_entity_as(agent_id, Agent)
    if agent is None or agent.x is None or agent.y is None:
        actions.extend(mutations_to_queue)
        return

    current_location = require_agent_location(agent)
    for index, action in enumerate(actions):
        if (
            isinstance(action, MoveAgent)
            and action.next_position(environment) == current_location
        ):
            actions[index:index] = mutations_to_queue
            return

    actions.extend(mutations_to_queue)

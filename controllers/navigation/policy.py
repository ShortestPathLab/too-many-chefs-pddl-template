"""Turn a queued plan into the mutations each chef makes this tick."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from controllers.navigation.movement import (
    direct_movement_mutation,
    is_next_to_target,
    orient_and_wrap,
    require_agent,
    require_agent_location,
)
from controllers.navigation.paths import find_path
from controllers.navigation.traffic import (
    get_escape_mutation,
    get_reserved_positions,
    insert_before_move_into_agent,
)
from simulator.context import Context
from simulator.environment import Environment
from simulator.mutations import Mutation, MutationWithLocation
from simulator.mutations.move_agent import MoveAgent
from simulator.mutations.mutation import can_apply_mutation
from simulator.types import Location

Plan = dict[str, list[tuple[int, MutationWithLocation]]]


class MutationInterpolationPolicy(ABC):
    @abstractmethod
    def get_mutations(
        self,
        plans: Plan,
        environment: Environment,
        context: Context,
    ) -> tuple[list[Mutation], Plan]:
        pass


@dataclass(frozen=True)
class PathCacheEntry:
    target_location: Location
    path: list[Location]


class DefaultMutationInterpolationPolicy(MutationInterpolationPolicy):
    """Convert queued actions into simulator mutations.

    The policy processes at most one queued action per agent per tick. Movement
    primitives such as ``TurnAgent`` and ``MoveAgentForward`` are passed through
    directly.

    Other actions carry a target location. The policy pathfinds to that location
    and caches the route for later ticks. It discards and recomputes stale or
    blocked paths.

    When the agent is adjacent to the target, the policy emits a facing turn and
    the action if ``can_apply_mutation(...)`` allows it.

    If the target is unreachable or the action is not yet legal, the policy
    returns no mutations and keeps the action queued.
    """

    def __init__(self) -> None:
        self._path_cache: dict[str, PathCacheEntry] = {}

    def get_mutations(
        self,
        plans: Plan,
        environment: Environment,
        context: Context,
    ) -> tuple[list[Mutation], Plan]:
        actions: list[Mutation] = []
        updated_plans = {agent_id: list(plan) for agent_id, plan in plans.items()}
        committed_agent_ids: set[str] = set()

        for agent_id in sorted(
            updated_plans,
            key=lambda agent_id: (
                updated_plans[agent_id][0][0] if len(updated_plans[agent_id]) else 9_999
            ),
        ):
            indexed_mutations = updated_plans[agent_id]
            queued_mutations = [
                mutation_with_location
                for _, mutation_with_location in indexed_mutations
            ]
            mutations_to_queue, next_mutation_list = self._get_agent_mutations(
                agent_id=agent_id,
                next_mutations=queued_mutations,
                committed_mutations=actions,
                committed_agent_ids=committed_agent_ids,
                environment=environment,
                context=context,
            )
            consumed_count = len(queued_mutations) - len(next_mutation_list)
            updated_plans[agent_id] = indexed_mutations[consumed_count:]
            insert_before_move_into_agent(
                actions=actions,
                mutations_to_queue=mutations_to_queue,
                agent_id=agent_id,
                environment=environment,
            )
            committed_agent_ids.add(agent_id)

        return actions, updated_plans

    def _get_agent_mutations(
        self,
        *,
        agent_id: str,
        next_mutations: list[MutationWithLocation],
        committed_mutations: list[Mutation],
        committed_agent_ids: set[str],
        environment: Environment,
        context: Context,
    ) -> tuple[list[Mutation], list[MutationWithLocation]]:
        agent = require_agent(environment, agent_id)
        current_location = require_agent_location(agent)
        reserved_positions = get_reserved_positions(
            committed_mutations=committed_mutations,
            committed_agent_ids=committed_agent_ids,
            environment=environment,
        )
        escape_mutation = get_escape_mutation(
            agent=agent,
            current_location=current_location,
            committed_mutations=committed_mutations,
            committed_agent_ids=committed_agent_ids,
            reserved_positions=reserved_positions,
            environment=environment,
        )
        if escape_mutation is not None:
            self._path_cache.pop(agent.id, None)
            return (escape_mutation, next_mutations)

        if not next_mutations:
            return ([], [])

        mutation_with_location = next_mutations[0]
        remaining_mutations = next_mutations[1:]
        mutation = mutation_with_location.mutation
        direct_mutation = direct_movement_mutation(mutation, environment)
        if direct_mutation is not None:
            if (
                isinstance(direct_mutation, MoveAgent)
                and direct_mutation.next_position(environment) in reserved_positions
            ):
                return ([], next_mutations)
            return ([direct_mutation], remaining_mutations)

        agent_id = agent.id
        target_location = mutation_with_location.location
        if target_location is None:
            raise ValueError(
                f"Missing target location for {mutation.__class__.__name__}"
            )

        if is_next_to_target(agent, target_location):
            interaction_mutations = orient_and_wrap(
                agent_id=agent.id,
                start=current_location,
                destination=target_location,
                mutation=mutation,
            )
            if can_apply_mutation(environment, *interaction_mutations):
                self._path_cache.pop(agent_id, None)
                return (interaction_mutations, remaining_mutations)
            return ([], next_mutations)

        cached_path = self._prepare_path(
            environment,
            agent_id=agent_id,
            current_location=current_location,
            target_location=target_location,
            reserved_positions=reserved_positions,
        )
        if len(cached_path) < 2:
            self._path_cache.pop(agent_id, None)
            cached_path = self._prepare_path(
                environment,
                agent_id=agent_id,
                current_location=current_location,
                target_location=target_location,
                reserved_positions=reserved_positions,
            )
            return ([], next_mutations)

        movement_mutations = orient_and_wrap(
            agent_id=agent_id,
            start=current_location,
            destination=cached_path[1],
            mutation=MoveAgent(
                agent_id=agent_id,
                dx=cached_path[1][0] - current_location[0],
                dy=cached_path[1][1] - current_location[1],
            ),
        )

        self._path_cache[agent_id] = PathCacheEntry(
            target_location=target_location,
            path=cached_path[1:],
        )
        return (movement_mutations, next_mutations)

    def _prepare_path(
        self,
        environment: Environment,
        *,
        agent_id: str,
        current_location: Location,
        target_location: Location,
        reserved_positions: set[Location],
    ) -> list[Location]:
        cached_entry = self._path_cache.get(agent_id)
        if cached_entry is not None:
            if (
                cached_entry.target_location != target_location
                or not cached_entry.path
                or cached_entry.path[0] != current_location
                or any(
                    location in reserved_positions for location in cached_entry.path[1:]
                )
            ):
                self._path_cache.pop(agent_id, None)
            else:
                return cached_entry.path

        path_to_target = find_path(
            environment,
            current_location,
            target_location,
            ignore_entity_id=agent_id,
            ignore_agents=True,
            blocked_locations=reserved_positions,
        )

        if not path_to_target:
            cached_path = [current_location]
        else:
            cached_path = [current_location, *path_to_target[:-1]]

        self._path_cache[agent_id] = PathCacheEntry(
            target_location=target_location,
            path=cached_path,
        )
        return cached_path

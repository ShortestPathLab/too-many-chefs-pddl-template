"""Convert queued plans to per-chef mutations for the current tick."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace

from controllers.navigation.floor import Floor, read_floor
from controllers.navigation.movement import (
    direct_movement_mutation,
    is_next_to_target,
    orient_and_wrap,
    require_agent,
    require_agent_location,
)
from controllers.navigation.traffic import Chef, Traffic
from simulator.context import Context
from simulator.entities import Agent
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


@dataclass
class _Intent:
    """What one chef's next queued action asks of it this tick."""

    chef: Chef
    #: Mutations to send if the chef keeps its tile.
    in_place: list[Mutation] = field(default_factory=list)
    #: Whether sending ``in_place`` uses up the queued action.
    consumes_in_place: bool = False
    #: A queued direct move, sent as it is when the chef takes that step.
    direct_move: Mutation | None = None


class DefaultMutationInterpolationPolicy(MutationInterpolationPolicy):
    """Convert queued actions into simulator mutations.

    The policy processes at most one queued action per agent per tick.
    Movement primitives such as ``TurnAgent`` and ``MoveAgentForward`` are
    passed through directly.

    Other actions carry a target location. The agent walks to a floor tile
    beside the target, turns to face it, and emits the action once
    ``can_apply_mutation(...)`` allows it. Until then the action stays queued.

    ``traffic.Traffic`` picks every agent's next tile, in the order of the
    agents' next queued steps. An agent may have to step aside for one that
    comes earlier, and it keeps its queued action when it does.
    """

    def __init__(self) -> None:
        self._last_location: dict[str, Location] = {}
        self._previous_location: dict[str, Location] = {}

    def get_mutations(
        self,
        plans: Plan,
        environment: Environment,
        context: Context,
    ) -> tuple[list[Mutation], Plan]:
        updated_plans = {agent_id: list(plan) for agent_id, plan in plans.items()}
        order = sorted(
            updated_plans,
            key=lambda agent_id: (
                updated_plans[agent_id][0][0] if len(updated_plans[agent_id]) else 9_999
            ),
        )
        floor = read_floor(environment)
        intents = {
            agent_id: self._intent(
                agent_id,
                [step for _, step in updated_plans[agent_id]],
                environment,
                floor,
            )
            for agent_id in order
        }
        # Chefs another controller drives keep their tiles as far as this
        # policy can tell.
        others = [
            Chef(agent_id=agent.id, location=(agent.x, agent.y), fixed=True)
            for agent in environment.get_entities_of_type(Agent)
            if agent.id not in intents and agent.x is not None and agent.y is not None
        ]
        traffic = Traffic(floor, [intent.chef for intent in intents.values()] + others)
        for agent_id in order:
            traffic.plan(agent_id)

        actions: list[Mutation] = []
        for agent_id in traffic.in_move_order(order):
            intent = intents[agent_id]
            here = intent.chef.location
            destination = traffic.next_location(agent_id)
            if destination == here:
                actions.extend(intent.in_place)
                if intent.consumes_in_place:
                    updated_plans[agent_id] = updated_plans[agent_id][1:]
            elif (
                intent.direct_move is not None
                and destination == intent.chef.step
                and not traffic.moved_by_others(agent_id)
            ):
                actions.append(intent.direct_move)
                updated_plans[agent_id] = updated_plans[agent_id][1:]
            else:
                actions.extend(
                    orient_and_wrap(
                        agent_id=agent_id,
                        start=here,
                        destination=destination,
                        mutation=MoveAgent(
                            agent_id=agent_id,
                            dx=destination[0] - here[0],
                            dy=destination[1] - here[1],
                        ),
                    )
                )
        return actions, updated_plans

    def _intent(
        self,
        agent_id: str,
        queued: list[MutationWithLocation],
        environment: Environment,
        floor: Floor,
    ) -> _Intent:
        agent = require_agent(environment, agent_id)
        here = require_agent_location(agent)
        if self._last_location.get(agent_id, here) != here:
            self._previous_location[agent_id] = self._last_location[agent_id]
        self._last_location[agent_id] = here
        chef = Chef(
            agent_id=agent_id,
            location=here,
            previous=self._previous_location.get(agent_id),
        )
        if not queued:
            return _Intent(chef=chef)

        mutation = queued[0].mutation
        direct = direct_movement_mutation(mutation, environment)
        if isinstance(direct, MoveAgent):
            step = direct.next_position(environment)
            if step not in floor.tiles:
                # Send it anyway so the simulator reports it as illegal.
                return _Intent(chef=chef, in_place=[direct], consumes_in_place=True)
            return _Intent(
                chef=replace(chef, step=step),
                direct_move=direct,
            )
        if direct is not None:
            return _Intent(chef=chef, in_place=[direct], consumes_in_place=True)

        target = queued[0].location
        if target is None:
            raise ValueError(
                f"Missing target location for {mutation.__class__.__name__}"
            )
        if is_next_to_target(agent, target):
            interaction = orient_and_wrap(
                agent_id=agent_id,
                start=here,
                destination=target,
                mutation=mutation,
            )
            if can_apply_mutation(environment, *interaction):
                return _Intent(
                    chef=replace(chef, fixed=True),
                    in_place=interaction,
                    consumes_in_place=True,
                )
        return _Intent(chef=replace(chef, goals=frozenset(floor.neighbours(target))))

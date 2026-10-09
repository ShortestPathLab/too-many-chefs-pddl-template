from __future__ import annotations

from collections import deque
from collections.abc import Container
from typing import TYPE_CHECKING, Literal

from simulator.entities import Agent, Bounds, get_objects_at
from simulator.mutations.agent_mutation import AgentMutation
from simulator.mutations.mutation import IllegalMutationError
from simulator.mutations.virtual_input import VirtualInput, step_input
from simulator.types import Location

if TYPE_CHECKING:
    from simulator.environment import Environment


def is_in_bounds(bounds: Bounds | None, x: int, y: int) -> bool:
    if not bounds:
        return True
    return bounds.contains(x, y)


def is_walkable(
    environment: Environment,
    x: int,
    y: int,
    *,
    ignore_entity_id: Container[str] = frozenset(),
    ignore_agents: bool = False,
) -> bool:
    bounds = environment.get_first_entity_of_type(Bounds)
    if not is_in_bounds(bounds, x, y):
        return False

    for entity in get_objects_at(environment, x, y):
        if entity.id in ignore_entity_id:
            continue
        if ignore_agents and isinstance(entity, Agent):
            continue
        if entity.blocks_movement:
            return False

    return True


def reachable_walkable_positions(
    environment: Environment,
    *,
    start: Location,
    ignore_entity_id: str | None = None,
) -> dict[Location, int]:
    shortest_path_costs = {start: 0}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        next_cost = shortest_path_costs[(x, y)] + 1
        for next_position in ((x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y)):
            if next_position in shortest_path_costs:
                continue
            if not is_walkable(
                environment,
                next_position[0],
                next_position[1],
                ignore_entity_id={ignore_entity_id} if ignore_entity_id else set(),
            ):
                continue
            shortest_path_costs[next_position] = next_cost
            queue.append(next_position)
    return shortest_path_costs


class MoveAgent(AgentMutation):
    kind: Literal["move_agent"] = "move_agent"
    dx: int
    dy: int

    def next_position(self, environment: Environment) -> Location:
        agent = environment.get_entity_as(self.agent_id, Agent)
        if not agent or agent.x is None or agent.y is None:
            raise IllegalMutationError("Agent invalid")
        if abs(self.dx) + abs(self.dy) != 1:
            raise IllegalMutationError("Movement invalid")
        return (agent.x + self.dx, agent.y + self.dy)

    def describe(self, environment: Environment) -> str:
        return f"{self.agent_id} moves"

    def virtual_input(self, environment: Environment) -> VirtualInput | None:
        return step_input(self.dx, self.dy)

    def run(self, environment: Environment) -> Environment:
        agent = environment.get_entity_as(self.agent_id, Agent)
        if not agent or agent.x is None or agent.y is None:
            raise IllegalMutationError()
        bounds = environment.get_first_entity_of_type(Bounds)
        next_x, next_y = self.next_position(environment)
        if not is_in_bounds(bounds, next_x, next_y):
            raise IllegalMutationError("Not in bounds")
        if not is_walkable(environment, next_x, next_y, ignore_entity_id=agent.id):
            raise IllegalMutationError("Not walkable")

        return environment.replace_entity(agent.copy_with(x=next_x, y=next_y))

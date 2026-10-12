"""Find paths across the kitchen floor.

A* searches the four-connected walkable tiles with unit cost.

The search reads walkability from the environment as it runs instead of first
copying the whole grid.
"""

from __future__ import annotations

import heapq
from collections.abc import Collection, Iterator

from simulator.entities import Bounds
from simulator.environment import Environment
from simulator.mutations.move_agent import is_walkable
from simulator.types import Location


def find_path(
    environment: Environment,
    start: Location,
    destination: Location,
    *,
    ignore_entity_id: str | None = None,
    ignore_agents: bool = True,
    blocked_locations: Collection[Location] = (),
) -> list[Location] | None:
    """Return the shortest path, excluding ``start``.

    Return ``None`` when no path exists. Treat ``start`` and ``destination`` as
    passable so an agent can leave its current tile and stand beside a target.
    """
    if start == destination:
        return []

    bounds = environment.get_first_entity_of_type(Bounds)
    if bounds is None:
        raise ValueError("Environment is missing Bounds")

    blocked = frozenset(blocked_locations)
    # Pass a set so a multi-character id is treated as one value.
    ignored = frozenset({ignore_entity_id} if ignore_entity_id else ())

    def passable(location: Location) -> bool:
        if location in (start, destination):
            return True
        if location in blocked:
            return False
        x, y = location
        return is_walkable(
            environment,
            x,
            y,
            ignore_entity_id=ignored,
            ignore_agents=ignore_agents,
        )

    came_from: dict[Location, Location] = {}
    cost_so_far: dict[Location, int] = {start: 0}
    # The counter breaks heap ties without comparing locations.
    counter = 0
    frontier: list[tuple[int, int, Location]] = [
        (_estimate(start, destination), 0, start)
    ]

    while frontier:
        _, _, current = heapq.heappop(frontier)
        if current == destination:
            return _walk_back(came_from, start, destination)

        next_cost = cost_so_far[current] + 1
        for neighbour in _neighbours(current):
            if neighbour in cost_so_far and cost_so_far[neighbour] <= next_cost:
                continue
            if not passable(neighbour):
                continue
            cost_so_far[neighbour] = next_cost
            came_from[neighbour] = current
            counter += 1
            heapq.heappush(
                frontier,
                (next_cost + _estimate(neighbour, destination), counter, neighbour),
            )

    return None


def _neighbours(location: Location) -> Iterator[Location]:
    """Yield the four neighboring tiles.

    The order is part of the path selection because it breaks ties between paths
    of equal length.
    """
    x, y = location
    yield (x - 1, y)
    yield (x + 1, y)
    yield (x, y - 1)
    yield (x, y + 1)


def _estimate(location: Location, destination: Location) -> int:
    """Return the Manhattan distance between two tiles."""
    x, y = location
    goal_x, goal_y = destination
    return abs(x - goal_x) + abs(y - goal_y)


def _walk_back(
    came_from: dict[Location, Location],
    start: Location,
    destination: Location,
) -> list[Location]:
    path = [destination]
    while path[-1] != start:
        path.append(came_from[path[-1]])
    path.reverse()
    return path[1:]

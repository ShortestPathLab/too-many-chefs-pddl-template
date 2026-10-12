"""Read the walkable floor of a kitchen.

Chefs are left out, so the floor stays the same while counters and stations
stay where they are. ``read_floor`` caches it for that reason.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Collection, Iterable, Iterator
from dataclasses import dataclass
from functools import lru_cache

from simulator.entities import Agent, Bounds
from simulator.entities.game_object import game_objects
from simulator.environment import Environment
from simulator.types import Location


@dataclass(frozen=True)
class Floor:
    tiles: frozenset[Location]
    #: Tiles that go when every tile with one floor neighbour or none is
    #: removed, again and again until no more go: nooks and the corridors that
    #: lead only to them.
    dead_ends: frozenset[Location]

    def neighbours(self, location: Location) -> Iterator[Location]:
        """Yield the floor tiles beside ``location``: west, east, north, south."""
        for neighbour in _around(location):
            if neighbour in self.tiles:
                yield neighbour

    def distances_to(
        self,
        goals: Iterable[Location],
        *,
        blocked: Collection[Location] = (),
    ) -> dict[Location, int]:
        """Return the steps from each tile to the nearest goal.

        Tiles in ``blocked`` can't be crossed. Tiles with no way to a goal are
        left out.
        """
        distances: dict[Location, int] = {}
        frontier: deque[Location] = deque()
        for goal in goals:
            if goal in self.tiles and goal not in blocked and goal not in distances:
                distances[goal] = 0
                frontier.append(goal)
        while frontier:
            location = frontier.popleft()
            for neighbour in self.neighbours(location):
                if neighbour not in distances and neighbour not in blocked:
                    distances[neighbour] = distances[location] + 1
                    frontier.append(neighbour)
        return distances


def read_floor(environment: Environment) -> Floor:
    bounds = environment.get_first_entity_of_type(Bounds)
    if bounds is None:
        raise ValueError("Environment is missing Bounds")
    obstacles = frozenset(
        (entity.x, entity.y)
        for entity in game_objects(environment)
        if entity.blocks_movement and not isinstance(entity, Agent)
    )
    return _floor(bounds.x or 0, bounds.y or 0, bounds.width, bounds.height, obstacles)


@lru_cache(maxsize=8)
def _floor(
    x: int,
    y: int,
    width: int,
    height: int,
    obstacles: frozenset[Location],
) -> Floor:
    tiles = frozenset(
        (column, row)
        for column in range(x, x + width)
        for row in range(y, y + height)
        if (column, row) not in obstacles
    )
    return Floor(tiles=tiles, dead_ends=_dead_ends(tiles))


def _dead_ends(tiles: frozenset[Location]) -> frozenset[Location]:
    remaining = set(tiles)

    def degree(location: Location) -> int:
        return sum(neighbour in remaining for neighbour in _around(location))

    queue = deque(location for location in remaining if degree(location) <= 1)
    while queue:
        location = queue.popleft()
        if location not in remaining or degree(location) > 1:
            continue
        remaining.remove(location)
        queue.extend(n for n in _around(location) if n in remaining)
    return tiles - remaining


def _around(location: Location) -> Iterator[Location]:
    x, y = location
    yield (x - 1, y)
    yield (x + 1, y)
    yield (x, y - 1)
    yield (x, y + 1)

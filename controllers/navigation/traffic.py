"""Choose each chef's next tile so that chefs never walk into each other.

This is Priority Inheritance with Backtracking (PIBT, Okumura et al., IJCAI
2019) with the swap step from LaCAM* (Okumura, IJCAI 2023). Chefs choose in
priority order. A chef that wants a tile held by a chef who hasn't chosen yet
lends that chef its priority, and the other chef must move out of the way
first. If it can't, the first chef falls back to its next choice.

Plain PIBT stalls when the chef in the way stands in a dead end, since it has
nowhere to go. The swap step handles that case: the chef who wants in backs
away and pulls the other chef out after it.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from controllers.navigation.floor import Floor
from simulator.entities import ORIENTATION_DELTAS
from simulator.types import Location

# A pushed chef that is equally happy with two tiles takes the one that comes
# first in this order.
_STEP_ASIDE_ORDER = tuple(ORIENTATION_DELTAS.values())


@dataclass(frozen=True)
class Chef:
    """Where one chef stands and where it wants to go this tick."""

    agent_id: str
    location: Location
    #: Tiles the chef wants to stand on. Empty when it has nowhere to go.
    goals: frozenset[Location] = frozenset()
    #: The tile a direct move steps onto. A chef with one tries that tile and
    #: otherwise stays where it is.
    step: Location | None = None
    #: A fixed chef keeps its tile and can't be pushed, for example because it
    #: acts this tick or another controller drives it.
    fixed: bool = False
    #: The tile the chef stood on before its last move.
    previous: Location | None = None


class Traffic:
    """Next tiles for one tick, chosen with PIBT and swap.

    Call ``plan`` for each chef in priority order. A chef can be decided before
    its own turn comes, when a chef with higher priority pushes it out of the
    way or pulls it out of a dead end.
    """

    def __init__(self, floor: Floor, chefs: Iterable[Chef]) -> None:
        self._floor = floor
        self._chefs = {chef.agent_id: chef for chef in chefs}
        self._standing = {chef.location: chef.agent_id for chef in self._chefs.values()}
        self._claims: dict[Location, str] = {}
        self._next: dict[str, Location] = {}
        self._moved_by_others: set[str] = set()
        self._goal_owners: dict[Location, set[str]] = {}
        for chef in self._chefs.values():
            for tile in chef.goals | ({chef.step} if chef.step else set()):
                self._goal_owners.setdefault(tile, set()).add(chef.agent_id)
            if chef.fixed:
                self._stay(chef.agent_id)

    def plan(self, agent_id: str) -> None:
        if agent_id not in self._next:
            self._choose(agent_id, pusher=None)

    def next_location(self, agent_id: str) -> Location:
        return self._next.get(agent_id, self._chefs[agent_id].location)

    def moved_by_others(self, agent_id: str) -> bool:
        """Return whether another chef pushed or pulled this chef."""
        return agent_id in self._moved_by_others

    def in_move_order(self, agent_ids: Iterable[str]) -> list[str]:
        """Order chefs so that each one moves after the chef leaving its tile.

        The simulator runs moves one at a time, so a chef stepping onto an
        occupied tile has to wait until the chef there has left.
        """
        ordered: list[str] = []
        placed: set[str] = set()

        def place(agent_id: str) -> None:
            if agent_id in placed:
                return
            placed.add(agent_id)
            leaving = self._standing.get(self.next_location(agent_id))
            if leaving is not None and leaving != agent_id:
                place(leaving)
            ordered.append(agent_id)

        for agent_id in agent_ids:
            place(agent_id)
        return ordered

    def _choose(self, agent_id: str, pusher: str | None) -> bool:
        """Claim a next tile for the chef and return whether it got one.

        ``pusher`` is the chef that wants this chef's tile, if any. A pushed
        chef has to leave, so staying put doesn't count as success for it.
        """
        chef = self._chefs[agent_id]
        here = chef.location
        partner = None
        if pusher is None:
            candidates, distances = self._own_candidates(chef)
            partner = self._swap_partner(chef, candidates, distances)
            if partner is not None:
                candidates.reverse()
        else:
            candidates = self._step_aside_candidates(chef)

        for tile in candidates:
            if tile in self._claims:
                continue
            occupant = self._standing.get(tile)
            if occupant == agent_id:
                occupant = None
            if occupant in self._next and self._closes_ring(agent_id, tile):
                continue
            self._claims[tile] = agent_id
            self._next[agent_id] = tile
            if (
                occupant is not None
                and occupant not in self._next
                and not self._choose(occupant, pusher=agent_id)
            ):
                continue
            if pusher is not None:
                self._moved_by_others.add(agent_id)
            if partner is not None and tile != here:
                self._pull(partner, into=here)
            return True

        self._stay(agent_id)
        return False

    def _own_candidates(self, chef: Chef) -> tuple[list[Location], dict[Location, int]]:
        """Return the tiles a chef would pick for itself, best first."""
        here = chef.location
        if chef.step is not None:
            return [chef.step, here], {}
        if not chef.goals:
            return [here], {}
        blocked = {
            tile for tile, owner in self._claims.items() if owner != chef.agent_id
        }
        distances = self._floor.distances_to(chef.goals, blocked=blocked)
        if here not in distances:
            return [here], distances
        options = [here, *(t for t in self._floor.neighbours(here) if t in distances)]
        order = {tile: index for index, tile in enumerate(options)}
        options.sort(
            key=lambda tile: (
                distances[tile],
                tile != here,
                self._held_by_other(tile, chef.agent_id),
                order[tile],
            )
        )
        return options, distances

    def _step_aside_candidates(self, chef: Chef) -> list[Location]:
        """Return the tiles a pushed chef can step to, best first.

        In order, a pushed chef prefers tiles that no other chef is heading
        for, tiles outside dead ends, tiles closer to its own goal, and tiles
        other than the one it just came from. Without the first two rules a
        chef pulled out of a nook would step straight back in.
        """
        here = chef.location
        distances = (
            self._floor.distances_to(chef.goals, blocked=self._claims)
            if chef.goals
            else {}
        )
        unreachable = len(self._floor.tiles)

        def rank(tile: Location) -> tuple[bool, bool, int, bool, bool, int]:
            delta = (tile[0] - here[0], tile[1] - here[1])
            return (
                bool(self._goal_owners.get(tile, set()) - {chef.agent_id}),
                tile in self._floor.dead_ends,
                distances.get(tile, unreachable) if chef.goals else 0,
                tile == chef.previous,
                self._held_by_other(tile, chef.agent_id),
                _STEP_ASIDE_ORDER.index(delta),
            )

        return sorted(self._floor.neighbours(here), key=rank)

    def _swap_partner(
        self,
        chef: Chef,
        candidates: list[Location],
        distances: dict[Location, int],
    ) -> str | None:
        """Return the chef to swap places with, if the chef needs a swap.

        A swap is needed when the chef's best tile is held by a chef that has
        no way to step aside, and possible when the chef itself has room to
        back away.
        """
        if chef.step is not None or not candidates or candidates[0] == chef.location:
            return None
        partner = self._standing.get(candidates[0])
        if partner is None or partner in self._next:
            return None
        if self._swap_required(chef.location, candidates[0], distances) and (
            self._swap_possible(chef.location, candidates[0])
        ):
            return partner
        return None

    def _swap_required(
        self,
        pusher_at: Location,
        pushed_at: Location,
        distances: dict[Location, int],
    ) -> bool:
        """Push the chef ahead on an empty floor and see whether it gets stuck.

        The push goes on for as long as it brings the pusher closer to its
        goal. It is stuck when it reaches a tile with no way out other than
        back towards the pusher.
        """
        for _ in range(len(self._floor.tiles)):
            if distances.get(pushed_at, len(self._floor.tiles)) >= distances.get(
                pusher_at, len(self._floor.tiles)
            ):
                return False
            exits = [t for t in self._floor.neighbours(pushed_at) if t != pusher_at]
            if len(exits) != 1:
                return not exits
            pusher_at, pushed_at = pushed_at, exits[0]
        return False

    def _swap_possible(self, puller_at: Location, pulled_at: Location) -> bool:
        """Back the puller away on an empty floor and see whether it finds room.

        There is room once the puller reaches a tile with two or more ways on,
        so it can step to one side while the pulled chef passes.
        """
        behind, at = pulled_at, puller_at
        for _ in range(len(self._floor.tiles)):
            exits = [t for t in self._floor.neighbours(at) if t != behind]
            if len(exits) != 1:
                return bool(exits)
            behind, at = at, exits[0]
        return False

    def _pull(self, agent_id: str, *, into: Location) -> None:
        if agent_id in self._next or into in self._claims:
            return
        self._claims[into] = agent_id
        self._next[agent_id] = into
        self._moved_by_others.add(agent_id)

    def _closes_ring(self, agent_id: str, tile: Location) -> bool:
        """Return whether stepping onto ``tile`` closes a ring of moves.

        In a ring every chef steps onto the tile of the next one. The simulator
        runs moves one at a time, so none of them can go first.
        """
        home = self._chefs[agent_id].location
        seen: set[Location] = set()
        while tile not in seen:
            seen.add(tile)
            occupant = self._standing.get(tile)
            if occupant is None or occupant not in self._next:
                return False
            tile = self._next[occupant]
            if tile == home:
                return True
        return False

    def _held_by_other(self, tile: Location, agent_id: str) -> bool:
        return self._standing.get(tile) not in (None, agent_id)

    def _stay(self, agent_id: str) -> None:
        here = self._chefs[agent_id].location
        self._next[agent_id] = here
        self._claims[here] = agent_id

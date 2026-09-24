"""Select the audio cues for one simulation step."""

from __future__ import annotations

from collections import defaultdict

from simulator.entities import Equipment, OvercookedState
from simulator.environment import Environment
from simulator.mutations import Mutation
from simulator.view.audio.agent_cues import (
    agent_cues,
    named_cues,
    processed_cue,
    served,
)
from simulator.view.audio.library import (
    CUES,
    EQUIPMENT_CUE_PREFIX,
    EQUIPMENT_DEFAULT_CUE,
)

STATION_CUES = frozenset({"cook", "combine", "wash"})
HAND_CUES = frozenset(
    {
        "take_from_storage",
        "pick_up",
        "pick_up_plate",
        "pick_up_equipment",
        "place",
        "place_plate",
        "place_equipment",
    }
)


def cues_for_step(
    previous: Environment | None,
    current: Environment,
    mutations: list[Mutation] | None,
) -> list[str]:
    """Return cues earned by a simulation step.

    Resolve cues per agent, then deduplicate the results across agents.
    """
    names: set[str] = set()

    for agent_id, mutation_names in _by_agent(mutations).items():
        if previous is None:
            names |= _prioritise(named_cues(mutation_names))
        else:
            names |= _prioritise(
                agent_cues(previous, current, agent_id, mutation_names),
                served=served(previous, current, agent_id),
            )

    names |= _order_cues(previous, current)
    names |= _cooking_cues(previous, current)
    return sorted(names, key=_rank)


def _prioritise(names: set[str], *, served: bool = False) -> set[str]:
    """Apply cue priority and suppression rules for one agent.

    Suppression is applied per agent so one agent's delivery does not suppress
    another agent's movement cue.
    """
    # Delivery takes priority over movement and handling cues for that agent.
    if served:
        names -= HAND_CUES | {"move", "turn", "blocked", "discard"}
    if any(_is_station_cue(name) for name in names):
        names -= {"turn", "blocked"}
    if "combine" in names:
        names -= {"place", "pick_up"}
    if "move" in names:
        names -= {"turn", "blocked"}
    if "blocked" in names:
        names.discard("turn")
    return names


def _is_station_cue(name: str) -> bool:
    return name in STATION_CUES or name.startswith(EQUIPMENT_CUE_PREFIX)


# Equipment cues use the rank of the generic station cue. Names break ties.
_CUE_RANKS: dict[str, int] = {cue.name: index for index, cue in enumerate(CUES)}


def _rank(name: str) -> tuple[int, str]:
    return (_CUE_RANKS.get(name, _CUE_RANKS[EQUIPMENT_DEFAULT_CUE]), name)


def _by_agent(mutations: list[Mutation] | None) -> dict[str, set[str]]:
    """Mutation class names grouped by the agent that ran them."""
    grouped: dict[str, set[str]] = defaultdict(set)
    for mutation in mutations or []:
        agent_id = getattr(mutation, "agent_id", None)
        if agent_id:
            grouped[agent_id].add(type(mutation).__name__)
    return grouped


def _cooking_cues(previous: Environment | None, current: Environment) -> set[str]:
    """Return the sound of each station that finished cooking by itself.

    No chef acts when a timed station finishes, so these cues belong to the
    kitchen rather than to an agent.
    """
    if previous is None:
        return set()
    return {
        processed_cue(current, equipment)
        for equipment in current.get_entities_of_type(Equipment)
        if equipment.last_cooked_at == previous.timestep
    }


def _order_cues(previous: Environment | None, current: Environment) -> set[str]:
    if previous is None:
        return set()

    before = previous.get_first_entity_of_type(OvercookedState)
    after = current.get_first_entity_of_type(OvercookedState)
    if before is None or after is None:
        return set()

    cues: set[str] = set()
    if after.order_queue.delivered_count > before.order_queue.delivered_count:
        # Delivery and its reward are queue-level events.
        cues |= {"deliver", "tip"}
    elif after.order_queue.revision > before.order_queue.revision:
        # A queue revision without delivery is an expiry or reveal.
        if len(after.order_queue.visible) < len(before.order_queue.visible):
            cues.add("order_expired")
        else:
            cues.add("order_revealed")
    return cues

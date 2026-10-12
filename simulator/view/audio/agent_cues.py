"""Infer sound cues from one agent's state changes.

Use state changes where possible so generic actions such as ``Interact`` can be
resolved to the station involved.
"""

from __future__ import annotations

from simulator.entities import (
    Agent,
    Bin,
    Counter,
    Delivery,
    Equipment,
    Food,
    GameObject,
    OvercookedState,
    Plate,
    Storage,
    get_first_game_object_of_type_at,
    get_game_objects_of_type_at,
)
from simulator.environment import Environment
from simulator.view.audio.library import EQUIPMENT_DEFAULT_CUE, equipment_cue_name

MOVE_MUTATIONS = frozenset({"MoveAgentForward", "MoveAgent"})
INTERACTION_MUTATIONS = frozenset(
    {
        "Interact",
        "PickUpOrPlace",
        "PickUp",
        "Place",
        "Cook",
        "Discard",
        "Deliver",
        "TakeFromStorage",
        "Wash",
    }
)

# Used on the first step, when no previous environment exists.
MUTATION_CUES: dict[str, str] = {
    "MoveAgentForward": "move",
    "MoveAgent": "move",
    "TurnAgent": "turn",
    "PickUp": "pick_up",
    "TakeFromStorage": "take_from_storage",
    "Place": "place",
    "PickUpOrPlace": "place",
    "Cook": "cook",
    "Interact": "cook",
    "Discard": "discard",
    "Deliver": "deliver",
    "Wash": "wash",
}

COMBINE_PREFIX = "Combine"


def named_cues(mutation_names: set[str]) -> set[str]:
    """Cues taken from the mutation names alone, with no diff to read."""
    cues: set[str] = set()
    for name in mutation_names:
        if name.startswith(COMBINE_PREFIX):
            cues.add("combine")
        elif name in MUTATION_CUES:
            cues.add(MUTATION_CUES[name])
    return cues


def agent_cues(
    previous: Environment,
    current: Environment,
    agent_id: str,
    mutation_names: set[str],
) -> set[str]:
    before = previous.get_entity_as(agent_id, Agent)
    after = current.get_entity_as(agent_id, Agent)
    if before is None or after is None:
        return named_cues(mutation_names)

    cues = _movement_cues(before, after, mutation_names)

    facing = _facing(before, after)
    if facing is not None:
        cues |= _hand_cues(previous, current, before, after, facing)
        cues |= _station_cues(previous, current, facing)

    # Asked to do something and nothing in the world moved.
    if not cues and mutation_names & INTERACTION_MUTATIONS:
        cues.add("blocked")
    return cues


def served(previous: Environment, current: Environment, agent_id: str) -> bool:
    """Return whether this agent just delivered a dish.

    The order queue confirms delivery. This function identifies the responsible
    agent.
    """
    before = previous.get_entity_as(agent_id, Agent)
    after = current.get_entity_as(agent_id, Agent)
    if before is None or after is None or before.held_item_id is None:
        return False
    if current.get_entity(before.held_item_id) is not None:
        return False
    facing = _facing(before, after)
    return facing is not None and _faces(previous, facing, Delivery)


def _facing(before: Agent, after: Agent) -> tuple[int, int] | None:
    """Return the tile the agent interacted with during the step.

    Use the new orientation with the previous position because a turn and its
    action may occur in the same step.
    """
    if before.x is None or before.y is None:
        return None
    return before.copy_with(orientation=after.orientation).looking_at


def _movement_cues(before: Agent, after: Agent, mutation_names: set[str]) -> set[str]:
    if mutation_names & MOVE_MUTATIONS:
        moved = (before.x, before.y) != (after.x, after.y)
        # A movement key may also turn the agent. Report a failed move as blocked.
        return {"move"} if moved else {"blocked"}
    if before.orientation != after.orientation:
        return {"turn"}
    return set()


def _hand_cues(
    previous: Environment,
    current: Environment,
    before: Agent,
    after: Agent,
    facing: tuple[int, int],
) -> set[str]:
    if before.held_item_id == after.held_item_id:
        if before.held_item_id is None:
            return set()
        return _held_contents_cues(previous, current, before.held_item_id, facing)

    cues: set[str] = set()
    if before.held_item_id is not None:
        cues |= _lost_cues(previous, current, before.held_item_id, facing)
    if after.held_item_id is not None:
        cues |= _gained_cues(previous, current, after.held_item_id)
    return cues


def _gained_cues(
    previous: Environment,
    current: Environment,
    item_id: str,
) -> set[str]:
    item = current.get_entity(item_id)
    if isinstance(item, Plate):
        return {"pick_up_plate"}
    if isinstance(item, Equipment):
        return {"pick_up_equipment"}
    if isinstance(item, Food) and previous.get_entity(item_id) is None:
        # Newly created food came from storage.
        return {"take_from_storage"}
    return {"pick_up"}


def _lost_cues(
    previous: Environment,
    current: Environment,
    item_id: str,
    facing: tuple[int, int],
) -> set[str]:
    item = previous.get_entity(item_id)
    if current.get_entity(item_id) is None:
        # Removed items are consumed, delivered, or merged. Only binning has its
        # own cue here.
        return {"discard"} if _faces(previous, facing, Bin) else set()
    if isinstance(item, Plate):
        return {"place_plate"}
    if isinstance(item, Equipment):
        return {"place_equipment"}
    return {"place"}


def _held_contents_cues(
    previous: Environment,
    current: Environment,
    item_id: str,
    facing: tuple[int, int],
) -> set[str]:
    """Return cues for contents changing inside held equipment."""
    before = previous.get_entity_as(item_id, Equipment)
    after = current.get_entity_as(item_id, Equipment)
    if before is None or after is None:
        return set()
    # Washing changes the plate state without changing the held item.
    if (
        isinstance(before, Plate)
        and isinstance(after, Plate)
        and before.dirty
        and not after.dirty
    ):
        return {"wash"}
    if before.held_item_id == after.held_item_id:
        return set()
    if after.held_item_id is None:
        return {"discard"} if _faces(previous, facing, Bin) else set()
    return {"combine"}


def _station_cues(
    previous: Environment,
    current: Environment,
    facing: tuple[int, int],
) -> set[str]:
    x, y = facing
    cues: set[str] = set()

    if _faces(previous, facing, Storage) and _food_appeared(previous, current):
        # Taking from storage into held equipment does not change the hand id.
        cues.add("take_from_storage")

    for equipment in get_game_objects_of_type_at(previous, x, y, Equipment):
        updated = current.get_entity_as(equipment.id, Equipment)
        if updated is None:
            continue
        if equipment.held_item_id == updated.held_item_id:
            if _worked_by_hand(equipment, updated):
                cues.add(processed_cue(current, updated))
            continue
        if equipment.held_item_id is not None and updated.held_item_id is not None:
            cues.add(processed_cue(current, updated))
        elif updated.held_item_id is not None:
            cues.add("combine")

    counter = get_first_game_object_of_type_at(previous, x, y, Counter)
    if counter is not None:
        updated_counter = current.get_entity_as(counter.id, Counter)
        if (
            updated_counter is not None
            and counter.held_item_id is not None
            and updated_counter.held_item_id is not None
            and counter.held_item_id != updated_counter.held_item_id
        ):
            cues.add("combine")

    return cues


def _worked_by_hand(before: Equipment, after: Equipment) -> bool:
    """Return whether a press of Cook moved a station's food along.

    Stations that cook by themselves move along without any chef, so only
    stations cooked by hand count.
    """
    if after.cooks_by_itself or after.cooking is None:
        return False
    return before.cooking is None or before.cooking.elapsed < after.cooking.elapsed


def processed_cue(environment: Environment, equipment: Equipment) -> str:
    # Plate contents changed by combining, not cooking.
    if not equipment.can_process_food:
        return "combine"
    state = environment.get_first_entity_of_type(OvercookedState)
    sound = state.get_equipment_sound(equipment.name) if state else None
    if sound is not None and sound.clips:
        return equipment_cue_name(equipment.name)
    return EQUIPMENT_DEFAULT_CUE


def _faces(
    environment: Environment, facing: tuple[int, int], entity_type: type[GameObject]
) -> bool:
    x, y = facing
    return get_first_game_object_of_type_at(environment, x, y, entity_type) is not None


def _food_appeared(previous: Environment, current: Environment) -> bool:
    return any(
        previous.get_entity(food.id) is None
        for food in current.get_entities_of_type(Food)
    )

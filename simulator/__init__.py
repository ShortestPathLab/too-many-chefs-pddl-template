from typing import TYPE_CHECKING, Any

from simulator.configuration import (
    Configuration,
    configuration_from_dict,
    load,
    load_configuration,
)
from simulator.controller import Controller
from simulator.entities import (
    Agent,
    Bin,
    Bounds,
    CombineRecipe,
    CookRecipe,
    Counter,
    Delivery,
    Entity,
    Equipment,
    Food,
    FoodDefinition,
    GameObject,
    Orientation,
    OvercookedState,
    Plate,
    PlateDispenser,
    Shadows,
    Sink,
    Sprite,
    SpriteDefinition,
    SpriteFrame,
    SpriteFramePart,
    Storage,
    get_first_game_object_of_type_at,
)
from simulator.environment import Environment
from simulator.mutations import (
    Combine,
    Cook,
    Deliver,
    Discard,
    Interact,
    MoveAgent,
    MoveAgentForward,
    Mutation,
    PickUp,
    PickUpOrPlace,
    Place,
    TakeFromStorage,
    TurnAgent,
    Wash,
)
from simulator.recording import Recording
from simulator.run import run_agent_mode

if TYPE_CHECKING:
    from simulator.run import run_play_mode, run_replay_mode


def __getattr__(name: str) -> Any:
    # Play and replay always open the visualiser, so they load on first use.
    if name in ("run_play_mode", "run_replay_mode"):
        import simulator.run

        return getattr(simulator.run, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Agent",
    "Bin",
    "Bounds",
    "Combine",
    "CombineRecipe",
    "Configuration",
    "Controller",
    "Cook",
    "CookRecipe",
    "Counter",
    "Deliver",
    "Delivery",
    "Discard",
    "Entity",
    "Environment",
    "Equipment",
    "Food",
    "FoodDefinition",
    "GameObject",
    "Interact",
    "MoveAgent",
    "MoveAgentForward",
    "Mutation",
    "Orientation",
    "OvercookedState",
    "PickUp",
    "PickUpOrPlace",
    "Place",
    "Plate",
    "PlateDispenser",
    "Recording",
    "Shadows",
    "Sink",
    "Sprite",
    "SpriteDefinition",
    "SpriteFrame",
    "SpriteFramePart",
    "Storage",
    "TakeFromStorage",
    "TurnAgent",
    "Wash",
    "configuration_from_dict",
    "get_first_game_object_of_type_at",
    "load",
    "load_configuration",
    "run_agent_mode",
    "run_play_mode",
    "run_replay_mode",
]

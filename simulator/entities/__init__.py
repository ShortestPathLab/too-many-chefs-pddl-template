from typing import Annotated

from pydantic import Field

from simulator.entities.agent import (
    ORIENTATION_DELTAS,
    Agent,
    Orientation,
    badge_order,
)
from simulator.entities.bin import Bin
from simulator.entities.bounds import Bounds
from simulator.entities.counter import Counter
from simulator.entities.delivery import Delivery
from simulator.entities.entity import Entity
from simulator.entities.equipment import Equipment
from simulator.entities.food import Food
from simulator.entities.game_object import (
    GameObject,
    game_objects,
    get_first_game_object_of_type_at,
    get_game_object,
    get_game_objects_of_type_at,
    get_objects_at,
)
from simulator.entities.order_bar import OrderBar
from simulator.entities.orders import OrderEntry, OrderGenerator, OrderQueue
from simulator.entities.overcooked_state import OvercookedState
from simulator.entities.plate import Plate
from simulator.entities.plate_dispenser import PlateDispenser
from simulator.entities.recipes import CombineRecipe, CookRecipe, FoodDefinition
from simulator.entities.scoring import ScoringState
from simulator.entities.shadows import Shadows
from simulator.entities.sink import Sink
from simulator.entities.sound import SoundDefinition, SoundtrackDefinition
from simulator.entities.sprite import (
    EquipmentAnimationDefinition,
    EquipmentSpriteDefinition,
    Sprite,
    SpriteDefinition,
    SpriteFrame,
    SpriteFramePart,
)
from simulator.entities.storage import Storage
from simulator.entities.teams import (
    TEAM_NAMES,
    resolve_rosters,
    team_label,
    team_rosters,
    team_scores,
)
from simulator.entities.walls import Walls

EntityModel = Annotated[
    Agent
    | Bin
    | Bounds
    | Counter
    | Delivery
    | Equipment
    | Food
    | OrderBar
    | OvercookedState
    | Plate
    | PlateDispenser
    | Shadows
    | Sink
    | Walls
    | Storage,
    Field(discriminator="kind"),
]

__all__ = [
    "ORIENTATION_DELTAS",
    "TEAM_NAMES",
    "Agent",
    "Bin",
    "Bounds",
    "CombineRecipe",
    "CookRecipe",
    "Counter",
    "Delivery",
    "Entity",
    "EntityModel",
    "Equipment",
    "EquipmentAnimationDefinition",
    "EquipmentSpriteDefinition",
    "Food",
    "FoodDefinition",
    "GameObject",
    "OrderBar",
    "OrderEntry",
    "OrderGenerator",
    "OrderQueue",
    "Orientation",
    "OvercookedState",
    "Plate",
    "PlateDispenser",
    "ScoringState",
    "Shadows",
    "Sink",
    "SoundDefinition",
    "SoundtrackDefinition",
    "Sprite",
    "SpriteDefinition",
    "SpriteFrame",
    "SpriteFramePart",
    "Storage",
    "Walls",
    "badge_order",
    "game_objects",
    "get_first_game_object_of_type_at",
    "get_game_object",
    "get_game_objects_of_type_at",
    "get_objects_at",
    "resolve_rosters",
    "team_label",
    "team_rosters",
    "team_scores",
]

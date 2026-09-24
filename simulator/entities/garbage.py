"""Define placeholder food for illegal recipes.

When illegal recipes are enabled, unsupported combinations produce one of two
non-deliverable foods.
"""

from __future__ import annotations

import random

from simulator.entities.recipes import FoodDefinition
from simulator.entities.sprite import SpriteDefinition, SpriteFramePart

DUBIOUS_FOOD = "catalog/food/dubious_food"
ROCK_HARD_FOOD = "catalog/food/rock_hard_food"

GARBAGE_FOOD_NAMES = (DUBIOUS_FOOD, ROCK_HARD_FOOD)

# TODO(art): replace these placeholder tiles with dedicated artwork.
PLACEHOLDER_TILES = {
    DUBIOUS_FOOD: (320, 240),
    ROCK_HARD_FOOD: (320, 176),
}


def is_garbage_food(food_name: str) -> bool:
    return food_name in GARBAGE_FOOD_NAMES


def garbage_food_definition(food_name: str) -> FoodDefinition | None:
    """Return a placeholder definition for an illegal recipe output.

    The output is raw and cannot be delivered.
    """
    if not is_garbage_food(food_name):
        return None
    return FoodDefinition(name=food_name, raw=True, deliverable=False)


def garbage_food_sprite(food_name: str) -> SpriteDefinition | None:
    tile = PLACEHOLDER_TILES.get(food_name)
    if not tile:
        return None
    x, y = tile
    return SpriteDefinition(
        parts=[SpriteFramePart(x=x, y=y, width=16, height=16, sheet="food.png")]
    )


def garbage_food_name(*inputs: str, timestep: int) -> str:
    """Return a deterministic placeholder name for an illegal recipe.

    The same inputs at the same timestep always produce the same name so
    recordings remain reproducible.
    """
    key = ":".join((str(timestep), *sorted(inputs)))
    return random.Random(key).choice(GARBAGE_FOOD_NAMES)

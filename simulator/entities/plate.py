from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities.equipment import (
    FOOD_ON_EQUIPMENT_SHIFT_Y,
    Equipment,
    equipment_held_item_sprite,
)
from simulator.entities.sprite import (
    EquipmentSpriteDefinition,
    Sprite,
    SpriteDefinition,
    SpriteFrame,
    SpriteFramePart,
)

if TYPE_CHECKING:
    from simulator.environment import Environment
    from simulator.mutations import Mutation


PLATE_NAME = "catalog/equipment/plate"

# Vertical offset for a plate in a grid cell.
PLATE_SHIFT_Y = -13

# Vertical offset for food drawn above a plate icon.
PLATED_FOOD_LIFT = FOOD_ON_EQUIPMENT_SHIFT_Y - PLATE_SHIFT_Y


class Plate(Equipment):
    kind: Literal["plate"] = "plate"  # pyright: ignore[reportIncompatibleVariableOverride]
    name: str = PLATE_NAME
    can_pick_up: bool = True
    can_process_food: bool = False
    # A plate that has been eaten off. It carries and stacks like any other, but
    # nothing will go on it until it has been through a sink.
    dirty: bool = False

    def sprite(
        self,
        environment: Environment,
        mutations: list[Mutation],
    ) -> Sprite:
        from simulator.entities.agent import Agent

        if any(
            agent.held_item_id == self.id
            for agent in environment.get_entities_of_type(Agent)
        ):
            return Sprite()

        return Sprite(
            loop_cycle_animation=[SpriteFrame(parts=plate_parts(environment, self))]
        )


def plate_parts(environment: Environment, plate: Plate) -> list[SpriteFramePart]:
    """Return the plate sprite and its contents."""
    sprite = plate_sprite(dirty=plate.dirty)
    food_parts, ui_parts = equipment_held_item_sprite(environment, plate, sprite)
    return [*sprite.as_parts(shift_y=PLATE_SHIFT_Y), *ui_parts, *food_parts]


def plated_parts(food: SpriteDefinition | None = None) -> list[SpriteFramePart]:
    """Return a plate icon and an optional dish for UI panels."""
    parts = list(plate_sprite().as_parts())
    if food is not None:
        parts.extend(food.as_parts(shift_y=PLATED_FOOD_LIFT))
    return parts


def plate_sprite(*, dirty: bool = False) -> EquipmentSpriteDefinition:
    """Return the clean or dirty plate sprite definition."""
    return EquipmentSpriteDefinition(
        parts=[
            SpriteFramePart(
                x=32,
                y=4400 if dirty else 4416,
                width=16,
                height=16,
                sheet="interiors.png",
            )
        ]
    )

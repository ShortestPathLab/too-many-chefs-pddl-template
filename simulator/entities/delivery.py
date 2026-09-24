from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import Field, field_serializer

from simulator.entities.food import Food
from simulator.entities.game_object import GameObject
from simulator.entities.sprite import Sprite, SpriteFrame, SpriteFramePart

if TYPE_CHECKING:
    from simulator.environment import Environment
    from simulator.mutations import Mutation


def _t(column: int, row: int, half: str = "default") -> SpriteFramePart:
    shift, width = {
        "left": (0, 8),
        "right": (8, 8),
        "default": (0, 16),
    }[half]
    return SpriteFramePart(
        x=0 + column * 16 + shift,
        y=4112 + row * 16,
        width=width,
        height=16,
        shift_x=shift,
        shift_y=-16,
        sheet="interiors.png",
    )


def _b(column: int, row: int) -> SpriteFramePart:
    return SpriteFramePart(
        x=0 + column * 16,
        y=4112 + row * 16,
        width=16,
        height=16,
        shift_x=0,
        shift_y=0,
        sheet="interiors.png",
    )


class Delivery(GameObject):
    kind: Literal["delivery"] = "delivery"
    accepted_item_names: set[str] = Field(default_factory=set)

    @field_serializer("accepted_item_names")
    def serialize_accepted_item_names(self, accepted_item_names: set[str]) -> list[str]:
        return sorted(accepted_item_names)

    @property
    def blocks_movement(self) -> bool:
        return True

    @property
    def render(self) -> str:
        return "DV"

    def sprite(
        self,
        environment: Environment,
        mutations: list[Mutation],
    ) -> Sprite:
        base_parts = [
            _t(4, 3, "left"),
            _t(6, 3, "right"),
            _b(7, 7),
        ]
        return Sprite(
            loop_cycle_animation=[
                SpriteFrame(
                    parts=[
                        *base_parts,
                        SpriteFramePart(
                            x=128 + frame_index * 16,
                            y=176,
                            width=16,
                            height=16,
                            shift_x=0,
                            shift_y=-20,
                            sheet="ui.png",
                        ),
                    ]
                )
                for frame_index in range(6)
            ]
        )

    def accepts(self, food: Food) -> bool:
        return not self.accepted_item_names or food.name in self.accepted_item_names

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import Field

from simulator.models import FrozenSimulatorModel


class SpriteFramePart(FrozenSimulatorModel):
    x: int
    y: int
    width: int
    height: int
    shift_x: int = 0
    shift_y: int = 0
    sheet: str = ""

    def as_part(self, *, shift_x: int = 0, shift_y: int = 0) -> SpriteFramePart:
        return self.copy_with(
            shift_x=self.shift_x + shift_x,
            shift_y=self.shift_y + shift_y,
        )


class SpriteFrame(FrozenSimulatorModel):
    parts: list[SpriteFramePart] = Field(default_factory=list)


class Sprite(FrozenSimulatorModel):
    init_animation: list[SpriteFrame] = Field(default_factory=list)
    loop_cycle_animation: list[SpriteFrame] = Field(default_factory=list)


class SpriteDefinition(FrozenSimulatorModel):
    parts: Sequence[SpriteFramePart] = Field(default_factory=list)

    def as_parts(self, *, shift_x: int = 0, shift_y: int = 0) -> list[SpriteFramePart]:
        return [part.as_part(shift_x=shift_x, shift_y=shift_y) for part in self.parts]


EquipmentDisplayFood = Literal["callout", "on_equipment"]


class EquipmentAnimationDefinition(FrozenSimulatorModel):
    parts: list[SpriteFramePart] = Field(default_factory=list)
    frames: int = Field(default=1, ge=1)

    def frame_parts(
        self,
        frame_index: int,
        *,
        shift_x: int = 0,
        shift_y: int = 0,
    ) -> list[SpriteFramePart]:
        return [
            SpriteFramePart(
                x=part.x + (part.width * frame_index),
                y=part.y,
                width=part.width,
                height=part.height,
                shift_x=part.shift_x + shift_x,
                shift_y=part.shift_y + shift_y,
                sheet=part.sheet,
            )
            for part in self.parts
        ]


class EquipmentSpriteDefinition(SpriteDefinition):
    # Sprite parts drawn above items on the station, in a separate renderable.
    overlay: Sequence[SpriteFramePart] = Field(default_factory=list)
    display_food: EquipmentDisplayFood = "on_equipment"
    on_food_in: EquipmentAnimationDefinition | None = None
    on_food_out: EquipmentAnimationDefinition | None = None
    on_cook: EquipmentAnimationDefinition | None = None

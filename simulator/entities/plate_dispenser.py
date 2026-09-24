from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import Field

from simulator.entities.game_object import GameObject
from simulator.entities.plate import plate_sprite
from simulator.entities.sprite import Sprite, SpriteFrame, SpriteFramePart

if TYPE_CHECKING:
    from simulator.environment import Environment
    from simulator.mutations import Mutation


class PlateDispenser(GameObject):
    """Station that dispenses plates and receives them after delivery.

    Plates are finite unless ``infinite_supply`` is set. Delivered plates return
    to the first dispenser.

    With ``returns_dirty``, delivered plates must be washed before reuse. Clean
    and dirty plates are counted separately, and clean plates are dispensed
    first.

    With ``infinite_supply``, the dispenser always returns a clean plate and
    ignores returned plates.
    """

    kind: Literal["plate_dispenser"] = "plate_dispenser"
    plate_count: int = Field(default=1, ge=0)
    dirty_plate_count: int = Field(default=0, ge=0)
    infinite_supply: bool = False
    returns_dirty: bool = False

    @property
    def blocks_movement(self) -> bool:
        return True

    @property
    def has_plate(self) -> bool:
        return (
            self.infinite_supply or self.plate_count > 0 or self.dirty_plate_count > 0
        )

    @property
    def dispenses_dirty(self) -> bool:
        """Return whether the next available plate is dirty."""
        return (
            not self.infinite_supply
            and self.plate_count <= 0
            and self.dirty_plate_count > 0
        )

    @property
    def render(self) -> str:
        return "PD"

    def take_plate(self) -> PlateDispenser:
        if self.infinite_supply:
            return self
        if self.dispenses_dirty:
            return self.copy_with(dirty_plate_count=self.dirty_plate_count - 1)
        return self.copy_with(plate_count=max(0, self.plate_count - 1))

    def return_plate(self) -> PlateDispenser:
        if self.infinite_supply:
            return self
        if self.returns_dirty:
            return self.copy_with(dirty_plate_count=self.dirty_plate_count + 1)
        return self.copy_with(plate_count=self.plate_count + 1)

    def sprite(
        self,
        environment: Environment,
        mutations: list[Mutation],
    ) -> Sprite:
        parts = [
            SpriteFramePart(
                x=32,
                y=7664,
                width=16,
                height=32,
                shift_x=0,
                shift_y=-9,
                sheet="interiors.png",
            )
        ]
        if self.has_plate:
            parts.extend(
                plate_sprite(dirty=self.dispenses_dirty).as_parts(shift_y=-14 + 2)
            )
        return Sprite(loop_cycle_animation=[SpriteFrame(parts=parts)])

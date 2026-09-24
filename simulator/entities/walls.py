from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities.game_object import GameObject
from simulator.entities.sprite import Sprite, SpriteFrame, SpriteFramePart

if TYPE_CHECKING:
    from simulator.environment import Environment
    from simulator.mutations import Mutation

DEFAULT_WALL_TYPE: int = -1


class Walls(GameObject):
    kind: Literal["walls"] = "walls"
    x: int | None = 0
    y: int | None = 0
    width: int = 0
    height: int = 0
    wall_type: int = DEFAULT_WALL_TYPE

    def sprite(
        self,
        environment: Environment,
        mutations: list[Mutation],
    ) -> Sprite:
        return Sprite(
            loop_cycle_animation=[
                SpriteFrame(
                    parts=(
                        [
                            *[
                                SpriteFramePart(
                                    x=16 + (self.wall_type % 3) * 11 * 16,
                                    y=176 + (self.wall_type // 3) * 32,
                                    width=16,
                                    height=32,
                                    shift_x=column * 16,
                                    shift_y=-2 * 16,
                                    sheet="room_builder.png",
                                )
                                for column in range(self.width)
                            ],
                            *[
                                SpriteFramePart(
                                    x=176 if row == -2 else 112,
                                    y=96 if row == -2 else 80,
                                    width=16,
                                    height=16,
                                    shift_x=-16,
                                    shift_y=row * 16,
                                    sheet="room_builder.png",
                                )
                                for row in range(-2, self.height)
                            ],
                            *[
                                SpriteFramePart(
                                    x=208 if row == -2 else 128,
                                    y=96 if row == -2 else 80,
                                    width=16,
                                    height=16,
                                    shift_x=self.width * 16,
                                    shift_y=row * 16,
                                    sheet="room_builder.png",
                                )
                                for row in range(-2, self.height)
                            ],
                            *[
                                SpriteFramePart(
                                    x=(
                                        176
                                        if column == -1
                                        else 192
                                        if column < self.width
                                        else 208
                                    ),
                                    y=128,
                                    width=16,
                                    height=16,
                                    shift_x=column * 16,
                                    shift_y=self.height * 16,
                                    sheet="room_builder.png",
                                )
                                for column in range(-1, self.width + 1)
                            ],
                        ]
                        if self.wall_type != -1
                        else []
                    )
                )
            ]
        )

    def contains(self, x: int, y: int) -> bool:
        if self.x is None or self.y is None:
            return False
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height

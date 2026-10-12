from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities.game_object import GameObject
from simulator.entities.sprite import Sprite, SpriteFrame, SpriteFramePart

if TYPE_CHECKING:
    from simulator.environment import Environment
    from simulator.mutations import Mutation

DEFAULT_BACKGROUND: int = 3

GRID_SIZE_PX: int = 16
BACKGROUND_WIDTH: int = 557
BACKGROUND_HEIGHT: int = 313


class Bounds(GameObject):
    kind: Literal["bounds"] = "bounds"
    x: int | None = 0
    y: int | None = 0
    width: int = 0
    height: int = 0
    background: int = DEFAULT_BACKGROUND

    def background_part(self) -> SpriteFramePart:
        # Center the full-sized background on the playable region.
        return SpriteFramePart(
            x=0,
            y=0,
            width=BACKGROUND_WIDTH,
            height=BACKGROUND_HEIGHT,
            shift_x=(self.width * GRID_SIZE_PX - BACKGROUND_WIDTH) // 2,
            shift_y=(self.height * GRID_SIZE_PX - BACKGROUND_HEIGHT) // 2,
            sheet=f"backgrounds/background_{self.background}.png",
        )

    def sprite(
        self,
        environment: Environment,
        mutations: list[Mutation],
    ) -> Sprite:
        return Sprite(
            loop_cycle_animation=[
                SpriteFrame(
                    parts=[
                        self.background_part(),
                        *(
                            [
                                SpriteFramePart(
                                    x=112,
                                    y=176,
                                    width=16,
                                    height=16,
                                    shift_x=column * 16,
                                    shift_y=row * 16,
                                    sheet="custom.png",
                                )
                                for row in range(self.height)
                                for column in range(self.width)
                            ]
                        ),
                    ]
                )
            ]
        )

    def contains(self, x: int, y: int) -> bool:
        if self.x is None or self.y is None:
            return False
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height

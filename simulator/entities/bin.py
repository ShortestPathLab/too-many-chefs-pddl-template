from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities.game_object import GameObject
from simulator.entities.sprite import Sprite, SpriteFrame, SpriteFramePart

if TYPE_CHECKING:
    from simulator.environment import Environment
    from simulator.mutations import Mutation


class Bin(GameObject):
    kind: Literal["bin"] = "bin"

    @property
    def blocks_movement(self) -> bool:
        return True

    @property
    def render(self) -> str:
        return "BN"

    def sprite(
        self,
        environment: Environment,
        mutations: list[Mutation],
    ) -> Sprite:
        return Sprite(
            loop_cycle_animation=[
                SpriteFrame(
                    parts=[
                        SpriteFramePart(
                            x=0,
                            y=10128,
                            width=16,
                            height=32,
                            shift_x=0,
                            shift_y=-12,
                            sheet="interiors.png",
                        )
                    ]
                )
            ]
        )

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities.bin import Bin
from simulator.entities.counter import Counter
from simulator.entities.delivery import Delivery
from simulator.entities.equipment import Equipment
from simulator.entities.game_object import GameObject
from simulator.entities.sink import Sink
from simulator.entities.sprite import Sprite, SpriteFrame, SpriteFramePart
from simulator.entities.storage import Storage

if TYPE_CHECKING:
    from simulator.environment import Environment
    from simulator.mutations import Mutation


class Shadows(GameObject):
    kind: Literal["shadows"] = "shadows"

    def sprite(
        self,
        environment: Environment,
        mutations: list[Mutation],
    ) -> Sprite:
        shadowed_objects = [
            *environment.get_entities_of_type(Equipment),
            *environment.get_entities_of_type(Counter),
            *environment.get_entities_of_type(Delivery),
            *environment.get_entities_of_type(Storage),
            *environment.get_entities_of_type(Sink),
        ]
        small_shadowed_objects = [
            *environment.get_entities_of_type(Bin),
        ]
        return Sprite(
            loop_cycle_animation=[
                SpriteFrame(
                    parts=[
                        *[
                            SpriteFramePart(
                                sheet="shadows.png",
                                x=48,
                                y=64,
                                width=64,
                                height=64,
                                shift_x=((o.x or 0) - (self.x or 0)) * 16 - 16,
                                shift_y=((o.y or 0) - (self.y or 0)) * 16 - 16,
                            )
                            for o in shadowed_objects
                            if o.x is not None and o.y is not None
                        ],
                        *[
                            SpriteFramePart(
                                sheet="shadows.png",
                                x=144,
                                y=64,
                                width=64,
                                height=64,
                                shift_x=((o.x or 0) - (self.x or 0)) * 16 - 16,
                                shift_y=((o.y or 0) - (self.y or 0)) * 16 - 16,
                            )
                            for o in small_shadowed_objects
                            if o.x is not None and o.y is not None
                        ],
                    ]
                )
            ]
        )

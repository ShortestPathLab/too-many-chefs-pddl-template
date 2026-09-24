from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities.game_object import GameObject
from simulator.entities.overcooked_state import OvercookedState
from simulator.entities.plate import plate_sprite
from simulator.entities.sprite import Sprite, SpriteFrame, SpriteFramePart

if TYPE_CHECKING:
    from simulator.environment import Environment
    from simulator.mutations import Mutation


class OrderBar(GameObject):
    kind: Literal["order_bar"] = "order_bar"

    def sprite(
        self,
        environment: Environment,
        mutations: list[Mutation],
    ) -> Sprite:
        state = environment.get_first_entity_of_type(OvercookedState)
        if not state:
            return Sprite()

        parts = []
        for index, order in enumerate(state.order_queue.visible):
            expiry = state.order_queue.expiry_percent(order, environment.timestep) or 0
            order_sprite = state.get_food_sprite(order.name)
            if order_sprite and order_sprite.parts:
                parts.append(
                    SpriteFramePart(
                        height=32,
                        width=32,
                        sheet="custom.png",
                        x=96,
                        y=48,
                        shift_x=-16 - 12 - 16 + index * 16,
                        shift_y=-16 - 12 + 5 - 16 - 4,
                    )
                )
                parts.append(
                    SpriteFramePart(
                        height=int(expiry * 23),  # 23 is exact pixel height of order
                        width=32,
                        sheet="custom.png",
                        x=96,
                        y=80,
                        shift_x=-16 - 12 - 16 + index * 16,
                        shift_y=-16 - 12 + 5 - 16 - 4,
                    )
                )
                parts.extend(
                    plate_sprite().as_parts(
                        shift_x=-16 - 12 - 16 + index * 16,
                        shift_y=-16 - 12 - 16 + 3,
                    )
                )
                parts.extend(
                    order_sprite.as_parts(
                        shift_x=-16 - 12 - 16 + index * 16,
                        shift_y=-16 - 12 - 16,
                    )
                )
        return Sprite(loop_cycle_animation=[SpriteFrame(parts=parts)])

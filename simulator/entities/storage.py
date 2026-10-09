from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities.food import Food
from simulator.entities.game_object import GameObject
from simulator.entities.overcooked_state import OvercookedState
from simulator.entities.sprite import Sprite, SpriteFrame, SpriteFramePart

if TYPE_CHECKING:
    from simulator.environment import Environment
    from simulator.mutations import Mutation


class Storage(GameObject):
    kind: Literal["storage"] = "storage"
    food_name: str = ""
    infinite_supply: bool = True

    @property
    def blocks_movement(self) -> bool:
        return True

    @property
    def render(self) -> str:
        if self.food_name:
            return f"{self.food_name[:1].upper()}+"
        return "ST"

    def sprite(
        self,
        environment: Environment,
        mutations: list[Mutation],
    ) -> Sprite:
        state = environment.get_first_entity_of_type(OvercookedState)
        frame = SpriteFrame(
            parts=[
                SpriteFramePart(
                    x=32,
                    y=7664,
                    width=16,
                    height=32,
                    shift_x=0,
                    shift_y=-9,
                    sheet="interiors.png",
                ),
                *_storage_food_parts(state, self.food_name),
                SpriteFramePart(
                    x=32,
                    y=7664 + 7,
                    width=16,
                    height=32 - 7,
                    shift_x=0,
                    shift_y=-9 + 7,
                    sheet="interiors.png",
                ),
            ]
        )
        return Sprite(loop_cycle_animation=[frame])

    def dispense_food(self) -> Food:
        return Food(name=self.food_name, raw=True)


def _storage_food_parts(
    state: OvercookedState | None,
    food_name: str,
) -> list[SpriteFramePart]:
    sprite = state.get_food_sprite(food_name) if state else None
    if not sprite:
        return [
            SpriteFramePart(
                x=240,
                y=4640,
                width=16,
                height=16,
                shift_x=0,
                shift_y=-14 + 2,
                sheet="interiors.png",
            )
        ]
    return sprite.as_parts(shift_y=-14 + 2)

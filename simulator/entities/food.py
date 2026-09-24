from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities.equipment import Equipment
from simulator.entities.game_object import GameObject
from simulator.entities.overcooked_state import OvercookedState
from simulator.entities.sprite import Sprite, SpriteFrame
from simulator.utils.required import required

if TYPE_CHECKING:
    from simulator.environment import Environment
    from simulator.mutations import Mutation


class Food(GameObject):
    kind: Literal["food"] = "food"
    name: str = ""
    raw: bool = True
    deliverable: bool = False

    @property
    def render(self) -> str:
        if self.name:
            return self.name[:2].upper()
        return "FD"

    def sprite(
        self,
        environment: Environment,
        mutations: list[Mutation],
    ) -> Sprite:
        from simulator.entities.agent import Agent

        if any(
            agent.held_item_id == self.id
            for agent in [
                *environment.get_entities_of_type(Agent),
                *environment.get_entities_of_type(Equipment),
            ]
        ):
            return Sprite()

        state = required(environment.get_first_entity_of_type(OvercookedState))
        sprite = required(state.get_food_sprite(self.name))
        base = SpriteFrame(parts=sprite.as_parts(shift_y=-16))
        bob = SpriteFrame(parts=sprite.as_parts(shift_y=-15))
        return Sprite(
            init_animation=[base],
            loop_cycle_animation=[base, base, bob, bob],
        )

    @property
    def portable(self) -> bool:
        return True

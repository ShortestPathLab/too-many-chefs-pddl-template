from __future__ import annotations

import random
from typing import TYPE_CHECKING, Literal

from simulator.entities.equipment import equipment_sprite_parts
from simulator.entities.game_object import GameObject
from simulator.entities.overcooked_state import OvercookedState
from simulator.entities.plate import PLATE_NAME, Plate, plate_sprite
from simulator.entities.sprite import (
    Sprite,
    SpriteDefinition,
    SpriteFrame,
    SpriteFramePart,
)
from simulator.types import Location
from simulator.utils import required

if TYPE_CHECKING:
    from simulator.entities.equipment import Equipment
    from simulator.entities.food import Food
    from simulator.environment import Environment
    from simulator.mutations import Mutation

Orientation = Literal["n", "s", "e", "w"]


ORIENTATION_DELTAS: dict[Orientation, Location] = {
    "n": (0, -1),
    "s": (0, 1),
    "e": (1, 0),
    "w": (-1, 0),
}


class Agent(GameObject):
    costume: str = "1"
    kind: Literal["agent"] = "agent"
    orientation: Orientation = "s"
    held_item_id: str | None = None
    bob_offset: int = 0
    # Team name used for score grouping. It does not affect simulation rules.
    team: str | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bob_offset = random.randint(0, 5)

    @property
    def blocks_movement(self) -> bool:
        return True

    @property
    def render(self) -> str:
        return {
            "n": "^",
            "s": "v",
            "e": ">",
            "w": "<",
        }[self.orientation]

    def sprite(
        self,
        environment: Environment,
        mutations: list[Mutation],
    ) -> Sprite:
        from simulator.mutations.agent_mutation import AgentMutation
        from simulator.mutations.combine import Combine
        from simulator.mutations.cook import Cook
        from simulator.mutations.deliver import Deliver
        from simulator.mutations.discard import Discard
        from simulator.mutations.interact import Interact
        from simulator.mutations.move_agent import MoveAgent
        from simulator.mutations.move_agent_forward import MoveAgentForward
        from simulator.mutations.pick_up import PickUp
        from simulator.mutations.pick_up_or_place import PickUpOrPlace
        from simulator.mutations.place import Place
        from simulator.mutations.take_from_storage import TakeFromStorage

        agent_mutations = [
            mutation
            for mutation in mutations
            if isinstance(mutation, AgentMutation) and mutation.agent_id == self.id
        ]
        held_item_part = _held_item_part(environment, self)
        interaction_mutations = (
            Discard,
            Deliver,
            Cook,
            Combine,
            PickUp,
            Interact,
            PickUpOrPlace,
            Place,
            TakeFromStorage,
        )
        init_animation = []
        if any(
            isinstance(mutation, interaction_mutations) for mutation in agent_mutations
        ):
            init_animation = _agent_frames(
                self.orientation,
                costume=self.costume,
                held_item_part=held_item_part,
                y=13 * 32,
            )[2:]  # Skip first 2 frames
        elif any(
            isinstance(mutation, (MoveAgent, MoveAgentForward))
            for mutation in agent_mutations
        ):
            init_animation = _agent_frames(
                self.orientation,
                costume=self.costume,
                held_item_part=held_item_part,
                y=64,
            )
        return Sprite(
            init_animation=init_animation,
            loop_cycle_animation=_agent_frames(
                self.orientation,
                costume=self.costume,
                held_item_part=held_item_part,
                y=32,
                offset=self.bob_offset,
            ),
        )

    @property
    def looking_at(self) -> Location:
        dx, dy = ORIENTATION_DELTAS[self.orientation]
        if self.x is None or self.y is None:
            raise ValueError("Agent position is not set")
        return (self.x + dx, self.y + dy)

    @property
    def hands_free(self) -> bool:
        return self.held_item_id is None


def badge_order(environment: Environment) -> list[Agent]:
    """Return agents in stable badge order.

    Do not sort by position because agents would be renumbered as they move.
    """
    return sorted(
        environment.get_entities_of_type(Agent),
        key=lambda agent: (agent.y or 0, agent.x or 0, agent.id),
    )


def _agent_frames(
    orientation: Orientation,
    *,
    costume: str,
    held_item_part: list[SpriteFramePart] | None = None,
    y: int,
    offset: int = 0,
) -> list[SpriteFrame]:
    x_by_orientation = {
        "e": 0,
        "n": 96,
        "w": 192,
        "s": 288,
    }
    start_x = x_by_orientation[orientation]
    return [
        SpriteFrame(
            parts=[
                SpriteFramePart(
                    sheet="shadows.png",
                    x=144,
                    y=0,
                    width=64,
                    height=64,
                    shift_x=-16,
                    shift_y=-16,
                ),
                SpriteFramePart(
                    x=start_x + ((frame_index + offset) % 6) * 16,
                    y=y,
                    width=16,
                    height=32,
                    shift_x=0,
                    shift_y=-24,
                    sheet=f"chefs/chef_{costume}.png",
                ),
                *(held_item_part or []),
            ]
        )
        for frame_index in range(6)
    ]


def _held_item_part(
    environment: Environment,
    agent: Agent,
) -> list[SpriteFramePart] | None:
    from simulator.entities.equipment import Equipment
    from simulator.entities.food import Food

    if not agent.held_item_id:
        return None

    held_item = environment.get_entity(agent.held_item_id)
    if not held_item:
        return None

    base_parts = [
        SpriteFramePart(
            x=48,
            y=112,
            width=17,
            height=17,
            shift_x=0,
            shift_y=-22 - 12 - 6,
            sheet="custom.png",
        ),
    ]

    state = required(environment.get_first_entity_of_type(OvercookedState))
    if isinstance(held_item, Food):
        sprite_parts = _food_sprite_parts(state, held_item, shift_y=-40)
        if sprite_parts is None:
            return None
        return [*base_parts, *sprite_parts]

    if not isinstance(held_item, Equipment):
        return None

    if held_item.name == PLATE_NAME:
        held_food = (
            environment.get_entity_as(held_item.held_item_id, Food)
            if held_item.held_item_id
            else None
        )
        return [
            *base_parts,
            *plate_sprite(
                dirty=isinstance(held_item, Plate) and held_item.dirty
            ).as_parts(shift_y=-38),
            *(_food_sprite_parts(state, held_food, shift_y=-41) if held_food else []),
        ]
    equipment_sprite = _equipment_sprite_definition(environment, held_item)
    parts = [*base_parts, *equipment_sprite.as_parts(shift_y=-25)]
    return parts


def _food_sprite_parts(
    state: OvercookedState,
    food: Food,
    *,
    shift_y: int,
) -> list[SpriteFramePart]:
    sprite = required(state.get_food_sprite(food.name))
    return sprite.as_parts(shift_y=shift_y)


def _equipment_sprite_definition(
    environment: Environment,
    equipment: Equipment,
) -> SpriteDefinition:
    return SpriteDefinition(
        parts=[p for ps in equipment_sprite_parts(environment, equipment) for p in ps]
    )

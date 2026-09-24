from __future__ import annotations

from itertools import zip_longest
from typing import TYPE_CHECKING, Literal

from pydantic import Field

from simulator.entities.game_object import GameObject
from simulator.entities.overcooked_state import (
    OvercookedState,
)
from simulator.entities.sprite import (
    EquipmentAnimationDefinition,
    EquipmentSpriteDefinition,
    Sprite,
    SpriteFrame,
    SpriteFramePart,
)
from simulator.models import FrozenSimulatorModel
from simulator.utils import required

if TYPE_CHECKING:
    from simulator.environment import Environment
    from simulator.mutations import Mutation

# Vertical offset for food drawn on equipment.
FOOD_ON_EQUIPMENT_SHIFT_Y = -16

poof = [
    SpriteFrame(
        parts=[
            SpriteFramePart(
                x=48,
                y=i * 16,
                width=16,
                height=16,
                shift_y=-16,
                sheet="poof.png",
            ),
        ]
    )
    for i in range(5)
]


class CookingTimer(FrozenSimulatorModel):
    """Progress of food cooking in a station, by itself or by hand.

    A timer belongs to one piece of food. It is stale once the station holds
    anything else.
    """

    food_id: str
    elapsed: int = Field(default=0, ge=0)
    # Chef credited when food cooking by itself finishes. None for food a level
    # starts with, and unused by stations cooked by hand, where the chef who
    # finishes the food is credited.
    started_by: str | None = None


class Equipment(GameObject):
    kind: Literal["equipment"] = "equipment"
    name: str = ""
    requires: str | None = None
    can_pick_up: bool = False
    held_item_id: str | None = None
    can_process_food: bool = True
    # Timesteps or Cook presses food takes here. Only rules.timed_cooking sets
    # these; otherwise every station cooks with one press.
    cook_time: int = Field(default=1, ge=1)
    cooks_by_itself: bool = False
    cooking: CookingTimer | None = None
    # Timestep during which cooking by itself last finished here.
    last_cooked_at: int | None = None

    @property
    def blocks_movement(self) -> bool:
        return True

    @property
    def render(self) -> str:
        return (self.name[:2] or "EQ").upper()

    def sprite(
        self,
        environment: Environment,
        mutations: list[Mutation],
    ) -> Sprite:
        from simulator.entities.agent import Agent

        if any(
            agent.held_item_id == self.id
            for agent in environment.get_entities_of_type(Agent)
        ):
            return Sprite()

        state = environment.get_first_entity_of_type(OvercookedState)
        sprite = state.get_equipment_sprite(self.name) if state else None
        sprite = sprite or _fallback_equipment_sprite(self.name)
        base_parts, ui_parts, food_parts = equipment_sprite_parts(environment, self)
        if sprite.display_food == "callout":
            # Draw callouts as a separate renderable so they can use their own
            # depth.
            ui_parts, food_parts = [], []
        return Sprite(
            init_animation=_init_animation(
                environment,
                mutations,
                self,
                sprite,
                base_parts,
                food_parts,
                ui_parts,
            ),
            loop_cycle_animation=[
                SpriteFrame(parts=[*base_parts, *ui_parts, *food_parts])
            ],
        )

    @property
    def empty(self) -> bool:
        return self.held_item_id is None

    @property
    def portable(self) -> bool:
        return self.can_pick_up


def equipment_sprite_parts(environment: Environment, equipment: Equipment):
    state = required(environment.get_first_entity_of_type(OvercookedState))
    sprite = required(state.get_equipment_sprite(equipment.name))
    base_parts = list(sprite.as_parts())
    food_parts, ui_parts = equipment_held_item_sprite(environment, equipment, sprite)
    return (
        base_parts,
        ui_parts,
        food_parts,
    )


def equipment_callout_parts(
    environment: Environment,
    equipment: Equipment,
) -> list[SpriteFramePart]:
    """Return the callout parts for food inside equipment.

    Return an empty list when the equipment has no callout or no food.
    """
    state = environment.get_first_entity_of_type(OvercookedState)
    sprite = state.get_equipment_sprite(equipment.name) if state else None
    if sprite is None or sprite.display_food != "callout":
        return []
    food_parts, ui_parts = equipment_held_item_sprite(environment, equipment, sprite)
    return [*ui_parts, *food_parts]


def equipment_held_item_sprite(
    environment: Environment,
    equipment: Equipment,
    sprite: EquipmentSpriteDefinition,
    *,
    callout: bool = True,
) -> tuple[list[SpriteFramePart], list[SpriteFramePart]]:
    """Return food and callout parts for equipment contents.

    ``callout=False`` forces the food to render on the equipment.
    """
    from simulator.entities.food import Food

    if not equipment.held_item_id:
        return ([], [])

    state = required(environment.get_first_entity_of_type(OvercookedState))
    held_item = required(environment.get_entity_as(equipment.held_item_id, Food))
    food_sprite = required(state.get_food_sprite(held_item.name))
    if callout and sprite.display_food == "callout":
        return (
            food_sprite.as_parts(shift_y=-25 - 6),
            [
                SpriteFramePart(
                    x=80,
                    y=0,
                    width=16,
                    height=16,
                    shift_x=0,
                    shift_y=-32 - 6,
                    sheet="ui.png",
                ),
                SpriteFramePart(
                    x=80,
                    y=16,
                    width=16,
                    height=16,
                    shift_x=0,
                    shift_y=-16 - 6,
                    sheet="ui.png",
                ),
            ],
        )
    return (food_sprite.as_parts(shift_y=FOOD_ON_EQUIPMENT_SHIFT_Y), [])


def _init_animation(
    environment: Environment,
    mutations: list[Mutation],
    equipment: Equipment,
    sprite: EquipmentSpriteDefinition,
    base_parts: list[SpriteFramePart],
    food_parts: list[SpriteFramePart],
    ui_parts: list[SpriteFramePart],
) -> list[SpriteFrame]:
    animation, did_cook = _matching_animation(environment, mutations, equipment, sprite)
    frames: list[SpriteFrame] = []
    if animation:
        frames = [
            SpriteFrame(
                parts=[
                    *base_parts,
                    *animation.frame_parts(frame_index),
                    *ui_parts,
                    *food_parts,
                ]
            )
            for frame_index in range(animation.frames)
        ]
    poof_frames = poof if did_cook else []
    return [
        SpriteFrame(
            parts=[
                *(a.parts if a else [*base_parts, *ui_parts, *food_parts]),
                *(p.parts if p else []),
            ]
        )
        for p, a in zip_longest(poof_frames, frames)
    ]


def _matching_animation(
    environment: Environment,
    mutations: list[Mutation],
    equipment: Equipment,
    sprite: EquipmentSpriteDefinition,
) -> tuple[EquipmentAnimationDefinition | None, bool]:
    from simulator.mutations.combine import Combine
    from simulator.mutations.cook import Cook
    from simulator.mutations.interact import Interact
    from simulator.mutations.pick_up import PickUp
    from simulator.mutations.place import Place

    # The station finished cooking by itself during the step being drawn.
    if (
        equipment.last_cooked_at is not None
        and equipment.last_cooked_at == environment.timestep - 1
    ):
        return (sprite.on_cook, True)
    for mutation in mutations:
        if not _mutation_targets_equipment(environment, mutation, equipment):
            continue
        # A press that leaves the food part-way through does not puff.
        if isinstance(mutation, (Cook, Interact)) and equipment.held_item_id:
            return (sprite.on_cook, equipment.cooking is None)
        if isinstance(mutation, (Place, Combine)):
            if equipment.held_item_id:
                return (sprite.on_food_in, False)
            return (sprite.on_food_out, False)
        if isinstance(mutation, PickUp) and not equipment.held_item_id:
            return (sprite.on_food_out, False)
    return (None, False)


def _mutation_targets_equipment(
    environment: Environment,
    mutation: Mutation,
    equipment: Equipment,
) -> bool:
    from simulator.entities.agent import Agent
    from simulator.mutations.agent_mutation import AgentMutation

    if not isinstance(mutation, AgentMutation):
        return False
    if equipment.x is None or equipment.y is None:
        return False
    agent = environment.get_entity_as(mutation.agent_id, Agent)
    if not agent:
        return False
    return agent.looking_at == (equipment.x, equipment.y)


def _fallback_equipment_sprite(name: str) -> EquipmentSpriteDefinition:
    return EquipmentSpriteDefinition(
        parts=[
            SpriteFramePart(
                x=64,
                y=96,
                width=16,
                height=16,
                sheet="interiors.png",
            )
        ]
    )

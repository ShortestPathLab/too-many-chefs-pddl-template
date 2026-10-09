from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities.equipment import Equipment
from simulator.entities.game_object import GameObject, get_game_objects_of_type_at
from simulator.entities.sprite import Sprite, SpriteFrame, SpriteFramePart

if TYPE_CHECKING:
    from simulator.environment import Environment
    from simulator.mutations import Mutation

DEFAULT_COUNTER_WOOD_VARIANT = 2

NEIGHBOR_DELTAS = {
    1: (0, -1),
    2: (1, 0),
    4: (0, 1),
    8: (-1, 0),
}


def _t(column: int, row: int, half: str = "default") -> SpriteFramePart:
    shift, width = {
        "left": (0, 8),
        "right": (8, 8),
        "default": (0, 16),
    }[half]
    return SpriteFramePart(
        x=0 + column * 16 + shift,
        y=4112 + row * 16,
        width=width,
        height=16,
        shift_x=shift,
        shift_y=-16,
        sheet="interiors.png",
    )


def _b(column: int, row: int, wood_variant: int) -> SpriteFramePart:
    return SpriteFramePart(
        x=0 + column * 16,
        y=4112 + row * 16 + wood_variant * 16,
        width=16,
        height=16,
        shift_x=0,
        shift_y=0,
        sheet="interiors.png",
    )


def counter_l_r_variants(wood_variant: int) -> list[SpriteFramePart]:
    return [
        _b(4, 7, wood_variant),
        _b(4, 7, wood_variant),
        _b(5, 7, wood_variant),
        # _b(6, 10, wood_variant),
    ]


def counter_tile_lookup(
    seed: int,
    wood_variant: int = DEFAULT_COUNTER_WOOD_VARIANT,
) -> dict[int, list[SpriteFramePart]]:
    l_r_variants = counter_l_r_variants(wood_variant)
    return {
        0: [
            _t(6, 1, "right"),
            _t(4, 1, "left"),
            _b(7, 7, wood_variant),
        ],  # isolated
        1: [_t(0, 3), _b(7, 7, wood_variant)],  # up
        2: [_t(4, 1), _b(7, 7, wood_variant)],  # right
        3: [_t(0, 3), _b(7, 7, wood_variant)],  # up+right
        4: [
            _t(0, 1, "left"),
            _t(1, 1, "right"),
            _b(7, 10, wood_variant),
        ],  # down
        5: [_t(0, 2), _b(7, 10, wood_variant)],  # up+down
        6: [_t(0, 1), _b(5, 10, wood_variant)],  # right+down
        7: [_t(0, 1), _b(5, 10, wood_variant)],  # up+right+down
        8: [_t(6, 1), _b(7, 7, wood_variant)],  # left
        9: [_t(0, 3), _b(7, 7, wood_variant)],  # up+left
        10: [
            _t(5, 1),
            l_r_variants[seed % len(l_r_variants)],
        ],  # right+left
        11: [_t(5, 1), _b(6, 10, wood_variant)],  # up+right+left
        12: [_t(1, 1), _b(7, 10, wood_variant)],  # down+left
        13: [_t(0, 2), _b(7, 10, wood_variant)],  # up+down+left
        14: [
            _t(1, 1, "left"),
            _t(0, 1, "right"),
            _b(6, 10, wood_variant),
        ],  # all but up
        15: [
            _t(1, 1, "left"),
            _t(0, 1, "right"),
            _b(6, 10, wood_variant),
        ],  # fully surrounded
    }


class Counter(GameObject):
    kind: Literal["counter"] = "counter"
    held_item_id: str | None = None
    wood_variant: int = DEFAULT_COUNTER_WOOD_VARIANT

    @property
    def blocks_movement(self) -> bool:
        return True

    @property
    def render(self) -> str:
        return "[]"

    def sprite(
        self,
        environment: Environment,
        mutations: list[Mutation],
    ) -> Sprite:
        bitmask = _counter_neighbor_bitmask(environment, self)
        frame = SpriteFrame(
            parts=counter_tile_lookup(
                (self.x or 0) + (self.y or 0),
                wood_variant=self.wood_variant,
            )[bitmask]
        )
        return Sprite(loop_cycle_animation=[frame])

    def empty(self, environment: Environment) -> bool:
        if self.x is None or self.y is None:
            return self.held_item_id is None
        return self.held_item_id is None and not get_game_objects_of_type_at(
            environment, self.x, self.y, Equipment
        )


def _counter_neighbor_bitmask(environment: Environment, counter: Counter) -> int:
    if counter.x is None or counter.y is None:
        return 0

    bitmask = 0
    for bit, (dx, dy) in NEIGHBOR_DELTAS.items():
        if get_game_objects_of_type_at(
            environment, counter.x + dx, counter.y + dy, Counter
        ):
            bitmask |= bit
    return bitmask

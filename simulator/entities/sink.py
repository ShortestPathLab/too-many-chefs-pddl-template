from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities.counter import DEFAULT_COUNTER_WOOD_VARIANT
from simulator.entities.game_object import GameObject
from simulator.entities.sprite import Sprite, SpriteFrame, SpriteFramePart

if TYPE_CHECKING:
    from simulator.environment import Environment
    from simulator.mutations import Mutation

# The basin spans neighboring cells and is drawn above them.
BASIN_WIDTH = 24
BASIN_HEIGHT = 14


class Sink(GameObject):
    """Station where agents wash used plates.

    Agents wash one plate at a time while holding it.
    """

    kind: Literal["sink"] = "sink"

    @property
    def blocks_movement(self) -> bool:
        return True

    @property
    def render(self) -> str:
        return "SK"

    def sprite(
        self,
        environment: Environment,
        mutations: list[Mutation],
    ) -> Sprite:
        return Sprite(loop_cycle_animation=[SpriteFrame(parts=_sink_parts())])


def _sink_parts() -> list[SpriteFramePart]:
    """Return the sink sprite parts."""
    wood_variant = DEFAULT_COUNTER_WOOD_VARIANT
    return [
        # The two halves of an isolated counter top, then its cabinet front.
        SpriteFramePart(
            x=4 * 16,
            y=4128,
            width=8,
            height=16,
            shift_x=0,
            shift_y=-16,
            sheet="interiors.png",
        ),
        SpriteFramePart(
            x=6 * 16 + 8,
            y=4128,
            width=8,
            height=16,
            shift_x=8,
            shift_y=-16,
            sheet="interiors.png",
        ),
        SpriteFramePart(
            x=7 * 16,
            y=4112 + 7 * 16 + wood_variant * 16,
            width=16,
            height=16,
            shift_x=0,
            shift_y=0,
            sheet="interiors.png",
        ),
        SpriteFramePart(
            x=133,
            y=113,
            width=BASIN_WIDTH,
            height=BASIN_HEIGHT,
            shift_x=(16 - BASIN_WIDTH) // 2,
            shift_y=-15,
            sheet="kitchen.png",
        ),
    ]

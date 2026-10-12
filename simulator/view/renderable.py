from __future__ import annotations

from typing import Literal

from pydantic import Field

from simulator.entities.sprite import Sprite
from simulator.models import FrozenSimulatorModel

DEFAULT_UNIT_PX: int = 16


class Renderable(FrozenSimulatorModel):
    """One drawable sprite with a position and draw order."""

    id: str
    x: float = 0.0
    y: float = 0.0
    z: int = 0
    order: int = 0
    sprite: Sprite = Field(default_factory=Sprite)


class CanvasBackdrop(FrozenSimulatorModel):
    """Optional flat fill and checkerboard drawn under every renderable."""

    fill: str | None = None
    checker: str | None = None


class CanvasFrame(FrozenSimulatorModel):
    """A rounded frame in world pixels, independent of the browser size."""

    x: int
    y: int
    width: int
    height: int
    radius: int = 8
    border_width: int = 3
    edge: str = "#241a11"
    rim: str = "#8a6540"


class CanvasTransform(FrozenSimulatorModel):
    """Map grid units to pixels, at a fixed scale or to cover the element."""

    mode: Literal["cover", "fixed"] = "fixed"
    unit: int = DEFAULT_UNIT_PX
    scale: int = 1
    grid_width: int = 1
    grid_height: int = 1
    # Cover mode fills the element with a region of this many pixels, centred
    # on the grid, and crops whatever overhangs, as CSS ``cover`` does. Given
    # ``extreme_aspect``, an element more than that many times wider or taller
    # than the region's own shape shows the whole region instead, as
    # ``contain`` does.
    cover_width: int = 0
    cover_height: int = 0
    extreme_aspect: float | None = None
    # Extra fixed-mode padding for sprites with shifted parts.
    pad: int = 0

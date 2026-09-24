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
    """Map grid units to pixels in fit or fixed mode."""

    mode: Literal["fit", "fixed"] = "fixed"
    unit: int = DEFAULT_UNIT_PX
    scale: int = 1
    grid_width: int = 1
    grid_height: int = 1
    padding_cells: int = 0
    # Extra fixed-mode padding for sprites with shifted parts.
    pad: int = 0

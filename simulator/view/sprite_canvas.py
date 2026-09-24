from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from nicegui import ui

from simulator.entities.sprite import Sprite, SpriteFramePart
from simulator.view.renderable import (
    DEFAULT_UNIT_PX,
    CanvasBackdrop,
    CanvasFrame,
    CanvasTransform,
    Renderable,
)
from simulator.view.scene import sprite_sheet_urls


class SpriteCanvas(ui.element, component="sprite_canvas.js"):  # pyright: ignore[reportGeneralTypeIssues, reportCallIssue]
    """Canvas component that renders a set of sprites."""

    def __init__(
        self,
        *,
        transform: CanvasTransform | None = None,
        backdrop: CanvasBackdrop | None = None,
        frame: CanvasFrame | None = None,
        renderables: Sequence[Renderable] | None = None,
        camera_id: str = "",
        animated: bool = True,
        sprite_sheets: dict[str, str] | None = None,
    ) -> None:
        super().__init__()
        self._props["spriteSheets"] = sprite_sheets or sprite_sheet_urls()
        self._props["cameraId"] = camera_id
        self._props["animated"] = animated
        self._props["frame"] = frame.to_dict() if frame else None
        self._props["backdrop"] = (backdrop or CanvasBackdrop()).to_dict()
        self._props["transform"] = (transform or CanvasTransform()).to_dict()
        self._props["renderables"] = _dump(renderables or [])

    def set_renderables(self, renderables: Sequence[Renderable]) -> None:
        # Avoid resending unchanged layers.
        payload = _dump(renderables)
        if payload == self._props["renderables"]:
            return
        self._props["renderables"] = payload
        self.update()

    def set_transform(self, transform: CanvasTransform) -> None:
        payload = transform.to_dict()
        if payload == self._props["transform"]:
            return
        self._props["transform"] = payload
        self.update()


def sprite_icon(sprite: Sprite, *, scale: int = 1) -> SpriteCanvas:
    """Return a HUD canvas containing one sprite."""
    frames, pad = fit_to_cell(sprite)
    return SpriteCanvas(
        transform=CanvasTransform(
            mode="fixed",
            unit=DEFAULT_UNIT_PX,
            grid_width=1,
            grid_height=1,
            pad=pad,
            scale=scale,
        ),
        renderables=[Renderable(id="icon", sprite=frames)],
        animated=False,
    )


def fit_to_cell(sprite: Sprite) -> tuple[Sprite, int]:
    """Return the icon frames and padding needed for their shifted parts."""
    parts = [part for frame in sprite.loop_cycle_animation for part in frame.parts]
    frames = Sprite(loop_cycle_animation=list(sprite.loop_cycle_animation))
    if not parts:
        return frames, 0

    return frames, max(
        0,
        -min(part.shift_x for part in parts),
        -min(part.shift_y for part in parts),
        max(part.shift_x + part.width for part in parts) - DEFAULT_UNIT_PX,
        max(part.shift_y + part.height for part in parts) - DEFAULT_UNIT_PX,
    )


def seat_on_cell(parts: Sequence[SpriteFramePart]) -> list[SpriteFramePart]:
    """Center a composite sprite within one grid cell."""
    if not parts:
        return list(parts)

    left = min(part.shift_x for part in parts)
    top = min(part.shift_y for part in parts)
    width = max(part.shift_x + part.width for part in parts) - left
    height = max(part.shift_y + part.height for part in parts) - top
    return [
        part.as_part(
            shift_x=(DEFAULT_UNIT_PX - width) // 2 - left,
            shift_y=(DEFAULT_UNIT_PX - height) // 2 - top,
        )
        for part in parts
    ]


def _dump(renderables: Sequence[Renderable]) -> list[dict[str, Any]]:
    return [renderable.to_dict() for renderable in renderables]

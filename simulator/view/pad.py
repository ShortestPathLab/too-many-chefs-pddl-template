from __future__ import annotations

import struct
from collections.abc import Sequence
from pathlib import Path

from simulator.assets import SPRITES_DIRECTORY
from simulator.models import FrozenSimulatorModel
from simulator.mutations import DIRECTIONS, VirtualInput

CONTROLLER_DIRECTORY = SPRITES_DIRECTORY / "controller"
CONTROLLER_URL = "/assets/sprites/controller"

# Pad sprite set and pressed-frame names.

DIRECTIONAL_SET = "DirectionalButtons/Color"  # Color | Flat | FlatInverted
FACE_SET = "FaceButtons/Color"  # Color | Famicom | Flat | FlatColor

DIRECTIONAL_PRESSED = "Highlighted"  # Pressed | Selected | Highlighted
FACE_PRESSED = "Highlighted"  # Pressed | Highlighted

UNPRESSED = "Unpressed"

# Keep the pixel-art scale integral.
PAD_SCALE = 2

# The directional pad is one image. Only opposing direction pairs have frames.
DIRECTION_FRAMES: dict[VirtualInput, str] = {
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
}
DIRECTION_PAIRS: dict[frozenset[str], str] = {
    frozenset({"up", "down"}): "UpDown",
    frozenset({"left", "right"}): "LeftRight",
}
FACE_FRAMES: dict[VirtualInput, str] = {"a": "A", "b": "B"}


class PadSprite(FrozenSimulatorModel):
    """One pad frame at its source size."""

    url: str
    width: int
    height: int

    @property
    def scaled_width(self) -> int:
        return self.width * PAD_SCALE

    @property
    def scaled_height(self) -> int:
        return self.height * PAD_SCALE


def directional_sprite(pressed: Sequence[VirtualInput] = ()) -> PadSprite:
    return _sprite(DIRECTIONAL_SET, _directional_frame(pressed))


def face_sprite(
    button: VirtualInput, pressed: Sequence[VirtualInput] = ()
) -> PadSprite:
    state = FACE_PRESSED if button in pressed else UNPRESSED
    return _sprite(FACE_SET, f"{FACE_FRAMES[button]}{state}")


def pad_sprites() -> list[PadSprite]:
    """Return all pad frames for preloading."""
    sprites = [directional_sprite()]
    sprites += [directional_sprite([direction]) for direction in DIRECTIONS]
    sprites += [
        face_sprite(button, pressed)
        for button in FACE_FRAMES
        for pressed in ((), (button,))
    ]
    return sprites


def _directional_frame(pressed: Sequence[VirtualInput]) -> str:
    directions = [direction for direction in DIRECTIONS if direction in pressed]
    if not directions:
        return UNPRESSED
    if len(directions) > 1:
        pair = DIRECTION_PAIRS.get(frozenset(directions))
        combined = f"{pair}{DIRECTIONAL_PRESSED}" if pair else None
        if combined and _exists(DIRECTIONAL_SET, combined):
            return combined
        # Mixed non-opposing directions have no combined frame.
    return f"{DIRECTION_FRAMES[directions[0]]}{DIRECTIONAL_PRESSED}"


def _sprite(sprite_set: str, frame: str) -> PadSprite:
    width, height = _size(_path(sprite_set, frame))
    return PadSprite(
        url=f"{CONTROLLER_URL}/{sprite_set}/{frame}.png",
        width=width,
        height=height,
    )


def _path(sprite_set: str, frame: str) -> Path:
    return CONTROLLER_DIRECTORY / sprite_set / f"{frame}.png"


def _exists(sprite_set: str, frame: str) -> bool:
    return _path(sprite_set, frame).is_file()


def _size(path: Path) -> tuple[int, int]:
    """Read PNG width and height from its header."""
    with path.open("rb") as file:
        header = file.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Not a PNG: {path}")
    return struct.unpack(">II", header[16:24])

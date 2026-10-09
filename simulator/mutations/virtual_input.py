from __future__ import annotations

from typing import Literal

VirtualInput = Literal["up", "down", "left", "right", "a", "b"]

# Six inputs match play mode: four directions, interact, and use.
DIRECTIONS: tuple[VirtualInput, ...] = ("up", "down", "left", "right")
FACE_BUTTONS: tuple[VirtualInput, ...] = ("b", "a")

# Keep the mapping keyed by input string so the mutation base can import it.
ORIENTATION_INPUTS: dict[str, VirtualInput] = {
    "n": "up",
    "s": "down",
    "e": "right",
    "w": "left",
}

ARROWS: dict[VirtualInput, str] = {
    "up": "▲",
    "down": "▼",
    "left": "◀",
    "right": "▶",
}


def step_input(dx: int, dy: int) -> VirtualInput | None:
    """The direction a step of ``(dx, dy)`` presses.

    Diagonals and teleports have no key behind them on a pad with four
    directions, so they light no button.
    """
    if dx and dy:
        return None
    if dx:
        return "right" if dx > 0 else "left"
    if dy:
        return "down" if dy > 0 else "up"
    return None

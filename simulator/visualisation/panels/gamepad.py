"""The pad, in the shape of the six inputs the game actually has."""

from __future__ import annotations

from collections.abc import Sequence

from nicegui import ui

from simulator.mutations import ARROWS, FACE_BUTTONS, VirtualInput
from simulator.view import (
    PadSprite,
    directional_sprite,
    face_sprite,
    pad_sprites,
    sentence_case,
)

PAD_SHELL = "items-center gap-2 flex-nowrap shrink-0"
FACE_ACTIONS = {"a": "Interact", "b": "Pick up / place"}


def pad_preloads() -> str:
    """Preload tags for every pad frame.

    A press lasts one step. Fetching its frame at the moment it is needed shows
    an empty box for exactly as long as the press is visible.
    """
    return "\n".join(
        f'<link rel="preload" as="image" href="{sprite.url}">'
        for sprite in pad_sprites()
    )


def gamepad(pressed: Sequence[VirtualInput]) -> None:
    """A pad showing what the last step pressed.

    Every run mode drives the simulation through the same mutations, so an
    agent run lights this the same way a person playing does. It is the
    cheapest way to see what a controller is doing without reading the log.

    Which art it wears, and what a press looks like, are decided in
    ``simulator.view.pad``.
    """
    with ui.row().classes(PAD_SHELL):
        directions = [direction for direction in ARROWS if direction in pressed]
        _pad_button(
            released=directional_sprite(),
            held=directional_sprite(pressed) if directions else None,
            tooltip=", ".join(sentence_case(name) for name in directions) or "Idle",
        )
        with ui.row().classes("items-center gap-1 flex-nowrap"):
            for button in FACE_BUTTONS:
                _pad_button(
                    released=face_sprite(button),
                    held=face_sprite(button, pressed) if button in pressed else None,
                    tooltip=FACE_ACTIONS[button],
                )


def _pad_button(
    *,
    released: PadSprite,
    held: PadSprite | None,
    tooltip: str,
) -> None:
    """One button, showing its press and then coming back up.

    The released frame is always the one underneath. A press lays the pressed
    frame over it and takes it away again on its own, so the button never
    waits for the next step to come back up. Both frames are already in the
    browser, so the release costs nothing.
    """
    wrapper = ui.element("div").classes(
        "relative block leading-none" + (" pad-press" if held else "")
    )
    wrapper.style(
        f"width: {released.scaled_width}px; height: {released.scaled_height}px"
    )
    with wrapper:
        _pad_image(released)
        if held is not None:
            _pad_image(held, overlay=True)
    wrapper.tooltip(tooltip)


def _pad_image(sprite: PadSprite, *, overlay: bool = False) -> None:
    # Use a plain img so pixel art stays at an integer scale.
    position = "absolute inset-0 pad-hold" if overlay else "block"
    ui.element("img").props(f'src="{sprite.url}" draggable="false"').classes(
        f"{position} select-none"
    ).style(
        f"width: {sprite.scaled_width}px; height: {sprite.scaled_height}px;"
        " image-rendering: pixelated"
    )

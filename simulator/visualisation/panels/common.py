"""Pieces more than one panel is built out of."""

from __future__ import annotations

from nicegui import ui

from simulator.visualisation.theme import (
    INK_DIM,
    KEYCAP,
    LABEL,
    LEADING_ZEROS,
    PANEL_BODY,
    PANEL_FRAME,
    PANEL_HEAD,
    ROUND_SMALL,
    RULE_LIGHT,
    TEXT,
)
from simulator.visualisation.types import HudSection


def panel_head(title: str) -> ui.row:
    """A panel's title bar.

    Returned open, so a caller can add a chip or a control beside the title.
    """
    head = ui.row().classes(PANEL_HEAD)
    with head:
        ui.label(title).classes(LABEL)
    return head


def counter(
    value: int,
    *,
    digits: int,
    classes: str,
    tone: str = "",
    muted: str = LEADING_ZEROS,
) -> None:
    """Render a fixed-width number with dimmed leading zeros."""
    text = str(value)
    padding = "0" * max(0, digits - len(text))
    with ui.row().classes("items-baseline gap-0 flex-nowrap tabular-nums"):
        if padding:
            ui.label(padding).classes(f"{classes} {muted}")
        ui.label(text).classes(f"{classes} {tone}")


def row(label: str, value: str) -> None:
    with ui.row().classes("w-full justify-between items-center gap-2 flex-nowrap"):
        ui.label(label).classes(LABEL)
        ui.label(value).classes(f"{TEXT} text-right break-words min-w-0")


def value_panel(section: HudSection) -> None:
    """A mode's own label/value list, whatever it happens to contain."""
    # Keep right-rail panels at the rail width.
    with ui.column().classes(PANEL_FRAME + " w-full"):
        panel_head(str(section.get("title", "")))
        with ui.column().classes(PANEL_BODY):
            for item in section.get("items", []):
                with ui.row().classes(
                    f"w-full justify-between items-center gap-2 {TEXT} flex-nowrap"
                ):
                    ui.label(str(item.get("label", ""))).classes(INK_DIM)
                    ui.label(str(item.get("value", ""))).classes(
                        "text-right break-words"
                    )


def controls_panel(section: HudSection) -> None:
    """Show keyboard hints as individual items along the bottom right."""
    items = section.get("items", [])
    if not items:
        return
    with (
        ui.row()
        .classes("w-full justify-end items-center gap-6 flex-wrap pointer-events-auto")
        .props('role="group"') as hints
    ):
        hints.props["aria-label"] = str(section.get("title", "Controls"))
        for item in items:
            with ui.row().classes(
                f"items-center gap-2 flex-nowrap max-w-full "
                f"{TEXT} {ROUND_SMALL} {RULE_LIGHT}"
            ):
                ui.label(str(item.get("action", ""))).classes(
                    "min-w-0 break-words [text-shadow:_1px_1px_0px_rgba(0,0,0,0.3)]"
                )
                ui.label(str(item.get("key", ""))).classes(f"{KEYCAP} shrink-0")

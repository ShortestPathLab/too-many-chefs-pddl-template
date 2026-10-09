"""The order queue down the left-hand side, and the level's name beneath it."""

from __future__ import annotations

from nicegui import ui

from simulator.view import OrdersView
from simulator.visualisation.panels.orders import orders_panel
from simulator.visualisation.theme import CAPTION, INK_DIM, RAIL, TEXT, TITLE


def left_rail(
    *,
    orders: OrdersView | None,
    level_label: str,
    level_name: str | None = None,
    description: str | None = None,
) -> None:
    # Let the order list use the height above the caption.
    with ui.column().classes(f"{RAIL} shrink-0 flex-nowrap gap-2 min-h-0 self-stretch"):
        if orders is not None:
            orders_panel(orders)
        level_caption(
            level_label=level_label, level_name=level_name, description=description
        )


def level_caption(
    *,
    level_label: str,
    level_name: str | None = None,
    description: str | None = None,
) -> None:
    """The level's name and what it asks for.

    It is read once, at the start of a run, so it sits out of the way in the
    bottom corner. The level's file name stands in for a level that gives
    itself no name.
    """
    with ui.column().classes(CAPTION):
        ui.label((level_name or "").strip() or level_label).classes(
            f"{TITLE} break-words"
        )
        if description and description.strip():
            ui.label(description.strip()).classes(f"{TEXT} {INK_DIM} break-words")

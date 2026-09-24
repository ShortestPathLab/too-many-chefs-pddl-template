"""The order queue down the left-hand side of the kitchen."""

from __future__ import annotations

from nicegui import ui

from simulator.view import OrdersView
from simulator.visualisation.panels.orders import orders_panel
from simulator.visualisation.theme import RAIL


def left_rail(*, orders: OrdersView | None) -> None:
    # Let the order list use the available height above the footer.
    with ui.column().classes(f"{RAIL} shrink-0 flex-nowrap gap-2 min-h-0 self-stretch"):
        if orders is not None:
            orders_panel(orders)

"""Render the order queue panel."""

from __future__ import annotations

from nicegui import ui

from simulator.view import (
    OrderCard,
    OrdersView,
    RecipeStep,
    and_list,
    sprite_icon,
)
from simulator.visualisation.panels.common import panel_head
from simulator.visualisation.theme import (
    ACCENT_EDGE,
    ACCENT_INK,
    CHIP,
    INK_FAINT,
    INK_GHOST,
    KEEPS_HEIGHT,
    ORDER_BAND,
    ORDER_CARD,
    ORDER_CARD_EDGE,
    ORDER_CARD_EDGE_NEXT,
    ORDER_DISH,
    ORDER_REWARD,
    ORDER_RULE,
    PANEL_BODY,
    PANEL_FRAME,
    PANEL_SCROLL,
    PAPER_BAND,
    PAPER_EXPIRY_CALM,
    PAPER_EXPIRY_CRITICAL,
    PAPER_EXPIRY_WARM,
    PAPER_INK_FAINT,
    PAPER_SLOT_DISH,
    PAPER_SLOT_STEP,
    PAPER_TRACK,
    RECIPE_PARTS,
    RECIPE_STEP,
    SPRITE_SCALE,
    SPRITE_SCALE_LARGE,
    TEXT,
    TEXT_SMALL,
    TRACK_FILL,
)


def orders_panel(view: OrdersView) -> None:
    with ui.column().classes(f"{PANEL_FRAME} w-full"):
        with panel_head("Orders"):
            ui.label(view.queue_label).classes(
                f"{CHIP} {ACCENT_EDGE} {ACCENT_INK} ml-auto"
            )
        # Preserve ticket height and scroll when the queue is long.
        with ui.column().classes(f"{PANEL_BODY} {PANEL_SCROLL} flex-nowrap"):
            for card in view.cards:
                _order_card(card)
            if not view.cards:
                ui.label("No orders").classes(f"{TEXT} {KEEPS_HEIGHT} {INK_FAINT}")
            if view.note:
                ui.label(view.note).classes(f"{TEXT_SMALL} {KEEPS_HEIGHT} {INK_GHOST}")


def _order_card(card: OrderCard) -> None:
    """Render one order ticket."""
    border = ORDER_CARD_EDGE_NEXT if card.is_next else ORDER_CARD_EDGE
    with ui.column().classes(f"{ORDER_CARD} {border}"):
        with ui.row().classes(ORDER_DISH):
            with ui.element("div").classes(PAPER_SLOT_DISH):
                sprite_icon(card.sprite, scale=SPRITE_SCALE_LARGE)
            # Use the ticket's foreground color for the dish name.
            ui.label(card.label).classes(
                f"{TEXT} text-xl leading-tight break-words min-w-0"
            )
            ui.label(f"+{card.reward}").classes(ORDER_REWARD)
        if card.recipe:
            # The dish is shown above, so this section contains only preparation.
            _rule()
            with ui.column().classes(ORDER_BAND):
                _step(card.recipe)
        if card.remaining_steps is not None or card.remaining_fraction is not None:
            _rule()
            _expiry(card)


def _rule() -> None:
    """Render a ticket divider."""
    ui.element("div").classes(ORDER_RULE)


def _expiry(card: OrderCard) -> None:
    """Render the order time remaining."""
    with ui.column().classes(ORDER_BAND):
        if card.remaining_fraction is not None:
            _expiry_bar(card.remaining_fraction)


def _step(step: RecipeStep) -> None:
    """Render one ingredient group and its stations."""
    with ui.element("div").classes(RECIPE_STEP):
        if step.parts:
            with ui.element("div").classes(RECIPE_PARTS):
                for index, part in enumerate(step.parts):
                    if index:
                        _ink("+")
                    _step(part)
        else:
            with ui.element("div").classes(PAPER_SLOT_STEP):
                sprite_icon(step.sprite, scale=SPRITE_SCALE).tooltip(step.label)
        if step.stations:
            verbs = and_list([station.verb for station in step.stations])
            ui.label(verbs).classes(PAPER_BAND)


def _ink(mark: str) -> ui.label:
    """Render a recipe separator."""
    return ui.label(mark).classes(f"{TEXT_SMALL} text-[{PAPER_INK_FAINT}] px-0.5")


def _expiry_bar(remaining: float) -> None:
    colour = (
        f"bg-[{PAPER_EXPIRY_CALM}]"
        if remaining > 0.5
        else f"bg-[{PAPER_EXPIRY_WARM}]"
        if remaining > 0.22
        else f"bg-[{PAPER_EXPIRY_CRITICAL}]"
    )
    with ui.element("div").classes(PAPER_TRACK):
        ui.element("div").classes(f"{TRACK_FILL} {colour}").style(
            f"width: {remaining * 100:.1f}%; transition: width 200ms linear"
        )

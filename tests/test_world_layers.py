"""Test how the kitchen's layers reach the screen."""

from __future__ import annotations

from unittest.mock import patch

from nicegui import ui

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.entities import Bounds
from simulator.entities.bounds import BACKGROUND_HEIGHT, BACKGROUND_WIDTH
from simulator.view import SpriteCanvas
from simulator.visualisation.theme import LAYER_FILTERS, LayerFilters
from simulator.visualisation.world import EXTREME_ASPECT, world_stack


def _layers(
    bounds: Bounds | None = None,
    filters: LayerFilters = LAYER_FILTERS,
) -> list[SpriteCanvas]:
    """Build the kitchen and return its canvases, the floor first."""
    environment = load(Configuration.from_dict({"layout": "| |"}))
    bounds = bounds or environment.get_first_entity_of_type(Bounds)
    assert bounds is not None
    with (
        ui.column() as container,
        patch("simulator.visualisation.world.LAYER_FILTERS", filters),
    ):
        world_stack(environment, bounds, selected_agent_id=None)
    found = [
        element
        for element in container.descendants()
        if isinstance(element, SpriteCanvas)
    ]
    container.delete()
    return found


def _filters(filters: LayerFilters) -> list[str | None]:
    return [canvas._style.get("filter") for canvas in _layers(filters=filters)]


def test_each_layer_is_shown_through_its_own_filter() -> None:
    # The layers are stacked floor first, then shadows, then everything else.
    filters = LayerFilters(
        background="sepia(1)", shadows="opacity(0.5)", objects="blur(1px)"
    )

    assert _filters(filters) == ["sepia(1)", "opacity(0.5)", "blur(1px)"]


def test_a_layer_with_no_filter_is_left_as_drawn() -> None:
    assert _filters(LayerFilters(objects="blur(1px)")) == [None, None, "blur(1px)"]


def test_the_camera_fills_the_window_with_the_room() -> None:
    # The room is the same size behind every kitchen, so how big a kitchen is
    # does not change how far in the camera sits.
    transforms = [canvas._props["transform"] for canvas in _layers()]

    assert transforms[0]["mode"] == "cover"
    assert (transforms[0]["cover_width"], transforms[0]["cover_height"]) == (
        BACKGROUND_WIDTH,
        BACKGROUND_HEIGHT,
    )
    assert transforms[0]["extreme_aspect"] == EXTREME_ASPECT
    # The layers are drawn one over another, so they share the camera.
    assert transforms[1:] == transforms[:1] * 2


def test_a_kitchen_larger_than_the_room_is_still_shown_whole() -> None:
    transform = _layers(Bounds(width=40, height=10))[0]._props["transform"]

    assert (transform["cover_width"], transform["cover_height"]) == (
        40 * 16,
        BACKGROUND_HEIGHT,
    )

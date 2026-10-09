"""The kitchen itself: three canvases sharing one camera."""

from __future__ import annotations

from simulator.entities import Bounds
from simulator.entities.bounds import GRID_SIZE_PX
from simulator.environment import Environment
from simulator.view import CanvasTransform, SceneLayers, SpriteCanvas, scene_layers
from simulator.view.renderable import CanvasFrame
from simulator.visualisation.theme import BACKDROP, LAYER_FILTERS

WORLD_CAMERA = "world"
# The camera fills the window with the room and crops whatever overhangs. A
# window this many times wider or taller than the room's own shape would crop
# most of the room away, so from there on it shows the whole room with bars
# beside it.
EXTREME_ASPECT = 2.0


class WorldStack:
    """World layers split by update frequency."""

    def __init__(self, bounds: Bounds, layers: SceneLayers) -> None:
        room = bounds.background_part()
        transform = CanvasTransform(
            mode="cover",
            grid_width=bounds.width,
            grid_height=bounds.height,
            # The room is the backdrop, unless the kitchen has outgrown it.
            cover_width=max(room.width, bounds.width * GRID_SIZE_PX),
            cover_height=max(room.height, bounds.height * GRID_SIZE_PX),
            extreme_aspect=EXTREME_ASPECT,
        )
        self._background = _layer(
            SpriteCanvas(
                transform=transform,
                backdrop=BACKDROP,
                frame=CanvasFrame(
                    x=room.shift_x,
                    y=room.shift_y,
                    width=room.width,
                    height=room.height,
                ),
                renderables=layers.background,
                animated=False,
            ),
            LAYER_FILTERS.background,
        )
        self._shadows = _layer(
            SpriteCanvas(
                transform=transform,
                renderables=layers.shadows,
                animated=False,
            ),
            LAYER_FILTERS.shadows,
        )
        self._objects = _layer(
            SpriteCanvas(
                transform=transform,
                renderables=layers.objects,
                camera_id=WORLD_CAMERA,
            ),
            LAYER_FILTERS.objects,
        )

    def draw(self, layers: SceneLayers) -> None:
        self._background.set_renderables(layers.background)
        self._shadows.set_renderables(layers.shadows)
        self._objects.set_renderables(layers.objects)

    def draw_objects(self, layers: SceneLayers) -> None:
        """Redraw only the object layer."""
        self._objects.set_renderables(layers.objects)


def _layer(canvas: SpriteCanvas, css_filter: str) -> SpriteCanvas:
    """Lay a canvas over the whole window and show it through its filter."""
    canvas.classes("absolute inset-0")
    if css_filter:
        canvas.style(f"filter: {css_filter}")
    return canvas


def world_stack(
    environment: Environment,
    bounds: Bounds,
    *,
    selected_agent_id: str | None,
) -> WorldStack:
    return WorldStack(
        bounds,
        scene_layers(environment, [], selected_agent_id=selected_agent_id),
    )

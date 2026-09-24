"""The kitchen itself: three canvases sharing one camera."""

from __future__ import annotations

from simulator.entities import Bounds
from simulator.environment import Environment
from simulator.view import CanvasTransform, SceneLayers, SpriteCanvas, scene_layers
from simulator.view.renderable import CanvasFrame
from simulator.visualisation.theme import BACKDROP, SHADOW_OPACITY

WORLD_CAMERA = "world"
VIEWPORT_PADDING_CELLS = 3


class WorldStack:
    """World layers split by update frequency."""

    def __init__(self, bounds: Bounds, layers: SceneLayers) -> None:
        transform = CanvasTransform(
            mode="fit",
            grid_width=bounds.width,
            grid_height=bounds.height,
            padding_cells=VIEWPORT_PADDING_CELLS,
        )
        room = bounds.background_part()
        self._background = SpriteCanvas(
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
        ).classes("absolute inset-0")

        self._shadows = (
            SpriteCanvas(
                transform=transform,
                renderables=layers.shadows,
                animated=False,
            )
            .classes("absolute inset-0")
            .style(f"opacity: {SHADOW_OPACITY}")
        )

        self._objects = SpriteCanvas(
            transform=transform,
            renderables=layers.objects,
            camera_id=WORLD_CAMERA,
        ).classes("absolute inset-0")

    def draw(self, layers: SceneLayers) -> None:
        self._background.set_renderables(layers.background)
        self._shadows.set_renderables(layers.shadows)
        self._objects.set_renderables(layers.objects)

    def draw_objects(self, layers: SceneLayers) -> None:
        """Redraw only the object layer."""
        self._objects.set_renderables(layers.objects)


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

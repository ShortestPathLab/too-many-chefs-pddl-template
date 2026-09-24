from __future__ import annotations

from nicegui import ui


class WorldAnchor(ui.element, component="world_anchor.js"):  # pyright: ignore[reportGeneralTypeIssues, reportCallIssue]
    """Position child elements at a world location.

    Use it as a context manager:

        with WorldAnchor(track_id=agent.id, offset_cells_y=-1.0):
            ui.label("1")

    ``track_id`` follows a renderable's interpolated position. ``grid_x`` and
    ``grid_y`` provide the initial position, and ``offset_cells_*`` shift the
    child relative to the tracked renderable. Without ``track_id``, the anchor
    uses the fixed grid position. The browser resolves positions from the world
    canvas camera.
    """

    def __init__(
        self,
        *,
        grid_x: float = 0.0,
        grid_y: float = 0.0,
        track_id: str = "",
        offset_cells_x: float = 0.0,
        offset_cells_y: float = 0.0,
        camera_id: str = "world",
        origin_x: float = 0.5,
        origin_y: float = 1.0,
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> None:
        super().__init__()
        self._props["cameraId"] = camera_id
        self._props["trackId"] = track_id
        self._props["gridX"] = grid_x
        self._props["gridY"] = grid_y
        self._props["offsetCellsX"] = offset_cells_x
        self._props["offsetCellsY"] = offset_cells_y
        self._props["originX"] = origin_x
        self._props["originY"] = origin_y
        self._props["offsetX"] = offset_x
        self._props["offsetY"] = offset_y

    def move_to(self, grid_x: float, grid_y: float) -> None:
        """Move an anchor that is not tracking a renderable."""
        if (grid_x, grid_y) == (self._props["gridX"], self._props["gridY"]):
            return
        self._props["gridX"] = grid_x
        self._props["gridY"] = grid_y
        self.update()

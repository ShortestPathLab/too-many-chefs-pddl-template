from __future__ import annotations

from nicegui import ui

from simulator.environment import Environment
from simulator.view.music import soundtrack_gain, track_urls


class MusicBox(ui.element, component="music_box.js"):  # pyright: ignore[reportGeneralTypeIssues, reportCallIssue]
    """Play a level soundtrack in the browser."""

    def __init__(
        self,
        environment: Environment | None = None,
        *,
        volume: float = 1.0,
        muted: bool = False,
    ) -> None:
        super().__init__()
        self._props["tracks"] = track_urls(environment)
        self._props["gain"] = soundtrack_gain(environment)
        self._props["volume"] = volume
        self._props["muted"] = muted

    def set_muted(self, muted: bool) -> None:
        if muted == self._props["muted"]:
            return
        self._props["muted"] = muted
        self.update()

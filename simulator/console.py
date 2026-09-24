"""Render terminal status panels.

The helpers keep terminal output separate from the visualiser and can suppress
status panels for scripted runs.
"""

from __future__ import annotations

import sys
import threading
from collections.abc import Callable

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

# Fall back to ASCII borders when box glyphs are unavailable.
_console = Console(highlight=False, safe_box=True)


def _glyph(char: str, fallback: str = "") -> str:
    """Return ``char`` if stdout can encode it, otherwise ``fallback``."""
    encoding = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        char.encode(encoding)
    except UnicodeEncodeError, LookupError:
        return fallback
    return char


_quiet = False


def set_quiet(quiet: bool = True) -> None:
    """Enable or disable terminal status output."""
    global _quiet
    _quiet = quiet


def is_quiet() -> bool:
    return _quiet


def warn(message: str, title: str = "WARNING") -> None:
    if _quiet:
        return
    _console.print()
    _console.print(
        Panel(
            Text(message),
            title=f"[bold]{_glyph('⚠ ', '! ')}{title}[/bold]",
            title_align="left",
            border_style="red",
            padding=(1, 2),
            expand=False,
        )
    )
    _console.print()
    _console.file.flush()


class ViewerStatus:
    """Live terminal panel showing the visualiser connection state."""

    _DOT = _glyph("●", "*")

    def __init__(
        self,
        url: str,
        port: int,
        *,
        count_viewers: Callable[[], int],
        windowed: bool,
        reason: str | None = None,
        remote: bool = False,
        background: bool = False,
    ) -> None:
        self.url = url
        self.port = port
        self.count_viewers = count_viewers
        self.windowed = windowed
        self.reason = reason
        self.remote = remote
        #: Whether the visualiser runs beside something else that owns the
        #: terminal, which a redrawing panel would scramble.
        self.background = background

        self._seen_viewer = False
        self._live: Live | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _connection(self) -> tuple[str, str]:
        try:
            viewers = self.count_viewers()
        except Exception:  # noqa: BLE001 - a status line must never break a run
            viewers = 0

        if viewers:
            self._seen_viewer = True
            if self.windowed:
                return "green", "Connected"
            watching = "viewer" if viewers == 1 else "viewers"
            return "green", f"Connected, {viewers} {watching} watching"
        if self._seen_viewer:
            return "red", "Disconnected"
        if self.windowed:
            return "yellow", "Opening the window ..."
        return "yellow", "Waiting for you to open the link ..."

    def _render(self) -> Panel:
        colour, message = self._connection()

        body = Text()
        if self.windowed:
            body.append("Showing the kitchen in a window of its own.\n")
            body.append(
                "Closing that window does not stop the run.\n\n"
                if self.background
                else "Closing that window ends the run.\n\n",
                style="dim",
            )
            body.append("Also viewable at ", style="dim")
            body.append(f"{self.url}\n", style="cyan underline")
        else:
            body.append("The kitchen is running, but no window was opened.\n\n")
            body.append("Open this link in your browser to watch it:\n\n", style="bold")
            body.append(f"    {self.url}\n", style="bold cyan underline")
            if self.remote:
                body.append(
                    f"\nOn a different machine? Use this machine's address,"
                    f" port {self.port}.\n",
                    style="dim",
                )
            if self.reason:
                body.append(
                    f"\nWhy there is no window: {self.reason}\n", style="dim italic"
                )

        body.append("\n")
        body.append(f"{self._DOT} ", style=f"bold {colour}")
        body.append(message, style=colour)

        if self.windowed:
            title = _glyph("\U0001f373 ", "") + "TOO MANY CHEFS"
            border = "green"
        else:
            title = _glyph("\U0001f440 ", "") + "OPEN THIS LINK IN YOUR BROWSER"
            border = "yellow"
        return Panel(
            body,
            title=f"[bold]{title}[/bold]",
            title_align="left",
            border_style=border,
            padding=(1, 2),
            expand=False,
        )

    def start(self) -> None:
        if _quiet:
            return
        # Do not redraw into a pipe, a CI log, or another program's output.
        if self.background or not _console.is_terminal:
            _console.print()
            _console.print(self._render())
            _console.print()
            _console.file.flush()
            return

        _console.print()
        self._live = Live(
            self._render(), console=_console, refresh_per_second=8, transient=False
        )
        self._live.start()
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()

    def _poll(self) -> None:
        while not self._stop.wait(0.25):
            # ``stop`` may have cleared the live display.
            live = self._live
            if live is None:
                return
            live.update(self._render())

    def stop(self) -> None:
        """Stop the live display before process exit."""
        self._stop.set()
        if self._live is not None:
            self._live.update(self._render())
            self._live.stop()
            self._live = None

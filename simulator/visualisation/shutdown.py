"""Install signal handlers that stop the visualiser cleanly."""

from __future__ import annotations

import signal
from collections.abc import Callable
from types import FrameType
from typing import Any, cast

from nicegui import app, ui

# Type accepted by ``signal.signal`` and returned by ``signal.getsignal``.
SignalHandler = Callable[[int, FrameType | None], Any] | int | signal.Handlers | None


def install_shutdown_signal_handlers() -> dict[signal.Signals, SignalHandler]:
    signals = (signal.SIGINT, signal.SIGTERM)
    previous_signal_handlers = {signum: signal.getsignal(signum) for signum in signals}

    def shutdown_handler(signum: int, frame: FrameType | None) -> None:
        current_handler = previous_signal_handlers[signal.Signals(signum)]
        app.shutdown()
        # SIG_DFL and SIG_IGN come back as ints, so only a callable is a handler
        # worth chaining to.
        if callable(current_handler):
            chained = cast(Callable[[int, FrameType | None], Any], current_handler)
            chained(signum, frame)

    for signum in signals:
        signal.signal(signum, shutdown_handler)

    return previous_signal_handlers


def request_shutdown() -> None:
    """Bring the app down from inside the page, the way Ctrl-C does from outside."""

    # Attempt to close
    ui.run_javascript("window.close(); top.close();")
    # Backup: Redirect to a blank page if the browser blocks window.close()
    ui.run_javascript('window.location.href = "about:blank";')
    # Shutdown
    app.shutdown()


def restore_signal_handlers(
    previous_signal_handlers: dict[signal.Signals, SignalHandler],
) -> None:
    for signum, handler in previous_signal_handlers.items():
        signal.signal(signum, handler)

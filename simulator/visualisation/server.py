"""Serve the visualiser and manage its browser window."""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Callable
from http.client import HTTPException
from urllib.request import ProxyHandler, build_opener

from nicegui import Client, __version__, app, ui

from simulator import console
from simulator.assets import ASSETS_DIRECTORY
from simulator.visualisation import theme, window
from simulator.visualisation.shutdown import (
    install_shutdown_signal_handlers,
    restore_signal_handlers,
)

# Preferred port and scan range.
DEFAULT_PORT = 8080
PORT_SCAN = 64

# Default native window size.
WINDOW_SIZE = (1280, 800)

# Maximum wait for the server to answer HTTP requests and serve Vue.
SERVER_START_TIMEOUT = 20.0

ALIVE_ROUTE = "/_too-many-chefs/alive"

# Watchdog page that detects a stopped server and closes native windows.
_WATCHDOG_HTML = """<!--html-->
    <style>
      /* The watchdog handles permanent disconnects. */
      .nicegui-error-popup { display: none !important; }
    </style>
    <script>
    (() => {
      // A failed Vue download leaves NiceGUI's misleading ES-module fallback
      // visible. Retry once, only after an actual script loading failure.
      const retryKey = 'too-many-chefs-startup-retry:' + location.pathname;
      let scriptFailed = false;
      window.addEventListener('error', (event) => {
        if (event.target instanceof HTMLScriptElement) scriptFailed = true;
      }, true);
      window.addEventListener('load', async () => {
        try {
          if (!document.getElementById('esm-fallback')) {
            sessionStorage.removeItem(retryKey);
            return;
          }
          if (!scriptFailed || !HTMLScriptElement.supports?.('importmap')
              || sessionStorage.getItem(retryKey)) return;
          const answer = await fetch('ALIVE_ROUTE', {cache: 'no-store'});
          if (!answer.ok) return;
          sessionStorage.setItem(retryKey, '1');
          location.reload();
        } catch (error) {
          // Leave the original error visible if storage or the server fails.
        }
      }, {once: true});

      let misses = 0;
      const ended = () => {
        window.close();
        document.title = 'Service ended';
        document.body.innerHTML =
          '<div style="display:flex;align-items:center;justify-content:center;'
          + 'height:100vh;font-family:ui-monospace,monospace;font-size:18px;'
          + 'color:#e8e2d0;background:#26221c;text-align:center">'
          + 'The run has ended. You can close this window.</div>';
      };
      const timer = setInterval(async () => {
        try {
          const answer = await fetch('ALIVE_ROUTE', {cache: 'no-store'});
          misses = answer.ok ? 0 : misses + 1;
        } catch (error) {
          misses += 1;
        }
        // Require several misses so one failed request does not end the page.
        if (misses >= 3) { clearInterval(timer); ended(); }
      }, 1000);
    })();
    </script>
""".replace("ALIVE_ROUTE", ALIVE_ROUTE)

_alive_route_registered = False


def serve(
    build_root: Callable[[], None],
    *,
    title: str,
    preloads: str = "",
    open_window: bool = True,
    background: bool = False,
) -> None:
    """Run the visualiser until the window closes or the process stops.

    A ``background`` visualiser runs on a thread of its own beside something
    that owns the process, such as a training loop. It leaves signals to the
    main thread, opens its window in a separate process, keeps serving when
    that window closes, and prints its link once instead of redrawing a status
    panel over the training log.
    """
    previous_signal_handlers = (
        None if background else install_shutdown_signal_handlers()
    )

    # WSL forwards Windows localhost through a wildcard-bound socket.
    host = "0.0.0.0" if window.is_wsl() else "127.0.0.1"
    port = _claim_port(host)
    url = _local_url(host, port)

    # ``reason`` is set only when a requested native window is unavailable.
    reason: str | None = None
    native = False
    if open_window and not window.is_wsl() and not background:
        reason = window.native_window_reason()
        native = reason is None

    # Disable caching so edited sprite sheets reload during development.
    app.add_static_files("/assets", str(ASSETS_DIRECTORY), max_cache_age=0)
    ui.add_head_html(theme.head_html(preloads=preloads) + _WATCHDOG_HTML, shared=True)
    _register_alive_route()

    status: console.ViewerStatus | None = None

    def announce() -> None:
        """Wait for the server, then open or announce the visualiser."""
        nonlocal status
        if not _wait_until_ready(port):
            console.warn(
                f"The visualiser did not become ready on port {port}"
                f" within {SERVER_START_TIMEOUT:.0f} seconds.",
                title="NOTHING IS SERVING",
            )
            return

        windowed, why_not = native, reason
        if open_window and window.is_wsl():
            opened, why_not = window.open_wsl_window(url, size=WINDOW_SIZE)
            windowed = opened is not None
            if opened is not None and not background:
                threading.Thread(
                    target=_shutdown_when_window_closes,
                    args=(opened,),
                    daemon=True,
                ).start()
        elif open_window and background:
            opened, why_not = window.open_native_window(
                url,
                title=title,
                size=WINDOW_SIZE,
                alive_url=f"http://127.0.0.1:{port}{ALIVE_ROUTE}",
            )
            windowed = opened is not None

        status = console.ViewerStatus(
            url,
            port,
            count_viewers=count_viewers,
            windowed=windowed,
            reason=None if windowed else why_not,
            remote=host == "0.0.0.0",
            background=background,
        )
        status.start()

    app.on_startup(lambda: threading.Thread(target=announce, daemon=True).start())

    try:
        ui.run(
            root=build_root,
            title=title,
            host=host,
            port=port,
            show=False,
            reload=False,
            # The status panel provides the URL.
            show_welcome_message=False,
            native=native,
            window_size=WINDOW_SIZE if native else None,
        )
    except Exception as error:  # noqa: BLE001 - a broken page must still tidy up
        console.warn(str(error), title="THE VISUALISER STOPPED")
    finally:
        if status is not None:
            status.stop()
        if previous_signal_handlers is not None:
            restore_signal_handlers(previous_signal_handlers)


def count_viewers() -> int:
    """Return how many browsers hold a live connection to the visualiser.

    A kitchen on another thread asks while the server adds and removes
    clients, so take a copy before looking through them.
    """
    clients = list(Client.instances.values())
    return sum(1 for client in clients if client.has_socket_connection)


def _local_url(host: str, port: int) -> str:
    """Return a browser URL for a bound host and port.

    Replace wildcard bind addresses with localhost.
    """
    return f"http://{'127.0.0.1' if host in ('0.0.0.0', '::') else host}:{port}/"


def _claim_port(host: str) -> int:
    """Return the first available port in the scan range.

    Probe before starting uvicorn so the announced URL belongs to this run.
    """
    for port in range(DEFAULT_PORT, DEFAULT_PORT + PORT_SCAN):
        probe = socket.socket()
        try:
            # Match uvicorn's bind behavior.
            probe.bind((host, port))
        except OSError:
            continue
        finally:
            probe.close()
        return port
    raise OSError(
        f"No free port between {DEFAULT_PORT} and {DEFAULT_PORT + PORT_SCAN - 1}."
    )


def _wait_until_ready(port: int) -> bool:
    """Check HTTP serving without building a page or starting its timers."""
    # Local readiness must not depend on the user's HTTP proxy configuration.
    opener = build_opener(ProxyHandler({}))
    paths = (ALIVE_ROUTE, f"/_nicegui/{__version__}/static/vue.esm-browser.prod.js")
    deadline = time.monotonic() + SERVER_START_TIMEOUT
    while time.monotonic() < deadline:
        try:
            for path in paths:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                with opener.open(
                    f"http://127.0.0.1:{port}{path}", timeout=min(0.5, remaining)
                ) as response:
                    if response.status != 200 or not response.read():
                        raise OSError("The visualiser is not ready")
            return True
        except OSError, HTTPException:
            time.sleep(0.1)
    return False


def _shutdown_when_window_closes(opened: object) -> None:
    """End the run when the opened window closes."""
    waited = getattr(opened, "wait", None)
    if waited is not None:
        waited()
    app.shutdown()


def _register_alive_route() -> None:
    """Register the route used by the watchdog page."""
    global _alive_route_registered
    if _alive_route_registered:
        return
    _alive_route_registered = True

    @app.get(ALIVE_ROUTE)
    def alive() -> dict[str, bool]:
        return {"alive": True}

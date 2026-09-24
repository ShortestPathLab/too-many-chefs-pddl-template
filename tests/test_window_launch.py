"""Test visualiser window selection."""

from __future__ import annotations

import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Self
from unittest.mock import patch

import pytest

from simulator.visualisation import server, window


def test_readiness_retries_until_http_and_vue_are_available() -> None:
    requests: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            requests.append(self.path)
            # Listening is not enough: the first HTTP request fails, then Vue
            # is unavailable once even though the health endpoint responds.
            unavailable = len(requests) == 1 or (
                "vue.esm" in self.path and requests.count(self.path) == 1
            )
            self.send_response(503 if unavailable else 200)
            self.end_headers()
            self.wfile.write(b"unavailable" if unavailable else b"ready")

        def log_message(self, format: str, *args: object) -> None:
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            assert server._wait_until_ready(httpd.server_port)
        finally:
            httpd.shutdown()
            thread.join()

    assert requests.count(server.ALIVE_ROUTE) == 3
    assert sum("vue.esm" in path for path in requests) == 2
    assert "/" not in requests  # Probing must not create a simulation client.


def test_readiness_times_out_when_only_the_socket_is_listening() -> None:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        with patch.object(server, "SERVER_START_TIMEOUT", 0.1):
            assert not server._wait_until_ready(listener.getsockname()[1])


def test_the_wildcard_address_is_never_handed_out_as_a_destination() -> None:
    assert server._local_url("0.0.0.0", 8080) == "http://127.0.0.1:8080/"
    assert server._local_url("::", 8080) == "http://127.0.0.1:8080/"
    assert server._local_url("127.0.0.1", 9001) == "http://127.0.0.1:9001/"


def test_a_busy_port_is_skipped_rather_than_reported() -> None:
    taken = socket.socket()
    taken.bind(("127.0.0.1", server.DEFAULT_PORT))
    try:
        assert server._claim_port("127.0.0.1") > server.DEFAULT_PORT
    finally:
        taken.close()


def test_running_out_of_ports_is_an_error_and_not_a_wrong_answer() -> None:
    held = []
    try:
        for port in range(server.DEFAULT_PORT, server.DEFAULT_PORT + server.PORT_SCAN):
            probe = socket.socket()
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                probe.close()
                continue
            held.append(probe)

        with pytest.raises(OSError):
            server._claim_port("127.0.0.1")
    finally:
        for probe in held:
            probe.close()


def test_wsl_is_recognised_from_the_kernel_release_alone() -> None:
    release = "5.15.0-microsoft-standard-WSL2"
    with (
        patch.dict("os.environ", {}, clear=True),
        patch("builtins.open", _reads(release)),
    ):
        assert window.is_wsl()


def test_an_ordinary_linux_kernel_is_not_wsl() -> None:
    with (
        patch.dict("os.environ", {}, clear=True),
        patch("builtins.open", _reads("6.6.0-generic")),
    ):
        assert not window.is_wsl()


def test_a_missing_pywebview_is_reported_rather_than_exited_on() -> None:
    with patch("importlib.util.find_spec", return_value=None):
        reason = window.native_window_reason()

    assert reason is not None
    assert "pywebview" in reason


def _reads(text: str):
    """Stub ``open`` and return the supplied text."""

    class Handle:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def read(self) -> str:
            return text

    return lambda *_args, **_kwargs: Handle()

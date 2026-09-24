"""How a match host and its seats talk: one JSON object per line on a socket.

The host sends ``start`` before each game, a ``tick`` with the whole kitchen
every timestep, ``end`` after each game, and ``bye`` when the set is over. A
seat sends ``hello`` once its controller's code has imported, ``ready`` once
the controller for a game is built, ``actions`` for a tick, and ``error`` when
the controller raised, after which it stops.

Everything a seat sends is checked by the host, which never trusts it: the
seat runs a student's code.
"""

from __future__ import annotations

import json
import select
import socket
import time
from typing import Any

#: Longest message either side accepts. A kitchen is a few kilobytes.
MAX_MESSAGE_BYTES = 4 * 1024 * 1024

Message = dict[str, Any]


class ProtocolError(Exception):
    """The other side sent something that is not a message."""


class ConnectionClosed(Exception):
    """The other side hung up."""


class Connection:
    """One end of a host-seat socket, reading whole messages."""

    def __init__(self, sock: socket.socket) -> None:
        self.socket = sock
        self._buffer = bytearray()
        self._closed = False

    def fileno(self) -> int:
        return self.socket.fileno()

    @property
    def closed(self) -> bool:
        return self._closed

    def send(self, message: Message) -> None:
        self.send_bytes(encode(message))

    def send_bytes(self, data: bytes) -> None:
        """Send an already encoded message, so one kitchen encodes once."""
        try:
            self.socket.sendall(data)
        except OSError as error:
            self._closed = True
            raise ConnectionClosed(str(error)) from error

    def read_available(self) -> list[Message]:
        """Read what has arrived without waiting, and return whole messages.

        Raises ``ConnectionClosed`` once the other side has hung up and every
        message it sent before that has been returned.
        """
        while not self._closed:
            try:
                readable, _, _ = select.select([self.socket], [], [], 0)
                if not readable:
                    break
                chunk = self.socket.recv(65536)
            except OSError:
                # A side that dies with messages unread resets the connection
                # instead of closing it. Either way it has gone.
                chunk = b""
            if not chunk:
                self._closed = True
                break
            self._buffer += chunk
            if len(self._buffer) > MAX_MESSAGE_BYTES and b"\n" not in self._buffer:
                raise ProtocolError("a message was longer than the limit")
        messages = self._take_messages()
        if not messages and self._closed:
            raise ConnectionClosed("the other side hung up")
        return messages

    def receive(self, timeout: float | None) -> list[Message]:
        """Wait up to ``timeout`` seconds for at least one whole message.

        Returns every whole message available, or an empty list on timeout.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            messages = self.read_available()
            if messages:
                return messages
            remaining = None if deadline is None else deadline - time.monotonic()
            if remaining is not None and remaining <= 0:
                return []
            select.select([self.socket], [], [], remaining)

    def close(self) -> None:
        self._closed = True
        try:
            self.socket.close()
        except OSError:
            pass

    def _take_messages(self) -> list[Message]:
        messages: list[Message] = []
        while (end := self._buffer.find(b"\n")) >= 0:
            line = bytes(self._buffer[:end])
            del self._buffer[: end + 1]
            if not line.strip():
                continue
            if len(line) > MAX_MESSAGE_BYTES:
                raise ProtocolError("a message was longer than the limit")
            try:
                message = json.loads(line)
            except ValueError as error:
                raise ProtocolError(f"a message was not JSON: {error}") from None
            if not isinstance(message, dict) or not isinstance(
                message.get("type"), str
            ):
                raise ProtocolError("a message had no type")
            messages.append(message)
        return messages


def encode(message: Message) -> bytes:
    return json.dumps(message, separators=(",", ":")).encode() + b"\n"


def connect(path: str, *, wait_seconds: float = 30.0) -> Connection:
    """Connect to a host's socket, waiting for it to appear."""
    deadline = time.monotonic() + wait_seconds
    while True:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(path)
            return Connection(sock)
        except FileNotFoundError, ConnectionRefusedError:
            sock.close()
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.05)


def listen(path: str) -> socket.socket:
    """Open a socket for one seat to connect to."""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(path)
    sock.listen(1)
    return sock

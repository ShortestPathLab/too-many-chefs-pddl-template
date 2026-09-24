"""Play a 2v2 set on this machine, each seat in its own process.

Seats are named A1, A2, B1 and B2 in the order ``--seat`` gives them; A1 and
A2 are one team and B1 and B2 the other. Each seat is ``example`` or a
submission: a checkout of the starter code, or a ``controllers/open/submission``
folder, so several people's controllers can play on one machine.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import typer

from simulator.configuration import Configuration
from simulator.match import (
    STARTUP_SECONDS,
    Connection,
    Seat,
    SetReport,
    Side,
    listen,
    play_set,
)

ROOT = Path(__file__).resolve().parent.parent
SEAT_NAMES = ("A1", "A2", "B1", "B2")
SUBMISSION = Path("controllers/open/submission")


@dataclass(frozen=True)
class SeatSource:
    """What one ``--seat`` plays."""

    label: str
    #: The submission folder, or ``None`` for the example.
    folder: Path | None


def parse_seat(text: str) -> SeatSource:
    """Read a ``--seat``: ``example``, a checkout, or a submission folder."""
    if text == "example":
        return SeatSource(label=text, folder=None)
    path = Path(text).expanduser()
    for candidate in (path / SUBMISSION, path):
        if (candidate / "controller.py").is_file():
            return SeatSource(label=text, folder=candidate.resolve())
    raise typer.BadParameter(
        f"{text} has no {SUBMISSION / 'controller.py'}, and is not a submission folder",
        param_hint="--seat",
    )


def play_local_set(
    configuration: Configuration,
    sources: list[SeatSource],
    *,
    level: str,
    games: int,
    tick_seconds: float,
    max_timesteps: int,
    replay_dir: Path | None,
    echo: Callable[[str], None] | None = None,
) -> SetReport:
    """Start a process per seat and play a set between them."""
    if len(sources) != len(SEAT_NAMES):
        raise ValueError(f"a set needs {len(SEAT_NAMES)} seats")
    with tempfile.TemporaryDirectory(prefix="cook-match-") as directory:
        listeners: list[socket.socket] = []
        processes: list[subprocess.Popen[str]] = []
        seats: list[Seat] = []
        try:
            for name, source in zip(SEAT_NAMES, sources, strict=True):
                path = str(Path(directory) / f"{name}.sock")
                listeners.append(listen(path))
                command = [
                    sys.executable,
                    "-m",
                    "controllers.open.seat",
                    "--connect",
                    path,
                ]
                if source.folder is None:
                    command.append("--example")
                else:
                    command += ["--submission", str(source.folder)]
                process = subprocess.Popen(
                    command,
                    cwd=ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                processes.append(process)
                _forward_output(process, name, echo)
            for name, listener in zip(SEAT_NAMES, listeners, strict=True):
                side: Side = "a" if name.startswith("A") else "b"
                seats.append(Seat(name=name, side=side, connection=_accept(listener)))
            return play_set(
                configuration,
                seats,
                level=level,
                games=games,
                tick_seconds=tick_seconds,
                max_timesteps=max_timesteps,
                replay_dir=replay_dir,
            )
        finally:
            for seat in seats:
                seat.connection.close()
            for process in processes:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            for listener in listeners:
                listener.close()


def summary(report: SetReport, sources: list[SeatSource]) -> list[str]:
    """Describe a set in a few lines for the terminal."""
    labels = dict(zip(SEAT_NAMES, (source.label for source in sources), strict=True))
    lines = [
        f"Team A: {labels['A1']} (A1) and {labels['A2']} (A2)",
        f"Team B: {labels['B1']} (B1) and {labels['B2']} (B2)",
    ]
    for number, game in enumerate(report.games, start=1):
        lines.append(
            f"Game {number}: A {game.score['a']}, B {game.score['b']}"
            f" (A played {game.teams['a']}, {game.timesteps} timesteps)"
        )
    if report.winner is None:
        lines.append(f"No result: {', '.join(report.crashed)} crashed.")
    elif report.winner == "draw":
        lines.append(f"Draw, {report.score['a']} each.")
    else:
        lines.append(
            f"Team {report.winner.upper()} wins, {report.score['a']} to {report.score['b']}."
        )
    for seat in report.seats:
        if seat.missed_ticks:
            lines.append(
                f"{seat.name} answered too late for {seat.missed_ticks} of {seat.ticks} ticks."
            )
    return lines


def _accept(listener: socket.socket) -> Connection:
    """Wait for a seat to connect. One that never does has crashed."""
    listener.settimeout(STARTUP_SECONDS)
    try:
        sock, _ = listener.accept()
    except TimeoutError:
        sock, other = socket.socketpair()
        other.close()
    sock.settimeout(None)
    return Connection(sock)


def _forward_output(
    process: subprocess.Popen[str], name: str, echo: Callable[[str], None] | None
) -> None:
    """Pass what a seat prints on, marked with its name."""

    def forward() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            if echo is not None:
                echo(f"[{name}] {line.rstrip()}")

    threading.Thread(target=forward, daemon=True).start()

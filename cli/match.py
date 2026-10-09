"""Play a set on this machine, each seat in its own process.

A set needs one seat for each chef on the kitchen's teams, and ``--seat``
fills them a team at a time. With teams of two, the first two seats are team
A, named A1 and A2, the next two are team B, and so on.

Each seat is ``example`` or a submission: a folder whose ``controller.py``
defines ``OpenController``, or a checkout of this repository, which plays the
one in ``controllers/open/submission``. So several people's controllers can
play on one machine.
"""

from __future__ import annotations

import random
import socket
import string
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import typer

from cli.teams import with_teams
from simulator.configuration import Configuration, load_configuration
from simulator.match import (
    STARTUP_SECONDS,
    Connection,
    MatchSetupError,
    Seat,
    SetReport,
    Side,
    listen,
    play_set,
    teams_of,
)

ROOT = Path(__file__).resolve().parent.parent
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


def seats_for(configuration: Configuration) -> list[tuple[str, Side]]:
    """Name the seats a set in this kitchen needs, with their sides, in order."""
    rosters = teams_of(configuration)
    size = len(next(iter(rosters.values())))
    return [
        (f"{side.upper()}{number}", side)
        for side in string.ascii_lowercase[: len(rosters)]
        for number in range(1, size + 1)
    ]


def choose_kitchen(
    level: Path, *, teams: list[str], seats: int
) -> tuple[Path, Configuration]:
    """Return the kitchen ``level``, or one drawn from the folder ``level``.

    ``teams`` are ``--team`` options, which replace each kitchen's own teams.
    A kitchen drawn from a folder is one of those with a chef for every seat.
    """
    if not level.is_dir():
        configuration, chefs = _kitchen(level, teams)
        if chefs != seats:
            raise typer.BadParameter(
                f"{level.name} has {chefs} chefs on its teams, so give {chefs}"
                f" seats, not {seats}",
                param_hint="--seat",
            )
        return level, configuration
    fits: dict[Path, Configuration] = {}
    sizes: set[int] = set()
    for path in sorted(level.glob("*.yaml")):
        try:
            configuration, chefs = _kitchen(path, teams)
        except typer.BadParameter:
            continue
        sizes.add(chefs)
        if chefs == seats:
            fits[path] = configuration
    if not fits:
        if not sizes:
            raise typer.BadParameter(
                f"{level} has no kitchens with two or more teams of the same size"
                + (" once --team is applied" if teams else ""),
                param_hint="--team" if teams else "--level",
            )
        raise typer.BadParameter(
            f"the kitchens in {level} take {' or '.join(map(str, sorted(sizes)))}"
            f" seats, not {seats}",
            param_hint="--seat",
        )
    path = random.choice(list(fits))
    return path, fits[path]


def _kitchen(path: Path, teams: list[str]) -> tuple[Configuration, int]:
    """Load a kitchen with ``--team`` applied, and count the chefs on its teams."""
    configuration = with_teams(load_configuration(path), teams=teams)
    try:
        rosters = teams_of(configuration)
    except MatchSetupError as error:
        raise typer.BadParameter(
            f"{path.name}: {error}", param_hint="--team" if teams else "--level"
        ) from None
    return configuration, sum(len(chefs) for chefs in rosters.values())


def play_local_set(
    configuration: Configuration,
    sources: list[SeatSource],
    *,
    level: str,
    games: int | None,
    tick_seconds: float,
    max_timesteps: int,
    replay_dir: Path | None,
    echo: Callable[[str], None] | None = None,
) -> SetReport:
    """Start a process per seat and play a set between them.

    Left out, ``games`` is one game for each of the kitchen's teams.
    """
    places = seats_for(configuration)
    if len(sources) != len(places):
        raise ValueError(
            f"a set in this kitchen needs {len(places)} seats, not {len(sources)}"
        )
    with tempfile.TemporaryDirectory(prefix="cook-match-") as directory:
        listeners: list[socket.socket] = []
        processes: list[subprocess.Popen[str]] = []
        seats: list[Seat] = []
        try:
            for (name, _), source in zip(places, sources, strict=True):
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
            for (name, side), listener in zip(places, listeners, strict=True):
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
    sides: dict[Side, list[str]] = {}
    for seat, source in zip(report.seats, sources, strict=True):
        sides.setdefault(seat.side, []).append(f"{source.label} ({seat.name})")
    lines = [f"Team {side.upper()}: {_listed(seats)}" for side, seats in sides.items()]
    for number, game in enumerate(report.games, start=1):
        scores = ", ".join(f"{side.upper()} {game.score[side]}" for side in sides)
        played = ", ".join(
            f"{side.upper()} played {game.teams[side]}" for side in sides
        )
        lines.append(f"Game {number}: {scores} ({played}, {game.timesteps} timesteps)")
    ranked = sorted(report.score.values(), reverse=True)
    if report.winner is None:
        lines.append(f"No result: {', '.join(report.crashed)} crashed.")
    elif report.winner == "draw":
        tied = [side.upper() for side in sides if report.score[side] == ranked[0]]
        lines.append(f"Teams {_listed(tied)} draw, {ranked[0]} each.")
    else:
        lines.append(
            f"Team {report.winner.upper()} wins, {' to '.join(map(str, ranked))}."
        )
    for seat in report.seats:
        if seat.missed_ticks:
            lines.append(
                f"{seat.name} answered too late for {seat.missed_ticks} of {seat.ticks} ticks."
            )
    return lines


def _listed(items: list[str]) -> str:
    """Join ``items`` as a phrase: ``a``, ``a and b``, or ``a, b and c``."""
    if len(items) < 2:
        return "".join(items)
    return f"{', '.join(items[:-1])} and {items[-1]}"


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

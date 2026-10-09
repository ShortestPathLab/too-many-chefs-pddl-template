"""Play a set of games between teams of seats, each seat its own controller.

The host owns the kitchen. Every timestep it sends each seat the whole
kitchen, waits up to ``tick_seconds`` for that seat's actions, checks they are
for the seat's own chef, and steps the kitchen with whatever arrived. A seat
that answers late misses the tick, and its chef stands still. A seat that
raises, hangs up or breaks the rules has crashed, and the set stops there.

A set is ``games`` games in one kitchen, with one side of seats for each of
the level's teams. In the first game the first side plays the level's first
team, the second side its second team, and so on. After each game every side
moves on to the next team, the last side wrapping round to the first, so any
advantage of one place in the kitchen evens out. The side with the highest
total score wins the set.
"""

from __future__ import annotations

import selectors
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import Field, TypeAdapter, ValidationError

from simulator.configuration import Configuration, load
from simulator.entities import badge_order, team_rosters
from simulator.models import SimulatorModel
from simulator.mutations import Mutation, MutationModel
from simulator.recording import save_recording
from simulator.run.end_conditions import EndConditions
from simulator.run.episode import Episode
from simulator.run.result import RunError

from .protocol import Connection, ConnectionClosed, Message, ProtocolError, encode

#: How long each seat has to answer a tick.
TICK_SECONDS = 0.2
#: Timesteps in a game.
MAX_TIMESTEPS = 300
#: Games in a set of the competition, one for each of its two teams.
GAMES = 2
#: How long a seat has to import its code, and to build its controller.
STARTUP_SECONDS = 30.0
#: More actions than this in one tick is not a controller driving one chef.
MAX_ACTIONS_PER_TICK = 16

#: The name of a side, the seats that play together as one team.
Side = str

_ACTIONS = TypeAdapter(list[MutationModel])


class MatchSetupError(ValueError):
    """The level cannot host a match. Nobody playing is to blame."""


@dataclass
class Seat:
    """One controller in a set, and the connection to it."""

    name: str
    side: Side
    connection: Connection


class SeatReport(SimulatorModel):
    """How one seat got on."""

    name: str
    side: Side
    #: The chef it drove, one per game played.
    chefs: list[str] = Field(default_factory=list)
    ticks: int = 0
    #: Ticks it answered too late for, when its chef stood still.
    missed_ticks: int = 0
    #: Why it crashed, when it did.
    error: RunError | None = None


class GameReport(SimulatorModel):
    """One game of a set."""

    level: str
    #: The level team each side played.
    teams: dict[Side, str]
    score: dict[Side, int]
    score_by_seat: dict[str, int]
    timesteps: int
    #: Where the replay was saved, when it was.
    replay: str | None = None


class SetReport(SimulatorModel):
    """A whole set: its games, the totals, and each seat."""

    games: list[GameReport]
    score: dict[Side, int]
    #: The side with the highest total, or ``"draw"`` when sides tie for it.
    #: ``None`` when a seat crashed, since the set then has no result.
    winner: Side | None
    seats: list[SeatReport]

    @property
    def crashed(self) -> list[str]:
        return [seat.name for seat in self.seats if seat.error is not None]


OnStep = Callable[[int, Episode], None]


def play_set(
    configuration: Configuration,
    seats: Sequence[Seat],
    *,
    level: str = "",
    games: int | None = None,
    tick_seconds: float = TICK_SECONDS,
    max_timesteps: int = MAX_TIMESTEPS,
    startup_seconds: float = STARTUP_SECONDS,
    replay_dir: Path | None = None,
    on_step: OnStep | None = None,
) -> SetReport:
    """Play ``games`` games between sides of seats, one side for each team.

    Seats with the same ``side`` play together. The sides take the level's
    teams in the order their first seats come, and each needs one seat for
    every chef on a team. Left out, ``games`` is one game for each team, so
    every side plays from every team's place.
    """
    rosters = teams_of(configuration)
    sides = _sides(seats, rosters)
    room = _Room(seats)
    played: list[GameReport] = []
    try:
        room.await_all("hello", startup_seconds)
        for game in range(len(rosters) if games is None else games):
            if room.crashed:
                break
            played.append(
                _play_game(
                    configuration,
                    room,
                    rosters=rosters,
                    sides=sides,
                    game=game,
                    level=level,
                    tick_seconds=tick_seconds,
                    max_timesteps=max_timesteps,
                    startup_seconds=startup_seconds,
                    replay_dir=replay_dir,
                    on_step=on_step,
                )
            )
    finally:
        room.broadcast({"type": "bye"})
    score: dict[Side, int] = {
        side: sum(game.score[side] for game in played) for side in sides
    }
    winner: Side | None = None
    if not room.crashed:
        best = max(score.values())
        leaders = [side for side in sides if score[side] == best]
        winner = leaders[0] if len(leaders) == 1 else "draw"
    return SetReport(
        games=played,
        score=score,
        winner=winner,
        seats=list(room.reports.values()),
    )


def teams_of(configuration: Configuration) -> dict[str, list[str]]:
    """Return the level's team rosters, or raise ``MatchSetupError``.

    A match needs two or more teams with the same number of chefs, since the
    sides change teams between games.
    """
    rosters = team_rosters(badge_order(load(configuration)))
    if len(rosters) < 2 or len({len(chefs) for chefs in rosters.values()}) != 1:
        found = ", ".join(f"{team}: {len(chefs)}" for team, chefs in rosters.items())
        raise MatchSetupError(
            "a match needs two or more teams with the same number of chefs,"
            f" and this kitchen has {found or 'none'}"
        )
    return rosters


def _sides(
    seats: Sequence[Seat], rosters: dict[str, list[str]]
) -> dict[Side, list[Seat]]:
    """Group the seats by side, one side of the right size for each team."""
    sides: dict[Side, list[Seat]] = {}
    for seat in seats:
        sides.setdefault(seat.side, []).append(seat)
    size = len(next(iter(rosters.values())))
    if len(sides) != len(rosters) or any(len(side) != size for side in sides.values()):
        raise ValueError(
            f"a set in this kitchen needs {len(rosters)} sides of {size} seats each"
        )
    return sides


def _play_game(
    configuration: Configuration,
    room: _Room,
    *,
    rosters: dict[str, list[str]],
    sides: dict[Side, list[Seat]],
    game: int,
    level: str,
    tick_seconds: float,
    max_timesteps: int,
    startup_seconds: float,
    replay_dir: Path | None,
    on_step: OnStep | None,
) -> GameReport:
    names = list(rosters)
    teams: dict[Side, str] = {
        side: names[(index + game) % len(names)] for index, side in enumerate(sides)
    }
    chef_of: dict[str, str] = {}
    for side, side_seats in sides.items():
        for seat, chef in zip(side_seats, rosters[teams[side]], strict=True):
            chef_of[seat.name] = chef
            room.reports[seat.name].chefs.append(chef)

    episode = Episode(load(configuration))
    for seat in room.live():
        room.send(
            seat,
            {
                "type": "start",
                "game": game,
                "chef": chef_of[seat.name],
                "team": teams[seat.side],
                "side": seat.side,
                "level": level,
                "tick_seconds": tick_seconds,
                "max_timesteps": max_timesteps,
            },
        )
    room.await_all("ready", startup_seconds, game=game)

    conditions = EndConditions(
        max_timesteps=max_timesteps,
        end_on_orders_delivered=True,
        end_on_budget_exhausted=False,
    )
    while not room.crashed and episode.end_reason(conditions) is None:
        environment = episode.environment
        tick = encode(
            {
                "type": "tick",
                "game": game,
                "timestep": environment.timestep,
                "environment": environment.to_dict(),
            }
        )
        actions = room.collect(
            tick,
            game=game,
            timestep=environment.timestep,
            timeout=tick_seconds,
            chef_of=chef_of,
        )
        if room.crashed:
            break
        # When two chefs reach for the same thing, the first action wins, so
        # the seats take turns to go first.
        order = _turn_order(list(sides.values()), environment.timestep)
        episode.advance(
            [action for seat in order for action in actions.get(seat.name, [])]
        )
        if on_step is not None:
            on_step(game, episode)
    room.broadcast({"type": "end", "game": game})

    result = episode.result(episode.end_reason(conditions) or "error")
    replay = None
    if replay_dir is not None:
        replay = str(
            save_recording(episode.recording, replay_dir / f"game-{game + 1}.yaml.gz")
        )
    return GameReport(
        level=level,
        teams=teams,
        score={side: result.score_by_team.get(teams[side], 0) for side in sides},
        score_by_seat={
            name: result.score_by_agent.get(chef, 0) for name, chef in chef_of.items()
        },
        timesteps=result.timesteps,
        replay=replay,
    )


def _turn_order[T](sides: list[list[T]], timestep: int) -> list[T]:
    """Return the seats in the order their actions apply at ``timestep``.

    The sides take turns to go first, and on every other timestep each side's
    seats go in reverse. With two sides the whole order flips each timestep.
    """
    first = timestep % len(sides)
    turn = sides[first:] + sides[:first]
    if timestep % 2:
        turn = [side[::-1] for side in turn]
    return [seat for side in turn for seat in side]


class _Room:
    """The seats of one set, and what each has sent."""

    def __init__(self, seats: Sequence[Seat]) -> None:
        self.seats = list(seats)
        self.reports = {
            seat.name: SeatReport(name=seat.name, side=seat.side) for seat in self.seats
        }
        self._selector = selectors.DefaultSelector()
        self._by_fd: dict[int, Seat] = {}
        for seat in self.seats:
            self._selector.register(seat.connection.socket, selectors.EVENT_READ)
            self._by_fd[seat.connection.fileno()] = seat

    @property
    def crashed(self) -> list[str]:
        return [
            name for name, report in self.reports.items() if report.error is not None
        ]

    def live(self) -> list[Seat]:
        return [seat for seat in self.seats if self.reports[seat.name].error is None]

    def crash(self, seat: Seat, error: RunError) -> None:
        report = self.reports[seat.name]
        if report.error is not None:
            return
        self.reports[seat.name] = report.copy_with(error=error)
        try:
            self._selector.unregister(seat.connection.socket)
        except KeyError, ValueError:
            pass
        seat.connection.close()

    def send(self, seat: Seat, message: Message) -> None:
        self.send_bytes(seat, encode(message))

    def send_bytes(self, seat: Seat, data: bytes) -> None:
        try:
            seat.connection.send_bytes(data)
        except ConnectionClosed:
            self.crash(seat, _exited())

    def broadcast(self, message: Message) -> None:
        for seat in self.live():
            self.send(seat, message)

    def await_all(self, kind: str, timeout: float, *, game: int | None = None) -> None:
        """Wait for every live seat to send ``kind``, crashing any that do not."""
        waiting = {seat.name for seat in self.live()}
        deadline = time.monotonic() + timeout
        while waiting:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                for seat in self.live():
                    if seat.name in waiting:
                        self.crash(seat, _too_slow_to_start(timeout))
                return
            for seat, message in self._receive(remaining):
                if message["type"] == kind and (
                    game is None or message.get("game") == game
                ):
                    waiting.discard(seat.name)
                elif message["type"] != "actions":
                    # Actions here answer a tick of a game that has ended.
                    self._unexpected(seat, message)
            waiting &= {seat.name for seat in self.live()}

    def collect(
        self,
        tick: bytes,
        *,
        game: int,
        timestep: int,
        timeout: float,
        chef_of: dict[str, str],
    ) -> dict[str, list[Mutation]]:
        """Send a tick to every live seat and gather the answers in time."""
        deadline = time.monotonic() + timeout
        for seat in self.live():
            self.send_bytes(seat, tick)
        waiting = {seat.name for seat in self.live()}
        actions: dict[str, list[Mutation]] = {}
        while waiting:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            for seat, message in self._receive(remaining):
                if message["type"] == "actions":
                    if (
                        message.get("game") != game
                        or message.get("timestep") != timestep
                    ):
                        # An answer to a tick that has already passed.
                        continue
                    if seat.name not in waiting:
                        continue
                    try:
                        actions[seat.name] = _parse_actions(
                            message.get("actions"), chef_of[seat.name]
                        )
                    except _RuleBroken as broken:
                        self.crash(seat, _rule_error(str(broken)))
                        continue
                    waiting.discard(seat.name)
                else:
                    self._unexpected(seat, message)
            waiting &= {seat.name for seat in self.live()}
        for seat in self.live():
            report = self.reports[seat.name]
            self.reports[seat.name] = report.copy_with(
                ticks=report.ticks + 1,
                missed_ticks=report.missed_ticks + (seat.name in waiting),
            )
        return actions

    def _receive(self, timeout: float) -> list[tuple[Seat, Message]]:
        """Wait up to ``timeout`` for messages from any live seat."""
        received: list[tuple[Seat, Message]] = []
        if not self.live():
            return received
        for key, _ in self._selector.select(timeout):
            seat = self._by_fd[key.fd]
            try:
                messages = seat.connection.read_available()
            except ConnectionClosed:
                self.crash(seat, _exited())
                continue
            except ProtocolError as error:
                self.crash(seat, _rule_error(str(error)))
                continue
            received.extend((seat, message) for message in messages)
        return received

    def _unexpected(self, seat: Seat, message: Message) -> None:
        if message["type"] == "error":
            self.crash(seat, _reported_error(message.get("error")))
        else:
            self.crash(seat, _rule_error(f"it sent {message['type']!r} out of turn"))


class _RuleBroken(Exception):
    pass


def _parse_actions(raw: object, chef: str) -> list[Mutation]:
    if not isinstance(raw, list):
        raise _RuleBroken("its actions were not a list")
    if len(raw) > MAX_ACTIONS_PER_TICK:
        raise _RuleBroken(
            f"it sent {len(raw)} actions in one tick, more than {MAX_ACTIONS_PER_TICK}"
        )
    try:
        actions = _ACTIONS.validate_python(raw)
    except ValidationError as error:
        first = error.errors()[0]
        raise _RuleBroken(
            f"it sent an action the simulator does not know: {first['msg']}"
        ) from None
    for action in actions:
        owner = getattr(action, "agent_id", None)
        if owner != chef:
            raise _RuleBroken(
                f"it sent an action for chef {owner!r}, not its own chef {chef!r}"
            )
    return list(actions)


def _reported_error(raw: object) -> RunError:
    try:
        return (
            RunError.model_validate(raw)
            if isinstance(raw, dict)
            else _rule_error("it reported an error without details")
        )
    except ValidationError:
        return _rule_error("it reported an error without details")


def _rule_error(message: str) -> RunError:
    return RunError(
        type="MatchRuleError",
        message=f"The controller broke a match rule: {message}.",
        traceback="",
    )


def _exited() -> RunError:
    return RunError(
        type="ControllerExited",
        message=(
            "The controller's process stopped without saying why. It may have run"
            " out of memory, or called exit."
        ),
        traceback="",
    )


def _too_slow_to_start(seconds: float) -> RunError:
    return RunError(
        type="TooSlowToStart",
        message=f"The controller was not ready within {seconds:g} seconds.",
        traceback="",
    )

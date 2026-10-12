"""Sets between teams of separate seat processes, as ``cook match`` plays them."""

from __future__ import annotations

import shutil
from pathlib import Path
from textwrap import dedent, indent

import pytest
import typer

from cli.match import (
    SeatSource,
    choose_kitchen,
    parse_seat,
    play_local_set,
    summary,
)
from simulator.configuration import Configuration, load_configuration
from simulator.match import (
    GameReport,
    MatchSetupError,
    SeatReport,
    SetReport,
    teams_of,
)
from simulator.match.host import _turn_order
from simulator.recording import load_recording

ROOT = Path(__file__).resolve().parent.parent
KITCHEN = ROOT / "levels" / "3_too_many_chefs" / "0_full_menu.yaml"
#: Three chefs and no teams of its own.
THREE_CHEFS = ROOT / "levels" / "1_we_can_cook" / "1_2_sushi_divided_3p.yaml"
EXAMPLE = SeatSource(label="example", folder=None)

HEADER = """
from simulator.controller import Controller
from simulator.mutations import MoveAgentForward


class OpenController(Controller):
    def is_busy(self):
        return False

    def has_finished(self, environment):
        return False

    def shutdown(self):
        pass
"""


def submission(tmp_path: Path, name: str, body: str) -> SeatSource:
    """A submission folder whose ``OpenController`` ends in ``body``."""
    folder = tmp_path / name
    folder.mkdir()
    (folder / "__init__.py").write_text("")
    (folder / "controller.py").write_text(dedent(HEADER) + indent(dedent(body), "    "))
    return SeatSource(label=name, folder=folder)


def play(
    sources: list[SeatSource],
    *,
    tmp_path: Path,
    kitchen: Configuration | None = None,
    games: int | None = 2,
    tick_seconds: float = 0.05,
    max_timesteps: int = 20,
) -> SetReport:
    return play_local_set(
        kitchen or load_configuration(KITCHEN),
        sources,
        level=KITCHEN.name,
        games=games,
        tick_seconds=tick_seconds,
        max_timesteps=max_timesteps,
        replay_dir=tmp_path / "replays",
    )


def test_examples_play_a_whole_set_and_swap_sides(tmp_path: Path) -> None:
    report = play([EXAMPLE] * 4, tmp_path=tmp_path)

    assert report.winner == "draw"
    assert [game.timesteps for game in report.games] == [20, 20]
    assert report.games[0].teams == {"a": "reds", "b": "blues"}
    assert report.games[1].teams == {"a": "blues", "b": "reds"}
    first, second = next(seat.chefs for seat in report.seats if seat.name == "A1")
    assert first != second
    assert all(seat.error is None and seat.ticks == 40 for seat in report.seats)
    replay = load_recording(report.games[0].replay or "")
    assert len(replay.environments) == 21


def test_a_controller_that_raises_crashes_its_seat_and_ends_the_set(
    tmp_path: Path,
) -> None:
    raising = submission(
        tmp_path,
        "raising",
        """
            def get_actions(self, environment, context):
                if environment.timestep == 5:
                    raise RuntimeError("lost track of the kitchen")
                return []
        """,
    )

    report = play([EXAMPLE, raising, EXAMPLE, EXAMPLE], tmp_path=tmp_path)

    assert report.winner is None
    assert report.crashed == ["A2"]
    error = next(seat.error for seat in report.seats if seat.name == "A2")
    assert error is not None
    assert error.type == "RuntimeError"
    assert error.stage == "run"
    assert "raising/controller.py" in error.traceback
    assert len(report.games) == 1


def test_a_controller_that_will_not_import_crashes_before_the_first_game(
    tmp_path: Path,
) -> None:
    broken = submission(tmp_path, "broken", "import not_a_real_module\n")

    report = play([EXAMPLE, EXAMPLE, broken, EXAMPLE], tmp_path=tmp_path)

    assert report.crashed == ["B1"]
    error = next(seat.error for seat in report.seats if seat.name == "B1")
    assert error is not None
    assert error.type == "ModuleNotFoundError"
    assert error.stage == "import"
    assert report.games == []


def test_a_slow_controller_misses_ticks_without_crashing(tmp_path: Path) -> None:
    slow = submission(
        tmp_path,
        "slow",
        """
            def get_actions(self, environment, context):
                import time

                time.sleep(0.12)
                return []
        """,
    )

    report = play([slow, EXAMPLE, EXAMPLE, EXAMPLE], tmp_path=tmp_path, games=1)

    assert report.crashed == []
    seat = next(seat for seat in report.seats if seat.name == "A1")
    assert seat.ticks == 20
    assert seat.missed_ticks > 10


def test_actions_for_another_chef_break_the_rules(tmp_path: Path) -> None:
    cheat = submission(
        tmp_path,
        "cheat",
        """
            def get_actions(self, environment, context):
                from simulator.entities import Agent

                mine = {agent.id for agent in self.controllable_agents(environment)}
                others = [
                    agent.id
                    for agent in environment.get_entities_of_type(Agent)
                    if agent.id not in mine
                ]
                return [MoveAgentForward(agent_id=others[0])]
        """,
    )

    report = play([EXAMPLE, EXAMPLE, EXAMPLE, cheat], tmp_path=tmp_path)

    error = next(seat.error for seat in report.seats if seat.name == "B2")
    assert error is not None
    assert error.type == "MatchRuleError"
    assert "not its own chef" in error.message


def test_a_controller_whose_process_dies_has_exited(tmp_path: Path) -> None:
    dying = submission(
        tmp_path,
        "dying",
        """
            def get_actions(self, environment, context):
                import os

                os._exit(137)
        """,
    )

    report = play([EXAMPLE, dying, EXAMPLE, EXAMPLE], tmp_path=tmp_path)

    error = next(seat.error for seat in report.seats if seat.name == "A2")
    assert error is not None
    assert error.type == "ControllerExited"


def test_a_seat_is_the_example_a_checkout_or_a_submission_folder(
    tmp_path: Path,
) -> None:
    assert parse_seat("example").folder is None
    assert parse_seat(str(ROOT)).folder == ROOT / "controllers" / "open" / "submission"
    folder = submission(tmp_path, "mine", "").folder
    assert folder is not None
    assert parse_seat(str(folder)).folder == folder.resolve()
    with pytest.raises(Exception, match="no controllers/open/submission"):
        parse_seat(str(tmp_path / "missing"))


def test_a_kitchen_needs_two_or_more_teams_of_one_size(tmp_path: Path) -> None:
    kitchen = load_configuration(KITCHEN)
    assert teams_of(kitchen) == {"reds": ["Ada", "Bo"], "blues": ["Cyd", "Dev"]}
    solo = kitchen.copy_with(teams={"red": ["Ada"], "blue": ["Bo"], "green": ["Cyd"]})
    assert teams_of(solo) == {"red": ["Ada"], "blue": ["Bo"], "green": ["Cyd"]}
    lopsided = Configuration.from_dict(
        {**kitchen.to_dict(), "teams": {"reds": ["Ada", "Bo", "Cyd"], "blues": ["Dev"]}}
    )
    alone = kitchen.copy_with(teams={"reds": ["Ada", "Bo"]})
    for configuration in (lopsided, alone):
        with pytest.raises(MatchSetupError, match="two or more teams with the same"):
            teams_of(configuration)


def test_three_teams_each_play_from_every_place(tmp_path: Path) -> None:
    kitchen = load_configuration(KITCHEN).copy_with(
        teams={"red": ["Ada"], "blue": ["Bo"], "green": ["Cyd"]}
    )

    first, second, third = teams_of(kitchen)

    report = play([EXAMPLE] * 3, tmp_path=tmp_path, kitchen=kitchen, games=None)

    assert [(seat.name, seat.side) for seat in report.seats] == [
        ("A1", "a"),
        ("B1", "b"),
        ("C1", "c"),
    ]
    assert [game.teams for game in report.games] == [
        {"a": first, "b": second, "c": third},
        {"a": second, "b": third, "c": first},
        {"a": third, "b": first, "c": second},
    ]
    assert len(set(report.seats[0].chefs)) == 3
    assert report.score == {"a": 0, "b": 0, "c": 0}
    assert report.winner == "draw"


def test_seats_take_turns_to_act_first() -> None:
    two = [["A1", "A2"], ["B1", "B2"]]
    assert _turn_order(two, 0) == ["A1", "A2", "B1", "B2"]
    assert _turn_order(two, 1) == ["B2", "B1", "A2", "A1"]
    assert _turn_order(two, 2) == ["A1", "A2", "B1", "B2"]
    three = [["A1"], ["B1"], ["C1"]]
    assert [_turn_order(three, timestep)[0] for timestep in range(4)] == [
        "A1",
        "B1",
        "C1",
        "A1",
    ]


def test_a_kitchen_must_seat_everyone_given() -> None:
    assert choose_kitchen(KITCHEN, teams=[], seats=4)[0] == KITCHEN
    with pytest.raises(typer.BadParameter, match="give 4 seats, not 3"):
        choose_kitchen(KITCHEN, teams=[], seats=3)
    _, kitchen = choose_kitchen(KITCHEN, teams=["red=1", "blue=2", "green=3"], seats=3)
    assert list(teams_of(kitchen)) == ["red", "blue", "green"]
    with pytest.raises(typer.BadParameter, match="this kitchen has none"):
        choose_kitchen(THREE_CHEFS, teams=[], seats=3)


def test_a_folder_draws_a_kitchen_that_seats_everyone(tmp_path: Path) -> None:
    pool = KITCHEN.parent
    assert choose_kitchen(pool, teams=[], seats=4)[0].parent == pool
    with pytest.raises(typer.BadParameter, match="take 4 seats, not 3"):
        choose_kitchen(pool, teams=[], seats=3)

    mixed = tmp_path / "kitchens"
    mixed.mkdir()
    shutil.copy(KITCHEN, mixed)
    shutil.copy(THREE_CHEFS, mixed)
    for _ in range(5):
        assert choose_kitchen(mixed, teams=[], seats=4)[0].name == KITCHEN.name
    teams = ["red=1", "blue=2", "green=3"]
    assert {choose_kitchen(mixed, teams=teams, seats=3)[0].name for _ in range(30)} == {
        KITCHEN.name,
        THREE_CHEFS.name,
    }
    with pytest.raises(typer.BadParameter, match="no kitchens"):
        choose_kitchen(mixed, teams=["red=1", "blue=2,3,4"], seats=4)


def test_a_summary_names_every_team_and_ranks_the_totals() -> None:
    sources = [SeatSource(label=label, folder=None) for label in ("ana", "ben", "cy")]
    seats = [
        SeatReport(name=name, side=name[0].lower(), chefs=["Ada"])
        for name in ("A1", "B1", "C1")
    ]
    game = GameReport(
        level="kitchen.yaml",
        teams={"a": "red", "b": "blue", "c": "green"},
        score={"a": 3, "b": 9, "c": 5},
        score_by_seat={"A1": 3, "B1": 9, "C1": 5},
        timesteps=300,
    )
    won = SetReport(games=[game], score=game.score, winner="b", seats=seats)
    tied = won.copy_with(score={"a": 9, "b": 9, "c": 5}, winner="draw")

    assert summary(won, sources) == [
        "Team A: ana (A1)",
        "Team B: ben (B1)",
        "Team C: cy (C1)",
        (
            "Game 1: A 3, B 9, C 5"
            " (A played red, B played blue, C played green, 300 timesteps)"
        ),
        "Team B wins, 9 to 5 to 3.",
    ]
    assert summary(tied, sources)[-1] == "Teams A and B draw, 9 each."


def test_a_controller_killed_with_ticks_unread_has_exited(tmp_path: Path) -> None:
    # Ticks pile up unread while it sleeps, so its end resets the connection
    # rather than closing it.
    dying = submission(
        tmp_path,
        "dying_late",
        """
            def get_actions(self, environment, context):
                import os
                import time

                time.sleep(0.3)
                os._exit(137)
        """,
    )

    report = play(
        [dying, EXAMPLE, EXAMPLE, EXAMPLE], tmp_path=tmp_path, tick_seconds=0.02
    )

    error = next(seat.error for seat in report.seats if seat.name == "A1")
    assert error is not None
    assert error.type == "ControllerExited"

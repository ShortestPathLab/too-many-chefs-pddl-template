"""2v2 sets between separate seat processes, as Part 4's competition plays them."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent, indent

import pytest

from cli.match import SeatSource, parse_seat, play_local_set
from simulator.configuration import Configuration, load_configuration
from simulator.match import MatchSetupError, SetReport, teams_of
from simulator.recording import load_recording

ROOT = Path(__file__).resolve().parent.parent
KITCHEN = ROOT / "levels" / "3_too_many_chefs" / "0_carrot_salad.yaml"
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
    games: int = 2,
    tick_seconds: float = 0.05,
    max_timesteps: int = 20,
) -> SetReport:
    return play_local_set(
        load_configuration(KITCHEN),
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


def test_a_kitchen_needs_two_teams_of_two(tmp_path: Path) -> None:
    kitchen = load_configuration(KITCHEN)
    assert teams_of(kitchen) == {"reds": ["Ada", "Bo"], "blues": ["Cyd", "Dev"]}
    lopsided = Configuration.from_dict(
        {**kitchen.to_dict(), "teams": {"reds": ["Ada", "Bo", "Cyd"], "blues": ["Dev"]}}
    )
    with pytest.raises(MatchSetupError, match="two teams of two"):
        teams_of(lopsided)


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

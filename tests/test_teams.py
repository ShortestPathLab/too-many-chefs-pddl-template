"""Test team assignment and team scores."""

from __future__ import annotations

import pytest
import typer

from cli.teams import with_teams
from simulator.configuration.configuration import Configuration
from simulator.entities import Agent, team_label, team_scores
from simulator.mutations import Cook, TakeFromStorage
from simulator.run.result import build_simulation_result
from simulator.view import agents_view, badge_order, score_view, summary_view
from tests.team_kitchens import (
    MIRRORED_KITCHEN,
    NAMED_CHEF_KITCHEN,
    TWO_CHEF_KITCHEN,
    kitchen,
    state_of,
    two_chefs,
)

SIDES = {"teams": {"red": ["1"], "blue": ["2"]}}


def split(level: dict = TWO_CHEF_KITCHEN, **overrides: object):
    """Return a two-chef kitchen with one agent per team."""
    environment, first, second = two_chefs(level, **{**SIDES, **overrides})
    played = Cook(agent_id=second.id).run(
        TakeFromStorage(agent_id=first.id).run(environment)
    )
    return played, first, second


def test_a_roster_puts_each_chef_on_their_side() -> None:
    _environment, first, second = two_chefs(TWO_CHEF_KITCHEN, **SIDES)

    assert (first.team, second.team) == ("red", "blue")


def test_chefs_can_be_named_rather_than_numbered() -> None:
    _environment, first, second = two_chefs(
        NAMED_CHEF_KITCHEN, teams={"red": ["Alfred"], "blue": ["Bruno"]}
    )

    assert (first.id, first.team) == ("Alfred", "red")
    assert (second.id, second.team) == ("Bruno", "blue")


def test_a_kitchen_nobody_split_has_no_sides() -> None:
    environment, first, second = two_chefs(TWO_CHEF_KITCHEN)

    assert first.team is None
    assert second.team is None
    assert team_scores(state_of(environment).scoring, [first, second]) == {}


def test_a_roster_naming_a_chef_the_level_lacks_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown agent '9'"):
        kitchen(TWO_CHEF_KITCHEN, teams={"red": ["9"]})


def test_a_chef_cannot_cook_for_two_sides() -> None:
    with pytest.raises(ValueError, match="more than one team"):
        kitchen(TWO_CHEF_KITCHEN, teams={"red": ["1"], "blue": ["1"]})


def test_each_side_is_worth_what_its_chefs_earned() -> None:
    played, _first, _second = split()

    scores = team_scores(state_of(played).scoring, badge_order(played))

    assert scores == {"red": 2, "blue": 5}
    assert sum(scores.values()) == state_of(played).score


def test_a_chef_on_no_side_is_counted_for_nobody() -> None:
    played, _first, _second = split(teams={"red": ["1"]})

    scores = team_scores(state_of(played).scoring, badge_order(played))

    assert scores == {"red": 2}
    assert state_of(played).score == 7


def test_a_side_reads_the_same_however_its_chefs_are_ordered() -> None:
    played, _first, _second = split(teams={"red": ["2", "1"]})

    assert team_scores(state_of(played).scoring, badge_order(played)) == {"red": 7}


def test_the_bar_carries_the_sides_alongside_the_total() -> None:
    played, _first, _second = split()

    view = score_view(played)

    assert view.score == 7
    assert [(team.name, team.label, team.score) for team in view.teams] == [
        ("red", "Team Red", 2),
        ("blue", "Team Blue", 5),
    ]


def test_the_bar_shows_no_sides_in_a_kitchen_nobody_split() -> None:
    environment, _first, _second = two_chefs(TWO_CHEF_KITCHEN)

    assert score_view(environment).teams == []


def test_the_agent_panel_names_a_chef_their_side() -> None:
    environment, first, second = two_chefs(TWO_CHEF_KITCHEN, **SIDES)

    view = agents_view(environment, order=[first.id, second.id])

    assert [(agent.team, agent.team_label) for agent in view.agents] == [
        ("red", "Team Red"),
        ("blue", "Team Blue"),
    ]


def test_the_agent_panel_leaves_the_team_blank_without_one() -> None:
    environment, first, second = two_chefs(TWO_CHEF_KITCHEN)

    view = agents_view(environment, order=[first.id, second.id])

    assert [(agent.team, agent.team_label) for agent in view.agents] == [
        ("", ""),
        ("", ""),
    ]


def test_the_result_reports_each_side() -> None:
    played, _first, _second = split()

    result = build_simulation_result(played, reason="completed", elapsed_seconds=1.0)

    assert result.score_by_team == {"red": 2, "blue": 5}
    assert result.score == 7


def test_an_unsplit_run_reports_no_sides() -> None:
    environment, _first, _second = two_chefs(TWO_CHEF_KITCHEN)

    result = build_simulation_result(
        environment, reason="completed", elapsed_seconds=1.0
    )

    assert result.score_by_team == {}


def test_the_ending_card_calls_the_winner() -> None:
    played, _first, _second = split()

    card = summary_view(
        build_simulation_result(played, reason="completed", elapsed_seconds=1.0)
    )

    assert card.contested
    assert card.leader == "blue"
    assert card.verdict == "Team Blue wins"
    assert [(team.label, team.score) for team in card.teams] == [
        ("Team Red", 2),
        ("Team Blue", 5),
    ]


def test_a_draw_is_called_a_draw() -> None:
    environment, first, second = two_chefs(MIRRORED_KITCHEN, **SIDES)
    drawn = TakeFromStorage(agent_id=second.id).run(
        TakeFromStorage(agent_id=first.id).run(environment)
    )

    card = summary_view(
        build_simulation_result(drawn, reason="completed", elapsed_seconds=1.0)
    )

    assert card.teams == [team for team in card.teams if team.score == 2]
    assert card.contested
    assert card.leader == ""
    assert card.verdict == "Draw"


def test_one_side_is_not_a_contest() -> None:
    played, _first, _second = split(teams={"red": ["1", "2"]})

    card = summary_view(
        build_simulation_result(played, reason="completed", elapsed_seconds=1.0)
    )

    assert not card.contested
    assert card.verdict == ""


def test_a_side_is_labelled_by_its_colour() -> None:
    assert team_label("red") == "Team Red"
    assert team_label("deep_fryers") == "Team Deep Fryers"


def configuration(level: dict = TWO_CHEF_KITCHEN, **overrides: object) -> Configuration:
    return Configuration.from_dict({**level, **overrides})


def test_the_command_line_splits_the_kitchen() -> None:
    split_configuration = with_teams(configuration(), teams=["red=1", "blue=2"])

    assert split_configuration.teams == {"red": ["1"], "blue": ["2"]}


def test_the_command_line_replaces_the_level_own_sides() -> None:
    split_configuration = with_teams(configuration(**SIDES), teams=["green=1,2"])

    assert split_configuration.teams == {"green": ["1", "2"]}


def test_a_level_keeps_its_sides_when_the_command_line_is_silent() -> None:
    assert with_teams(configuration(**SIDES), teams=[]).teams == SIDES["teams"]


def test_the_command_line_rejects_a_chef_the_level_lacks() -> None:
    with pytest.raises(typer.BadParameter):
        with_teams(configuration(), teams=["red=9"])


def test_the_command_line_rejects_a_chef_on_two_sides() -> None:
    with pytest.raises(typer.BadParameter):
        with_teams(configuration(), teams=["red=1", "blue=1"])


def test_the_command_line_rejects_a_spec_with_no_equals() -> None:
    with pytest.raises(typer.BadParameter):
        with_teams(configuration(), teams=["red"])


def test_a_team_named_twice_on_the_command_line_gathers_its_chefs() -> None:
    split_configuration = with_teams(configuration(), teams=["red=1", "red=2"])

    assert split_configuration.teams == {"red": ["1", "2"]}


def test_sides_survive_a_round_trip_through_a_recording() -> None:
    environment, _first, _second = two_chefs(TWO_CHEF_KITCHEN, **SIDES)

    restored = type(environment).from_dict(environment.to_dict())

    assert [agent.team for agent in restored.get_entities_of_type(Agent)] == [
        agent.team for agent in environment.get_entities_of_type(Agent)
    ]

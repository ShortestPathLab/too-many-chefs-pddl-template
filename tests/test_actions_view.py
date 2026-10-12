from __future__ import annotations

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.environment import Environment
from simulator.mutations import (
    Interact,
    MoveAgentForward,
    PickUpOrPlace,
    TurnAgent,
)
from simulator.recording import Recording
from simulator.view import ActionsView, actions_view, badge_order
from tests.scoring_states import TOMATO
from tests.team_kitchens import TWO_CHEF_KITCHEN

LEVEL = {
    "layout": "| 1 |   |\n| 2 |   |",
    "legend": {
        "agents": [{"symbol": "1"}, {"symbol": "2"}],
    },
}


# A chef between a counter and a crate, with a second chef out of the way.
PASS_KITCHEN = {
    "layout": "|-|1|T|\n| |2| |",
    "legend": {
        "agents": [
            {"symbol": "1", "orientation": "e"},
            {"symbol": "2", "orientation": "s"},
        ],
        "counters": [{"symbol": "-"}],
        "storages": [{"symbol": "T", "food_name": TOMATO}],
        "foods": [{"name": TOMATO, "sprite": [{"x": 0, "y": 0, "sheet": "food.png"}]}],
    },
}

# The two-chef kitchen with a verb on its station, as the catalogue gives one.
CHOPPING_KITCHEN = {
    **TWO_CHEF_KITCHEN,
    "legend": {
        **TWO_CHEF_KITCHEN["legend"],
        "equipment": [
            {**station, "verb": "Chop"}
            for station in TWO_CHEF_KITCHEN["legend"]["equipment"]
        ],
    },
}


def _environment(level: dict = LEVEL) -> Environment:
    return load(Configuration.from_dict(level))


def _order(environment: Environment) -> list[str]:
    return [agent.id for agent in badge_order(environment)]


def _recording(environment: Environment, steps: list[list]) -> Recording:
    """Run each step so the history is a real one."""
    environments = [environment]
    for mutations in steps:
        environments.append(environments[-1].step(mutations))
    return Recording(environments=environments, mutations=[[], *steps])


def _history(level: dict, steps_for: object) -> ActionsView:
    """Play ``steps_for(first, second)`` in ``level`` and return its history."""
    environment = _environment(level)
    first, second = _order(environment)
    recording = _recording(environment, steps_for(first, second))  # type: ignore[operator]
    return actions_view(recording, recording.environments[-1], order=[first, second])


def _kinds(view: ActionsView, lane: int = 0) -> list[str]:
    return [segment.kind for segment in view.lanes[lane].segments]


def test_an_untouched_run_gives_every_chef_an_empty_lane() -> None:
    environment = _environment()
    recording = Recording(environments=[environment], mutations=[[]])

    view = actions_view(recording, environment, order=_order(environment))

    assert [lane.segments for lane in view.lanes] == [[], []]
    assert view.current_step == 0


def test_lanes_are_numbered_the_way_the_badges_are() -> None:
    environment = _environment()
    order = _order(environment)
    recording = Recording(environments=[environment], mutations=[[]])

    view = actions_view(recording, environment, order=order)

    assert [(lane.number, lane.agent_id) for lane in view.lanes] == [
        (1, order[0]),
        (2, order[1]),
    ]


def test_without_an_order_the_lanes_follow_the_badges() -> None:
    environment = _environment()
    recording = Recording(environments=[environment], mutations=[[]])

    view = actions_view(recording, environment)

    assert [lane.agent_id for lane in view.lanes] == _order(environment)


def test_a_turn_and_a_step_in_one_go_read_as_walking() -> None:
    view = _history(
        LEVEL,
        lambda first, second: [
            [
                TurnAgent(agent_id=first, orientation="e"),
                MoveAgentForward(agent_id=first),
            ]
        ],
    )

    assert _kinds(view) == ["walk"]


def test_a_chef_who_did_nothing_that_step_is_waiting() -> None:
    view = _history(
        LEVEL,
        lambda first, second: [[TurnAgent(agent_id=first, orientation="e")]],
    )

    assert _kinds(view, lane=1) == ["idle"]


def test_steps_spent_the_same_way_join_into_one_segment() -> None:
    view = _history(
        LEVEL,
        lambda first, second: [
            [TurnAgent(agent_id=first, orientation="e")],
            [TurnAgent(agent_id=first, orientation="s")],
            [],
            [],
            [],
        ],
    )

    segments = view.lanes[0].segments
    assert [(s.kind, s.first, s.last, s.steps) for s in segments] == [
        ("walk", 1, 2, 2),
        ("idle", 3, 5, 3),
    ]


def test_the_history_stops_at_the_environment_being_shown() -> None:
    # Replay scrubs backwards, and a history that keeps showing the future
    # would give away what is about to happen.
    environment = _environment()
    agent_id = _order(environment)[0]
    recording = _recording(
        environment,
        [
            [TurnAgent(agent_id=agent_id, orientation="e")],
            [TurnAgent(agent_id=agent_id, orientation="s")],
            [TurnAgent(agent_id=agent_id, orientation="w")],
        ],
    )

    view = actions_view(recording, recording.environments[2], order=_order(environment))

    assert view.current_step == 2
    assert view.lanes[0].segments[-1].last == 2


def test_the_history_keeps_only_the_last_few_steps() -> None:
    environment = _environment()
    agent_id = _order(environment)[0]
    steps = [
        [TurnAgent(agent_id=agent_id, orientation=orientation)]
        for orientation in ["e", "s", "w", "n", "e", "s", "w", "n"]
    ]
    recording = _recording(environment, steps)

    view = actions_view(
        recording, recording.environments[-1], order=_order(environment), window=3
    )

    assert (view.first_step, view.current_step, view.window) == (6, 8, 3)
    assert view.lanes[0].segments[0].first == 6


def test_an_environment_the_recording_never_saw_shows_nothing() -> None:
    environment = _environment()
    recording = Recording(environments=[environment], mutations=[[]])

    view = actions_view(recording, environment.copy_with(timestep=99))

    assert view.lanes == []


def test_interacting_with_a_crate_reads_as_taking_from_it() -> None:
    # A person presses one key to interact, and the kitchen decides what that
    # was. The lane names what happened, not the key.
    view = _history(PASS_KITCHEN, lambda first, second: [[Interact(agent_id=first)]])

    taken = view.lanes[0].segments[0]
    assert (taken.kind, taken.label, taken.mark) == ("act", "Take", "↑")
    assert "tomato" in taken.detail
    assert taken.sprite is not None


def test_interacting_with_a_station_reads_as_its_verb() -> None:
    view = _history(
        CHOPPING_KITCHEN, lambda first, second: [[Interact(agent_id=second)]]
    )

    worked = view.lanes[1].segments[0]
    assert (worked.kind, worked.label) == ("work", "Chop")


def test_a_press_that_did_nothing_leaves_the_chef_waiting() -> None:
    # Play mode records a key the kitchen refused so the pad can show it.
    view = _history(LEVEL, lambda first, second: [[PickUpOrPlace(agent_id=first)]])

    assert _kinds(view) == ["idle"]


def test_walking_with_something_in_hand_shows_what_it_is() -> None:
    view = _history(
        PASS_KITCHEN,
        lambda first, second: [
            [Interact(agent_id=first)],
            [TurnAgent(agent_id=first, orientation="s")],
        ],
    )

    carried = view.lanes[0].segments[-1]
    assert carried.kind == "walk"
    assert "tomato" in carried.detail
    assert carried.sprite is not None


def test_a_key_the_kitchen_refused_leaves_the_chef_waiting() -> None:
    # The second press asks the crate for a tomato with both hands full.
    view = _history(
        TWO_CHEF_KITCHEN,
        lambda first, second: [[Interact(agent_id=first)], [Interact(agent_id=first)]],
    )

    assert _kinds(view) == ["act", "idle"]


def test_one_key_reads_as_whichever_of_its_deeds_happened() -> None:
    view = _history(
        PASS_KITCHEN,
        lambda first, second: [
            [Interact(agent_id=first)],
            [TurnAgent(agent_id=first, orientation="w"), PickUpOrPlace(agent_id=first)],
            [PickUpOrPlace(agent_id=first)],
        ],
    )

    assert [segment.label for segment in view.lanes[0].segments] == [
        "Take",
        "Place",
        "Take",
    ]

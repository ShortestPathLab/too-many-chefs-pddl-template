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
from simulator.view import actions_view, badge_order, with_agent_names

LEVEL = {
    "layout": "| 1 |   |\n| 2 |   |",
    "legend": {
        "agents": [{"symbol": "1"}, {"symbol": "2"}],
    },
}


def _environment() -> Environment:
    return load(Configuration.from_dict(LEVEL))


def _order(environment: Environment) -> list[str]:
    return [agent.id for agent in badge_order(environment)]


def _recording(environment: Environment, steps: list[list]) -> Recording:
    """Run each step so the log uses a real history."""
    environments = [environment]
    for mutations in steps:
        environments.append(environments[-1].step(mutations))
    return Recording(environments=environments, mutations=[[], *steps])


def test_an_untouched_run_has_nothing_to_show() -> None:
    environment = _environment()
    recording = Recording(environments=[environment], mutations=[[]])

    view = actions_view(recording, environment, order=_order(environment))

    assert view.lines == []


def test_each_step_that_did_something_gets_a_line() -> None:
    environment = _environment()
    agent_id = _order(environment)[0]
    recording = _recording(
        environment,
        [
            [TurnAgent(agent_id=agent_id, orientation="e")],
            [MoveAgentForward(agent_id=agent_id)],
        ],
    )

    view = actions_view(
        recording, recording.environments[-1], order=_order(environment)
    )

    assert [line.step for line in view.lines] == [1, 2]


def test_a_step_where_nothing_happened_leaves_no_line() -> None:
    environment = _environment()
    agent_id = _order(environment)[0]
    recording = _recording(
        environment,
        [
            [TurnAgent(agent_id=agent_id, orientation="e")],
            [],
            [TurnAgent(agent_id=agent_id, orientation="s")],
        ],
    )

    view = actions_view(
        recording, recording.environments[-1], order=_order(environment)
    )

    assert [line.step for line in view.lines] == [1, 3]


def test_only_the_newest_line_is_the_current_one() -> None:
    environment = _environment()
    agent_id = _order(environment)[0]
    recording = _recording(
        environment,
        [
            [TurnAgent(agent_id=agent_id, orientation="e")],
            [TurnAgent(agent_id=agent_id, orientation="s")],
        ],
    )

    view = actions_view(
        recording, recording.environments[-1], order=_order(environment)
    )

    assert [line.current for line in view.lines] == [False, True]


def test_the_log_stops_at_the_environment_being_shown() -> None:
    # Replay scrubs backwards, and a log that keeps showing the future
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

    assert [line.step for line in view.lines] == [1, 2]


def test_the_log_keeps_only_the_last_few_steps() -> None:
    environment = _environment()
    agent_id = _order(environment)[0]
    steps = [
        [TurnAgent(agent_id=agent_id, orientation=orientation)]
        for orientation in ["e", "s", "w", "n", "e", "s", "w", "n"]
    ]
    recording = _recording(environment, steps)

    view = actions_view(
        recording, recording.environments[-1], order=_order(environment), limit=3
    )

    assert [line.step for line in view.lines] == [6, 7, 8]


def test_one_line_holds_everything_that_happened_that_step() -> None:
    environment = _environment()
    first, second = _order(environment)
    recording = _recording(
        environment,
        [
            [
                TurnAgent(agent_id=first, orientation="e"),
                TurnAgent(agent_id=second, orientation="w"),
            ]
        ],
    )

    view = actions_view(
        recording, recording.environments[-1], order=_order(environment)
    )

    assert len(view.lines) == 1
    assert "Agent 1" in view.lines[0].text
    assert "Agent 2" in view.lines[0].text


def test_an_environment_the_recording_never_saw_shows_nothing() -> None:
    environment = _environment()
    recording = Recording(environments=[environment], mutations=[[]])

    view = actions_view(recording, environment.copy_with(timestep=99))

    assert view.lines == []


def test_agent_ids_read_as_the_numbers_shown_everywhere_else() -> None:
    environment = _environment()
    agent_id = _order(environment)[0]
    recording = _recording(
        environment, [[TurnAgent(agent_id=agent_id, orientation="e")]]
    )

    view = actions_view(
        recording, recording.environments[-1], order=_order(environment)
    )

    assert agent_id not in view.lines[0].text
    assert view.lines[0].text.startswith("Agent 1")


def test_an_id_inside_a_longer_word_is_left_alone() -> None:
    assert (
        with_agent_names("ab12 sees ab12x", {"ab12": "Agent 1"}) == "Agent 1 sees ab12x"
    )


def test_without_an_order_the_ids_stay_as_they_are() -> None:
    environment = _environment()
    agent_id = _order(environment)[0]
    recording = _recording(
        environment, [[TurnAgent(agent_id=agent_id, orientation="e")]]
    )

    view = actions_view(recording, recording.environments[-1])

    assert agent_id in view.lines[0].text


def test_a_step_is_described_against_the_world_it_started_in() -> None:
    # Interact reads as one thing before the step and another after it, so
    # describing against the wrong environment quietly rewrites history.
    environment = _environment()
    agent_id = _order(environment)[0]
    recording = _recording(
        environment,
        [[Interact(agent_id=agent_id)], [PickUpOrPlace(agent_id=agent_id)]],
    )

    view = actions_view(
        recording, recording.environments[-1], order=_order(environment)
    )

    assert [line.text for line in view.lines] == [
        f"Agent 1 {suffix}"
        for suffix in ("interacts", "picks up, places, or combines item")
    ]

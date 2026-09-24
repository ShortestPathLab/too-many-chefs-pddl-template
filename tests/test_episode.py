"""Test the kitchen loop shared by the run modes and the learning environments."""

from __future__ import annotations

from simulator.configuration import load
from simulator.configuration.configuration import Configuration
from simulator.entities import Agent
from simulator.mutations import MoveAgentForward, PickUpOrPlace
from simulator.recording import Recording
from simulator.run import EndConditions, Episode
from simulator.run.common import OnStep
from tests.run_controllers import AGENT_LEVEL


def new_episode(on_step: OnStep | None = None) -> Episode:
    return Episode(load(Configuration.from_dict(AGENT_LEVEL)), on_step=on_step)


def chef_id(episode: Episode) -> str:
    agent = episode.environment.get_first_entity_of_type(Agent)
    assert agent is not None
    return agent.id


def test_a_step_records_the_environment_and_what_ran() -> None:
    episode = new_episode()
    chef = chef_id(episode)

    step = episode.advance([MoveAgentForward(agent_id=chef)])

    assert step.previous is episode.recording.environments[0]
    assert step.current is episode.environment
    assert [environment.timestep for environment in episode.recording.environments] == [
        0,
        1,
    ]
    assert episode.recording.mutations == [[], step.mutations]
    assert len(step.mutations) == 1


def test_illegal_mutations_are_left_out_of_the_recording() -> None:
    episode = new_episode()
    chef = chef_id(episode)

    step = episode.advance([PickUpOrPlace(agent_id=chef)])

    assert step.mutations == []
    assert episode.recording.mutations[-1] == []


def test_play_mode_can_keep_a_press_that_did_nothing() -> None:
    episode = new_episode()
    chef = chef_id(episode)
    press = PickUpOrPlace(agent_id=chef)

    step = episode.advance([press], keep_illegal=True)

    assert step.mutations == [press]
    assert step.current.get_entity(chef) == step.previous.get_entity(chef)


def test_the_listener_hears_the_start_and_every_step() -> None:
    heard: list[int] = []

    def listen(recording: Recording) -> None:
        heard.append(len(recording.environments))

    episode = new_episode(on_step=listen)
    episode.advance([])
    episode.advance([])

    assert heard == [1, 2, 3]


def test_end_conditions_need_no_controller() -> None:
    episode = new_episode()
    conditions = EndConditions(max_timesteps=2)

    reasons = []
    for _ in range(2):
        episode.advance([])
        reasons.append(episode.end_reason(conditions))

    assert reasons == [None, "max_timesteps"]
    assert episode.result("max_timesteps").timesteps == 2

from __future__ import annotations

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.entities import Agent
from simulator.entities.agent import Orientation
from simulator.environment import Environment
from simulator.mutations import (
    ARROWS,
    DIRECTIONS,
    FACE_BUTTONS,
    Combine,
    Cook,
    Deliver,
    Discard,
    Interact,
    MoveAgent,
    MoveAgentForward,
    PickUp,
    PickUpOrPlace,
    Place,
    TakeFromStorage,
    TurnAgent,
    VirtualInput,
)
from simulator.view import agents_view, badge_order, pressed_inputs

LEVEL = {
    "layout": "| 1 |   |\n| 2 |   |",
    "legend": {"agents": [{"symbol": "1"}, {"symbol": "2"}]},
}

PAD = set(DIRECTIONS) | set(FACE_BUTTONS)


def _environment() -> Environment:
    return load(Configuration.from_dict(LEVEL))


def _order(environment: Environment) -> list[str]:
    return [agent.id for agent in badge_order(environment)]


def test_the_pad_has_a_glyph_for_every_direction() -> None:
    assert set(ARROWS) == set(DIRECTIONS)


def test_turning_presses_the_direction_it_turns_to() -> None:
    environment = _environment()
    agent_id = _order(environment)[0]

    cases: list[tuple[Orientation, VirtualInput]] = [
        ("n", "up"),
        ("s", "down"),
        ("e", "right"),
        ("w", "left"),
    ]
    for orientation, expected in cases:
        mutation = TurnAgent(agent_id=agent_id, orientation=orientation)
        assert mutation.virtual_input(environment) == expected


def test_stepping_forwards_presses_the_way_the_agent_faces() -> None:
    environment = _environment()
    agent_id = _order(environment)[0]
    agent = environment.get_entity_as(agent_id, Agent)
    assert agent is not None
    environment = environment.replace_entity(agent.copy_with(orientation="e"))

    mutation = MoveAgentForward(agent_id=agent_id)

    assert mutation.virtual_input(environment) == "right"


def test_a_step_forwards_by_an_agent_that_is_gone_presses_nothing() -> None:
    environment = _environment()

    assert MoveAgentForward(agent_id="nobody").virtual_input(environment) is None


def test_a_single_cell_move_presses_its_direction() -> None:
    environment = _environment()
    agent_id = _order(environment)[0]

    for dx, dy, expected in [
        (1, 0, "right"),
        (-1, 0, "left"),
        (0, 1, "down"),
        (0, -1, "up"),
    ]:
        mutation = MoveAgent(agent_id=agent_id, dx=dx, dy=dy)
        assert mutation.virtual_input(environment) == expected


def test_a_move_with_no_key_behind_it_presses_nothing() -> None:
    # A pad has four directions. A diagonal or a standstill has no key.
    environment = _environment()
    agent_id = _order(environment)[0]

    for dx, dy in [(1, 1), (-1, 1), (0, 0)]:
        mutation = MoveAgent(agent_id=agent_id, dx=dx, dy=dy)
        assert mutation.virtual_input(environment) is None


def test_reaching_into_a_station_is_the_a_button() -> None:
    environment = _environment()
    agent_id = _order(environment)[0]

    for kind in (Interact, Cook, TakeFromStorage, Deliver, Discard):
        assert kind(agent_id=agent_id).virtual_input(environment) == "a"


def test_handling_what_is_in_your_hands_is_the_b_button() -> None:
    environment = _environment()
    agent_id = _order(environment)[0]

    for kind in (PickUpOrPlace, PickUp, Place, Combine):
        assert kind(agent_id=agent_id).virtual_input(environment) == "b"


def test_every_button_a_mutation_names_is_on_the_pad() -> None:
    environment = _environment()
    agent_id = _order(environment)[0]
    mutations = [
        TurnAgent(agent_id=agent_id, orientation="n"),
        MoveAgent(agent_id=agent_id, dx=1, dy=0),
        Interact(agent_id=agent_id),
        PickUpOrPlace(agent_id=agent_id),
    ]

    for mutation in mutations:
        assert mutation.virtual_input(environment) in PAD


def test_one_arrow_key_lights_one_direction() -> None:
    # Play mode queues a turn and a step forwards together. Both answer
    # with the same direction, and the pad should not show it twice.
    environment = _environment()
    agent_id = _order(environment)[0]

    mutations = [
        TurnAgent(agent_id=agent_id, orientation="e"),
        MoveAgentForward(agent_id=agent_id),
    ]

    pressed = pressed_inputs(environment.step(mutations), mutations, agent_id)

    assert pressed == ["right"]


def test_a_pad_only_shows_its_own_agent() -> None:
    environment = _environment()
    first, second = _order(environment)

    pressed = pressed_inputs(
        environment,
        [
            TurnAgent(agent_id=first, orientation="n"),
            Interact(agent_id=second),
        ],
        second,
    )

    assert pressed == ["a"]


def test_an_agent_that_sat_the_step_out_lights_nothing() -> None:
    environment = _environment()
    first, second = _order(environment)

    assert pressed_inputs(environment, [Interact(agent_id=first)], second) == []


def test_a_direction_and_a_button_in_one_step_both_light() -> None:
    environment = _environment()
    agent_id = _order(environment)[0]

    pressed = pressed_inputs(
        environment,
        [
            TurnAgent(agent_id=agent_id, orientation="s"),
            Interact(agent_id=agent_id),
        ],
        agent_id,
    )

    assert pressed == ["down", "a"]


def test_the_inspector_carries_the_pad_state() -> None:
    environment = _environment()
    order = _order(environment)
    mutations = [TurnAgent(agent_id=order[0], orientation="e")]
    stepped = environment.step(mutations)

    view = agents_view(
        stepped,
        order=order,
        selected_agent_id=order[0],
        mutations=mutations,
    )

    assert view.agents[0].pressed == ["right"]
    assert view.agents[1].pressed == []


def test_a_turn_and_a_step_light_the_direction_they_ended_up_going() -> None:
    # One arrow key sends both, and the turn comes first. Reading the
    # orientation before the step would light the way the agent used to be
    # facing and the way it went, which is two arrows for one key.
    environment = _environment()
    order = _order(environment)
    mutations = [
        TurnAgent(agent_id=order[0], orientation="e"),
        MoveAgentForward(agent_id=order[0]),
    ]

    view = agents_view(environment.step(mutations), order=order, mutations=mutations)

    assert view.agents[0].pressed == ["right"]


def test_a_refresh_with_no_step_behind_it_lights_nothing() -> None:
    environment = _environment()
    order = _order(environment)

    view = agents_view(environment, order=order)

    assert [agent.pressed for agent in view.agents] == [[], []]

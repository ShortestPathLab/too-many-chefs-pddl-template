from __future__ import annotations

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.entities import Agent
from simulator.environment import Environment
from simulator.mutations import MoveAgentForward
from simulator.view import (
    SELECTION_MARKER_PART,
    SELECTION_MARKER_SUFFIX,
    Renderable,
    scene_layers,
)

LEGEND = {
    "agents": [
        {"kind": "agent", "symbol": "A"},
        {"kind": "agent", "symbol": "B"},
    ]
}


def _environment() -> Environment:
    return load(Configuration.from_dict({"layout": "|A|B|", "legend": LEGEND}))


def _agent_ids(environment: Environment) -> list[str]:
    return [agent.id for agent in environment.get_entities_of_type(Agent)]


def _by_id(renderables: list[Renderable]) -> dict[str, Renderable]:
    return {renderable.id: renderable for renderable in renderables}


def test_no_marker_is_drawn_without_a_selection() -> None:
    environment = _environment()

    layers = scene_layers(environment)

    assert [
        renderable.id
        for renderable in layers.objects
        if renderable.id.endswith(SELECTION_MARKER_SUFFIX)
    ] == []


def test_only_the_selected_agent_gets_a_ring() -> None:
    environment = _environment()
    first, second = _agent_ids(environment)

    objects = _by_id(scene_layers(environment, selected_agent_id=first).objects)

    assert f"{first}{SELECTION_MARKER_SUFFIX}" in objects
    assert f"{second}{SELECTION_MARKER_SUFFIX}" not in objects


def test_the_ring_sits_in_the_agent_cell_and_under_the_agent() -> None:
    environment = _environment()
    agent_id = _agent_ids(environment)[0]

    objects = _by_id(scene_layers(environment, selected_agent_id=agent_id).objects)
    agent = objects[agent_id]
    marker = objects[f"{agent_id}{SELECTION_MARKER_SUFFIX}"]

    assert (marker.x, marker.y) == (agent.x, agent.y)
    assert marker.z < agent.z
    assert [frame.parts for frame in marker.sprite.loop_cycle_animation] == [
        [SELECTION_MARKER_PART]
    ]


def test_the_ring_transitions_over_as_many_frames_as_the_agent() -> None:
    # The canvas walks a renderable across the cell over its transition
    # frames. Counting them out the same way is what keeps the ring under
    # the chef's feet for the length of a step rather than waiting in the
    # destination cell.
    environment = _environment()
    agent_id = _agent_ids(environment)[0]

    objects = _by_id(
        scene_layers(
            environment,
            [MoveAgentForward(agent_id=agent_id)],
            selected_agent_id=agent_id,
        ).objects
    )
    agent = objects[agent_id]
    marker = objects[f"{agent_id}{SELECTION_MARKER_SUFFIX}"]

    assert len(agent.sprite.init_animation) > 0
    assert len(marker.sprite.init_animation) == len(agent.sprite.init_animation)

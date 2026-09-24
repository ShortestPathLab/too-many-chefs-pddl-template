from __future__ import annotations

from simulator.entities import OvercookedState
from simulator.environment import Environment
from simulator.mutations import Deliver, Interact, MoveAgentForward, TurnAgent
from simulator.view import cues_for_step
from tests.audio_kitchens import agent_id, kitchen, minimal, order, pass_kitchen, step


def _with_queue(environment: Environment, **changes) -> Environment:
    state = environment.get_first_entity_of_type(OvercookedState)
    assert state is not None
    return environment.with_entity(
        state.copy_with(order_queue=state.order_queue.copy_with(**changes))
    )


def test_a_delivery_is_heard_over_the_movement_that_produced_it() -> None:
    environment, server, _ = pass_kitchen()

    _, cues = step(
        environment,
        Deliver(agent_id=server.id),
        MoveAgentForward(agent_id=server.id),
    )

    assert cues == ["deliver", "tip"]


def test_a_delivery_silences_the_server_and_nobody_else() -> None:
    # The rules that decide a delivery is all you want to hear are claims
    # about the chef who served it. Reading them over the whole kitchen is
    # how a dish going out used to swallow the footsteps of everyone else.
    environment, server, runner = pass_kitchen()

    _, cues = step(
        environment,
        Deliver(agent_id=server.id),
        MoveAgentForward(agent_id=runner.id),
    )

    assert cues == ["deliver", "tip", "move"]


def test_a_queue_that_shrinks_without_a_delivery_expired() -> None:
    before = _with_queue(minimal(), visible=[order("a"), order("b")])
    after = _with_queue(before, visible=[order("a")], revision=1)

    assert cues_for_step(before, after, []) == ["order_expired"]


def test_a_queue_that_changes_without_shrinking_revealed() -> None:
    before = _with_queue(minimal(), visible=[order("a")])
    after = _with_queue(before, visible=[order("a"), order("b")], revision=1)

    assert cues_for_step(before, after, []) == ["order_revealed"]


def test_the_first_step_has_nothing_to_compare_against() -> None:
    environment = minimal()

    assert cues_for_step(None, environment, []) == []


def test_a_step_with_no_mutations_is_silent() -> None:
    environment = minimal()

    assert cues_for_step(environment, environment, []) == []
    assert cues_for_step(environment, environment, None) == []


def test_cues_come_back_in_a_stable_order() -> None:
    environment = kitchen()
    chef_id = agent_id(environment)
    forwards = cues_for_step(
        environment,
        environment,
        [
            TurnAgent(agent_id=chef_id, orientation="n"),
            Interact(agent_id=chef_id),
        ],
    )
    backwards = cues_for_step(
        environment,
        environment,
        [
            Interact(agent_id=chef_id),
            TurnAgent(agent_id=chef_id, orientation="n"),
        ],
    )

    assert forwards == backwards

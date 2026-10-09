from __future__ import annotations

from controllers.navigation import DefaultMutationInterpolationPolicy
from controllers.pddl.default_controller import DefaultPDDLController
from simulator.context import Context
from simulator.environment import filter_legal_actions
from simulator.mutations import (
    Cook,
    MoveAgent,
    MoveAgentForward,
    MutationWithLocation,
    PickUp,
    TurnAgent,
)
from tests.traffic_kitchens import chef, chef_location, kitchen, planned


def test_waiting_higher_priority_agent_still_reserves_current_position() -> None:
    waiting = chef("A", 2, 1)
    lower = chef("D", 2, 2, costume="red")
    environment = kitchen(4, 3, waiting, lower)
    controller = DefaultPDDLController()
    controller._has_planned = True
    controller._agent_ids = [waiting.id, lower.id]
    controller._plans = {
        waiting.id: [
            planned(
                0,
                Cook(
                    agent_id=waiting.id,
                    expected_held_food="catalog/food/batter",
                ),
                at=(2, 0),
            )
        ],
        lower.id: [planned(1, PickUp(agent_id=lower.id), at=(2, 0))],
    }

    actions = controller.get_actions(environment, Context())

    assert actions == [
        TurnAgent(agent_id=lower.id, orientation="w"),
        MoveAgent(agent_id=lower.id, dx=-1, dy=0),
    ]


def test_direct_move_into_higher_priority_current_position_is_deferred() -> None:
    lower = chef("lower", 0, 0, orientation="e")
    higher = chef("higher", 1, 0, costume="red")
    environment = kitchen(2, 1, lower, higher)
    lower_mutation = MutationWithLocation(
        mutation=MoveAgent(agent_id=lower.id, dx=1, dy=0),
        location=None,
    )

    mutations, updated_plans = DefaultMutationInterpolationPolicy().get_mutations(
        {
            higher.id: [planned(0, TurnAgent(agent_id=higher.id, orientation="n"))],
            lower.id: [(1, lower_mutation)],
        },
        environment,
        Context(),
    )

    assert mutations == [TurnAgent(agent_id=higher.id, orientation="n")]
    assert updated_plans[lower.id] == [(1, lower_mutation)]


def test_finished_agent_escapes_displacement_chain_before_moves_execute() -> None:
    first = chef("1", 0, 0, orientation="e")
    finished = chef("2", 1, 0, orientation="e", costume="red")
    third = chef("3", 0, 1, costume="green")
    environment = kitchen(3, 3, first, finished, third)
    controller = DefaultPDDLController()
    controller._has_planned = True
    controller._agent_ids = [first.id, finished.id, third.id]
    controller._plans = {
        third.id: [planned(0, MoveAgentForward(agent_id=third.id))],
        first.id: [planned(1, MoveAgentForward(agent_id=first.id))],
        finished.id: [],
    }

    actions = controller.get_actions(environment, Context())

    moves = [action for action in actions if isinstance(action, MoveAgent)]
    assert [move.agent_id for move in moves] == [finished.id, first.id, third.id]
    assert filter_legal_actions(environment, actions) == actions
    next_environment = environment.step(actions)
    assert chef_location(next_environment, finished.id) == (1, 1)
    assert chef_location(next_environment, first.id) == (1, 0)
    assert chef_location(next_environment, third.id) == (0, 0)


def test_cached_path_is_replanned_around_higher_priority_reservations() -> None:
    lower = chef("lower", 0, 0, orientation="e")
    higher = chef("higher", 2, 1, costume="red")
    environment = kitchen(4, 3, lower, higher)
    lower_mutation = MutationWithLocation(
        mutation=PickUp(agent_id=lower.id),
        location=(3, 0),
    )
    policy = DefaultMutationInterpolationPolicy()

    first_mutations, _ = policy.get_mutations(
        {lower.id: [(0, lower_mutation)]},
        environment,
        Context(),
    )
    for mutation in first_mutations:
        environment = mutation.run(environment)

    second_mutations, updated_plans = policy.get_mutations(
        {
            higher.id: [planned(0, MoveAgent(agent_id=higher.id, dx=0, dy=-1))],
            lower.id: [(1, lower_mutation)],
        },
        environment,
        Context(),
    )

    assert second_mutations == [
        MoveAgent(agent_id=higher.id, dx=0, dy=-1),
        TurnAgent(agent_id=lower.id, orientation="s"),
        MoveAgent(agent_id=lower.id, dx=0, dy=1),
    ]
    assert updated_plans[lower.id] == [(1, lower_mutation)]

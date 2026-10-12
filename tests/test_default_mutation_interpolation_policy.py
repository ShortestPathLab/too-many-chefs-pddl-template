from __future__ import annotations

from controllers.navigation import DefaultMutationInterpolationPolicy
from controllers.pddl.default_controller import DefaultPDDLController
from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.context import Context
from simulator.entities import Agent
from simulator.environment import Environment, filter_legal_actions
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


def _layout_kitchen(*rows: str) -> Environment:
    return load(
        Configuration.from_dict(
            {
                "layout": "\n".join(rows),
                "legend": {
                    "counters": [{"kind": "counter", "symbol": "-"}],
                    "foods": [
                        {"kind": "food", "symbol": "t", "name": "catalog/food/tomato"}
                    ],
                    "agents": [
                        {"kind": "agent", "symbol": "1"},
                        {"kind": "agent", "symbol": "2"},
                    ],
                },
            }
        )
    )


def _chef_at(environment: Environment, x: int, y: int) -> str:
    return next(
        agent.id
        for agent in environment.get_entities_of_type(Agent)
        if (agent.x, agent.y) == (x, y)
    )


def test_idle_chef_in_a_nook_is_pulled_out_and_stays_out() -> None:
    # The tomato's only free side is the nook, where chef two stands idle.
    environment = _layout_kitchen(
        "| - | - |-t | - |",
        "|   |   | 2 | - |",
        "| 1 |   | - | - |",
    )
    one = _chef_at(environment, 0, 2)
    two = _chef_at(environment, 2, 1)
    nook = (2, 1)
    policy = DefaultMutationInterpolationPolicy()
    plans = {
        one: [planned(0, PickUp(agent_id=one), at=(2, 0))],
        two: [],
    }

    left_nook = False
    for _ in range(8):
        actions, plans = policy.get_mutations(plans, environment, Context())
        assert filter_legal_actions(environment, actions) == actions
        environment = environment.step(actions)
        if chef_location(environment, two) != nook:
            left_nook = True
        elif left_nook:
            raise AssertionError("chef two stepped back into the nook")
        if not plans[one]:
            break

    assert plans[one] == []
    assert chef_location(environment, one) == nook


def test_chef_acting_this_tick_is_not_pushed() -> None:
    environment = _layout_kitchen(
        "| 1 | 2 |-t |",
        "|   |   | - |",
    )
    one = _chef_at(environment, 0, 0)
    two = _chef_at(environment, 1, 0)
    move = MutationWithLocation(
        mutation=MoveAgent(agent_id=one, dx=1, dy=0), location=None
    )

    mutations, updated_plans = DefaultMutationInterpolationPolicy().get_mutations(
        {
            one: [(0, move)],
            two: [planned(1, PickUp(agent_id=two), at=(2, 0))],
        },
        environment,
        Context(),
    )

    assert mutations == [
        TurnAgent(agent_id=two, orientation="e"),
        PickUp(agent_id=two),
    ]
    assert updated_plans == {one: [(0, move)], two: []}


def test_chefs_never_step_round_in_a_ring() -> None:
    # Each chef wants the next one's tile, clockwise. The simulator runs moves
    # one at a time, so none of them can go first.
    chefs = [
        chef("A", 0, 0, orientation="e"),
        chef("B", 1, 0, orientation="s"),
        chef("C", 1, 1, orientation="w"),
        chef("D", 0, 1, orientation="n"),
    ]
    environment = kitchen(2, 2, *chefs)
    plans = {
        standing.id: [planned(index, MoveAgentForward(agent_id=standing.id))]
        for index, standing in enumerate(chefs)
    }

    mutations, updated_plans = DefaultMutationInterpolationPolicy().get_mutations(
        plans, environment, Context()
    )

    assert mutations == []
    assert updated_plans == plans


def test_chef_walks_around_a_chef_it_does_not_drive() -> None:
    walker = chef("walker", 0, 0, orientation="e")
    stranger = chef("stranger", 1, 0, costume="red")
    environment = kitchen(3, 2, walker, stranger)

    mutations, _ = DefaultMutationInterpolationPolicy().get_mutations(
        {walker.id: [planned(0, PickUp(agent_id=walker.id), at=(2, 0))]},
        environment,
        Context(),
    )

    assert mutations == [
        TurnAgent(agent_id=walker.id, orientation="s"),
        MoveAgent(agent_id=walker.id, dx=0, dy=1),
    ]

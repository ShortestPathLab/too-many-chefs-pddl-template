"""Test order rewards and scoring."""

from __future__ import annotations

import pytest

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.entities import Agent, Delivery, Food, OvercookedState, Plate
from simulator.entities.orders import OrderEntry, OrderQueue
from simulator.mutations import Combine, Cook, Deliver, TakeFromStorage
from simulator.mutations.mutation import IllegalMutationError
from tests.scoring_states import CHOPPED_TOMATO, SALAD, TOMATO, scoring_state


def test_notify_methods_are_immutable_and_return_self_for_no_op() -> None:
    state = scoring_state()

    unchanged = state.notify_item_retrieved("catalog/food/unrelated")
    retrieved = state.notify_item_retrieved(TOMATO)
    prepared_component = retrieved.notify_item_prepared(CHOPPED_TOMATO)
    prepared_order = prepared_component.notify_item_prepared(SALAD)

    assert unchanged is state
    assert state.score == 0
    assert retrieved.score == 2
    assert prepared_component.score == 5
    assert prepared_order.score == 10


def test_plating_an_existing_ordered_item_does_not_score_as_preparation() -> None:
    environment = load(
        Configuration.from_dict(
            {
                "layout": "| A | p |",
                "state": {"orders": [SALAD]},
                "legend": {
                    "agents": [
                        {
                            "kind": "agent",
                            "symbol": "A",
                            "orientation": "e",
                            "held_item": {"name": SALAD},
                        }
                    ],
                    "plates": [{"kind": "plate", "symbol": "p"}],
                    "foods": [{"kind": "food", "name": SALAD}],
                },
            }
        )
    )
    agent = environment.get_first_entity_of_type(Agent)
    assert agent is not None

    plated = Combine(agent_id=agent.id).run(environment)
    state = plated.get_first_entity_of_type(OvercookedState)

    assert state is not None
    assert state.score == 0


def test_delivery_mutation_replaces_state_and_awards_order_reward() -> None:
    environment = load(
        Configuration.from_dict(
            {
                "layout": "| A | * |",
                "state": {"orders": [SALAD]},
                "legend": {
                    "agents": [
                        {
                            "kind": "agent",
                            "symbol": "A",
                            "orientation": "e",
                        }
                    ],
                    "deliveries": [{"kind": "delivery", "symbol": "*"}],
                    "foods": [{"kind": "food", "name": SALAD}],
                },
            }
        )
    )
    agent = environment.get_first_entity_of_type(Agent)
    delivery = environment.get_first_entity_of_type(Delivery)
    assert agent is not None
    assert delivery is not None
    food = Food(name=SALAD, x=None, y=None)
    plate = Plate(x=None, y=None, held_item_id=food.id)
    environment = (
        environment.with_entity(food)
        .with_entity(plate)
        .replace_entity(agent.copy_with(held_item_id=plate.id))
    )

    delivered = Deliver(agent_id=agent.id).run(environment)
    state = delivered.get_first_entity_of_type(OvercookedState)

    assert state is not None
    assert state.visible_orders == []
    assert state.score == 50
    assert state.order_revision == 1

    with pytest.raises(IllegalMutationError):
        Deliver(agent_id=agent.id).run(delivered)


# Each way of moving a step closer to an order pays out once.
def test_taking_a_component_from_storage_scores() -> None:
    environment = load(
        Configuration.from_dict(
            {
                "layout": "| A | T |",
                "state": {"orders": [CHOPPED_TOMATO]},
                "legend": {
                    "agents": [{"kind": "agent", "symbol": "A", "orientation": "e"}],
                    "storages": [
                        {
                            "kind": "storage",
                            "symbol": "T",
                            "food_name": TOMATO,
                        }
                    ],
                    "foods": [
                        {"kind": "food", "name": TOMATO},
                        {"kind": "food", "name": CHOPPED_TOMATO},
                    ],
                },
                "recipes": {
                    "cook": [
                        {
                            "ingredient": TOMATO,
                            "with": "catalog/equipment/cutboard",
                            "to_make": CHOPPED_TOMATO,
                        }
                    ]
                },
            }
        )
    )
    agent = environment.get_first_entity_of_type(Agent)
    assert agent is not None

    retrieved = TakeFromStorage(agent_id=agent.id).run(environment)

    state = retrieved.get_first_entity_of_type(OvercookedState)
    assert state is not None
    assert state.score == 1


def test_cooking_an_ordered_item_scores() -> None:
    environment = load(
        Configuration.from_dict(
            {
                "layout": "| A | P |",
                "state": {"orders": [CHOPPED_TOMATO]},
                "legend": {
                    "agents": [{"kind": "agent", "symbol": "A", "orientation": "e"}],
                    "equipment": [
                        {
                            "kind": "equipment",
                            "symbol": "P",
                            "name": "catalog/equipment/cutboard",
                            "held_item": {"name": TOMATO},
                        }
                    ],
                    "foods": [
                        {"kind": "food", "name": TOMATO},
                        {"kind": "food", "name": CHOPPED_TOMATO},
                    ],
                },
                "recipes": {
                    "cook": [
                        {
                            "ingredient": TOMATO,
                            "with": "catalog/equipment/cutboard",
                            "to_make": CHOPPED_TOMATO,
                        }
                    ]
                },
            }
        )
    )
    agent = environment.get_first_entity_of_type(Agent)
    assert agent is not None

    cooked = Cook(agent_id=agent.id).run(environment)

    state = cooked.get_first_entity_of_type(OvercookedState)
    assert state is not None
    assert state.score == 1


def test_combining_to_a_recipe_output_scores() -> None:
    environment = load(
        Configuration.from_dict(
            {
                "layout": "| A | - |",
                "state": {"orders": ["catalog/food/hamburger"]},
                "legend": {
                    "agents": [
                        {
                            "kind": "agent",
                            "symbol": "A",
                            "orientation": "e",
                            "held_item": {"name": "catalog/food/bun"},
                        }
                    ],
                    "counters": [
                        {
                            "kind": "counter",
                            "symbol": "-",
                            "held_item": {"name": "catalog/food/grilled_meat"},
                        }
                    ],
                    "foods": [
                        {"kind": "food", "name": "catalog/food/bun"},
                        {
                            "kind": "food",
                            "name": "catalog/food/grilled_meat",
                        },
                        {
                            "kind": "food",
                            "name": "catalog/food/hamburger",
                        },
                    ],
                },
                "recipes": {
                    "combine": [
                        {
                            "ingredients": [
                                "catalog/food/bun",
                                "catalog/food/grilled_meat",
                            ],
                            "to_make": "catalog/food/hamburger",
                        }
                    ]
                },
            }
        )
    )
    agent = environment.get_first_entity_of_type(Agent)
    assert agent is not None

    combined = Combine(agent_id=agent.id).run(environment)

    state = combined.get_first_entity_of_type(OvercookedState)
    assert state is not None
    assert state.score == 1


# A tip is paid once per order, so repeating a step cannot farm points.
def test_fetching_the_same_component_again_pays_nothing_more() -> None:
    state = scoring_state()

    first = state.notify_item_retrieved(TOMATO)
    second = first.notify_item_retrieved(TOMATO)
    third = second.notify_item_retrieved(TOMATO)

    # Two salad orders each owe one tomato tip.
    assert [first.score, second.score, third.score] == [2, 4, 4]
    assert third is second


def test_duplicate_orders_each_pay_their_own_tips() -> None:
    state = scoring_state()

    for _ in range(3):
        state = state.notify_item_prepared(CHOPPED_TOMATO)
        state = state.notify_item_prepared(SALAD)

    # Each of the two salads pays 3 for its chopped tomato and 5 for itself.
    assert state.score == 2 * (3 + 5)
    assert state.order_queue.tipped == {"": {CHOPPED_TOMATO: 2, SALAD: 2}}


def test_tipping_leaves_the_order_revision_alone() -> None:
    state = scoring_state()

    tipped = state.notify_item_retrieved(TOMATO)

    assert tipped.score == 2
    assert tipped.order_revision == state.order_revision
    assert tipped.visible_orders == state.visible_orders


def test_a_delivered_order_takes_its_tips_with_it() -> None:
    state = scoring_state(reveal="sequential")

    state = state.notify_item_retrieved(TOMATO)
    state = state.notify_item_retrieved(TOMATO)
    assert state.score == 2

    state = state.notify_item_delivered(SALAD, timestep=0)
    state = state.notify_item_retrieved(TOMATO)

    # The second salad was hidden until the first was served.
    assert state.score == 2 + 50 + 2


def test_each_team_earns_its_own_tips_for_a_shared_order() -> None:
    state = scoring_state(reveal="sequential")

    for team in ("red", "blue", "red", "blue"):
        state = state.notify_item_retrieved(TOMATO, agent_id=team, team=team)

    # One visible salad pays each side once, however often it fetches.
    assert state.score_by_agent == {"red": 2, "blue": 2}
    assert state.order_queue.tipped == {"red": {TOMATO: 1}, "blue": {TOMATO: 1}}


def test_an_order_served_with_food_tipped_for_another_gives_it_back() -> None:
    # Two different orders that both need a tomato.
    state = scoring_state().copy_with(
        order_queue=OrderQueue.from_orders(
            [OrderEntry(name=SALAD), OrderEntry(name=CHOPPED_TOMATO)]
        )
    )

    # One tomato is fetched and chopped, which tips once for each order's
    # count, and the chopped tomato is served on its own.
    state = state.notify_item_retrieved(TOMATO)
    state = state.notify_item_prepared(CHOPPED_TOMATO)
    state = state.notify_item_delivered(CHOPPED_TOMATO, timestep=0)
    served = state.score

    # The salad still needs its own tomato, and it pays in full.
    state = state.notify_item_retrieved(TOMATO)
    state = state.notify_item_prepared(CHOPPED_TOMATO)

    assert served == 2 + 5 + 50
    assert state.score == served + 2 + 3

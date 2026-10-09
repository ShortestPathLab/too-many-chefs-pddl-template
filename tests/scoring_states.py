"""A kitchen's rules and rewards, shared by the order and scoring tests."""

from __future__ import annotations

from typing import Literal

from simulator.entities import OrderEntry, OrderQueue, OvercookedState, ScoringState

TOMATO = "catalog/food/tomato"
CHOPPED_TOMATO = "catalog/food/chopped_tomato"
SALAD = "catalog/food/salad"


def scoring_state(
    *,
    reveal: Literal["all", "sequential"] = "all",
    time_limit: int | None = None,
) -> OvercookedState:
    """Return two salad orders and their recipe chain."""
    return OvercookedState(
        order_queue=OrderQueue.from_orders(
            [
                OrderEntry(name=SALAD, reward=50, time_limit=time_limit),
                OrderEntry(name=SALAD, reward=50, time_limit=time_limit),
            ],
            order_reveal=reveal,
        ),
        scoring=ScoringState(
            retrieve_order_component_reward=2,
            produce_order_component_reward=3,
            produce_ordered_item_reward=5,
        ),
        food_definitions={},
        cook_recipes=[
            {
                "ingredient": TOMATO,
                "equipment": "catalog/equipment/cutboard",
                "output": CHOPPED_TOMATO,
            }
        ],
        combine_recipes=[
            {
                "ingredients": [CHOPPED_TOMATO, "catalog/food/lettuce"],
                "output": SALAD,
            }
        ],
    )

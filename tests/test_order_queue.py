from __future__ import annotations

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.entities import (
    OrderEntry,
    OrderQueue,
    OvercookedState,
    ScoringState,
)
from tests.scoring_states import SALAD, scoring_state


def test_strict_ordering_only_accepts_first_visible_order() -> None:
    state = scoring_state().copy_with(
        order_queue=OrderQueue.from_orders(
            [
                OrderEntry(name=SALAD),
                OrderEntry(name="catalog/food/soup"),
            ],
            strict_ordering=True,
        )
    )

    assert state.accepts_dish(SALAD, 0)
    assert not state.accepts_dish("catalog/food/soup", 0)


def test_sequential_delivery_reveals_next_and_records_revision() -> None:
    state = scoring_state(reveal="sequential")

    delivered = state.notify_item_delivered(SALAD, timestep=4)

    assert state.visible_orders == [SALAD]
    assert delivered.visible_orders == [SALAD]
    assert delivered.order_revision == 1
    assert delivered.score == 50
    assert delivered.delivery_succeeded_previous_tick(5)
    assert not delivered.delivery_succeeded_previous_tick(4)
    assert delivered.order_queue.visible[0].revealed_at == 5


def test_time_limit_is_inclusive_and_expiration_reveals_next() -> None:
    state = scoring_state(reveal="sequential", time_limit=2)

    assert state.accepts_dish(SALAD, 2)
    advanced = state.advance_to_timestep(3)

    assert advanced is not state
    assert advanced.visible_orders == [SALAD]
    assert advanced.order_queue.visible[0].revealed_at == 3
    assert advanced.order_revision == 1
    assert advanced.score == 0


def test_environment_step_expires_orders_after_advancing_clock() -> None:
    environment = load(
        Configuration.from_dict(
            {
                "layout": "| |",
                "state": {"orders": [SALAD]},
                "rules": {
                    "order_reveal": "sequential",
                    "default_order_time_limit": 0,
                },
                "legend": {
                    "foods": [{"kind": "food", "name": SALAD}],
                },
            }
        )
    )

    advanced = environment.step([])
    state = advanced.get_first_entity_of_type(OvercookedState)

    assert state is not None
    assert advanced.timestep == 1
    assert state.visible_orders == []
    assert state.order_revision == 1


def test_per_order_reward_is_awarded_on_delivery() -> None:
    state = OvercookedState(
        order_queue=OrderQueue.from_orders(
            [OrderEntry(name=SALAD, reward=150)],
        ),
        scoring=ScoringState(),
    )

    delivered = state.notify_item_delivered(SALAD, timestep=0)

    assert delivered.score == 150


def test_per_order_time_limit_drives_expiry_independently() -> None:
    state = OvercookedState(
        order_queue=OrderQueue.from_orders(
            [
                OrderEntry(name=SALAD, time_limit=2),
                OrderEntry(name="catalog/food/soup", time_limit=10),
            ],
        ),
    )

    advanced = state.advance_to_timestep(3)

    # Only the tightly-timed order expires; the other survives.
    assert advanced.visible_orders == ["catalog/food/soup"]

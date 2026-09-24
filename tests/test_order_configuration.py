from __future__ import annotations

import pytest
from pydantic import ValidationError

from simulator.configuration.configuration import Configuration
from simulator.configuration.load.state import build_overcooked_state
from tests.scoring_states import SALAD


def test_configuration_rejects_negative_values_and_unknown_reveal() -> None:
    with pytest.raises(ValidationError):
        Configuration.from_dict({"scoring": {"default_order_reward": -1}})
    with pytest.raises(ValidationError):
        Configuration.from_dict({"rules": {"default_order_time_limit": -1}})
    with pytest.raises(ValidationError):
        Configuration.from_dict({"rules": {"order_reveal": "sometimes"}})
    with pytest.raises(ValidationError):
        Configuration.from_dict({"state": {"orders": [{"food": SALAD, "reward": -1}]}})


def test_orders_accept_string_and_object_forms_and_resolve_defaults() -> None:
    configuration = Configuration.from_dict(
        {
            "state": {
                "orders": [
                    SALAD,
                    {"food": SALAD, "reward": 150, "time_limit": 10},
                    {"food": SALAD},
                ]
            },
            "rules": {"default_order_time_limit": 20},
            "scoring": {"default_order_reward": 50},
            "legend": {"foods": [{"kind": "food", "name": SALAD}]},
        }
    )
    state = build_overcooked_state(configuration)
    visible = state.order_queue.visible

    assert [entry.name for entry in visible] == [SALAD, SALAD, SALAD]
    # Plain string inherits both defaults.
    assert (visible[0].reward, visible[0].time_limit) == (50, 20)
    # Object form overrides both.
    assert (visible[1].reward, visible[1].time_limit) == (150, 10)
    # Object with omitted fields inherits both defaults.
    assert (visible[2].reward, visible[2].time_limit) == (50, 20)

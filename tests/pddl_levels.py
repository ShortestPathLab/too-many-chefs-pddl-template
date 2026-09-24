"""Levels used by more than one of the PDDL tests."""

from __future__ import annotations

from simulator.configuration.configuration import Configuration


def coconut_juice_configuration() -> Configuration:
    """Return the smallest single-agent planning level."""
    return Configuration.from_dict(
        {
            "layout": (
                "|   |   |-/ |   | -p| -p|   |\n"
                "|   | C |   | 1 |   | * |   |\n"
                "|   |   |   |   |   | X |   |"
            ),
            "state": {"orders": ["catalog/food/coconut_juice"]},
            "legend": {
                "agents": [
                    {
                        "kind": "agent",
                        "symbol": "1",
                        "orientation": "s",
                    }
                ],
                "bins": [{"kind": "bin", "symbol": "X"}],
                "counters": [{"kind": "counter", "symbol": "-"}],
                "deliveries": [{"kind": "delivery", "symbol": "*"}],
                "equipment": [
                    {
                        "kind": "equipment",
                        "symbol": "/",
                        "name": "catalog/equipment/cutboard",
                    }
                ],
                "foods": [
                    {
                        "kind": "food",
                        "name": "catalog/food/coconut",
                    },
                    {
                        "kind": "food",
                        "name": "catalog/food/coconut_juice",
                    },
                ],
                "plates": [{"kind": "plate", "symbol": "p"}],
                "storages": [
                    {
                        "kind": "storage",
                        "symbol": "C",
                        "food_name": "catalog/food/coconut",
                    }
                ],
            },
            "recipes": {
                "cook": [
                    {
                        "ingredient": "catalog/food/coconut",
                        "with": "catalog/equipment/cutboard",
                        "to_make": "catalog/food/coconut_juice",
                    }
                ],
                "combine": [],
            },
        }
    )


def cutboard_reuse_configuration() -> Configuration:
    """Return a fruit salad level that reuses one board."""
    return Configuration.from_dict(
        {
            "layout": "| -/| -P| -p| * |\n| 1 |   |   |   |",
            "state": {"orders": ["catalog/food/fruit_salad"]},
            "legend": {
                "agents": [
                    {
                        "kind": "agent",
                        "symbol": "1",
                        "orientation": "n",
                        "held_item": {
                            "name": "catalog/food/watermelon",
                            "raw": True,
                        },
                    }
                ],
                "counters": [{"kind": "counter", "symbol": "-"}],
                "deliveries": [{"kind": "delivery", "symbol": "*"}],
                "equipment": [
                    {
                        "kind": "equipment",
                        "symbol": "/",
                        "name": "catalog/equipment/cutboard",
                    }
                ],
                "foods": [
                    {
                        "kind": "food",
                        "symbol": "P",
                        "name": "catalog/food/pineapple",
                    },
                    {
                        "kind": "food",
                        "name": "catalog/food/watermelon",
                    },
                    {
                        "kind": "food",
                        "name": "catalog/food/chopped_watermelon",
                        "raw": False,
                    },
                    {
                        "kind": "food",
                        "name": "catalog/food/chopped_pineapple",
                        "raw": False,
                    },
                    {
                        "kind": "food",
                        "name": "catalog/food/fruit_salad",
                        "raw": False,
                        "deliverable": True,
                    },
                ],
                "plates": [{"kind": "plate", "symbol": "p"}],
            },
            "recipes": {
                "cook": [
                    {
                        "ingredient": "catalog/food/watermelon",
                        "with": "catalog/equipment/cutboard",
                        "to_make": "catalog/food/chopped_watermelon",
                    },
                    {
                        "ingredient": "catalog/food/pineapple",
                        "with": "catalog/equipment/cutboard",
                        "to_make": "catalog/food/chopped_pineapple",
                    },
                ],
                "combine": [
                    {
                        "ingredients": [
                            "catalog/food/chopped_watermelon",
                            "catalog/food/chopped_pineapple",
                        ],
                        "to_make": "catalog/food/fruit_salad",
                    }
                ],
            },
        }
    )

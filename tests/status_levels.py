from __future__ import annotations

LEVEL = {
    "layout": "|1| |2|",
    "legend": {"agents": [{"symbol": "1"}, {"symbol": "2"}]},
}

PATTY = "catalog/food/patty"
PAN = "catalog/equipment/pan"

# Define sprites explicitly so these tests are independent of the catalog.
KITCHEN = {
    "layout": "|1|R|",
    "legend": {
        "agents": [{"symbol": "1"}],
        "equipment": [
            {
                "symbol": "R",
                "name": PAN,
                "can_pick_up": True,
                # Two cells wide, and hung above the counter it sits on, which
                # is what a panel sized to one cell used to cut off.
                "sprite": [
                    {
                        "x": 0,
                        "y": 16,
                        "width": 32,
                        "shift_y": -14,
                        "sheet": "custom.png",
                    }
                ],
            }
        ],
        "foods": [{"name": PATTY, "sprite": [{"x": 64, "y": 0, "sheet": "food.png"}]}],
    },
}

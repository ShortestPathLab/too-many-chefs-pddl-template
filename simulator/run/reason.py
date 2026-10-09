"""Why a run ended."""

from __future__ import annotations

from typing import Literal

TerminationReason = Literal[
    "completed",
    "gave_up",
    "time_limit",
    "max_timesteps",
    "orders_delivered",
    "planning_budget_exhausted",
    "stopped",
    "error",
]

"""Build run end conditions from command-line options."""

from __future__ import annotations

import typer

from simulator.configuration import Configuration
from simulator.run import EndConditions


def build_end_conditions(
    configuration: Configuration,
    *,
    headless: bool,
    time_limit: float | None,
    max_timesteps: int | None,
    planning_budget: float | None,
    end_on_orders_delivered: bool,
    end_on_budget_exhausted: bool,
) -> EndConditions:
    """Build end conditions and validate unbounded headless runs.

    An infinite-order level needs a time limit, timestep limit, or an exhausted
    planning budget when run headlessly.
    """
    if headless and configuration.rules.infinite_orders:
        bounded = (
            time_limit is not None
            or max_timesteps is not None
            or (planning_budget is not None and end_on_budget_exhausted)
        )
        if not bounded:
            raise typer.BadParameter(
                "Headless runs of infinite-order levels need --time-limit,"
                " --max-timesteps, or a planning budget that can expire.",
                param_hint="--time-limit",
            )

    return EndConditions(
        time_limit_seconds=time_limit,
        max_timesteps=max_timesteps,
        end_on_orders_delivered=end_on_orders_delivered,
        end_on_budget_exhausted=end_on_budget_exhausted,
    )

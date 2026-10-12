"""Conditions that can end a run."""

from __future__ import annotations

from pydantic import Field

from simulator.controller import Controller
from simulator.entities import OvercookedState
from simulator.environment import Environment
from simulator.models import FrozenSimulatorModel
from simulator.planning_budget import all_budgets_exhausted

from .reason import TerminationReason


class EndConditions(FrozenSimulatorModel):
    """Configured run end conditions.

    Conditions are checked in a fixed order. The first matching condition is
    reported when several match on the same timestep.
    """

    #: Wall-clock limit measured from run start.
    time_limit_seconds: float | None = Field(default=None, ge=0)
    #: Maximum simulation timestep.
    max_timesteps: int | None = Field(default=None, ge=0)
    end_on_orders_delivered: bool = False
    #: End when all finite controller budgets are exhausted.
    end_on_budget_exhausted: bool = True

    def reached(
        self,
        environment: Environment,
        controller: Controller | None,
        *,
        elapsed_seconds: float,
    ) -> TerminationReason | None:
        """Return the matching end reason, or ``None`` to continue.

        Without a controller there are no planning budgets to run out.
        """
        if (
            self.time_limit_seconds is not None
            and elapsed_seconds >= self.time_limit_seconds
        ):
            return "time_limit"
        if (
            self.max_timesteps is not None
            and environment.timestep >= self.max_timesteps
        ):
            return "max_timesteps"
        if self.end_on_orders_delivered and every_order_delivered(environment):
            return "orders_delivered"
        if self.end_on_budget_exhausted and all_budgets_exhausted(controller):
            return "planning_budget_exhausted"
        return None


def every_order_delivered(environment: Environment) -> bool:
    """Return whether every order has been delivered.

    Expired orders prevent this from returning true. Infinite-order queues do
    not become empty while they are generating new orders.
    """
    state = environment.get_first_entity_of_type(OvercookedState)
    if state is None:
        return False
    queue = state.order_queue
    return not queue.visible and not queue.pending and not queue.expired_count

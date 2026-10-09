from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

from simulator.mutations.mutation import Mutation

if TYPE_CHECKING:
    from simulator.environment import Environment


class TickMutation(Mutation, ABC):
    """World effect the environment applies once per step.

    Tick mutations run after the chefs' mutations and before the timestep
    advances. No agent performs them, so they are not recorded with the step's
    actions. They never raise ``IllegalMutationError``: with nothing to do, they
    return the environment unchanged.
    """

    def pending(self, environment: Environment) -> bool:
        """Return whether a step with no chef actions would change anything."""
        return False

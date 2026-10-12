from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from simulator.models import SimulatorModel
from simulator.mutations.virtual_input import VirtualInput
from simulator.types import Location


class Mutation(SimulatorModel, ABC):
    """Operation that transforms the environment."""

    @abstractmethod
    def run(self, environment: Environment) -> Environment:
        """Return a modified environment."""

    @abstractmethod
    def describe(self, environment: Environment) -> str:
        """Return a simple description of the mutation."""

    def virtual_input(self, environment: Environment) -> VirtualInput | None:
        """Return the virtual input represented by this mutation, if any."""
        return None


@dataclass(frozen=True)
class MutationWithLocation:
    mutation: Mutation
    location: Location | None


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulator.environment import Environment


class IllegalMutationError(ValueError):
    pass


def expected_matches(expected: str | None, actual: str | None) -> bool:
    return expected is None or expected == actual


def can_apply_mutation(
    environment: Environment,
    *mutations: Mutation,
) -> bool:
    try:
        for mutation in mutations:
            environment = mutation.run(environment)
        return True
    except IllegalMutationError:
        return False

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities import (
    Agent,
    Bin,
    Delivery,
    Equipment,
    PlateDispenser,
    Sink,
    Storage,
    get_first_game_object_of_type_at,
)
from simulator.mutations.agent_mutation import AgentMutation
from simulator.mutations.cook import Cook
from simulator.mutations.deliver import Deliver
from simulator.mutations.discard import Discard
from simulator.mutations.mutation import IllegalMutationError
from simulator.mutations.take_from_storage import TakeFromStorage
from simulator.mutations.virtual_input import VirtualInput
from simulator.mutations.wash import Wash

if TYPE_CHECKING:
    from simulator.environment import Environment


def interaction_at(
    environment: Environment,
    x: int,
    y: int,
) -> type[AgentMutation] | None:
    """Return what interacting with the cell at ``(x, y)`` does, if anything."""
    if get_first_game_object_of_type_at(environment, x, y, Bin):
        return Discard
    if get_first_game_object_of_type_at(environment, x, y, Sink):
        return Wash
    if get_first_game_object_of_type_at(environment, x, y, Delivery):
        return Deliver
    if get_first_game_object_of_type_at(
        environment, x, y, Storage
    ) or get_first_game_object_of_type_at(environment, x, y, PlateDispenser):
        return TakeFromStorage
    if get_first_game_object_of_type_at(environment, x, y, Equipment):
        return Cook
    return None


class Interact(AgentMutation):
    kind: Literal["interact"] = "interact"

    def describe(self, environment: Environment) -> str:
        return f"{self.agent_id} interacts"

    def virtual_input(self, environment: Environment) -> VirtualInput | None:
        return "a"

    def run(self, environment: Environment) -> Environment:
        agent = environment.get_entity_as(self.agent_id, Agent)
        if not agent:
            raise IllegalMutationError()

        mutation_type = interaction_at(environment, *agent.looking_at)
        if not mutation_type:
            raise IllegalMutationError()

        return mutation_type(**self.agent_mutation_args).run(environment)

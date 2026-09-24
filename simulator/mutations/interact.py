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

        target_x, target_y = agent.looking_at
        mutation_type: type[AgentMutation] | None = None
        if get_first_game_object_of_type_at(environment, target_x, target_y, Bin):
            mutation_type = Discard
        elif get_first_game_object_of_type_at(environment, target_x, target_y, Sink):
            mutation_type = Wash
        elif get_first_game_object_of_type_at(
            environment, target_x, target_y, Delivery
        ):
            mutation_type = Deliver
        elif get_first_game_object_of_type_at(
            environment, target_x, target_y, Storage
        ) or get_first_game_object_of_type_at(
            environment, target_x, target_y, PlateDispenser
        ):
            mutation_type = TakeFromStorage
        elif get_first_game_object_of_type_at(
            environment, target_x, target_y, Equipment
        ):
            mutation_type = Cook

        if not mutation_type:
            raise IllegalMutationError()

        return mutation_type(**self.agent_mutation_args).run(environment)

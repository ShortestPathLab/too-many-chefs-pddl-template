from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities import Agent, Equipment, Food
from simulator.mutations.agent_mutation import AgentMutation
from simulator.mutations.combine import Combine, get_facing_food, get_top_equipment_at
from simulator.mutations.mutation import IllegalMutationError
from simulator.mutations.pick_up import PickUp
from simulator.mutations.place import Place
from simulator.mutations.virtual_input import VirtualInput

if TYPE_CHECKING:
    from simulator.environment import Environment


class PickUpOrPlace(AgentMutation):
    kind: Literal["pick_up_or_place"] = "pick_up_or_place"

    def describe(self, environment: Environment) -> str:
        return f"{self.agent_id} picks up, places, or combines item"

    def virtual_input(self, environment: Environment) -> VirtualInput | None:
        return "b"

    def run(self, environment: Environment) -> Environment:
        agent = environment.get_entity_as(self.agent_id, Agent)
        if not agent:
            raise IllegalMutationError()

        mutation_type: type[AgentMutation]
        if agent.hands_free:
            mutation_type = PickUp
        else:
            mutation_type = _held_item_mutation_type(environment, agent)

        return mutation_type(**self.agent_mutation_args).run(environment)


def _held_item_mutation_type(
    environment: Environment,
    agent: Agent,
) -> type[AgentMutation]:
    if not agent.held_item_id:
        raise IllegalMutationError()

    held_item = environment.get_entity(agent.held_item_id)
    target_x, target_y = agent.looking_at
    facing_food = get_facing_food(environment, target_x, target_y)
    facing_equipment = get_top_equipment_at(environment, target_x, target_y)
    facing_equipment_has_food = bool(facing_equipment and facing_equipment.held_item_id)
    held_equipment_has_food = isinstance(held_item, Equipment) and bool(
        held_item.held_item_id
    )

    if isinstance(held_item, Food) and (facing_food or facing_equipment):
        return Combine
    if isinstance(held_item, Equipment) and (
        facing_food
        or facing_equipment_has_food
        or (held_equipment_has_food and facing_equipment)
    ):
        return Combine
    return Place

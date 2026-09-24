from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities import (
    Agent,
    Equipment,
    OvercookedState,
    Plate,
    PlateDispenser,
    Storage,
    get_first_game_object_of_type_at,
)
from simulator.mutations.agent_mutation import AgentMutation
from simulator.mutations.combine.combine_food_into_held_equipment import (
    combine_food_into_held_equipment,
)
from simulator.mutations.mutation import IllegalMutationError, expected_matches
from simulator.mutations.virtual_input import VirtualInput
from simulator.utils import required

if TYPE_CHECKING:
    from simulator.environment import Environment


class TakeFromStorage(AgentMutation):
    kind: Literal["take_from_storage"] = "take_from_storage"

    def describe(self, environment: Environment) -> str:
        return f"{self.agent_id} takes from storage"

    def virtual_input(self, environment: Environment) -> VirtualInput | None:
        return "a"

    def run(self, environment: Environment) -> Environment:
        agent = environment.get_entity_as(self.agent_id, Agent)
        state = environment.get_first_entity_of_type(OvercookedState)
        if not agent or not state:
            raise IllegalMutationError()

        target_x, target_y = agent.looking_at
        storage = get_first_game_object_of_type_at(
            environment, target_x, target_y, Storage
        )
        if not storage:
            return self._take_plate(environment, agent, target_x, target_y)
        if not expected_matches(self.expected_input_name, storage.food_name):
            raise IllegalMutationError()

        food = required(
            state.create_food(storage.food_name, x=None, y=None),
            message=f"Missing food definition for {storage.food_name}",
        )
        updated_state = state.notify_item_retrieved(
            food.name, agent_id=self.agent_id, team=agent.team
        )

        if agent.hands_free:
            if not expected_matches(self.expected_output_name, food.name):
                raise IllegalMutationError()
            return environment.with_entity(food).replace_entity(
                agent.copy_with(held_item_id=food.id),
                updated_state,
            )

        held_equipment = environment.get_entity_as(
            required(agent.held_item_id), Equipment
        )
        if held_equipment:
            placed_environment = combine_food_into_held_equipment(
                environment.with_entity(food),
                state,
                held_equipment=held_equipment,
                source_food=food,
                counter=None,
                expected_output_name=self.expected_output_name,
            )
            if placed_environment:
                return placed_environment.replace_entity(updated_state)

        raise IllegalMutationError()

    def _take_plate(
        self,
        environment: Environment,
        agent: Agent,
        target_x: int,
        target_y: int,
    ) -> Environment:
        dispenser = get_first_game_object_of_type_at(
            environment, target_x, target_y, PlateDispenser
        )
        if not dispenser or not dispenser.has_plate:
            raise IllegalMutationError()
        if not agent.hands_free:
            raise IllegalMutationError()

        plate = Plate(x=None, y=None, dirty=dispenser.dispenses_dirty)
        return environment.with_entity(plate).replace_entity(
            agent.copy_with(held_item_id=plate.id),
            dispenser.take_plate(),
        )

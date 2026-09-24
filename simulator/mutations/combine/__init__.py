from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities import Agent, Equipment, Food, OvercookedState
from simulator.entities.teams import team_of
from simulator.mutations.advance_cooking import start_timers_for_new_food
from simulator.mutations.agent_mutation import AgentMutation
from simulator.mutations.mutation import IllegalMutationError, expected_matches
from simulator.mutations.virtual_input import VirtualInput

from .combine_equipment_into_equipment import combine_equipment_into_equipment
from .combine_facing_equipment_into_held_equipment import (
    combine_facing_equipment_into_held_equipment,
)
from .combine_food_into_equipment import combine_food_into_equipment
from .combine_food_into_hand import combine_food_into_hand
from .combine_food_into_held_equipment import combine_food_into_held_equipment
from .combine_from_equipment import combine_from_equipment
from .combine_from_food import combine_from_food
from .common import (
    get_counter_item,
    get_equipments_at,
    get_facing_food,
    get_top_equipment_at,
    held_food,
    matches_equipment_expectations,
)

if TYPE_CHECKING:
    from simulator.environment import Environment


class Combine(AgentMutation):
    kind: Literal["combine"] = "combine"

    def describe(self, environment: Environment) -> str:
        return f"{self.agent_id} combines item"

    def virtual_input(self, environment: Environment) -> VirtualInput | None:
        return "b"

    def run(self, environment: Environment) -> Environment:
        agent = environment.get_entity_as(self.agent_id, Agent)
        state = environment.get_first_entity_of_type(OvercookedState)
        if not agent or not agent.held_item_id or not state:
            raise IllegalMutationError()

        held_item = environment.get_entity(agent.held_item_id)
        target_x, target_y = agent.looking_at
        if isinstance(held_item, Equipment):
            equipment_food = held_food(environment, held_item)
            if not matches_equipment_expectations(
                equipment=held_item,
                expected_equipment_name=self.expected_held_equipment_name,
                expected_contents_name=self.expected_held_equipment_contents_name,
                contents_name=equipment_food.name if equipment_food else None,
            ):
                raise IllegalMutationError()
            combined_environment = combine_from_equipment(
                environment,
                state,
                agent,
                held_item,
                target_x,
                target_y,
                expected_target_food_name=self.expected_target_food_name,
                expected_target_equipment_name=self.expected_target_equipment_name,
                expected_target_equipment_contents_name=self.expected_target_equipment_contents_name,
                expected_output_name=self.expected_output_name,
            )
            if combined_environment:
                return self._finish(environment, combined_environment, state)
            raise IllegalMutationError()

        if isinstance(held_item, Food):
            if not expected_matches(self.expected_held_food, held_item.name):
                raise IllegalMutationError()
            combined_environment = combine_from_food(
                environment,
                state,
                agent,
                held_item,
                target_x,
                target_y,
                expected_target_food_name=self.expected_target_food_name,
                expected_target_equipment_name=self.expected_target_equipment_name,
                expected_target_equipment_contents_name=self.expected_target_equipment_contents_name,
                expected_output_name=self.expected_output_name,
            )
            if combined_environment:
                return self._finish(environment, combined_environment, state)
            raise IllegalMutationError()
        raise IllegalMutationError()

    def _finish(
        self,
        before: Environment,
        after: Environment,
        state: OvercookedState,
    ) -> Environment:
        after = _notify_prepared_food(before, after, state, agent_id=self.agent_id)
        return start_timers_for_new_food(before, after, agent_id=self.agent_id)


def _notify_prepared_food(
    before: Environment,
    after: Environment,
    state: OvercookedState,
    *,
    agent_id: str | None = None,
) -> Environment:
    before_foods = {food.id: food for food in before.get_entities_of_type(Food)}
    after_foods = {food.id: food for food in after.get_entities_of_type(Food)}
    removed = [
        food for food_id, food in before_foods.items() if food_id not in after_foods
    ]
    created = [
        food for food_id, food in after_foods.items() if food_id not in before_foods
    ]
    if len(created) != 1 or not removed:
        return after

    output = created[0]
    transformed = len(removed) > 1 or removed[0].name != output.name
    if not transformed:
        return after

    updated_state = state.notify_item_prepared(
        output.name, agent_id=agent_id, team=team_of(before, agent_id)
    )
    return after.replace_entity(updated_state)


__all__ = [
    "Combine",
    "combine_equipment_into_equipment",
    "combine_facing_equipment_into_held_equipment",
    "combine_food_into_equipment",
    "combine_food_into_hand",
    "combine_food_into_held_equipment",
    "combine_from_equipment",
    "combine_from_food",
    "get_counter_item",
    "get_equipments_at",
    "get_facing_food",
    "get_top_equipment_at",
]

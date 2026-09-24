from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities import Agent, Food, OvercookedState
from simulator.entities.equipment import CookingTimer
from simulator.mutations.agent_mutation import AgentMutation
from simulator.mutations.combine import get_equipments_at
from simulator.mutations.cooking import (
    current_timer,
    has_required_support,
    replace_with_cooked_food,
)
from simulator.mutations.mutation import IllegalMutationError, expected_matches
from simulator.mutations.virtual_input import VirtualInput
from simulator.utils import RequiredValueError, required

if TYPE_CHECKING:
    from simulator.environment import Environment


class Cook(AgentMutation):
    """Work the food in the facing station.

    Each press counts towards the station's ``cook_time``, and the food cooks on
    the press that reaches it. Stations that cook by themselves refuse it.
    """

    kind: Literal["cook"] = "cook"

    def describe(self, environment: Environment) -> str:
        return f"{self.agent_id} cooks"

    def virtual_input(self, environment: Environment) -> VirtualInput | None:
        return "a"

    def run(self, environment: Environment) -> Environment:
        cooks_by_itself = False
        try:
            agent = required(environment.get_entity_as(self.agent_id, Agent))
            state = required(environment.get_first_entity_of_type(OvercookedState))
            target_x, target_y = agent.looking_at
            equipments = get_equipments_at(environment, target_x, target_y)
            for equipment in equipments:
                try:
                    held_item_id = required(equipment.held_item_id)
                    food = required(
                        environment.get_entity_as(held_item_id, Food),
                        message=f"Equipment {equipment.id} held non-food item {held_item_id}",
                    )
                    if equipment.cooks_by_itself:
                        cooks_by_itself = True
                        continue
                    if not has_required_support(environment, equipment):
                        continue
                    if not expected_matches(self.expected_held_food, food.name):
                        continue
                    if not expected_matches(self.expected_input_name, equipment.name):
                        continue
                    output_name = required(
                        state.resolve_cook_output(
                            food.name,
                            equipment.name,
                            timestep=environment.timestep,
                        ),
                        message=f"Missing cook recipe for {food.name} with {equipment.name}",
                    )
                    if not expected_matches(self.expected_output_name, output_name):
                        continue
                    timer = current_timer(equipment, food) or CookingTimer(
                        food_id=food.id
                    )
                    timer = timer.copy_with(elapsed=timer.elapsed + 1)
                    if timer.elapsed < equipment.cook_time:
                        return environment.replace_entity(
                            equipment.copy_with(cooking=timer)
                        )
                    return replace_with_cooked_food(
                        environment,
                        state,
                        equipment.copy_with(cooking=None),
                        food,
                        output_name,
                        agent_id=self.agent_id,
                    )
                except RequiredValueError:
                    continue
        except RequiredValueError:
            pass
        if cooks_by_itself:
            raise IllegalMutationError("this station cooks by itself")
        raise IllegalMutationError()

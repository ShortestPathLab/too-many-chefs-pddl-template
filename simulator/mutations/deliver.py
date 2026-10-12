from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from simulator.entities import (
    Agent,
    Delivery,
    Food,
    OvercookedState,
    Plate,
    PlateDispenser,
    get_first_game_object_of_type_at,
)
from simulator.mutations.agent_mutation import AgentMutation
from simulator.mutations.mutation import IllegalMutationError, expected_matches
from simulator.mutations.virtual_input import VirtualInput

if TYPE_CHECKING:
    from simulator.environment import Environment


class Deliver(AgentMutation):
    kind: Literal["deliver"] = "deliver"

    def describe(self, environment: Environment) -> str:
        return f"{self.agent_id} delivers item"

    def virtual_input(self, environment: Environment) -> VirtualInput | None:
        return "a"

    def run(self, environment: Environment) -> Environment:
        agent = environment.get_entity_as(self.agent_id, Agent)
        state = environment.get_first_entity_of_type(OvercookedState)
        if not agent or not agent.held_item_id or not state:
            raise IllegalMutationError()

        target_x, target_y = agent.looking_at
        delivery = get_first_game_object_of_type_at(
            environment, target_x, target_y, Delivery
        )
        if not delivery:
            raise IllegalMutationError()

        held_plate = environment.get_entity_as(agent.held_item_id, Plate)
        if not held_plate or not held_plate.held_item_id or held_plate.dirty:
            raise IllegalMutationError()
        if not expected_matches(self.expected_held_equipment_name, held_plate.name):
            raise IllegalMutationError()

        food = environment.get_entity_as(held_plate.held_item_id, Food)
        if (
            not food
            or not delivery.accepts(food)
            or not state.accepts_dish(food.name, environment.timestep)
        ):
            raise IllegalMutationError()
        if not expected_matches(self.expected_held_food, food.name):
            raise IllegalMutationError()
        if not expected_matches(
            self.expected_held_equipment_contents_name,
            food.name,
        ):
            raise IllegalMutationError()
        if not expected_matches(self.expected_output_name, food.name):
            raise IllegalMutationError()

        updated_state = state.notify_item_delivered(
            food.name,
            environment.timestep,
            agent_id=self.agent_id,
        )
        if updated_state is state:
            raise IllegalMutationError()

        delivered_environment = (
            environment.without_entity(food.id)
            .without_entity(held_plate.id)
            .replace_entity(
                agent.copy_with(held_item_id=None),
                updated_state,
            )
        )
        return _return_plate_to_dispenser(delivered_environment)


def _return_plate_to_dispenser(environment: Environment) -> Environment:
    """Return the consumed plate to the first plate dispenser, if any exists.

    Keeps plates a conserved resource so infinite-order levels never run out.
    When there is no dispenser the plate is simply discarded, as before.
    """
    dispenser = next(
        iter(
            sorted(
                environment.get_entities_of_type(PlateDispenser),
                key=lambda dispenser: (
                    dispenser.y if dispenser.y is not None else -1,
                    dispenser.x if dispenser.x is not None else -1,
                    dispenser.id,
                ),
            )
        ),
        None,
    )
    if dispenser is None:
        return environment
    return environment.replace_entity(dispenser.return_plate())

from typing import Annotated

from pydantic import Field

from simulator.mutations.advance_cooking import AdvanceCooking
from simulator.mutations.agent_mutation import AgentMutation
from simulator.mutations.combine import Combine
from simulator.mutations.cook import Cook
from simulator.mutations.deliver import Deliver
from simulator.mutations.discard import Discard
from simulator.mutations.interact import Interact
from simulator.mutations.move_agent import MoveAgent
from simulator.mutations.move_agent_forward import MoveAgentForward
from simulator.mutations.mutation import Mutation, MutationWithLocation
from simulator.mutations.pick_up import PickUp
from simulator.mutations.pick_up_or_place import PickUpOrPlace
from simulator.mutations.place import Place
from simulator.mutations.take_from_storage import TakeFromStorage
from simulator.mutations.tick_mutation import TickMutation
from simulator.mutations.turn_agent import TurnAgent
from simulator.mutations.virtual_input import (
    ARROWS,
    DIRECTIONS,
    FACE_BUTTONS,
    ORIENTATION_INPUTS,
    VirtualInput,
    step_input,
)
from simulator.mutations.wash import Wash

MutationModel = Annotated[
    Combine
    | Cook
    | Discard
    | Deliver
    | Interact
    | MoveAgent
    | MoveAgentForward
    | PickUp
    | PickUpOrPlace
    | Place
    | TakeFromStorage
    | TurnAgent
    | Wash,
    Field(discriminator="kind"),
]

# World effects an environment applies every step. Add new kinds to this union.
TickMutationModel = Annotated[AdvanceCooking, Field(discriminator="kind")]

__all__ = [
    "ARROWS",
    "DIRECTIONS",
    "FACE_BUTTONS",
    "ORIENTATION_INPUTS",
    "AdvanceCooking",
    "AgentMutation",
    "Combine",
    "Cook",
    "Deliver",
    "Discard",
    "Interact",
    "MoveAgent",
    "MoveAgentForward",
    "Mutation",
    "MutationModel",
    "MutationWithLocation",
    "PickUp",
    "PickUpOrPlace",
    "Place",
    "TakeFromStorage",
    "TickMutation",
    "TickMutationModel",
    "TurnAgent",
    "VirtualInput",
    "Wash",
    "step_input",
]

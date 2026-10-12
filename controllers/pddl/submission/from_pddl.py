"""Translate PDDL plans using a minimal example implementation.

``DefaultPDDLController`` creates a ``DefaultFromPDDL`` instance with the
environment used to generate the plan, then calls ``from_pddl`` in a worker
process with the solver's steps. Each ``PDDLPlanStep`` contains an action name
and its arguments, exactly as returned by the solver, for example
``pick_up empty_plate loc_2_0``. The domain has no chef type, so steps do not
name a chef; every step is assigned to the first chef in the kitchen.

``translate`` supports the three actions defined in ``overcooked.pddl``.
Each step produces one mutation and the location the chef must face to
perform it. For each action added to the domain, add a corresponding branch
to ``translate``.

A mutation is one action in the simulator, such as ``PickUp`` or ``Deliver``.
The plan does not include movement. For each mutation, the controller moves
the chef to an adjacent tile, turns it towards the target location, and
applies the mutation once it is legal. Until then, execution of that chef's
plan remains at the current step.
"""

from __future__ import annotations

import re

from controllers.pddl.interfaces import FromPDDL, PDDLPlanStep
from simulator.entities import Agent, OvercookedState
from simulator.entities.plate import PLATE_NAME
from simulator.environment import Environment
from simulator.mutations import Combine, Deliver, MutationWithLocation, PickUp
from simulator.types import Location

# These names match problem_generator.py: EMPTY_PLATE denotes a clean, empty
# plate; DISH_PREFIX precedes the food name for a plate containing food, so
# plated_catalog_food_coconut_juice is a plate of coconut juice.
EMPTY_PLATE = "empty_plate"
DISH_PREFIX = "plated_"


class DefaultFromPDDL(FromPDDL):
    """Translate a symbolic plan into simulator mutations.

    The environment is the same one supplied to ``to_pddl``, allowing plan
    symbols to be resolved to the corresponding food and steps to be assigned
    to the chef.

    The environment is a snapshot taken when planning starts. The kitchen
    state may change before a step executes, for example if another chef
    moves an item. Each mutation's ``expected_*`` fields check the relevant
    conditions against the state at execution.
    """

    def __init__(self, environment: Environment) -> None:
        self._environment = environment

    def from_pddl(self, steps: list[PDDLPlanStep]) -> list[MutationWithLocation]:
        """Translate all steps in plan order.

        The controller carries out the mutations in the order returned.
        """
        plan: list[MutationWithLocation] = []
        for step in steps:
            plan.append(self.translate(step))
        return plan

    def translate(self, step: PDDLPlanStep) -> MutationWithLocation:
        """Convert one plan step to a mutation and the location it acts on.

        ``step.parameters`` contains arguments in the order declared by the
        action's ``:parameters`` in overcooked.pddl. Each branch below
        unpacks the arguments in that order.

        The ``expected_*`` fields specify what the chef should be holding and
        facing. If the kitchen state no longer meets these conditions, the
        mutation is illegal and the chef waits. A field left as None is not
        checked.
        """
        chef_id = self.chef_id()
        if step.name == "pick_up":
            item, location = step.parameters
            if is_plate(item):
                # Plates are equipment, so PickUp checks the equipment name
                # and contents. food_on_plate returns None for empty_plate,
                # which disables the contents check; this step therefore
                # does not verify that the plate is empty.
                mutation = PickUp(
                    agent_id=chef_id,
                    expected_held_equipment_name=PLATE_NAME,
                    expected_held_equipment_contents_name=self.food_on_plate(item),
                )
            else:
                # Loose food is checked by its kitchen name.
                mutation = PickUp(
                    agent_id=chef_id,
                    expected_input_name=self.food_name(item),
                )
        elif step.name == "add_to_plate":
            # The chef holds ?plate and faces ?food at ?location. Combine adds
            # the food to the plate. expected_output_name checks that the
            # resulting dish matches ?result.
            plate, food, location, result = step.parameters
            mutation = Combine(
                agent_id=chef_id,
                expected_held_equipment_name=PLATE_NAME,
                expected_held_equipment_contents_name=self.food_on_plate(plate),
                expected_target_food_name=self.food_name(food),
                expected_output_name=self.food_on_plate(result),
            )
        elif step.name == "deliver":
            # Deliver requires a delivery tile and a plate containing an
            # ordered dish.
            plate, location = step.parameters
            mutation = Deliver(
                agent_id=chef_id,
                expected_held_equipment_name=PLATE_NAME,
                expected_held_food=self.food_on_plate(plate),
            )
        else:
            # An unsupported action terminates the run with an error
            # identifying the step.
            raise ValueError(f"No translation for this action yet: {step}")
        # location is the tile the chef acts on, not the tile it stands on.
        return MutationWithLocation(
            mutation=mutation, location=parse_location(location)
        )

    def chef_id(self) -> str:
        """Return the ID of the chef that performs every step.

        Plan steps do not specify a chef, so all steps are assigned to the
        first chef in the kitchen.
        """
        return self._environment.get_entities_of_type(Agent)[0].id

    # --- Resolving PDDL symbols -----------------------------------------------
    #
    # These methods reverse the naming used in problem_generator.py.
    # Changes to the naming convention must be applied to both files.

    def food_name(self, symbol: str) -> str:
        """Return the kitchen food name corresponding to ``symbol``.

        ``pddl_name`` is not invertible because it replaces several distinct
        characters with ``_``. This method searches the level's food
        definitions for a name that produces ``symbol``.
        """
        state = self._environment.get_first_entity_of_type(OvercookedState)
        if state is not None:
            for food_name in state.food_definitions:
                if pddl_name(food_name) == symbol:
                    return food_name
        raise ValueError(f"Unknown food in plan: {symbol}")

    def food_on_plate(self, symbol: str) -> str | None:
        """Return the food name for a plate symbol, or None for an empty plate.

        For example, ``plated_catalog_food_coconut_juice`` gives
        ``catalog/food/coconut_juice``.
        """
        if symbol == EMPTY_PLATE:
            return None
        if symbol.startswith(DISH_PREFIX):
            return self.food_name(symbol.removeprefix(DISH_PREFIX))
        raise ValueError(f"Unknown plate in plan: {symbol}")


def is_plate(symbol: str) -> bool:
    """Return whether ``symbol`` names a plate rather than loose food."""
    return symbol == EMPTY_PLATE or symbol.startswith(DISH_PREFIX)


def parse_location(symbol: str) -> Location:
    """Extract tile coordinates from a location symbol such as ``loc_2_0``.

    This reverses ``location_symbol`` in problem_generator.py: ``loc_2_0`` is
    the tile at x = 2, y = 0.
    """
    match = re.fullmatch(r"loc_(\d+)_(\d+)", symbol)
    if match is None:
        raise ValueError(f"Unknown location in plan: {symbol}")
    return int(match.group(1)), int(match.group(2))


def pddl_name(value: str) -> str:
    """Convert a kitchen name to PDDL using the problem_generator.py convention.

    This duplicates ``pddl_name`` in problem_generator.py, where the naming
    rules are documented. It can also be imported from that module to maintain
    a single implementation.
    """
    return re.sub(r"[^0-9a-z_]+", "_", value.lower()).strip("_")

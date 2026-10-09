"""Generate PDDL problems using a minimal example implementation.

``DefaultPDDLController`` creates one ``DefaultProblemGenerator`` instance and
calls ``to_pddl`` in a worker process whenever a plan is required. The solver's
result is then passed to ``DefaultFromPDDL`` in ``from_pddl.py``.

This implementation and the domain in ``overcooked.pddl`` model the kitchen
operations required to complete
``levels/0_i_can_cook/0_0_coconut_juice_finished_on_counter.yaml``. The juice is
already prepared; the chef must collect a plate, place the juice on it and
deliver it.

The model does not include storage, stations, recipes or counter
reachability. For levels requiring these features, the solver finds no plan
and the chefs remain idle.

A PDDL problem has three parts:

- objects that a plan can reference, each with a type from the domain,
  such as ``loc_2_0 - location``;
- initial facts describing the current state, such as
  ``(item_at empty_plate loc_2_0)``;
- goals specifying the required final state, such as
  ``(delivered plated_catalog_food_coconut_juice)``.

The planner uses only the information supplied in the domain and problem.
If a plan omits a kitchen operation, or the solver finds no plan, check that
the problem includes the relevant state. ``print(problem.to_pddl())`` in
``build_problem`` displays the problem supplied to the planner.

Extend the existing example rather than replacing it. ``build_problem`` calls
a ``describe_*`` function for each aspect of the kitchen to add the relevant
objects, facts and goals to a ``ProblemBuilder``, which writes the problem
file. To extend the model, define another ``describe_*`` function, call it
from ``build_problem``, and add domain actions that use the new facts.
"""

from __future__ import annotations

import re
from collections.abc import Collection
from pathlib import Path

from controllers.pddl.interfaces import PDDLProblem, ProblemGenerator
from controllers.pddl.problem_builder import ProblemBuilder
from simulator.entities import (
    Agent,
    Counter,
    Delivery,
    Food,
    GameObject,
    OvercookedState,
    Plate,
)
from simulator.environment import Environment

# The domain is shared by all levels; to_pddl supplies this file unchanged.
DOMAIN_PATH = Path(__file__).with_name("overcooked.pddl")

# The domain represents plates by their contents, without distinguishing
# individual plates. All clean, empty plates use EMPTY_PLATE; plates
# containing food use ``dish_symbol``.
EMPTY_PLATE = "empty_plate"


class DefaultProblemGenerator(ProblemGenerator):
    """Generate a PDDL problem from the kitchen state and determine when to replan.

    The inherited ``ProblemGenerator.should_replan`` retains the current plan
    until all steps have been executed. Override this method if the controller
    needs to respond to changes in the kitchen state before then.
    """

    def to_pddl(
        self,
        environment: Environment,
        controlled_agent_ids: Collection[str] | None = None,
    ) -> PDDLProblem:
        """Return the domain and a problem for ``environment``.

        ``controlled_agent_ids`` identifies the chefs assigned to this
        controller. Other chefs remain in the kitchen as obstacles. ``None``
        assigns all chefs to this controller.

        This method runs in a separate worker process. Changes it makes to
        ``self`` are therefore not visible to ``should_replan``, which runs
        in the simulator process.
        """
        chef = the_chef(environment, controlled_agent_ids)
        return PDDLProblem(
            domain=build_domain(), problem=build_problem(environment, chef)
        )


def build_domain() -> str:
    """Return the text of overcooked.pddl."""
    return DOMAIN_PATH.read_text(encoding="utf-8")


def build_problem(environment: Environment, chef: Agent | None) -> str:
    """Describe the kitchen as a problem for the domain in overcooked.pddl.

    Every object symbol used in a fact or goal must be declared with ``add_object``.
    ``describe_food`` declares the food and plate symbols that the other
    functions use in their facts.
    """
    # domain_name must match the "(define (domain overcooked)" line in
    # overcooked.pddl, or the planner rejects the problem. problem_name can be
    # any PDDL name.
    problem = ProblemBuilder(domain_name="overcooked", problem_name="kitchen")
    describe_food(environment, problem)
    describe_chef(environment, chef, problem)
    describe_counters(environment, problem)
    describe_deliveries(environment, problem)
    describe_orders(environment, problem)
    return problem.to_pddl()


# --- Kitchen description ----------------------------------------------------


def describe_food(environment: Environment, problem: ProblemBuilder) -> None:
    """Declare a symbol for each food in the level and for a plate holding it.

    ``food_definitions`` lists the level's ingredients, intermediate foods
    and finished dishes. Each has a food symbol and a plated symbol,
    regardless of whether an order requires its plated form.

    Food and its plated form are separate objects, allowing the plan to
    distinguish which the chef is carrying. A ``plating`` fact relates them:
    ``(plating empty_plate catalog_food_coconut_juice
    plated_catalog_food_coconut_juice)`` specifies that adding coconut juice
    to an empty plate produces a plate of coconut juice.
    """
    empty_plate = problem.add_object(EMPTY_PLATE, "plate")
    for food_name in kitchen_state(environment).food_definitions:
        food = problem.add_object(food_symbol(food_name), "food")
        dish = problem.add_object(dish_symbol(food_name), "plate")
        problem.add_fact(f"(plating {empty_plate} {food} {dish})")


def describe_chef(
    environment: Environment, chef: Agent | None, problem: ProblemBuilder
) -> None:
    """Record what the chef is holding.

    The chef is not a PDDL object: ``hand_empty`` and ``holding`` describe the
    chef that performs every action. To plan for several chefs, the domain
    would require a chef type and a chef parameter in these facts.

    If there is no chef to plan for, or ``item_symbol`` cannot represent the
    held item, neither fact is added and the solver finds no plan.
    """
    if chef is None:
        return
    if chef.held_item_id is None:
        problem.add_fact("(hand_empty)")
        return
    held = item_symbol(environment, chef.held_item_id)
    if held is not None:
        problem.add_fact(f"(holding {held})")


def describe_counters(environment: Environment, problem: ProblemBuilder) -> None:
    """Record the items on counters.

    Counters containing supported items are represented by location objects
    named by their grid positions, such as ``loc_1_0``. Empty counters are
    omitted because this domain has no action for putting an item down.
    Adding such an action would require those counters to be included.
    Items that ``item_symbol`` cannot represent, such as dirty plates, are
    also omitted from the planner's model.
    """
    for counter in environment.get_entities_of_type(Counter):
        if counter.held_item_id is None:
            continue
        item = item_symbol(environment, counter.held_item_id)
        if item is None:
            continue
        location = problem.add_object(location_symbol(counter), "location")
        problem.add_fact(f"(item_at {item} {location})")


def describe_deliveries(environment: Environment, problem: ProblemBuilder) -> None:
    """Identify delivery locations for plated food.

    Delivery tiles become location objects, named after their grid position
    in the same way as counters.
    """
    for delivery in environment.get_entities_of_type(Delivery):
        location = problem.add_object(location_symbol(delivery), "location")
        problem.add_fact(f"(delivery_location {location})")


def describe_orders(environment: Environment, problem: ProblemBuilder) -> None:
    """Add a goal to deliver each visible order on a plate.

    ``ProblemBuilder`` combines goals with ``and``, requiring the plan to
    satisfy all of them. Orders for the same dish produce identical goals,
    which the builder includes only once. This example therefore serves
    that dish once; serving duplicate orders requires distinct goals.
    """
    for order in kitchen_state(environment).visible_orders:
        problem.add_goal(f"(delivered {dish_symbol(order)})")


# --- Environment access -----------------------------------------------------


def the_chef(
    environment: Environment, controlled_agent_ids: Collection[str] | None
) -> Agent | None:
    """Return the chef that performs every action in the plan.

    Returns the first chef assigned to this controller, or None if no chef
    is assigned. from_pddl.py assigns every plan step to the first chef in
    the kitchen. These selections agree when the kitchen has a single chef.
    """
    chefs = environment.get_entities_of_type(Agent)
    if controlled_agent_ids is not None:
        chefs = [chef for chef in chefs if chef.id in controlled_agent_ids]
    return chefs[0] if chefs else None


def kitchen_state(environment: Environment) -> OvercookedState:
    """Return the entity containing orders, recipes and food definitions.

    This information applies to the entire kitchen and is stored in a single
    ``OvercookedState`` entity.
    """
    state = environment.get_first_entity_of_type(OvercookedState)
    if state is None:
        raise ValueError("The environment has no OvercookedState")
    return state


# --- PDDL names --------------------------------------------------------------
#
# Each problem object has a symbol, which the planner uses in its output.
# These functions define the naming convention. from_pddl.py uses the same
# convention to resolve plan symbols to kitchen names; changes must be
# applied consistently in both files.


def item_symbol(environment: Environment, item_id: str) -> str | None:
    """Return the symbol for an item, or None if this example cannot describe it.

    Food uses ``food_symbol``. Clean plates are represented by their contents,
    using ``EMPTY_PLATE`` or ``dish_symbol``. Unsupported items, such as dirty
    plates or pots, return None and are omitted by the ``describe_*`` functions.
    """
    item = environment.get_entity(item_id)
    if isinstance(item, Food):
        return food_symbol(item.name)
    if isinstance(item, Plate) and not item.dirty:
        if item.held_item_id is None:
            return EMPTY_PLATE
        food = environment.get_entity_as(item.held_item_id, Food)
        if food is not None:
            return dish_symbol(food.name)
    return None


def food_symbol(food_name: str) -> str:
    """Return the symbol for a food, such as ``catalog_food_coconut_juice``."""
    return pddl_name(food_name)


def dish_symbol(food_name: str) -> str:
    """Return the symbol for a plate holding ``food_name``.

    For coconut juice this is ``plated_catalog_food_coconut_juice``.
    """
    return "plated_" + pddl_name(food_name)


def location_symbol(tile: GameObject) -> str:
    """Return the symbol for a tile's grid position, such as ``loc_2_0``.

    The symbol is ``loc_{x}_{y}``. No two tiles share a position, so no two
    share a symbol.
    """
    return f"loc_{tile.x}_{tile.y}"


def pddl_name(value: str) -> str:
    """Convert a kitchen name to a PDDL symbol.

    PDDL names may contain only letters, digits, ``-`` and ``_``, and must
    start with a letter. Kitchen names such as ``catalog/food/coconut_juice``
    contain ``/`` and cannot be used unchanged. This function converts names
    to lower case, replaces each run of other characters with ``_`` and trims
    ``_`` from both ends, so ``catalog/food/coconut_juice`` becomes
    ``catalog_food_coconut_juice``.

    Planners return names in lower case. Generating lower-case symbols ensures
    that the returned names match those used for lookup in from_pddl.py.

    ``ProblemBuilder.add_object`` raises ``ValueError`` for a name that still
    violates these rules, such as one that starts with a digit.
    """
    return re.sub(r"[^0-9a-z_]+", "_", value.lower()).strip("_")

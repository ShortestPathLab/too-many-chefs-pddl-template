"""The example planner students start from: every chef turns around.

The student template replaces ``problem_generator.py`` and ``from_pddl.py``
with thin wrappers around this module, and ``overcooked.pddl`` with the
matching domain; see template/README.md. The
example deliberately models nothing about the kitchen beyond chefs and the
way they face. It is there to show the pipeline running, not to hint at how
to model cooking.

Keeping it here rather than in the overlays means it is imported with absolute
paths, so ty checks it in master and the master suite can run it.
"""

from __future__ import annotations

import re
from collections.abc import Collection

from controllers.pddl.interfaces import PDDLPlanStep
from simulator.entities import Agent
from simulator.environment import Environment
from simulator.mutations import MutationWithLocation, TurnAgent

DIRECTIONS = ("n", "e", "s", "w")
OPPOSITE = {"n": "s", "s": "n", "e": "w", "w": "e"}


def controlled_chefs(
    environment: Environment, controlled_agent_ids: Collection[str] | None
) -> list[Agent]:
    """Return the chefs the plan may move, in a stable order."""
    chefs = environment.get_entities_of_type(Agent)
    if controlled_agent_ids is not None:
        wanted = set(controlled_agent_ids)
        chefs = [chef for chef in chefs if chef.id in wanted]
    return sorted(chefs, key=lambda chef: chef.id)


def build_demo_problem(chefs: list[Agent]) -> str:
    """Describe the chefs' current orientations and ask for the opposite."""
    objects = [f"{chef_symbol(chef)} - chef" for chef in chefs]
    objects += [f"{direction} - direction" for direction in DIRECTIONS]
    init = [f"(facing {chef_symbol(chef)} {chef.orientation})" for chef in chefs]
    goal = [
        f"(facing {chef_symbol(chef)} {OPPOSITE[chef.orientation]})" for chef in chefs
    ]
    return (
        "(define (problem turn-around)\n"
        "  (:domain kitchen-demo)\n"
        f"  (:objects {' '.join(objects)})\n"
        f"  (:init {' '.join(init)})\n"
        f"  (:goal (and {' '.join(goal)})))\n"
    )


def turns_to_mutations(
    environment: Environment, steps: list[PDDLPlanStep]
) -> list[MutationWithLocation]:
    """Translate ``turn`` steps into ``TurnAgent`` mutations.

    Turning happens where the chef stands, so the location is ``None``. An
    interaction with a station or counter would carry that tile instead, and
    the controller would walk the chef there first.
    """
    plan: list[MutationWithLocation] = []
    for step in steps:
        if step.name != "turn":
            raise ValueError(f"Unsupported action in plan: {step}")
        chef, _facing, to = step.parameters
        if to not in DIRECTIONS:
            raise ValueError(f"Unknown direction in plan step: {step}")
        mutation = TurnAgent(agent_id=resolve_chef(environment, chef), orientation=to)
        plan.append(MutationWithLocation(mutation=mutation, location=None))
    return plan


def chef_symbol(chef: Agent) -> str:
    """Name a chef in PDDL.

    Agent ids can hold characters PDDL does not allow, and solvers lower-case
    what they echo back, so the symbol is normalised here and matched
    case-insensitively by ``resolve_chef``.
    """
    return "chef_" + pddl_symbol(chef.id)


def resolve_chef(environment: Environment, symbol: str) -> str:
    """Map a chef's PDDL symbol back to its agent id."""
    for chef in environment.get_entities_of_type(Agent):
        if chef_symbol(chef) == symbol.lower():
            return chef.id
    raise ValueError(f"Unknown chef in plan: {symbol}")


def pddl_symbol(value: object) -> str:
    """Reduce any value to a PDDL-safe, lower-case identifier."""
    normalised = re.sub(r"[^0-9A-Za-z_]+", "_", str(value)).strip("_").lower()
    return normalised or "value"

"""Limit each chef's actions within a simulation step.

Each step permits one turn and a configurable number of movements or other
actions per chef. The default is one, matching a single play-mode input.
``TurnAgent`` represents a turn. All other agent mutations, including
``MoveAgent``, count towards the action limit.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from simulator.mutations.agent_mutation import AgentMutation
from simulator.mutations.mutation import Mutation
from simulator.mutations.turn_agent import TurnAgent


def limit_actions_per_chef(mutations: Iterable[Mutation], limit: int) -> list[Mutation]:
    """Return permitted mutations for this step, with turns first.

    Retain each chef's first turn and first ``limit`` movements or other
    actions. Excess mutations are discarded before execution and cannot
    replace retained actions that fail legality checks. Turns precede all
    other mutations so chefs face the requested direction before moving or
    acting. Mutations without a chef retain their order among the remaining
    non-turn mutations.
    """
    turns: list[Mutation] = []
    rest: list[Mutation] = []
    turned: set[str] = set()
    acted: Counter[str] = Counter()
    for mutation in mutations:
        if not isinstance(mutation, AgentMutation):
            rest.append(mutation)
        elif isinstance(mutation, TurnAgent):
            if mutation.agent_id not in turned:
                turned.add(mutation.agent_id)
                turns.append(mutation)
        elif acted[mutation.agent_id] < limit:
            acted[mutation.agent_id] += 1
            rest.append(mutation)
    return turns + rest

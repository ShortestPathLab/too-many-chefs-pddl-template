"""Your plan translator, wired to a small working example.

``DefaultPDDLController`` builds a ``DefaultFromPDDL`` around the environment
the plan was made for and calls ``from_pddl`` in a worker process with the
solver's steps. Each ``PDDLPlanStep`` is the action name and its arguments,
exactly as the solver printed them, for example ``turn chef_alfred s n``.

As shipped, ``from_pddl`` hands the steps to ``demo.py``, which only knows the
``turn`` action from the example domain. It shows how a step's symbols are
resolved back to entities and how a mutation is paired with the tile where it
has to happen. The contract you have to meet is under "The Files You Will
Edit" in getting-started.md. Replace the example with a translator for your
own domain.
"""

from __future__ import annotations

from controllers.pddl.interfaces import FromPDDL, PDDLPlanStep
from controllers.pddl.submission.demo import turns_to_mutations
from simulator.environment import Environment
from simulator.mutations import MutationWithLocation


class DefaultFromPDDL(FromPDDL):
    """Translate a symbolic plan into simulator mutations.

    The environment is the one ``to_pddl`` saw, so symbols in the plan can be
    resolved back to the entities they came from.
    """

    def __init__(self, environment: Environment) -> None:
        self._environment = environment

    def from_pddl(self, steps: list[PDDLPlanStep]) -> list[MutationWithLocation]:
        return turns_to_mutations(self._environment, steps)

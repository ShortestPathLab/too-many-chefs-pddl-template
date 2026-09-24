"""Your problem generator, wired to a small working example.

``DefaultPDDLController`` builds one ``DefaultProblemGenerator`` and calls its
``to_pddl`` in a worker process whenever it needs a plan. The solver's answer
then goes to ``DefaultFromPDDL`` in ``from_pddl.py``.

As shipped, the plan is deliberately trivial: every chef turns to face the
opposite way. The domain is in ``overcooked.pddl`` and the problem comes from
``demo.py``, which reads the chefs off the environment and names them in a way
``from_pddl`` can reverse. The contract you have to meet is under "The Files
You Will Edit" in getting-started.md. Replace the example with your own model
of the kitchen; ``demo.py`` can go once nothing imports it.
"""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path

from controllers.pddl.interfaces import PDDLProblem, ProblemGenerator
from controllers.pddl.submission.demo import build_demo_problem, controlled_chefs
from simulator.environment import Environment

DOMAIN_PATH = Path(__file__).with_name("overcooked.pddl")


class DefaultProblemGenerator(ProblemGenerator):
    """Build a PDDL problem from the kitchen and decide when to replan.

    ``should_replan`` is inherited from ``ProblemGenerator`` and keeps the
    first plan until it runs out. Override it once your controller needs to
    react to the kitchen changing.
    """

    def to_pddl(
        self,
        environment: Environment,
        controlled_agent_ids: Collection[str] | None = None,
    ) -> PDDLProblem:
        """Return the domain and a problem for ``environment``.

        ``controlled_agent_ids`` names the chefs this controller owns. Other
        chefs are still in the kitchen, as obstacles. ``None`` means every
        chef is yours.
        """
        chefs = controlled_chefs(environment, controlled_agent_ids)
        return PDDLProblem(domain=build_domain(), problem=build_demo_problem(chefs))


def build_domain() -> str:
    return DOMAIN_PATH.read_text(encoding="utf-8")

"""Write a PDDL problem from its objects, initial facts and goals.

``ProblemBuilder`` collects and formats PDDL problem definitions without
kitchen-specific logic. Problem generators supply objects, facts and goals.
Names and parentheses are validated when added, so errors are reported during
problem construction.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from types import MappingProxyType

# PDDL names begin with a letter, followed by letters, digits, "-" or "_".
PDDL_NAME = re.compile(r"[A-Za-z][-_A-Za-z0-9]*")


class ProblemBuilder:
    """Collect the objects, initial facts and goals of a PDDL problem.

    Facts and goals are PDDL text, such as ``"(at truck depot)"``. Adding the
    same fact or goal twice keeps one copy. ``to_pddl`` joins the goals with
    ``and``.

    For example::

        problem = ProblemBuilder(domain_name="logistics")
        truck = problem.add_object("truck", "vehicle")
        depot = problem.add_object("depot", "location")
        problem.add_fact(f"(at {truck} {depot})")
        problem.add_goal(f"(delivered {truck})")
        problem.to_pddl()
    """

    def __init__(self, domain_name: str, problem_name: str = "instance") -> None:
        self.domain_name = _pddl_name("Domain name", domain_name)
        self.problem_name = _pddl_name("Problem name", problem_name)
        self._objects: dict[str, str] = {}
        self._facts: dict[str, None] = {}
        self._goals: dict[str, None] = {}
        self._metric: str | None = None

    @property
    def objects(self) -> Mapping[str, str]:
        """Each declared object's name, mapped to its type."""
        return MappingProxyType(self._objects)

    @property
    def facts(self) -> tuple[str, ...]:
        """The initial facts, in the order they were first added."""
        return tuple(self._facts)

    @property
    def goals(self) -> tuple[str, ...]:
        """The goals, in the order they were first added."""
        return tuple(self._goals)

    def add_object(self, name: str, pddl_type: str) -> str:
        """Declare ``name`` as an object of ``pddl_type`` and return ``name``.

        Declaring an object again with the same type does nothing. Declaring
        it with a different type raises ``ValueError``.
        """
        _pddl_name("Object name", name)
        _pddl_name("Type", pddl_type)
        declared = self._objects.setdefault(name, pddl_type)
        if declared != pddl_type:
            raise ValueError(
                f"Object {name!r} is already declared as a {declared!r},"
                f" so it cannot also be a {pddl_type!r}"
            )
        return name

    def add_fact(self, fact: str) -> None:
        """Add ``fact``, such as ``"(at truck depot)"``, to the initial state."""
        self._facts[_formula("Fact", fact)] = None

    def add_goal(self, goal: str) -> None:
        """Add ``goal``, such as ``"(delivered truck)"``, to the goals."""
        self._goals[_formula("Goal", goal)] = None

    def set_metric(self, metric: str) -> None:
        """Set the plan metric, such as ``"minimize (total-cost)"``."""
        direction, _, expression = metric.strip().partition(" ")
        if direction not in ("minimize", "maximize") or not expression.strip():
            raise ValueError(
                f"Metric {metric!r} must be 'minimize' or 'maximize'"
                " followed by an expression"
            )
        self._metric = f"{direction} {expression.strip()}"

    def to_pddl(self) -> str:
        """Return the problem as PDDL text, one object or fact per line."""
        objects = "".join(
            f"    {name} - {pddl_type}\n" for name, pddl_type in self._objects.items()
        )
        facts = "".join(f"    {fact}\n" for fact in self._facts)
        goals = "".join(f"      {goal}\n" for goal in self._goals)
        metric = "" if self._metric is None else f"  (:metric {self._metric})\n"
        return (
            f"(define (problem {self.problem_name})\n"
            f"  (:domain {self.domain_name})\n"
            f"  (:objects\n{objects}  )\n"
            f"  (:init\n{facts}  )\n"
            f"  (:goal\n    (and\n{goals}    )\n  )\n"
            f"{metric}"
            ")\n"
        )


def _pddl_name(kind: str, name: str) -> str:
    if not PDDL_NAME.fullmatch(name):
        raise ValueError(
            f"{kind} {name!r} is not a PDDL name: use letters, digits, '-' and"
            " '_', starting with a letter"
        )
    return name


def _formula(kind: str, text: str) -> str:
    formula = text.strip()
    if not _is_one_formula(formula):
        raise ValueError(
            f"{kind} {text!r} is not one formula in parentheses,"
            " such as '(at truck depot)'"
        )
    return formula


def _is_one_formula(text: str) -> bool:
    """Return whether ``text`` contains one formula with balanced parentheses."""
    if not text.startswith("("):
        return False
    depth = 0
    for index, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index == len(text) - 1
    return False

"""Test the PDDL problem builder that problem generators write with."""

from __future__ import annotations

import pytest

from controllers.pddl import PDDLPlanStep, PDDLProblem, ProblemBuilder
from tests.pddl_solving import solve_for_test

DOMAIN = """
(define (domain logistics)
  (:requirements :strips :typing)
  (:types vehicle location)
  (:predicates
    (at ?vehicle - vehicle ?location - location)
    (road ?from - location ?to - location)
  )
  (:action drive
    :parameters (?vehicle - vehicle ?from - location ?to - location)
    :precondition (and (at ?vehicle ?from) (road ?from ?to))
    :effect (and (at ?vehicle ?to) (not (at ?vehicle ?from)))
  )
)
"""


def logistics_problem() -> ProblemBuilder:
    problem = ProblemBuilder(domain_name="logistics", problem_name="delivery")
    truck = problem.add_object("truck", "vehicle")
    depot = problem.add_object("depot", "location")
    shop = problem.add_object("shop", "location")
    problem.add_fact(f"(at {truck} {depot})")
    problem.add_fact(f"(road {depot} {shop})")
    problem.add_goal(f"(at {truck} {shop})")
    return problem


def test_writes_one_object_fact_and_goal_per_line() -> None:
    assert logistics_problem().to_pddl() == (
        "(define (problem delivery)\n"
        "  (:domain logistics)\n"
        "  (:objects\n"
        "    truck - vehicle\n"
        "    depot - location\n"
        "    shop - location\n"
        "  )\n"
        "  (:init\n"
        "    (at truck depot)\n"
        "    (road depot shop)\n"
        "  )\n"
        "  (:goal\n"
        "    (and\n"
        "      (at truck shop)\n"
        "    )\n"
        "  )\n"
        ")\n"
    )


def test_the_written_problem_solves() -> None:
    problem = PDDLProblem(domain=DOMAIN, problem=logistics_problem().to_pddl())
    assert solve_for_test(problem) == [
        PDDLPlanStep("drive", ("truck", "depot", "shop"))
    ]


def test_add_object_returns_the_name() -> None:
    assert ProblemBuilder("logistics").add_object("truck", "vehicle") == "truck"


def test_declaring_an_object_again_with_its_type_keeps_one() -> None:
    problem = ProblemBuilder("logistics")
    problem.add_object("truck", "vehicle")
    problem.add_object("truck", "vehicle")
    assert dict(problem.objects) == {"truck": "vehicle"}


def test_declaring_an_object_with_a_second_type_raises() -> None:
    problem = ProblemBuilder("logistics")
    problem.add_object("truck", "vehicle")
    with pytest.raises(ValueError, match="already declared as a 'vehicle'"):
        problem.add_object("truck", "location")


@pytest.mark.parametrize("name", ["", "1st_truck", "catalog/food/rice", "a b"])
def test_rejects_names_pddl_cannot_hold(name: str) -> None:
    with pytest.raises(ValueError, match="is not a PDDL name"):
        ProblemBuilder("logistics").add_object(name, "vehicle")


def test_rejects_a_type_pddl_cannot_hold() -> None:
    with pytest.raises(ValueError, match="Type 'big truck' is not a PDDL name"):
        ProblemBuilder("logistics").add_object("truck", "big truck")


def test_repeated_facts_and_goals_appear_once_in_first_order() -> None:
    problem = ProblemBuilder("logistics")
    problem.add_fact("(road depot shop)")
    problem.add_fact("(at truck depot)")
    problem.add_fact(" (road depot shop) ")
    problem.add_goal("(at truck shop)")
    problem.add_goal("(at truck shop)")
    assert problem.facts == ("(road depot shop)", "(at truck depot)")
    assert problem.goals == ("(at truck shop)",)


@pytest.mark.parametrize(
    "fact",
    ["hand_empty", "(at truck depot", "(at truck depot))", "(a) (b)", ""],
)
def test_rejects_a_fact_that_is_not_one_formula(fact: str) -> None:
    with pytest.raises(ValueError, match="is not one formula in parentheses"):
        ProblemBuilder("logistics").add_fact(fact)


def test_accepts_nested_formulas() -> None:
    problem = ProblemBuilder("logistics")
    problem.add_fact("(= (total-cost) 0)")
    problem.add_goal("(or (at truck shop) (at truck depot))")
    assert problem.facts == ("(= (total-cost) 0)",)
    assert problem.goals == ("(or (at truck shop) (at truck depot))",)


def test_writes_the_metric_after_the_goal() -> None:
    problem = ProblemBuilder("logistics")
    problem.set_metric("minimize (total-cost)")
    assert problem.to_pddl().endswith("  )\n  (:metric minimize (total-cost))\n)\n")


def test_rejects_a_metric_without_a_direction() -> None:
    with pytest.raises(ValueError, match="must be 'minimize' or 'maximize'"):
        ProblemBuilder("logistics").set_metric("(total-cost)")


def test_an_empty_problem_still_has_every_section() -> None:
    assert ProblemBuilder("logistics").to_pddl() == (
        "(define (problem instance)\n"
        "  (:domain logistics)\n"
        "  (:objects\n  )\n"
        "  (:init\n  )\n"
        "  (:goal\n    (and\n    )\n  )\n"
        ")\n"
    )

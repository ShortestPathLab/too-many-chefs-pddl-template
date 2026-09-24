"""Parse plans returned by PDDL planners.

The supported format is one parenthesized action per line, such as
``(action arg arg)``.
"""

from __future__ import annotations

from pathlib import Path

from ..interfaces import PDDLPlanStep


def parse_plan_step(line: str) -> PDDLPlanStep | None:
    """Parse one ``(action arg arg)`` line, or ``None`` if it is not a step."""
    stripped = line.strip()
    if not stripped or stripped.startswith(";"):
        return None
    if not (stripped.startswith("(") and stripped.endswith(")")):
        return None
    tokens = stripped[1:-1].split()
    if not tokens:
        return None
    return PDDLPlanStep(name=tokens[0], parameters=tuple(tokens[1:]))


def parse_sas_plan(plan_path: Path) -> list[PDDLPlanStep]:
    """Read a Fast Downward style plan file."""
    plan: list[PDDLPlanStep] = []
    for raw_line in plan_path.read_text(encoding="utf-8").splitlines():
        step = parse_plan_step(raw_line)
        if step is not None:
            plan.append(step)
    return plan

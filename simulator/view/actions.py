from __future__ import annotations

import re

from pydantic import Field

from simulator.environment import Environment
from simulator.models import FrozenSimulatorModel
from simulator.recording import Recording

DEFAULT_LIMIT = 6


class ActionLine(FrozenSimulatorModel):
    """One line in the action log."""

    step: int
    text: str
    current: bool = False


class ActionsView(FrozenSimulatorModel):
    """Action log data, oldest line first."""

    lines: list[ActionLine] = Field(default_factory=list)
    empty_label: str = "Nothing yet"


def actions_view(
    recording: Recording,
    environment: Environment,
    *,
    order: list[str] | None = None,
    limit: int = DEFAULT_LIMIT,
) -> ActionsView:
    """Return recent steps that changed the environment.

    Steps where every mutation was refused are omitted.
    """
    index = environment_index_for(recording, environment)
    if index is None:
        return ActionsView()

    names = agent_names(order or [])
    lines = [
        ActionLine(
            step=step,
            text=describe_step(
                recording.mutations[step], recording.environments[step], names
            ),
        )
        for step in range(min(index + 1, len(recording.mutations)))
        if recording.mutations[step]
    ]
    lines = lines[-limit:]
    if lines:
        lines[-1] = lines[-1].copy_with(current=True)
    return ActionsView(lines=lines)


def agent_names(order: list[str]) -> dict[str, str]:
    """Map agent ids to the numbers shown in the HUD."""
    return {
        agent_id: f"Agent {number}" for number, agent_id in enumerate(order, start=1)
    }


def describe_step(
    mutations: list,
    environment: Environment,
    names: dict[str, str],
) -> str:
    text = ", ".join(mutation.describe(environment) for mutation in mutations)
    return with_agent_names(text, names)


def with_agent_names(text: str, names: dict[str, str]) -> str:
    """Replace raw agent ids with the names shown in the HUD.

    Mutation descriptions do not know the display names, so this substitution is
    done when the action log is built.
    """
    for agent_id, name in names.items():
        text = re.sub(rf"\b{re.escape(agent_id)}\b", name, text)
    return text


def environment_index_for(
    recording: Recording,
    environment: Environment,
) -> int | None:
    for index, candidate in enumerate(recording.environments):
        if candidate == environment:
            return index
    return None

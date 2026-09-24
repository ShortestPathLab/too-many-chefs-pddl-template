from __future__ import annotations

from collections.abc import Callable

from simulator.entities import Agent
from simulator.environment import Environment
from simulator.recording import Recording

OnStep = Callable[[Recording], None]


def emit_step(recording: Recording, on_step: OnStep | None) -> None:
    if on_step is not None:
        on_step(recording)


def ordered_agents(environment: Environment) -> list[Agent]:
    return sorted(
        environment.get_entities_of_type(Agent),
        key=lambda agent: (
            agent.y if agent.y is not None else -1,
            agent.x if agent.x is not None else -1,
            agent.id,
        ),
    )

"""The example controller: a sparring partner for ``cook match``.

It walks each of its chefs around the kitchen and does nothing else, so it
scores nothing. ``--seat example`` plays it, and the contest uses it to fill
the other seats when it checks a new Part 4 entry. It is not your code; that
is in ``submission/``.
"""

from __future__ import annotations

from typing import ClassVar

from simulator.context import Context
from simulator.controller import Controller
from simulator.entities import Orientation
from simulator.environment import Environment
from simulator.mutations import MoveAgentForward, Mutation, TurnAgent


class ExampleController(Controller):
    """Walk forward, turning clockwise every fourth tick."""

    _clockwise: ClassVar[dict[Orientation, Orientation]] = {
        "n": "e",
        "e": "s",
        "s": "w",
        "w": "n",
    }

    def __init__(self) -> None:
        self._ticks = 0

    def get_actions(self, environment: Environment, context: Context) -> list[Mutation]:
        self._ticks += 1
        actions: list[Mutation] = []
        for agent in self.controllable_agents(environment):
            if self._ticks % 4 == 0:
                actions.append(
                    TurnAgent(
                        agent_id=agent.id,
                        orientation=self._clockwise[agent.orientation],
                    )
                )
            else:
                actions.append(MoveAgentForward(agent_id=agent.id))
        return actions

    def is_busy(self) -> bool:
        return False

    def has_finished(self, environment: Environment) -> bool:
        return False

    def shutdown(self) -> None:
        pass

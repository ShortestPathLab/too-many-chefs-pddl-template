"""Part 4 controller implementation.

Each chef in a competition match has a separate controller. This controller
manages one chef; a classmate's controller manages the teammate, and two
others manage the opposing team. ``self.controllable_agents(environment)``
returns the assigned chef. The remaining chefs are teammates and opponents.

``get_actions`` receives the full kitchen state once per tick and returns
actions for the assigned chef. Each tick permits one turn followed by one
movement or other action; additional actions are ignored. All controllers
can observe the full state.
Responses must arrive within 200 ms; otherwise, the chef waits for that tick.
Any technique, including PDDL, is permitted if it uses only packages installed
by the starter. An exception ends the team's set and records a loss.

Play a set with your controller on both chefs of one team against the example:

    uv run python main.py match --seat . --seat . --seat example --seat example

Replace the placeholder below, which only moves the chef around the kitchen.
"""

from __future__ import annotations

from typing import ClassVar

from simulator.context import Context
from simulator.controller import Controller
from simulator.entities import Orientation
from simulator.environment import Environment
from simulator.mutations import MoveAgentForward, Mutation, TurnAgent


class OpenController(Controller):
    """Control one chef in a 2v2 match."""

    _clockwise: ClassVar[dict[Orientation, Orientation]] = {
        "n": "e",
        "e": "s",
        "s": "w",
        "w": "n",
    }

    def __init__(self) -> None:
        # Each game creates a new controller instance; this state lasts one game.
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
        # The match duration determines when play ends.
        return False

    def shutdown(self) -> None:
        """Release controller resources, including any processes it started."""

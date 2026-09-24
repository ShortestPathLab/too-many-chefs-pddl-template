"""Your Part 4 controller.

In a competition match every chef has its own controller: yours drives one
chef, a classmate's drives your teammate, and two more drive the other team.
``self.controllable_agents(environment)`` returns the one chef that is yours;
the others are in the kitchen as teammates and opponents.

``get_actions`` is called once per tick with the whole kitchen, which every
controller can see, and returns your chef's actions for that tick. It has 200
ms to answer. When it takes longer, your chef stands still that tick. Any
technique is allowed, PDDL included, as long as it only uses what the starter
installs. If it raises, your team's set ends and it counts as a loss for you.

Play a set with your controller on both chefs of one team against the example:

    uv run python main.py match --seat . --seat . --seat example --seat example

The placeholder below walks your chef around the kitchen. Replace it.
"""

from __future__ import annotations

from typing import ClassVar

from simulator.context import Context
from simulator.controller import Controller
from simulator.entities import Orientation
from simulator.environment import Environment
from simulator.mutations import MoveAgentForward, Mutation, TurnAgent


class OpenController(Controller):
    """Drive your chef in a 2v2 match."""

    _clockwise: ClassVar[dict[Orientation, Orientation]] = {
        "n": "e",
        "e": "s",
        "s": "w",
        "w": "n",
    }

    def __init__(self) -> None:
        # A new controller is built for every game, so state kept here lasts
        # one game.
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
        # A match ends on its own clock, not when a controller is done.
        return False

    def shutdown(self) -> None:
        """Release anything the controller started, such as processes."""

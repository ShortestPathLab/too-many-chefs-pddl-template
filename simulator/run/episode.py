"""One kitchen from its first timestep, stepped by whoever drives it.

Agent mode, play mode, and the reinforcement-learning environments all move a
kitchen forward the same way: drop the actions it cannot take, step, record the
result, and tell anyone listening. ``Episode`` does that once for all of them.
What decides the actions stays with the caller: a controller on a timer, keys
from a human, or a training loop.

``on_step`` gets the recording once at the start and after every step. A YAML
recording sink is one such listener. A live visualiser is another.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

from simulator.controller import Controller
from simulator.entities import badge_order
from simulator.environment import Environment, filter_legal_actions
from simulator.mutations import Mutation, MutationModel
from simulator.recording import Recording

from .common import OnStep
from .end_conditions import EndConditions
from .reason import TerminationReason
from .result import RunError, SimulationResult, build_simulation_result
from .setup import RunSetup


@dataclass(frozen=True)
class Step:
    """One timestep: the kitchen before, what ran, and the kitchen after."""

    previous: Environment
    mutations: list[Mutation]
    current: Environment


class Episode:
    """Step a kitchen, record every environment, and report to listeners.

    ``agent_order`` is badge order in the first environment. It stays fixed as
    chefs move, so results and panels list chefs the same way all episode.
    """

    def __init__(
        self,
        environment: Environment,
        *,
        on_step: OnStep | None = None,
    ) -> None:
        self.environment = environment
        self.recording = Recording(environments=[environment], mutations=[[]])
        self.agent_order = [agent.id for agent in badge_order(environment)]
        self._started = time.monotonic()
        self._on_step = on_step
        self._emit()

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self._started

    def advance(
        self,
        mutations: Sequence[Mutation],
        *,
        keep_illegal: bool = False,
    ) -> Step:
        """Apply ``mutations`` in order and move the clock on one timestep.

        Illegal mutations are dropped before the step and left out of the
        recording. Play mode sets ``keep_illegal`` so a human's press still
        shows on the pad when it did nothing; the step skips it all the same.
        """
        previous = self.environment
        applied = (
            list(mutations)
            if keep_illegal
            else filter_legal_actions(previous, mutations)
        )
        current = previous.step(applied)
        self.environment = current
        self.recording.environments.append(current)
        self.recording.mutations.append(cast(list[MutationModel], applied))
        self._emit()
        return Step(previous=previous, mutations=applied, current=current)

    def end_reason(
        self,
        conditions: EndConditions,
        controller: Controller | None = None,
    ) -> TerminationReason | None:
        """Return why the episode should end now, or ``None`` to go on."""
        return conditions.reached(
            self.environment,
            controller,
            elapsed_seconds=self.elapsed_seconds,
        )

    def result(
        self,
        reason: TerminationReason,
        *,
        setup: RunSetup | None = None,
        error: RunError | None = None,
    ) -> SimulationResult:
        """Summarise the episode as it stands."""
        return build_simulation_result(
            self.environment,
            reason=reason,
            elapsed_seconds=self.elapsed_seconds,
            agent_order=self.agent_order,
            setup=setup,
            error=error,
        )

    def _emit(self) -> None:
        if self._on_step is not None:
            self._on_step(self.recording)

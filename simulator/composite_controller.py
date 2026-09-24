from __future__ import annotations

from collections.abc import Collection

from simulator.context import Context
from simulator.controller import Controller
from simulator.entities import Agent
from simulator.environment import Environment
from simulator.mutations import Mutation
from simulator.mutations.agent_mutation import AgentMutation


class ControllerOwnershipError(RuntimeError):
    """Raised when a controller emits a mutation for an unowned agent."""


class CompositeController(Controller):
    """Run several controllers, each responsible for its assigned agents.

    Each controller may return mutations only for the agents it owns. A fallback
    controller receives agents not claimed by an explicit assignment. Fallback
    ownership is resolved against the live environment so generated agent ids
    are supported. Controllers with no agents are removed.

    Controllers do not coordinate. The runner filters illegal mutations, and
    each controller plans with the other agents as obstacles.
    """

    def __init__(
        self,
        assignments: Collection[tuple[Controller, Collection[str]]],
        *,
        fallback: Controller | None = None,
    ) -> None:
        self._assignments: list[tuple[Controller, frozenset[str]]] = []
        for controller, agent_ids in assignments:
            owned = frozenset(agent_ids)
            controller.set_controlled_agents(owned)
            self._assignments.append((controller, owned))
        self._explicit_agent_ids = frozenset(
            agent_id for _, owned in self._assignments for agent_id in owned
        )
        self._fallback = fallback
        self._fallback_resolved = False

    def get_actions(self, environment: Environment, context: Context) -> list[Mutation]:
        self._resolve_fallback(environment)

        actions: list[Mutation] = []
        for controller, owned in self._assignments:
            controller_actions = controller.get_actions(environment, context)
            for mutation in controller_actions:
                _require_owned(controller, owned, mutation)
            actions.extend(controller_actions)
        return actions

    def is_busy(self) -> bool:
        return any(controller.is_busy() for controller, _ in self._assignments)

    def has_finished(self, environment: Environment) -> bool:
        return all(
            controller.has_finished(environment) for controller, _ in self._assignments
        )

    def shutdown(self) -> None:
        for controller, _ in self._assignments:
            controller.shutdown()

    def child_controllers(self) -> list[Controller]:
        return [controller for controller, _ in self._assignments]

    def nested_controllers(self) -> list[Controller]:
        """Return every controller here, including a fallback still waiting.

        The fallback joins ``_assignments`` on the first step, once the live
        environment says which agents are left for it.
        """
        controllers = self.child_controllers()
        if self._fallback is not None:
            controllers.append(self._fallback)
        return controllers

    def _resolve_fallback(self, environment: Environment) -> None:
        if self._fallback_resolved:
            return
        self._fallback_resolved = True
        if self._fallback is None:
            return

        leftover = [
            agent.id
            for agent in environment.get_entities_of_type(Agent)
            if agent.id not in self._explicit_agent_ids
        ]
        if not leftover:
            self._fallback.shutdown()
            self._fallback = None
            return

        owned = frozenset(leftover)
        self._fallback.set_controlled_agents(owned)
        self._assignments.append((self._fallback, owned))


def _require_owned(
    controller: Controller,
    owned: frozenset[str],
    mutation: Mutation,
) -> None:
    if not isinstance(mutation, AgentMutation):
        raise ControllerOwnershipError(
            f"{type(controller).__name__} emitted a non-agent mutation "
            f"{type(mutation).__name__}, which cannot be attributed to an owned "
            f"agent. Controllers sharing a level may only emit agent mutations."
        )
    if mutation.agent_id not in owned:
        raise ControllerOwnershipError(
            f"{type(controller).__name__} emitted a "
            f"{type(mutation).__name__} for agent {mutation.agent_id!r}, which it "
            f"does not control (owns: {sorted(owned)}). A controller may only act "
            f"on the agents assigned to it."
        )

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TypeVar, cast

from pydantic import Field

from simulator.entities import Entity, EntityModel
from simulator.models import SimulatorModel
from simulator.mutations import (
    Mutation,
    MutationModel,
    TickMutationModel,
    limit_actions_per_chef,
)
from simulator.mutations.mutation import IllegalMutationError

TEntity = TypeVar("TEntity", bound=Entity)

logger = logging.getLogger(__name__)


def filter_legal_actions(
    environment: Environment,
    mutations: Sequence[Mutation],
) -> list[Mutation]:
    legal: list[Mutation] = []
    for mutation in mutations:
        try:
            environment = mutation.run(environment)
            legal.append(mutation)
        except IllegalMutationError:
            continue
    return legal


class Environment(SimulatorModel):
    """Grid-based state for one simulation timestep."""

    timestep: int = 0
    entities: dict[str, EntityModel] = Field(default_factory=dict)
    # World effects applied every step, built from the level's rules.
    tick_mutations: list[TickMutationModel] = Field(default_factory=list)
    # Maximum movements or other actions per chef per step, in addition to one
    # turn. Set from the level's rules.actions_per_step; None removes the limit.
    actions_per_step: int | None = 1

    def step(self, mutations: Sequence[Mutation | MutationModel]) -> Environment:
        """Apply permitted mutations and tick effects, then advance the clock.

        ``limit_actions`` selects and orders the submitted mutations before
        execution.
        """

        environment = self
        for mutation in self.limit_actions(mutations):
            try:
                environment = mutation.run(environment)
            except IllegalMutationError as illegal:
                # Illegal actions are expected during a run. Skip them without
                # stopping the simulation.
                reason = str(illegal)
                logger.warning(
                    "Skipped action: %s isn't possible right now%s",
                    mutation.describe(self),
                    f" ({reason})" if reason else "",
                )
        for effect in environment.tick_mutations:
            environment = effect.run(environment)
        next_timestep = environment.timestep + 1
        environment = environment.copy_with(timestep=next_timestep)

        from simulator.entities import OvercookedState

        state = environment.get_first_entity_of_type(OvercookedState)
        if state:
            environment = environment.replace_entity(
                state.advance_to_timestep(next_timestep)
            )
        return environment

    def limit_actions(self, mutations: Sequence[Mutation]) -> list[Mutation]:
        """Return mutations permitted by the kitchen's per-step action limit.

        When ``actions_per_step`` is set, ``limit_actions_per_chef`` retains
        each chef's first turn and first ``actions_per_step`` movements or
        other actions, placing turns first. With no limit, all mutations are
        returned in their original order.
        """
        if self.actions_per_step is None:
            return list(mutations)
        return limit_actions_per_chef(mutations, self.actions_per_step)

    def has_pending_effects(self) -> bool:
        """Return whether a step with no mutations would still change anything."""
        return any(effect.pending(self) for effect in self.tick_mutations)

    def with_entity(self, entity: EntityModel) -> Environment:
        """Return a new environment containing the provided entity."""

        entities = dict(self.entities)
        entities[entity.id] = entity
        return self.copy_with(entities=entities)

    def replace_entity(self, *entities_to_replace: EntityModel) -> Environment:
        """Return a new environment with the provided existing entities replaced."""

        if not entities_to_replace:
            return self

        entities = dict(self.entities)
        replaced = False
        for entity in entities_to_replace:
            if entity.id not in entities:
                continue
            entities[entity.id] = entity
            replaced = True

        if not replaced:
            return self

        return self.copy_with(entities=entities)

    def without_entity(self, entity_id: str) -> Environment:
        """Return a new environment with the entity removed if present."""

        if entity_id not in self.entities:
            return self

        entities = dict(self.entities)
        del entities[entity_id]
        return self.copy_with(entities=entities)

    def get_entity(self, entity_id: str) -> Entity | None:
        return self.entities.get(entity_id)

    def get_entity_as(
        self, entity_id: str, entity_type: type[TEntity]
    ) -> TEntity | None:
        entity = self.get_entity(entity_id)
        if isinstance(entity, entity_type):
            return entity
        return None

    def get_entities_of_type(self, entity_type: type[TEntity]) -> list[TEntity]:
        return cast(
            list[TEntity],
            [
                entity
                for entity in self.entities.values()
                if isinstance(entity, entity_type)
            ],
        )

    def get_first_entity_of_type(self, entity_type: type[TEntity]) -> TEntity | None:
        entities = self.get_entities_of_type(entity_type)
        if not entities:
            return None
        return entities[0]

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TypeVar, cast

from pydantic import Field

from simulator.entities import Entity, EntityModel
from simulator.models import SimulatorModel
from simulator.mutations import Mutation, MutationModel, TickMutationModel
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

    def step(self, mutations: Sequence[Mutation | MutationModel]) -> Environment:
        """Apply mutations in order, then tick mutations, then advance the clock."""

        environment = self
        for mutation in mutations:
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

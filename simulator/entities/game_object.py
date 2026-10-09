from __future__ import annotations

from typing import TYPE_CHECKING

from simulator.entities.entity import Entity
from simulator.entities.sprite import Sprite, SpriteFrame, SpriteFramePart

if TYPE_CHECKING:
    from simulator.environment import Environment
    from simulator.mutations import Mutation


class GameObject(Entity):
    """Entity placed on the game grid."""

    x: int | None = 0
    y: int | None = 0

    @property
    def blocks_movement(self) -> bool:
        return False

    @property
    def render(self) -> str:
        return self.__class__.__name__[:2].upper()

    def sprite(
        self,
        environment: Environment,
        mutations: list[Mutation],
    ) -> Sprite:
        return Sprite(
            loop_cycle_animation=[_frame(0, 0, sheet="interiors.png")],
        )

    @property
    def position(self) -> tuple[int | None, int | None]:
        return (self.x, self.y)

    def is_at(self, x: int, y: int) -> bool:
        return self.x is not None and self.y is not None and self.x == x and self.y == y


def get_objects_at(environment: Environment, x: int, y: int) -> list[GameObject]:
    return [entity for entity in game_objects(environment) if entity.is_at(x, y)]


def get_game_object(environment: Environment, entity_id: str) -> GameObject | None:
    return environment.get_entity_as(entity_id, GameObject)


def game_objects(environment: Environment) -> list[GameObject]:
    return [
        entity
        for entity in environment.get_entities_of_type(GameObject)
        if entity.x is not None and entity.y is not None
    ]


def get_game_objects_of_type_at[TGameObject: GameObject](
    environment: Environment,
    x: int,
    y: int,
    entity_type: type[TGameObject],
) -> list[TGameObject]:
    return [
        entity
        for entity in get_objects_at(environment, x, y)
        if isinstance(entity, entity_type)
    ]


def get_first_game_object_of_type_at[TGameObject: GameObject](
    environment: Environment,
    x: int,
    y: int,
    entity_type: type[TGameObject],
) -> TGameObject | None:
    objects = get_game_objects_of_type_at(environment, x, y, entity_type)
    if not objects:
        return None
    return objects[0]


def _frame(
    x: int,
    y: int,
    *,
    width: int = 16,
    height: int = 16,
    shift_x: int = 0,
    shift_y: int = 0,
    sheet: str,
) -> SpriteFrame:
    return SpriteFrame(
        parts=[
            SpriteFramePart(
                x=x,
                y=y,
                width=width,
                height=height,
                shift_x=shift_x,
                shift_y=shift_y,
                sheet=sheet,
            )
        ]
    )

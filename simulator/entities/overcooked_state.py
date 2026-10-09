from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import Field

from simulator.entities.entity import Entity
from simulator.entities.garbage import (
    garbage_food_definition,
    garbage_food_name,
    garbage_food_sprite,
)
from simulator.entities.orders import OrderQueue
from simulator.entities.recipes import CombineRecipe, CookRecipe, FoodDefinition
from simulator.entities.scoring import ScoringState
from simulator.entities.sound import SoundDefinition, SoundtrackDefinition
from simulator.entities.sprite import EquipmentSpriteDefinition, SpriteDefinition

if TYPE_CHECKING:
    from simulator.entities import Food


class OvercookedState(Entity):
    """Level state that is not represented by a physical object.

    This includes orders, scores, recipes, and visual and audio definitions.
    """

    kind: Literal["overcooked_state"] = "overcooked_state"
    name: str | None = None
    description: str | None = None
    order_queue: OrderQueue = Field(default_factory=OrderQueue)
    scoring: ScoringState = Field(default_factory=ScoringState)
    food_sprites: dict[str, SpriteDefinition] = Field(default_factory=dict)
    equipment_sprites: dict[str, EquipmentSpriteDefinition] = Field(
        default_factory=dict
    )
    equipment_sounds: dict[str, SoundDefinition] = Field(default_factory=dict)
    equipment_verbs: dict[str, str] = Field(default_factory=dict)
    soundtrack: SoundtrackDefinition = Field(default_factory=SoundtrackDefinition)
    food_definitions: dict[str, FoodDefinition] = Field(default_factory=dict)
    cook_recipes: list[CookRecipe] = Field(default_factory=list)
    combine_recipes: list[CombineRecipe] = Field(default_factory=list)
    # Allow unsupported combinations to produce placeholder food.
    allow_illegal_recipes: bool = False

    @property
    def orders(self) -> list[str]:
        return self.order_queue.orders

    @property
    def visible_orders(self) -> list[str]:
        return self.order_queue.orders

    @property
    def order_revision(self) -> int:
        return self.order_queue.revision

    @property
    def score(self) -> int:
        return self.scoring.score

    @property
    def score_by_agent(self) -> dict[str, int]:
        return self.scoring.score_by_agent

    def score_for(self, agent_id: str) -> int:
        return self.scoring.score_for(agent_id)

    def accepts_dish(self, dish_name: str, timestep: int = 0) -> bool:
        return self.order_queue.accepts(dish_name, timestep)

    def notify_item_retrieved(
        self,
        item_name: str,
        *,
        agent_id: str | None = None,
        team: str | None = None,
    ) -> OvercookedState:
        # A dish that is itself on order is never a component to fetch.
        if item_name in self.visible_orders:
            return self
        return self._tip(
            item_name,
            self.scoring.retrieve_order_component_reward,
            agent_id=agent_id,
            team=team,
        )

    def notify_item_prepared(
        self,
        item_name: str,
        *,
        agent_id: str | None = None,
        team: str | None = None,
    ) -> OvercookedState:
        return self._tip(
            item_name,
            self.scoring.produce_ordered_item_reward
            if item_name in self.visible_orders
            else self.scoring.produce_order_component_reward,
            agent_id=agent_id,
            team=team,
        )

    def _tip(
        self,
        item_name: str,
        reward: int,
        *,
        agent_id: str | None,
        team: str | None,
    ) -> OvercookedState:
        """Pay ``reward`` for progress on ``item_name`` if an order still owes it.

        Each visible order that is, or needs, the food owes each team one tip
        for it. Teams keep separate tallies, so one side's progress never uses
        up the other's tips.
        """
        demand = sum(
            entry.name == item_name or item_name in self._order_components(entry.name)
            for entry in self.order_queue.visible
        )
        order_queue = self.order_queue.tip(item_name, demand, team=team)
        if order_queue is None:
            return self
        return self.copy_with(
            order_queue=order_queue,
            scoring=self.scoring.rewarded(reward, agent_id=agent_id),
        )

    def notify_item_delivered(
        self,
        item_name: str,
        timestep: int,
        *,
        agent_id: str | None = None,
    ) -> OvercookedState:
        order_queue, reward = self.order_queue.delivered(item_name, timestep)
        if reward is None:
            return self
        scoring = self.scoring.rewarded(reward, agent_id=agent_id)
        return self.copy_with(order_queue=self._released(order_queue), scoring=scoring)

    def advance_to_timestep(self, timestep: int) -> OvercookedState:
        order_queue = self.order_queue.advance_to_timestep(timestep)
        return (
            self
            if order_queue is self.order_queue
            else self.copy_with(order_queue=self._released(order_queue))
        )

    def _released(self, order_queue: OrderQueue) -> OrderQueue:
        """Give back the tips of every order that has left the visible list."""
        for entry in self.order_queue.visible:
            if not any(entry is kept for kept in order_queue.visible):
                order_queue = order_queue.release(
                    {entry.name, *self._order_components(entry.name)}
                )
        return order_queue

    def delivery_succeeded_previous_tick(self, timestep: int) -> bool:
        return self.order_queue.last_successful_delivery_timestep == timestep

    def _order_components(self, dish_name: str) -> set[str]:
        """Return every food on any recipe route to ``dish_name``.

        The dish itself is excluded.
        """
        components: set[str] = set()
        remaining = [dish_name]
        while remaining:
            output = remaining.pop()
            for recipe in self.cook_recipes:
                if recipe.output == output and recipe.ingredient not in components:
                    components.add(recipe.ingredient)
                    remaining.append(recipe.ingredient)
            for recipe in self.combine_recipes:
                if recipe.output == output:
                    for ingredient in recipe.ingredients - components:
                        components.add(ingredient)
                        remaining.append(ingredient)
        components.discard(dish_name)
        return components

    def get_food_sprite(self, food_name: str) -> SpriteDefinition | None:
        sprite = self.food_sprites.get(food_name)
        if sprite or not self.allow_illegal_recipes:
            return sprite
        return garbage_food_sprite(food_name)

    def get_equipment_sprite(
        self, equipment_name: str
    ) -> EquipmentSpriteDefinition | None:
        return self.equipment_sprites.get(equipment_name)

    def get_equipment_sound(self, equipment_name: str) -> SoundDefinition | None:
        return self.equipment_sounds.get(equipment_name)

    def get_equipment_verb(self, equipment_name: str) -> str:
        """Return the verb used for an equipment action.

        Use the equipment name when no verb is configured.
        """
        verb = self.equipment_verbs.get(equipment_name)
        return verb or equipment_name.rsplit("/", 1)[-1].replace("_", " ").capitalize()

    def get_food_definition(self, food_name: str) -> FoodDefinition | None:
        definition = self.food_definitions.get(food_name)
        if definition or not self.allow_illegal_recipes:
            return definition
        # Illegal-recipe outputs have built-in definitions. Level definitions
        # take precedence above.
        return garbage_food_definition(food_name)

    def create_food(
        self,
        food_name: str,
        *,
        x: int | None = None,
        y: int | None = None,
    ) -> Food | None:
        from simulator.entities.food import Food

        definition = self.get_food_definition(food_name)
        if not definition:
            return None

        return Food(
            x=x,
            y=y,
            name=definition.name,
            raw=definition.raw,
            deliverable=definition.deliverable,
        )

    def is_raw_food(self, food_name: str) -> bool:
        definition = self.get_food_definition(food_name)
        return bool(definition and definition.raw)

    def get_cook_output(self, ingredient: str, equipment_name: str) -> str | None:
        for recipe in self.cook_recipes:
            if recipe.ingredient == ingredient and recipe.equipment == equipment_name:
                return recipe.output
        return None

    def can_cook_with(self, ingredient: str, equipment_name: str) -> bool:
        return bool(self.get_cook_output(ingredient, equipment_name))

    def is_cooking_equipment(self, equipment_name: str) -> bool:
        """Return whether any recipe uses this equipment for cooking.

        A stove or plate is not cooking equipment unless a recipe names it.
        """
        return any(recipe.equipment == equipment_name for recipe in self.cook_recipes)

    def equipment_accepts(self, ingredient: str, equipment_name: str) -> bool:
        if self.can_cook_with(ingredient, equipment_name):
            return True
        if self.allow_illegal_recipes and self.is_cooking_equipment(equipment_name):
            return True
        return any(
            self.equipment_accepts(recipe.output, equipment_name)
            for recipe in self.combine_recipes
            if ingredient in recipe.ingredients
        )

    def get_combine_output(self, first: str, second: str) -> str | None:
        ingredients = frozenset((first, second))
        for recipe in self.combine_recipes:
            if recipe.ingredients == ingredients:
                return recipe.output
        return None

    def resolve_cook_output(
        self,
        ingredient: str,
        equipment_name: str,
        *,
        timestep: int,
    ) -> str | None:
        """Resolve a cook output, including illegal-recipe behavior.

        Unsupported inputs return a placeholder output only when illegal recipes
        are enabled and the equipment is used for cooking.
        """
        output = self.get_cook_output(ingredient, equipment_name)
        if output or not self.allow_illegal_recipes:
            return output
        if not self.is_cooking_equipment(equipment_name):
            return None
        return garbage_food_name(ingredient, equipment_name, timestep=timestep)

    def resolve_combine_output(
        self,
        first: str,
        second: str,
        *,
        timestep: int,
    ) -> str | None:
        """Resolve a combine output, including illegal-recipe behavior."""
        output = self.get_combine_output(first, second)
        if output or not self.allow_illegal_recipes:
            return output
        return garbage_food_name(first, second, timestep=timestep)

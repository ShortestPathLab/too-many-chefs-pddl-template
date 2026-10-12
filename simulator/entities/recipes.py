"""Recipe and food definitions for a level.

Cook recipes transform one ingredient with equipment. Combine recipes transform
two ingredients into one output.
"""

from __future__ import annotations

from pydantic import field_serializer

from simulator.models import FrozenSimulatorModel


class FoodDefinition(FrozenSimulatorModel):
    name: str
    raw: bool = True
    deliverable: bool = False


class CookRecipe(FrozenSimulatorModel):
    ingredient: str
    equipment: str
    output: str


class CombineRecipe(FrozenSimulatorModel):
    ingredients: frozenset[str]
    output: str

    @field_serializer("ingredients")
    def serialize_ingredients(self, ingredients: frozenset[str]) -> list[str]:
        return sorted(ingredients)

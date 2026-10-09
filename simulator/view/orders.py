from __future__ import annotations

from pydantic import Field

from simulator.entities import OrderEntry, OvercookedState
from simulator.entities.plate import PLATE_NAME, plate_sprite, plated_parts
from simulator.entities.sprite import Sprite, SpriteFrame
from simulator.environment import Environment
from simulator.models import FrozenSimulatorModel
from simulator.view.sprite_canvas import seat_on_cell
from simulator.view.text import sentence_case


class RecipeStation(FrozenSimulatorModel):
    """Equipment used by a recipe step.

    The verb is the label shown on the order ticket.
    """

    name: str
    verb: str


class RecipeStep(FrozenSimulatorModel):
    """One step in a recipe expression.

    A leaf is an ingredient. A group contains parts that are combined from left
    to right. ``stations`` lists equipment used after the step.
    """

    name: str = ""
    label: str = ""
    sprite: Sprite = Sprite()
    parts: list[RecipeStep] = Field(default_factory=list)
    stations: list[RecipeStation] = Field(default_factory=list)


class OrderCard(FrozenSimulatorModel):
    name: str
    label: str
    reward: int
    sprite: Sprite
    recipe: RecipeStep | None = None
    # ``None`` means the order has no time limit.
    remaining_fraction: float | None = None
    remaining_steps: int | None = None
    is_next: bool = False


class OrdersView(FrozenSimulatorModel):
    """Data rendered by the orders rail.

    Expiry is represented as a fraction and a remaining step count.
    """

    cards: list[OrderCard] = Field(default_factory=list)
    queue_label: str = ""
    pending_count: int = 0
    note: str = ""


def orders_view(environment: Environment) -> OrdersView:
    state = environment.get_first_entity_of_type(OvercookedState)
    if state is None:
        return OrdersView()

    queue = state.order_queue
    ordered_matters = queue.order_reveal == "sequential" or queue.strict_ordering

    cards = [
        _card(
            state, entry, environment.timestep, is_next=ordered_matters and index == 0
        )
        for index, entry in enumerate(queue.visible)
    ]

    return OrdersView(
        cards=cards,
        queue_label=_queue_label(state),
        pending_count=len(queue.pending),
        note=_note(state),
    )


def recipe_steps(state: OvercookedState, dish: str) -> RecipeStep | None:
    """Return a left-to-right recipe expression for ``dish``.

    Equivalent combine orders are folded into one expression. The dish itself
    is omitted because the order card already displays it.
    """
    if _cook_route(state, dish) is None and not _combine_members(state, dish):
        return None
    return _expand(state, dish, ())


def recipe_expression(step: RecipeStep | None, *, nested: bool = False) -> str:
    """Return a recipe expression as text."""
    if step is None:
        return ""
    if step.parts:
        body = " + ".join(recipe_expression(part, nested=True) for part in step.parts)
        # Keep a group together when another part or station follows it.
        if nested or step.stations:
            body = f"({body})"
    else:
        body = f"[{step.label}]"
    return body + "".join(f"({station.verb})" for station in step.stations)


def _expand(state: OvercookedState, name: str, path: tuple[str, ...]) -> RecipeStep:
    """Expand ``name`` into its recipe steps.

    Treat a name already in ``path`` as a leaf to avoid recursive recipe loops.
    """
    if name in path:
        return _leaf(state, name)
    path = (*path, name)

    cooked = _cook_route(state, name)
    if cooked is not None:
        ingredient, equipment = cooked
        inner = _expand(state, ingredient, path)
        station = RecipeStation(
            name=equipment, verb=state.get_equipment_verb(equipment)
        )
        return inner.copy_with(stations=[*inner.stations, station])

    members = _combine_members(state, name)
    if not members:
        return _leaf(state, name)

    parts: list[RecipeStep] = []
    for index, member in enumerate(_build_order(state, members)):
        part = _expand(state, member, path)
        # Flatten a leading assembly into its component parts.
        if index == 0 and part.parts and not part.stations:
            parts.extend(part.parts)
        else:
            parts.append(part)
    return RecipeStep(parts=parts)


def _cook_route(state: OvercookedState, name: str) -> tuple[str, str] | None:
    for recipe in state.cook_recipes:
        if recipe.output == name:
            return recipe.ingredient, recipe.equipment
    return None


def _combine_members(state: OvercookedState, name: str) -> set[str]:
    """Return the base ingredients needed for ``name``."""
    routes = [
        recipe.ingredients for recipe in state.combine_recipes if recipe.output == name
    ]
    if not routes:
        return set()
    if len(routes) == 1:
        return set(routes[0])

    members: set[str] = set().union(*routes)
    # Each pass removes at least one member.
    for _ in range(len(members)):
        partial = next(
            (
                (member, ingredients)
                for member in sorted(members)
                for ingredients in _routes_to(state, member)
                if ingredients & (members - {member})
            ),
            None,
        )
        if partial is None:
            break
        member, ingredients = partial
        members = (members - {member}) | set(ingredients)
    return members


def _routes_to(state: OvercookedState, name: str) -> list[frozenset[str]]:
    return [
        recipe.ingredients for recipe in state.combine_recipes if recipe.output == name
    ]


def _build_order(state: OvercookedState, members: set[str]) -> list[str]:
    """Order members so each merge is a valid recipe.

    Prefer assembled members first and break ties by name for stable output.
    """
    candidates = sorted(
        members, key=lambda member: (not _routes_to(state, member), member)
    )
    order = _fold_from(state, candidates)
    return order if order is not None else candidates


def _fold_from(state: OvercookedState, members: list[str]) -> list[str] | None:
    for first in members:
        rest = [member for member in members if member != first]
        found = _fold_rest(state, first, rest)
        if found is not None:
            return [first, *found]
    return None


def _fold_rest(state: OvercookedState, held: str, rest: list[str]) -> list[str] | None:
    if not rest:
        return []
    for nxt in rest:
        merged = state.get_combine_output(held, nxt)
        if merged is None:
            continue
        found = _fold_rest(state, merged, [member for member in rest if member != nxt])
        if found is not None:
            return [nxt, *found]
    return None


def _leaf(state: OvercookedState, name: str) -> RecipeStep:
    return RecipeStep(
        name=name, label=food_label(name), sprite=item_sprite(state, name)
    )


def food_sprite(state: OvercookedState, name: str, *, on_plate: bool = False) -> Sprite:
    definition = state.get_food_sprite(name)
    if on_plate:
        # Compose the dish with its plate for the order card.
        parts = plated_parts(definition)
    else:
        parts = list(definition.as_parts()) if definition else []
    if not parts:
        return Sprite()
    return Sprite(loop_cycle_animation=[SpriteFrame(parts=parts)])


def equipment_sprite(state: OvercookedState, name: str) -> Sprite:
    """A station as an icon, empty when the level never drew one."""
    definition = state.get_equipment_sprite(name)
    if definition is None and name == PLATE_NAME:
        # Plates have a built-in sprite and need not appear in the legend.
        definition = plate_sprite()
    # Icons flatten the station base and overlay into one image.
    parts = (
        seat_on_cell([*definition.as_parts(), *definition.overlay])
        if definition
        else []
    )
    if not parts:
        return Sprite()
    return Sprite(loop_cycle_animation=[SpriteFrame(parts=parts)])


def item_sprite(state: OvercookedState, name: str) -> Sprite:
    """Return the food or equipment sprite for ``name``."""
    sprite = food_sprite(state, name)
    if sprite.loop_cycle_animation:
        return sprite
    return equipment_sprite(state, name)


def food_label(name: str) -> str:
    """Format a catalog name for display."""
    return sentence_case(name.rsplit("/", 1)[-1].replace("_", " "))


def _card(
    state: OvercookedState,
    entry: OrderEntry,
    timestep: int,
    *,
    is_next: bool,
) -> OrderCard:
    remaining_fraction: float | None = None
    remaining_steps: int | None = None
    if entry.time_limit:
        remaining_steps = max(0, entry.revealed_at + entry.time_limit - timestep)
        remaining_fraction = min(1.0, max(0.0, remaining_steps / entry.time_limit))

    return OrderCard(
        name=entry.name,
        label=food_label(entry.name),
        reward=entry.reward,
        sprite=food_sprite(state, entry.name, on_plate=True),
        recipe=recipe_steps(state, entry.name),
        remaining_fraction=remaining_fraction,
        remaining_steps=remaining_steps,
        is_next=is_next,
    )


def _queue_label(state: OvercookedState) -> str:
    queue = state.order_queue
    if queue.generator is not None:
        return "Endless"
    if queue.order_reveal == "sequential":
        return "Sequential"
    if queue.strict_ordering:
        return "In order"
    return "Any order"


def _note(state: OvercookedState) -> str:
    queue = state.order_queue
    if queue.generator is not None:
        return f"Seed {queue.generator.seed} / refills to {queue.generator.max_visible}"
    if queue.pending:
        return f"{len(queue.pending)} not revealed"
    return ""

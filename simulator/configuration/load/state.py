from __future__ import annotations

from simulator.configuration.configuration import (
    Configuration,
    EquipmentAnimationConfiguration,
    EquipmentSymbolConfiguration,
)
from simulator.entities import (
    Bounds,
    CombineRecipe,
    CookRecipe,
    EquipmentAnimationDefinition,
    EquipmentSpriteDefinition,
    FoodDefinition,
    OrderEntry,
    OrderGenerator,
    OrderQueue,
    OvercookedState,
    ScoringState,
    Shadows,
    SoundDefinition,
    SoundtrackDefinition,
    SpriteDefinition,
)
from simulator.entities.plate import PLATE_NAME
from simulator.entities.sprite import SpriteFramePart
from simulator.entities.walls import Walls
from simulator.mutations import AdvanceCooking, TickMutationModel


def equipment_sprite_definition(
    entry: EquipmentSymbolConfiguration,
) -> EquipmentSpriteDefinition:
    return EquipmentSpriteDefinition(
        parts=sprite_frame_parts(entry.sprite_parts),
        overlay=sprite_frame_parts(entry.overlay_parts),
        display_food=entry.display_food,
        on_food_in=equipment_animation_definition(entry.on_food_in),
        on_food_out=equipment_animation_definition(entry.on_food_out),
        on_cook=equipment_animation_definition(entry.on_cook),
    )


def equipment_sound_definition(
    entry: EquipmentSymbolConfiguration,
) -> SoundDefinition | None:
    if not entry.sound or not entry.sound.clips:
        return None
    return SoundDefinition(
        clips=tuple(entry.sound.clips),
        gain=entry.sound.gain,
        jitter=entry.sound.jitter,
    )


def equipment_animation_definition(
    animation: EquipmentAnimationConfiguration | None,
) -> EquipmentAnimationDefinition | None:
    if not animation:
        return None

    return EquipmentAnimationDefinition(
        parts=sprite_frame_parts(animation.sprite_parts),
        frames=animation.frames,
    )


def build_overcooked_state(configuration: Configuration) -> OvercookedState:
    equipment_sprites = {
        entry.name: equipment_sprite_definition(entry)
        for entry in [*configuration.legend.equipment]
        # Keep definitions for stations that only have an overlay.
        if entry.sprite_parts or entry.overlay_parts
    }
    equipment_sounds = {
        entry.name: sound
        for entry, sound in (
            (entry, equipment_sound_definition(entry))
            for entry in configuration.legend.equipment
        )
        if sound is not None
    }
    equipment_verbs = {
        entry.name: entry.verb for entry in configuration.legend.equipment if entry.verb
    }
    plate_with_sprite = next(
        (
            plate
            for plate in reversed(configuration.legend.plates)
            if plate.sprite_parts
        ),
        None,
    )
    if plate_with_sprite:
        equipment_sprites[PLATE_NAME] = EquipmentSpriteDefinition(
            parts=sprite_frame_parts(plate_with_sprite.sprite_parts),
            display_food="on_equipment",
            on_food_in=None,
            on_food_out=None,
            on_cook=None,
        )

    default_reward = configuration.scoring.default_order_reward
    default_time_limit = configuration.rules.default_order_time_limit
    order_entries = [
        OrderEntry(
            name=order.food,
            reward=order.reward if order.reward is not None else default_reward,
            time_limit=(
                order.time_limit if order.time_limit is not None else default_time_limit
            ),
        )
        for order in configuration.state.orders
    ]

    order_generator = None
    if configuration.rules.infinite_orders:
        if not order_entries:
            raise ValueError(
                "rules.infinite_orders requires at least one order in"
                " state.orders to use as the generation pool"
            )
        order_generator = OrderGenerator(
            pool=order_entries,
            seed=configuration.rules.order_seed,
            max_visible=configuration.rules.max_visible_orders or len(order_entries),
        )

    return OvercookedState(
        name=configuration.name,
        description=configuration.description,
        order_queue=OrderQueue.from_orders(
            order_entries,
            strict_ordering=configuration.rules.strict_ordering,
            order_reveal=configuration.rules.order_reveal,
            generator=order_generator,
        ),
        scoring=ScoringState(
            retrieve_order_component_reward=(
                configuration.scoring.retrieve_order_component_reward
            ),
            produce_order_component_reward=(
                configuration.scoring.produce_order_component_reward
            ),
            produce_ordered_item_reward=(
                configuration.scoring.produce_ordered_item_reward
            ),
        ),
        food_sprites={
            food.name: SpriteDefinition(parts=sprite_frame_parts(food.sprite_parts))
            for food in configuration.legend.foods
        },
        equipment_sprites=equipment_sprites,
        equipment_verbs=equipment_verbs,
        equipment_sounds=equipment_sounds,
        soundtrack=SoundtrackDefinition(
            tracks=tuple(configuration.soundtrack.tracks),
            gain=configuration.soundtrack.gain,
        ),
        food_definitions={
            food.name: FoodDefinition(
                name=food.name,
                raw=food.raw,
                deliverable=food.deliverable,
            )
            for food in configuration.legend.foods
        },
        cook_recipes=[
            CookRecipe(
                ingredient=recipe.ingredient,
                equipment=recipe.with_,
                output=recipe.to_make,
            )
            for recipe in configuration.recipes.cook
        ],
        combine_recipes=[
            CombineRecipe(
                ingredients=frozenset(recipe.ingredients),
                output=recipe.to_make,
            )
            for recipe in configuration.recipes.combine
        ],
        allow_illegal_recipes=configuration.rules.allow_illegal_recipes,
    )


def build_tick_mutations(configuration: Configuration) -> list[TickMutationModel]:
    """Return the world effects the level's rules switch on."""
    effects: list[TickMutationModel] = []
    if configuration.rules.timed_cooking and any(
        entry.cooks_by_itself for entry in configuration.legend.equipment
    ):
        effects.append(AdvanceCooking())
    return effects


def build_bounds(configuration: Configuration, rows: list[list[str]]) -> Bounds:
    return Bounds(
        x=0,
        y=0,
        width=configuration.bounds.width or max((len(row) for row in rows), default=0),
        height=configuration.bounds.height or len(rows),
        floor_type=configuration.appearance.floor_type,
        background=configuration.appearance.background,
    )


def build_walls(configuration: Configuration, rows: list[list[str]]) -> Walls:
    return Walls(
        x=0,
        y=0,
        width=configuration.bounds.width or max((len(row) for row in rows), default=0),
        height=configuration.bounds.height or len(rows),
        wall_type=configuration.appearance.wall_type,
    )


def build_shadows(configuration: Configuration) -> Shadows:
    return Shadows(
        id="shadows",
        x=configuration.bounds.x,
        y=configuration.bounds.y,
    )


def sprite_frame_parts(parts: list) -> list[SpriteFramePart]:
    return [
        SpriteFramePart(
            x=part.x,
            y=part.y,
            width=part.width,
            height=part.height,
            shift_x=part.shift_x,
            shift_y=part.shift_y,
            sheet=part.sheet,
        )
        for part in parts
    ]

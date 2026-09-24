from __future__ import annotations

from dataclasses import dataclass

from simulator.assets import SPRITES_DIRECTORY, asset_url
from simulator.entities import (
    Agent,
    Bin,
    Bounds,
    Counter,
    Delivery,
    Equipment,
    Food,
    GameObject,
    OrderBar,
    OvercookedState,
    Plate,
    Shadows,
    Sink,
    Sprite,
    SpriteFrame,
    SpriteFramePart,
    Storage,
    game_objects,
)
from simulator.entities.equipment import equipment_callout_parts
from simulator.environment import Environment
from simulator.mutations import Mutation
from simulator.mutations.cooking import cooking_progress
from simulator.view.renderable import Renderable

# Sprite used for the selected-agent marker.
SELECTION_MARKER_PART = SpriteFramePart(
    sheet="custom.png",
    x=0,
    y=176,
    width=16,
    height=16,
)
SELECTION_MARKER_SUFFIX = ":selected"

# Draw lift for station overlays.
OVERLAY_DRAW_LIFT = 150
OVERLAY_SUFFIX = ":overlay"

# Draw lift for station callouts.
CALLOUT_DRAW_LIFT = 250
CALLOUT_SUFFIX = ":callout"

# Draw lift for cooking progress bars, above callouts and chefs.
PROGRESS_DRAW_LIFT = 300
PROGRESS_SUFFIX = ":progress"
# Top of the bar: above food on a station, or above a callout bubble.
PROGRESS_BAR_TOP = -21
PROGRESS_BAR_TOP_OVER_CALLOUT = -35
# The bar is cut from the colour swatches along the top of kitchen.png.
PROGRESS_BAR_WIDTH = 16
PROGRESS_FILL_WIDTH = PROGRESS_BAR_WIDTH - 2


@dataclass(frozen=True)
class SceneLayers:
    """World renderables grouped by update frequency.

    ``background`` is static floor and backdrop data. ``shadows`` contains
    objects whose shadows change less often. ``objects`` contains the remaining
    renderables.
    """

    background: list[Renderable]
    shadows: list[Renderable]
    objects: list[Renderable]


def scene_layers(
    environment: Environment,
    mutations: list[Mutation] | None = None,
    *,
    selected_agent_id: str | None = None,
) -> SceneLayers:
    bounds = environment.get_first_entity_of_type(Bounds)
    if bounds is None:
        raise ValueError("Cannot build a scene without a Bounds entity")

    origin = (bounds.x or 0, bounds.y or 0)
    resolved_mutations = mutations or []

    background: list[Renderable] = []
    shadows: list[Renderable] = []
    objects: list[Renderable] = []

    for order, entity in enumerate(ordered_game_objects(environment)):
        # OrderBar is retained for compatibility with old recordings. The order
        # rail is now rendered in the DOM.
        if isinstance(entity, OrderBar):
            continue
        renderable = to_renderable(
            environment,
            entity,
            resolved_mutations,
            origin=origin,
            order=order,
        )
        if isinstance(entity, Bounds):
            background.append(renderable)
        elif isinstance(entity, Shadows):
            shadows.append(renderable)
        else:
            if isinstance(entity, Agent) and entity.id == selected_agent_id:
                objects.append(selection_marker(renderable))
            objects.append(renderable)
            overlay = equipment_overlay(environment, entity, renderable)
            if overlay is not None:
                objects.append(overlay)
            callout = equipment_callout(environment, entity, renderable)
            if callout is not None:
                objects.append(callout)
            progress = equipment_progress(environment, entity, renderable)
            if progress is not None:
                objects.append(progress)

    return SceneLayers(background=background, shadows=shadows, objects=objects)


def equipment_callout(
    environment: Environment,
    entity: GameObject,
    renderable: Renderable,
) -> Renderable | None:
    """Return a separate renderable for an equipment callout."""
    if not isinstance(entity, Equipment):
        return None
    if not renderable.sprite.loop_cycle_animation:
        return None
    parts = equipment_callout_parts(environment, entity)
    if not parts:
        return None

    frame = SpriteFrame(parts=parts)
    return Renderable(
        id=f"{entity.id}{CALLOUT_SUFFIX}",
        x=renderable.x,
        y=renderable.y,
        z=renderable.z + CALLOUT_DRAW_LIFT,
        order=renderable.order,
        sprite=Sprite(
            init_animation=[frame] * len(renderable.sprite.init_animation),
            loop_cycle_animation=[frame],
        ),
    )


def equipment_progress(
    environment: Environment,
    entity: GameObject,
    renderable: Renderable,
) -> Renderable | None:
    """Return a progress bar for food cooking over several steps in a station."""
    if not isinstance(entity, Equipment):
        return None
    if not renderable.sprite.loop_cycle_animation:
        return None
    progress = cooking_progress(environment, entity)
    if progress is None:
        return None

    top = (
        PROGRESS_BAR_TOP_OVER_CALLOUT
        if equipment_callout_parts(environment, entity)
        else PROGRESS_BAR_TOP
    )
    frame = SpriteFrame(parts=progress_bar_parts(progress, top=top))
    return Renderable(
        id=f"{entity.id}{PROGRESS_SUFFIX}",
        x=renderable.x,
        y=renderable.y,
        z=renderable.z + PROGRESS_DRAW_LIFT,
        order=renderable.order,
        sprite=Sprite(
            init_animation=[frame] * len(renderable.sprite.init_animation),
            loop_cycle_animation=[frame],
        ),
    )


def progress_bar_parts(progress: float, *, top: int) -> list[SpriteFramePart]:
    """Return a framed bar filled to ``progress``, between 0 and 1."""

    def swatch(x: int, y: int, width: int, height: int, shift_x: int, shift_y: int):
        return SpriteFramePart(
            sheet="kitchen.png",
            x=x,
            y=y,
            width=width,
            height=height,
            shift_x=shift_x,
            shift_y=top + shift_y,
        )

    outline_row = (16, 6)
    outline_column = (0, 27)
    track = (80, 7)
    fill = (16, 7)
    fill_width = round(PROGRESS_FILL_WIDTH * max(0.0, min(1.0, progress)))
    parts = [
        swatch(*outline_row, PROGRESS_BAR_WIDTH, 1, 0, 0),
        swatch(*outline_row, PROGRESS_BAR_WIDTH, 1, 0, 3),
        swatch(*outline_column, 1, 2, 0, 1),
        swatch(*outline_column, 1, 2, PROGRESS_BAR_WIDTH - 1, 1),
        swatch(*track, PROGRESS_FILL_WIDTH, 2, 1, 1),
    ]
    if fill_width:
        parts.append(swatch(*fill, fill_width, 2, 1, 1))
    return parts


def equipment_overlay(
    environment: Environment,
    entity: GameObject,
    renderable: Renderable,
) -> Renderable | None:
    """Return the overlay renderable for an equipment sprite.

    The overlay is drawn separately so contents can appear between the station's
    base and front parts.
    """
    if not isinstance(entity, Equipment):
        return None
    state = environment.get_first_entity_of_type(OvercookedState)
    sprite = state.get_equipment_sprite(entity.name) if state else None
    if sprite is None or not sprite.overlay:
        return None
    # Equipment in an agent's hands has no world sprite or overlay.
    if not renderable.sprite.loop_cycle_animation:
        return None

    frame = SpriteFrame(parts=list(sprite.overlay))
    return Renderable(
        id=f"{entity.id}{OVERLAY_SUFFIX}",
        x=renderable.x,
        y=renderable.y,
        z=renderable.z + OVERLAY_DRAW_LIFT,
        order=renderable.order,
        sprite=Sprite(
            init_animation=[frame] * len(renderable.sprite.init_animation),
            loop_cycle_animation=[frame],
        ),
    )


def selection_marker(agent: Renderable) -> Renderable:
    """Return the selected-agent marker renderable."""
    frame = SpriteFrame(parts=[SELECTION_MARKER_PART])
    return Renderable(
        id=f"{agent.id}{SELECTION_MARKER_SUFFIX}",
        x=agent.x,
        y=agent.y,
        # Draw just below the agent.
        z=agent.z - 1,
        order=agent.order,
        sprite=Sprite(
            init_animation=[frame] * len(agent.sprite.init_animation),
            loop_cycle_animation=[frame],
        ),
    )


def to_renderable(
    environment: Environment,
    entity: GameObject,
    mutations: list[Mutation],
    *,
    origin: tuple[int, int] = (0, 0),
    order: int = 0,
) -> Renderable:
    """Convert a simulation entity to renderer data."""
    origin_x, origin_y = origin
    return Renderable(
        id=entity.id,
        x=float((entity.x or 0) - origin_x),
        y=float((entity.y or 0) - origin_y),
        z=draw_z(entity),
        order=order,
        sprite=entity.sprite(environment, mutations),
    )


def draw_z(entity: GameObject) -> int:
    return (entity.y or 0) * 1000 + draw_priority(entity)


def ordered_game_objects(environment: Environment) -> list[GameObject]:
    return [
        entity
        for _, entity in sorted(
            enumerate(game_objects(environment)),
            key=lambda item: (
                draw_priority(item[1]),
                item[1].y if item[1].y is not None else -1,
                item[1].x if item[1].x is not None else -1,
                item[0],
            ),
        )
    ]


def draw_priority(entity: GameObject) -> int:
    if isinstance(entity, (Counter, Bin, Storage, Delivery)):
        return 0
    # Draw the wide sink basin above neighboring counters.
    if isinstance(entity, Sink):
        return 100
    if isinstance(entity, Equipment):
        if isinstance(entity, Plate):
            return 50
        return 200 if entity.can_pick_up else 100
    if isinstance(entity, Agent):
        return 0
    if isinstance(entity, Food):
        return 300
    return -100


# Aliases for sheet names used by older recordings.
LEGACY_SHEET_NAMES: dict[str, str] = {
    "Custom.png": "custom.png",
    "VibrantFoodsNoBackground.png": "food.png",
    "Interiors_16x16.png": "interiors.png",
    "Room_Builder_16x16.png": "room_builder.png",
    "UI_16x16.png": "ui.png",
    "Shadows.png": "shadows.png",
    "Poof.png": "poof.png",
    "animated_kitchen_oven.png": "oven.png",
    **{f"bg_{index}.png": f"backgrounds/background_{index}.png" for index in range(9)},
    **{f"chef_{index}.png": f"chefs/chef_{index}.png" for index in range(1, 17)},
}


def sprite_sheet_urls() -> dict[str, str]:
    """Return served URLs for all sprite sheets and legacy aliases."""
    urls = {
        path.relative_to(SPRITES_DIRECTORY).as_posix(): (asset_url(path))
        for path in sorted(SPRITES_DIRECTORY.rglob("*.png"))
        if path.is_file()
    }
    for legacy, current in LEGACY_SHEET_NAMES.items():
        if current in urls:
            urls.setdefault(legacy, urls[current])
    return urls

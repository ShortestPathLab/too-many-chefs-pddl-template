from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from simulator.entities import Orientation
from simulator.models import SimulatorModel


class ConfigurationModel(SimulatorModel):
    pass


class BoundsConfiguration(ConfigurationModel):
    x: int = 0
    y: int = 0
    width: int | None = None
    height: int | None = None


class AppearanceConfiguration(ConfigurationModel):
    floor_type: int = 42
    wall_type: int = 6
    counter_wood_variant: int = 2
    background: int = 0


class HeldItemConfiguration(ConfigurationModel):
    name: str = ""
    raw: bool = True
    deliverable: bool = False


class SpritePartConfiguration(ConfigurationModel):
    x: int = 0
    y: int = 0
    width: int = 16
    height: int = 16
    shift_x: int = 0
    shift_y: int = 0
    sheet: str = ""


class EquipmentAnimationConfiguration(ConfigurationModel):
    sprite_parts: list[SpritePartConfiguration] = Field(
        default_factory=list,
        alias="sprite",
    )
    frames: int = Field(default=1, ge=1)


class SoundConfiguration(ConfigurationModel):
    """Sound settings for an equipment action.

    The value can be one filename, a list of clips, or a mapping::

        sound: chop.ogg
        sound: [chop.ogg, knifeSlice.ogg]
        sound: {clips: [chop.ogg, knifeSlice.ogg], gain: 0.5, jitter: 0.07}

    Paths are relative to ``assets/audio``. Equipment without a sound uses a
    generic cue.
    """

    clips: list[str] = Field(default_factory=list)
    gain: float | None = Field(default=None, gt=0, le=1)
    jitter: float | None = Field(default=None, ge=0, lt=1)

    @model_validator(mode="before")
    @classmethod
    def expand_shorthand(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"clips": [value]}
        if isinstance(value, list):
            return {"clips": value}
        return value


class SoundtrackConfiguration(ConfigurationModel):
    """Music settings for a level.

    The value can be one track, a list of tracks, or a mapping::

        soundtrack: low-key-cooking-side-a
        soundtrack: [low-key-cooking-side-a, low-key-cooking-side-b]
        soundtrack: {tracks: [turning-up-the-heat], gain: 0.2}

    Tracks are file stems resolved against ``assets/audio/soundtrack``. The
    visualiser loops them in the order given. A level without tracks uses only
    action cues.
    """

    tracks: list[str] = Field(default_factory=list)
    gain: float | None = Field(default=None, gt=0, le=1)

    @model_validator(mode="before")
    @classmethod
    def expand_shorthand(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"tracks": [value]}
        if isinstance(value, list):
            return {"tracks": value}
        return value


class SymbolConfiguration(ConfigurationModel):
    symbol: str = ""
    key: str | None = None


class AgentSymbolConfiguration(SymbolConfiguration):
    name: str = ""
    kind: Literal["agent"] = "agent"
    orientation: Orientation = "s"
    held_item: HeldItemConfiguration | None = None
    costume: str | None = None


class CounterSymbolConfiguration(SymbolConfiguration):
    kind: Literal["counter"] = "counter"
    held_item: HeldItemConfiguration | None = None


class DeliverySymbolConfiguration(SymbolConfiguration):
    kind: Literal["delivery"] = "delivery"
    accepted_item_names: list[str] = Field(default_factory=list)


class BinSymbolConfiguration(SymbolConfiguration):
    kind: Literal["bin"] = "bin"


class EquipmentSymbolConfiguration(SymbolConfiguration):
    kind: Literal["equipment"] = "equipment"
    name: str = ""
    # Verb shown for this station in order and action views.
    verb: str = ""
    requires: str | None = None
    can_pick_up: bool = False
    can_process_food: bool = True
    # Under rules.timed_cooking, the timesteps food takes to cook here. A
    # station that cooks by itself counts them down on its own; otherwise a chef
    # presses Cook this many times.
    cook_time: int = Field(default=1, ge=1)
    cooks_by_itself: bool = False
    display_food: Literal["callout", "on_equipment"] = "on_equipment"
    on_food_in: EquipmentAnimationConfiguration | None = None
    on_food_out: EquipmentAnimationConfiguration | None = None
    on_cook: EquipmentAnimationConfiguration | None = None
    sound: SoundConfiguration | None = None
    sprite_parts: list[SpritePartConfiguration] = Field(
        default_factory=list,
        alias="sprite",
    )
    # Sprite parts drawn above items placed on the station.
    overlay_parts: list[SpritePartConfiguration] = Field(
        default_factory=list,
        alias="overlay",
    )
    held_item: HeldItemConfiguration | None = None


class PlateSymbolConfiguration(SymbolConfiguration):
    kind: Literal["plate"] = "plate"
    sprite_parts: list[SpritePartConfiguration] = Field(
        default_factory=list,
        alias="sprite",
    )
    held_item: HeldItemConfiguration | None = None
    # Whether a starting plate is dirty.
    dirty: bool = False


class SinkSymbolConfiguration(SymbolConfiguration):
    kind: Literal["sink"] = "sink"


class FoodSymbolConfiguration(SymbolConfiguration):
    kind: Literal["food"] = "food"
    name: str = ""
    sprite_parts: list[SpritePartConfiguration] = Field(
        default_factory=list,
        alias="sprite",
    )
    raw: bool = True
    deliverable: bool = False


class StorageSymbolConfiguration(SymbolConfiguration):
    kind: Literal["storage"] = "storage"
    food_name: str = ""
    infinite_supply: bool = True


class PlateDispenserSymbolConfiguration(SymbolConfiguration):
    kind: Literal["plate_dispenser"] = "plate_dispenser"
    plate_count: int = Field(default=1, ge=0)
    dirty_plate_count: int = Field(default=0, ge=0)
    infinite_supply: bool = False
    # Whether delivered plates return dirty. Dirty plates require a sink.
    returns_dirty: bool = False


SymbolConfigurationModel = Annotated[
    AgentSymbolConfiguration
    | BinSymbolConfiguration
    | CounterSymbolConfiguration
    | DeliverySymbolConfiguration
    | EquipmentSymbolConfiguration
    | FoodSymbolConfiguration
    | PlateSymbolConfiguration
    | PlateDispenserSymbolConfiguration
    | SinkSymbolConfiguration
    | StorageSymbolConfiguration,
    Field(discriminator="kind"),
]


class LegendConfiguration(ConfigurationModel):
    agents: list[AgentSymbolConfiguration] = Field(default_factory=list)
    bins: list[BinSymbolConfiguration] = Field(default_factory=list)
    counters: list[CounterSymbolConfiguration] = Field(default_factory=list)
    deliveries: list[DeliverySymbolConfiguration] = Field(default_factory=list)
    equipment: list[EquipmentSymbolConfiguration] = Field(default_factory=list)
    plates: list[PlateSymbolConfiguration] = Field(default_factory=list)
    plate_dispensers: list[PlateDispenserSymbolConfiguration] = Field(
        default_factory=list
    )
    sinks: list[SinkSymbolConfiguration] = Field(default_factory=list)
    foods: list[FoodSymbolConfiguration] = Field(default_factory=list)
    storages: list[StorageSymbolConfiguration] = Field(default_factory=list)


class OrderConfiguration(ConfigurationModel):
    food: str = ""
    reward: int | None = Field(default=None, ge=0)
    time_limit: int | None = Field(default=None, ge=0)

    @model_validator(mode="before")
    @classmethod
    def _coerce_plain_food(cls, data: Any) -> Any:
        """Accept a food string as shorthand for a food mapping."""
        if isinstance(data, str):
            return {"food": data}
        return data


class OvercookedStateConfiguration(ConfigurationModel):
    orders: list[OrderConfiguration] = Field(default_factory=list)


class RulesConfiguration(ConfigurationModel):
    """Rules that change what the kitchen permits."""

    strict_ordering: bool = False
    order_reveal: Literal["all", "sequential"] = "all"
    default_order_time_limit: int | None = Field(default=None, ge=0)
    infinite_orders: bool = False
    order_seed: int = 0
    max_visible_orders: int | None = Field(default=None, ge=1)
    allow_illegal_recipes: bool = False
    # Stations follow their own cook_time and cooks_by_itself settings. Without
    # this rule, every station cooks with one Cook action.
    timed_cooking: bool = False


class ScoringConfiguration(ConfigurationModel):
    default_order_reward: int = Field(default=50, ge=0)
    retrieve_order_component_reward: int = Field(default=1, ge=0)
    produce_order_component_reward: int = Field(default=1, ge=0)
    produce_ordered_item_reward: int = Field(default=1, ge=0)


class CookRecipeConfiguration(ConfigurationModel):
    ingredient: str = ""
    with_: str = Field(default="", alias="with")
    to_make: str = ""


class CombineRecipeConfiguration(ConfigurationModel):
    ingredients: list[str] = Field(default_factory=list)
    to_make: str = ""


class RecipesConfiguration(ConfigurationModel):
    cook: list[CookRecipeConfiguration] = Field(default_factory=list)
    combine: list[CombineRecipeConfiguration] = Field(default_factory=list)


class Configuration(ConfigurationModel):
    name: str | None = None
    description: str | None = None
    layout: str = ""
    bounds: BoundsConfiguration = Field(default_factory=BoundsConfiguration)
    appearance: AppearanceConfiguration = Field(default_factory=AppearanceConfiguration)
    soundtrack: SoundtrackConfiguration = Field(default_factory=SoundtrackConfiguration)
    state: OvercookedStateConfiguration = Field(
        default_factory=OvercookedStateConfiguration
    )
    legend: LegendConfiguration = Field(default_factory=LegendConfiguration)
    recipes: RecipesConfiguration = Field(default_factory=RecipesConfiguration)
    rules: RulesConfiguration = Field(default_factory=RulesConfiguration)
    scoring: ScoringConfiguration = Field(default_factory=ScoringConfiguration)
    # Team rosters, for example ``team: [agent, agent]``.
    teams: dict[str, list[str]] = Field(default_factory=dict)

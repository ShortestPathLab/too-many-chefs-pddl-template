from __future__ import annotations

from simulator.configuration.configuration import (
    AgentSymbolConfiguration,
    AppearanceConfiguration,
    BinSymbolConfiguration,
    CounterSymbolConfiguration,
    DeliverySymbolConfiguration,
    EquipmentSymbolConfiguration,
    FoodSymbolConfiguration,
    HeldItemConfiguration,
    PlateDispenserSymbolConfiguration,
    PlateSymbolConfiguration,
    SinkSymbolConfiguration,
    StorageSymbolConfiguration,
    SymbolConfigurationModel,
)
from simulator.entities import (
    Agent,
    Bin,
    Counter,
    Delivery,
    Equipment,
    Food,
    Plate,
    PlateDispenser,
    Sink,
    Storage,
)
from simulator.environment import Environment

CellEntity = (
    Agent
    | Bin
    | Counter
    | Delivery
    | Equipment
    | Plate
    | PlateDispenser
    | Sink
    | Food
    | Storage
)
HolderEntity = Agent | Counter | Equipment | Plate


def place_cell(
    environment: Environment,
    entries: list[SymbolConfigurationModel],
    x: int,
    y: int,
    appearance: AppearanceConfiguration,
    *,
    timed_cooking: bool = False,
) -> Environment:
    cell_entities = []
    for entry in entries:
        entities = entities_from_symbol(
            entry, x, y, appearance, timed_cooking=timed_cooking
        )
        # Food a symbol already puts in its own holder stays there, rather than
        # going to an empty holder below it, such as the stove under a pan.
        held_ids = {
            entity.held_item_id
            for entity in entities
            if isinstance(entity, HolderEntity) and entity.held_item_id
        }
        for entity in entities:
            if entity.id in held_ids:
                cell_entities.append(entity)
            else:
                cell_entities = attach_entity_to_cell(cell_entities, entity)

    for entity in cell_entities:
        environment = environment.with_entity(entity)
    return environment


def entities_from_symbol(
    entry: SymbolConfigurationModel,
    x: int,
    y: int,
    appearance: AppearanceConfiguration,
    *,
    timed_cooking: bool = False,
) -> list[CellEntity]:
    if isinstance(entry, AgentSymbolConfiguration):
        held_food = food_entity_from_held_item(entry.held_item, None, None)
        return with_optional_food(
            held_food,
            Agent(
                # A chef without a name is known by where it starts, so it has
                # the same id every time the level loads.
                id=entry.name or f"chef_{x}_{y}",
                costume=entry.costume or entry.symbol or "1",
                x=x,
                y=y,
                orientation=entry.orientation,
                held_item_id=held_food.id if held_food else None,
            ),
        )

    if isinstance(entry, BinSymbolConfiguration):
        return [Bin(x=x, y=y)]

    if isinstance(entry, CounterSymbolConfiguration):
        held_food = food_entity_from_held_item(entry.held_item, x, y)
        return with_optional_food(
            held_food,
            Counter(
                x=x,
                y=y,
                held_item_id=held_food.id if held_food else None,
                wood_variant=appearance.counter_wood_variant,
            ),
        )

    if isinstance(entry, DeliverySymbolConfiguration):
        return [Delivery(x=x, y=y, accepted_item_names=set(entry.accepted_item_names))]

    if isinstance(entry, EquipmentSymbolConfiguration):
        held_food = food_entity_from_held_item(entry.held_item, x, y)
        return with_optional_food(
            held_food,
            Equipment(
                x=x,
                y=y,
                name=entry.name,
                requires=entry.requires,
                can_pick_up=entry.can_pick_up,
                can_process_food=entry.can_process_food,
                held_item_id=held_food.id if held_food else None,
                # Without the rule, every station cooks with one press.
                **(
                    {
                        "cook_time": entry.cook_time,
                        "cooks_by_itself": entry.cooks_by_itself,
                    }
                    if timed_cooking
                    else {}
                ),
            ),
        )

    if isinstance(entry, PlateSymbolConfiguration):
        held_food = food_entity_from_held_item(entry.held_item, x, y)
        return with_optional_food(
            held_food,
            Plate(
                x=x,
                y=y,
                held_item_id=held_food.id if held_food else None,
                dirty=entry.dirty,
            ),
        )

    if isinstance(entry, SinkSymbolConfiguration):
        return [Sink(x=x, y=y)]

    if isinstance(entry, FoodSymbolConfiguration):
        return [
            Food(
                x=x,
                y=y,
                name=entry.name,
                raw=entry.raw,
                deliverable=entry.deliverable,
            )
        ]

    if isinstance(entry, StorageSymbolConfiguration):
        return [
            Storage(
                x=x,
                y=y,
                food_name=entry.food_name,
                infinite_supply=entry.infinite_supply,
            )
        ]

    if isinstance(entry, PlateDispenserSymbolConfiguration):
        return [
            PlateDispenser(
                x=x,
                y=y,
                plate_count=entry.plate_count,
                dirty_plate_count=entry.dirty_plate_count,
                infinite_supply=entry.infinite_supply,
                returns_dirty=entry.returns_dirty,
            )
        ]

    raise TypeError(f"Unsupported symbol configuration: {type(entry).__name__}")


def attach_entity_to_cell(
    cell_entities: list[CellEntity],
    entity: CellEntity,
) -> list[CellEntity]:
    updated = list(cell_entities)
    for index in range(len(updated) - 1, -1, -1):
        current = updated[index]
        if (
            isinstance(current, Equipment)
            and current.empty
            and isinstance(entity, Food)
        ):
            updated[index] = current.copy_with(held_item_id=entity.id)
            updated.append(entity)
            return updated
        if isinstance(current, Counter) and current.empty and can_counter_hold(entity):
            updated[index] = current.copy_with(held_item_id=entity.id)
            updated.append(entity)
            return updated

    updated.append(entity)
    return updated


def can_counter_hold(
    entity: CellEntity,
) -> bool:
    return isinstance(entity, (Food, Equipment)) and getattr(entity, "portable", True)


def food_entity_from_held_item(
    configuration: HeldItemConfiguration | None,
    x: int | None,
    y: int | None,
) -> Food | None:
    if not configuration:
        return None

    return Food(
        x=x,
        y=y,
        name=configuration.name,
        raw=configuration.raw,
        deliverable=configuration.deliverable,
    )


def with_optional_food(
    food: Food | None,
    entity: HolderEntity,
) -> list[CellEntity]:
    entities: list[CellEntity] = [entity]
    if food:
        entities.insert(0, food)
    return entities

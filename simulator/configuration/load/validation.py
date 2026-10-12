from __future__ import annotations

from simulator.configuration.configuration import Configuration
from simulator.entities.plate import PLATE_NAME

BUILT_IN_ITEM_NAMES = {PLATE_NAME}


def required_food_names(configuration: Configuration) -> set[str]:
    names = {order.food for order in configuration.state.orders}
    names.update(food.name for food in configuration.legend.foods)
    names.update(storage.food_name for storage in configuration.legend.storages)

    for agent in configuration.legend.agents:
        if agent.held_item:
            names.add(agent.held_item.name)
    for counter in configuration.legend.counters:
        if counter.held_item:
            names.add(counter.held_item.name)
    for equipment in configuration.legend.equipment:
        if equipment.held_item:
            names.add(equipment.held_item.name)
    for plate in configuration.legend.plates:
        if plate.held_item:
            names.add(plate.held_item.name)

    for recipe in configuration.recipes.cook:
        names.add(recipe.ingredient)
        names.add(recipe.to_make)
    for recipe in configuration.recipes.combine:
        names.update(
            ingredient
            for ingredient in recipe.ingredients
            if ingredient not in BUILT_IN_ITEM_NAMES
        )
        names.add(recipe.to_make)

    return names


def required_food_names_from_dict(data: dict) -> set[str]:
    names = {
        order if isinstance(order, str) else order.get("food", "")
        for order in data.get("state", {}).get("orders", [])
    }
    legend_data = data.get("legend", {})
    names.update(food.get("name", "") for food in legend_data.get("foods", []))
    names.update(
        storage.get("food_name", "") for storage in legend_data.get("storages", [])
    )

    for section_name in ("agents", "counters", "equipment", "plates"):
        for entry in legend_data.get(section_name, []):
            held_item = entry.get("held_item")
            if held_item:
                names.add(held_item["name"])

    for recipe in data.get("recipes", {}).get("cook", []):
        names.add(recipe["ingredient"])
        names.add(recipe["to_make"])
    for recipe in data.get("recipes", {}).get("combine", []):
        names.update(
            ingredient
            for ingredient in recipe["ingredients"]
            if ingredient not in BUILT_IN_ITEM_NAMES
        )
        names.add(recipe["to_make"])

    return {name for name in names if name}


def validate_food_definitions(configuration: Configuration) -> None:
    defined_foods = {food.name for food in configuration.legend.foods}
    missing_foods = sorted(required_food_names(configuration) - defined_foods)
    if missing_foods:
        raise ValueError(
            "legend.foods must define every food item used by the level, including intermediate items. "
            f"Missing definitions: {', '.join(missing_foods)}"
        )


def validate_station_cooking(configuration: Configuration) -> None:
    """Refuse a timed kitchen where stations of one name cook differently.

    A planner treats every station with the same name as one kind of
    equipment, so they must agree on whether they cook by themselves.
    """
    if not configuration.rules.timed_cooking:
        return
    by_name: dict[str, set[bool]] = {}
    for entry in configuration.legend.equipment:
        by_name.setdefault(entry.name, set()).add(entry.cooks_by_itself)
    mixed = sorted(name for name, settings in by_name.items() if len(settings) > 1)
    if mixed:
        raise ValueError(
            "Equipment sharing a name must agree on cooks_by_itself. "
            f"Mixed settings: {', '.join(mixed)}"
        )

from __future__ import annotations

from typing import Any

from simulator.configuration.configuration import (
    Configuration,
    EquipmentSymbolConfiguration,
    FoodSymbolConfiguration,
    LegendConfiguration,
)

from .validation import required_food_names_from_dict


def merge_catalog_defaults(
    data: dict[str, Any],
    *,
    food_catalog: list[FoodSymbolConfiguration],
    equipment_catalog: list[EquipmentSymbolConfiguration],
) -> dict[str, Any]:
    legend_data = dict(data.get("legend", {}))
    merged_legend = {
        **legend_data,
        "equipment": merge_catalog_entries(
            legend_data.get("equipment", []),
            equipment_catalog,
        ),
        "foods": merge_catalog_foods(data, legend_data.get("foods", []), food_catalog),
    }
    return {
        **data,
        "legend": merged_legend,
    }


def merge_catalog_entries(
    level_entries: list[dict[str, Any]],
    catalog_entries: list[EquipmentSymbolConfiguration],
) -> list[dict[str, Any]]:
    catalog_by_name = {
        entry.name: catalog_equipment_to_dict(entry)
        for entry in catalog_entries
        if entry.name
    }
    return [
        merge_catalog_entry(
            level_entry, catalog_by_name.get(level_entry.get("name", ""))
        )
        for level_entry in level_entries
    ]


def merge_catalog_foods(
    data: dict[str, Any],
    level_entries: list[dict[str, Any]],
    catalog_entries: list[FoodSymbolConfiguration],
) -> list[dict[str, Any]]:
    required_food_names = sorted(required_food_names_from_dict(data))
    level_food_names = {entry.get("name", "") for entry in level_entries}
    catalog_by_name = {
        entry.name: catalog_food_to_dict(entry)
        for entry in catalog_entries
        if entry.name
    }

    merged_entries = [
        merge_catalog_entry(
            level_entry, catalog_by_name.get(level_entry.get("name", ""))
        )
        for level_entry in level_entries
    ]
    merged_entries.extend(
        catalog_by_name[name]
        for name in required_food_names
        if name in catalog_by_name and name not in level_food_names
    )
    return merged_entries


def merge_catalog_entry(
    level_entry: dict[str, Any],
    catalog_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    if not catalog_entry:
        return dict(level_entry)
    return merge_mappings(catalog_entry, level_entry)


def merge_mappings(
    base: dict[str, Any],
    override: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_mappings(merged[key], value)
        else:
            merged[key] = value
    return merged


def catalog_food_to_dict(entry: FoodSymbolConfiguration) -> dict[str, Any]:
    return Configuration(legend=LegendConfiguration(foods=[entry])).to_dict()["legend"][
        "foods"
    ][0]


def catalog_equipment_to_dict(entry: EquipmentSymbolConfiguration) -> dict[str, Any]:
    return Configuration(legend=LegendConfiguration(equipment=[entry])).to_dict()[
        "legend"
    ]["equipment"][0]

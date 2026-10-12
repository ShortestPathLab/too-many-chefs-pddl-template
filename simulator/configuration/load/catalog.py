from __future__ import annotations

from pathlib import Path

import yaml

from simulator.configuration.configuration import (
    Configuration,
    EquipmentSymbolConfiguration,
    FoodSymbolConfiguration,
)


def load_catalogs(
    level_path: Path,
) -> tuple[list[FoodSymbolConfiguration], list[EquipmentSymbolConfiguration]]:
    catalog_dir = find_catalog_dir(level_path)
    if not catalog_dir:
        return ([], [])

    return (
        load_food_catalog(catalog_dir / "food.yaml"),
        load_equipment_catalog(catalog_dir / "equipment.yaml"),
    )


def find_catalog_dir(level_path: Path) -> Path | None:
    resolved = level_path.resolve()
    for parent in (resolved.parent, *resolved.parents):
        candidate = parent / "catalog"
        if candidate.is_dir():
            return candidate
    return None


def load_food_catalog(path: Path) -> list[FoodSymbolConfiguration]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or []
    return Configuration.from_dict({"legend": {"foods": data}}).legend.foods


def load_equipment_catalog(path: Path) -> list[EquipmentSymbolConfiguration]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or []
    return Configuration.from_dict({"legend": {"equipment": data}}).legend.equipment

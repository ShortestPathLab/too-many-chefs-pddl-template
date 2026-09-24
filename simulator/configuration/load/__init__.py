from __future__ import annotations

from pathlib import Path

import yaml

from simulator.configuration.configuration import (
    Configuration,
    EquipmentSymbolConfiguration,
    FoodSymbolConfiguration,
)
from simulator.environment import Environment

from .catalog import load_catalogs
from .entities import place_cell
from .layout import build_symbol_index, parse_layout_rows
from .merge_defaults import merge_catalog_defaults
from .state import (
    build_bounds,
    build_overcooked_state,
    build_shadows,
    build_tick_mutations,
    build_walls,
)
from .teams import assign_teams
from .validation import validate_food_definitions, validate_station_cooking


def load_configuration(path: str | Path) -> Configuration:
    path = Path(path)
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    food_catalog, equipment_catalog = load_catalogs(path)
    return configuration_from_dict(
        data,
        food_catalog=food_catalog,
        equipment_catalog=equipment_catalog,
    )


def configuration_from_dict(
    data: dict,
    *,
    food_catalog: list[FoodSymbolConfiguration] | None = None,
    equipment_catalog: list[EquipmentSymbolConfiguration] | None = None,
) -> Configuration:
    configuration = Configuration.from_dict(
        merge_catalog_defaults(
            data,
            food_catalog=food_catalog or [],
            equipment_catalog=equipment_catalog or [],
        )
    )
    validate_food_definitions(configuration)
    validate_station_cooking(configuration)
    return configuration


def load(
    configuration: Configuration,
    environment: Environment | None = None,
) -> Environment:
    environment = environment or Environment()
    rows = parse_layout_rows(configuration.layout)

    environment = (
        environment.copy_with(tick_mutations=build_tick_mutations(configuration))
        .with_entity(build_bounds(configuration, rows))
        .with_entity(build_shadows(configuration))
        .with_entity(build_walls(configuration, rows))
        .with_entity(build_overcooked_state(configuration))
    )

    symbol_index = build_symbol_index(configuration.legend)

    for row_index, row in enumerate(rows):
        for column_index, cell in enumerate(row):
            symbols = [symbol for symbol in cell if symbol != " "]
            if not symbols:
                continue

            x = configuration.bounds.x + column_index
            y = configuration.bounds.y + row_index
            entries = []
            for symbol in symbols:
                entry = symbol_index.get(symbol)
                if not entry:
                    raise ValueError(f"Unknown layout symbol: {symbol!r}")
                entries.append(entry)
            environment = place_cell(
                environment,
                entries,
                x,
                y,
                configuration.appearance,
                timed_cooking=configuration.rules.timed_cooking,
            )

    # Last, because a roster names chefs and there are none to name until the
    # layout has been walked.
    return assign_teams(environment, configuration.teams)

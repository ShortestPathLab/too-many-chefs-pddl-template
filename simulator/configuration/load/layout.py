from __future__ import annotations

from simulator.configuration.configuration import (
    FoodSymbolConfiguration,
    LegendConfiguration,
    SymbolConfigurationModel,
)


def parse_layout_rows(layout: str) -> list[list[str]]:
    parsed_rows: list[list[str]] = []
    for row in (row.strip() for row in layout.splitlines()):
        if not row:
            continue
        if "|" not in row:
            raise ValueError("Layout rows must use '|' separators.")
        cells = row.split("|")
        parsed_rows.append([cell.strip() for cell in cells[1:-1]])
    return parsed_rows


def build_symbol_index(
    legend: LegendConfiguration,
) -> dict[str, SymbolConfigurationModel]:
    index: dict[str, SymbolConfigurationModel] = {}
    for entry in (
        list(legend.agents)
        + list(legend.bins)
        + list(legend.counters)
        + list(legend.deliveries)
        + list(legend.equipment)
        + list(legend.plates)
        + list(legend.plate_dispensers)
        + list(legend.sinks)
        + list(legend.foods)
        + list(legend.storages)
    ):
        if isinstance(entry, FoodSymbolConfiguration) and not entry.symbol:
            continue
        if len(entry.symbol) != 1:
            raise ValueError(
                f"Layout symbols must be a single character: {entry.symbol!r}"
            )
        if entry.symbol in index:
            raise ValueError(f"Duplicate symbol definition: {entry.symbol!r}")
        index[entry.symbol] = entry
    return index

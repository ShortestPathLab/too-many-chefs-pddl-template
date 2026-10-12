"""Adapter for SymK.

SymK uses the Fast Downward driver interface and symbolic bidirectional search.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from .downward import DownwardDriverSolver, packaged_driver
from .registry import register_solver


@register_solver
@dataclass(frozen=True)
class SymKSolver(DownwardDriverSolver):
    name: ClassVar[str] = "symk"
    summary: ClassVar[str] = "SymK, optimal symbolic bidirectional search"
    extra: ClassVar[str | None] = "symk"
    priority: ClassVar[int] = 30

    search: str = "sym_bd()"

    @classmethod
    def driver_path(cls) -> Path | None:
        return packaged_driver("up_symk", "symk", "fast-downward.py")

    def search_arguments(self) -> list[str]:
        return ["--search-options", "--search", self.search]

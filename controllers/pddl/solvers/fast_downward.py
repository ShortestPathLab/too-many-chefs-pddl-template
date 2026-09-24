"""Fast Downward, from the ``fast-downward`` extra or from the PATH."""

from __future__ import annotations

import functools
import importlib
import importlib.util
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from .downward import DownwardDriverSolver, PlannerComponents, packaged_driver
from .registry import register_solver


@register_solver
@dataclass(frozen=True)
class FastDownwardSolver(DownwardDriverSolver):
    name: ClassVar[str] = "fast-downward"
    summary: ClassVar[str] = "Fast Downward, satisficing search (lama-first)"
    extra: ClassVar[str | None] = "fast-downward"
    priority: ClassVar[int] = 10

    #: Driver alias that selects the search and heuristics.
    alias: str = "lama-first"

    @classmethod
    def driver_path(cls) -> Path | None:
        packaged = cls._packaged_driver()
        if packaged is not None:
            return packaged
        # Fall back to a system installation.
        on_path = shutil.which("fast-downward")
        return None if on_path is None else Path(on_path)

    def driver_arguments(self, time_limit_seconds: float) -> list[str]:
        return ["--alias", self.alias, *super().driver_arguments(time_limit_seconds)]

    def components(self) -> PlannerComponents | None:
        """Return the packaged translator and search, set up as the alias says.

        A system installation, or an alias for a portfolio of searches, runs
        through the driver instead.
        """
        driver = self._packaged_driver()
        if driver is None:
            return None
        search_options = _driver_aliases(driver.parent / "driver").get(self.alias)
        if search_options is None:
            return None
        build = driver.parent / "builds" / "release" / "bin"
        search = next(
            (
                path
                for path in (build / "downward", build / "downward.exe")
                if path.exists()
            ),
            None,
        )
        if search is None or not (build / "translate").is_dir():
            return None
        return PlannerComponents(
            translator=build,
            search=search,
            search_options=tuple(search_options),
        )

    @staticmethod
    def _packaged_driver() -> Path | None:
        return packaged_driver("up_fast_downward", "downward", "fast-downward.py")


@functools.cache
def _driver_aliases(driver_dir: Path) -> dict[str, list[str]]:
    """Return the search options for each alias the driver in ``driver_dir`` has.

    The table comes from the driver itself, so the options always match the
    search executable beside it. Its package is loaded under a private name,
    because ``driver`` is too plain a name to put on the import path.
    """
    name = "_too_many_chefs_fast_downward_driver"
    spec = importlib.util.spec_from_file_location(
        name,
        driver_dir / "__init__.py",
        submodule_search_locations=[str(driver_dir)],
    )
    if spec is None or spec.loader is None:
        return {}
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
    return dict(importlib.import_module(f"{name}.aliases").ALIASES)

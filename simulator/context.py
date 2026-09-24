from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Context:
    log: bool = False

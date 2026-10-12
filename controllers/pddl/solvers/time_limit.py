"""Apply a wall-clock limit to in-process planners."""

from __future__ import annotations

import signal
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from .base import SolverTimeoutError


@contextmanager
def time_limit(seconds: float) -> Iterator[None]:
    """Apply a best-effort SIGALRM limit on POSIX main threads."""
    if seconds <= 0 or not hasattr(signal, "SIGALRM"):
        yield
        return

    def _raise_timeout(_signum: int, _frame: Any) -> None:
        raise SolverTimeoutError(f"Exceeded {seconds:g}s time limit")

    try:
        previous_handler = signal.signal(signal.SIGALRM, _raise_timeout)
    except ValueError:
        # SIGALRM is only available in the main thread.
        yield
        return

    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)

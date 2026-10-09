from __future__ import annotations


class RequiredValueError(ValueError):
    """Raised when a value expected to exist is missing."""


def required[TRequired](
    value: TRequired | None, *, message: str | None = None
) -> TRequired:
    if value is None:
        raise RequiredValueError(message or "Required value was missing")
    return value

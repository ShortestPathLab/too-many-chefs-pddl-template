from __future__ import annotations

from typing import Any, Self

from pydantic import BaseModel, ConfigDict


class SimulatorModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls.model_validate(data)

    @classmethod
    def from_json(cls, data: str | bytes | bytearray) -> Self:
        return cls.model_validate_json(data)

    def to_dict(self, *, by_alias: bool = True) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=by_alias)

    def to_json(self, *, by_alias: bool = True, **kwargs: Any) -> str:
        return self.model_dump_json(by_alias=by_alias, **kwargs)

    def copy_with(self, **update: Any) -> Self:
        return self.model_copy(update=update)


class FrozenSimulatorModel(SimulatorModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
        frozen=True,
    )

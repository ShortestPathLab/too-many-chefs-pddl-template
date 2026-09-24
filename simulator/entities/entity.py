from __future__ import annotations

from uuid import uuid4

from pydantic import Field

from simulator.models import SimulatorModel


class Entity(SimulatorModel):
    """Base type for simulator entities."""

    # Eight hex digits keep ids short in plans and recordings. Four collided in
    # about one load in a hundred of a large level, and the later entity
    # replaced the earlier one.
    id: str = Field(default_factory=lambda: str(uuid4())[:8])

"""The order queue: what has been asked for, and what is still coming."""

from __future__ import annotations

import random
from collections.abc import Iterable
from typing import Literal

from pydantic import Field

from simulator.models import FrozenSimulatorModel


class OrderEntry(FrozenSimulatorModel):
    name: str
    reward: int = Field(default=50, ge=0)
    time_limit: int | None = Field(default=None, ge=0)
    revealed_at: int = Field(default=0, ge=0)


class OrderGenerator(FrozenSimulatorModel):
    """Generate a deterministic sequence of orders from a template pool."""

    pool: list[OrderEntry] = Field(default_factory=list)
    seed: int = 0
    max_visible: int = Field(default=1, ge=1)
    generated_count: int = Field(default=0, ge=0)

    def draw(self, timestep: int) -> tuple[OrderGenerator, OrderEntry]:
        template = random.Random(f"{self.seed}:{self.generated_count}").choice(
            self.pool
        )
        entry = template.copy_with(revealed_at=timestep)
        return self.copy_with(generated_count=self.generated_count + 1), entry


class OrderQueue(FrozenSimulatorModel):
    visible: list[OrderEntry] = Field(default_factory=list)
    pending: list[OrderEntry] = Field(default_factory=list)
    strict_ordering: bool = False
    order_reveal: Literal["all", "sequential"] = "all"
    generator: OrderGenerator | None = None
    revision: int = Field(default=0, ge=0)
    delivered_count: int = Field(default=0, ge=0)
    # Expired orders distinguish an empty queue from a served queue.
    expired_count: int = Field(default=0, ge=0)
    last_successful_delivery_timestep: int | None = None
    # Progress tips paid towards the visible orders, counted by team ("" in a
    # kitchen without teams) and then by food. A food tips while fewer have
    # been paid than the visible orders need, so repeating a step cannot farm
    # points. Tips are not tied to one order: whichever dish ends up using the
    # food, each order that leaves the queue gives back its share.
    tipped: dict[str, dict[str, int]] = Field(default_factory=dict)

    @classmethod
    def from_orders(
        cls,
        orders: list[OrderEntry],
        *,
        strict_ordering: bool = False,
        order_reveal: Literal["all", "sequential"] = "all",
        generator: OrderGenerator | None = None,
    ) -> OrderQueue:
        if generator is not None:
            visible, generator = cls._refill([], generator, timestep=0)
            pending: list[OrderEntry] = []
        elif order_reveal == "sequential":
            visible = [orders[0]] if orders else []
            pending = list(orders[1:])
        else:
            visible = list(orders)
            pending = []
        return cls(
            visible=visible,
            pending=pending,
            strict_ordering=strict_ordering,
            order_reveal=order_reveal,
            generator=generator,
        )

    @staticmethod
    def _refill(
        visible: list[OrderEntry],
        generator: OrderGenerator | None,
        timestep: int,
    ) -> tuple[list[OrderEntry], OrderGenerator | None]:
        if generator is None or not generator.pool:
            return visible, generator
        while len(visible) < generator.max_visible:
            generator, entry = generator.draw(timestep)
            visible.append(entry)
        return visible, generator

    @property
    def orders(self) -> list[str]:
        return [entry.name for entry in self.visible]

    def accepts(self, dish_name: str, timestep: int) -> bool:
        eligible = [
            entry for entry in self.visible if not self._expired(entry, timestep)
        ]
        if not eligible:
            return False
        if self.order_reveal == "sequential" or self.strict_ordering:
            return eligible[0].name == dish_name
        return any(entry.name == dish_name for entry in eligible)

    def tip(
        self,
        food_name: str,
        demand: int,
        *,
        team: str | None = None,
    ) -> OrderQueue | None:
        """Pay a progress tip for ``food_name`` if the orders still owe one.

        ``demand`` is how many visible orders need the food. Return ``None``
        when ``team`` has already been paid that many tips for it. The
        revision is unchanged, because the orders on display are the same.
        """
        key = team or ""
        paid = self.tipped.get(key, {})
        if paid.get(food_name, 0) >= demand:
            return None
        return self.copy_with(
            tipped={
                **self.tipped,
                key: {**paid, food_name: paid.get(food_name, 0) + 1},
            }
        )

    def release(self, food_names: Iterable[str]) -> OrderQueue:
        """Give back one tip per food, for every team, as an order leaves."""
        wanted = set(food_names)
        tipped = {
            team: {
                food: count - (food in wanted)
                for food, count in paid.items()
                if count - (food in wanted) > 0
            }
            for team, paid in self.tipped.items()
        }
        return self.copy_with(
            tipped={team: paid for team, paid in tipped.items() if paid}
        )

    def delivered(self, dish_name: str, timestep: int) -> tuple[OrderQueue, int | None]:
        """Return the updated queue and the delivered order's reward.

        Return ``None`` for the reward when no visible order accepts the dish.
        """
        if not self.accepts(dish_name, timestep):
            return self, None

        index = next(
            index
            for index, entry in enumerate(self.visible)
            if entry.name == dish_name and not self._expired(entry, timestep)
        )
        reward = self.visible[index].reward
        visible = list(self.visible)
        del visible[index]
        pending = list(self.pending)
        if self.order_reveal == "sequential" and pending:
            visible.append(pending.pop(0).copy_with(revealed_at=timestep + 1))
        visible, generator = self._refill(visible, self.generator, timestep + 1)
        queue = self.copy_with(
            visible=visible,
            pending=pending,
            generator=generator,
            revision=self.revision + 1,
            delivered_count=self.delivered_count + 1,
            last_successful_delivery_timestep=timestep + 1,
        )
        return queue, reward

    def advance_to_timestep(self, timestep: int) -> OrderQueue:
        visible = [
            entry for entry in self.visible if not self._expired(entry, timestep)
        ]
        expired = len(self.visible) - len(visible)
        if not expired:
            return self

        pending = list(self.pending)
        if self.order_reveal == "sequential" and not visible and pending:
            visible.append(pending.pop(0).copy_with(revealed_at=timestep))
        visible, generator = self._refill(visible, self.generator, timestep)
        return self.copy_with(
            visible=visible,
            pending=pending,
            generator=generator,
            revision=self.revision + 1,
            expired_count=self.expired_count + expired,
        )

    def expiry_percent(self, entry: OrderEntry, timestep: int) -> float | None:
        return (
            1
            - max(
                0.0,
                (entry.revealed_at + entry.time_limit - timestep) / entry.time_limit,
            )
            if entry.time_limit is not None
            else None
        )

    def _expired(self, entry: OrderEntry, timestep: int) -> bool:
        return (
            entry.time_limit is not None
            and timestep > entry.revealed_at + entry.time_limit
        )

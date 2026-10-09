"""Build the action history: one lane per chef, the newest step on the right.

Everything here is read back from the recording. A lane says what a chef did
on each recent step and nothing about what their controller means to do next.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import Field

from simulator.entities import Agent, OvercookedState, badge_order
from simulator.entities.sprite import Sprite
from simulator.environment import Environment
from simulator.models import FrozenSimulatorModel
from simulator.mutations import (
    AgentMutation,
    Interact,
    MoveAgent,
    MoveAgentForward,
    Mutation,
    PickUpOrPlace,
    TurnAgent,
)
from simulator.mutations.combine.common import get_equipments_top_first
from simulator.mutations.interact import interaction_at
from simulator.recording import Recording
from simulator.view.agents import held_label, held_sprite

# How many steps a lane shows.
DEFAULT_WINDOW = 14

# What a chef was doing over a run of steps. ``act`` is a single deed with
# something in hand, ``work`` is time spent at a station.
LaneKind = Literal["idle", "walk", "act", "work", "serve"]

# Mutations that only move a chef about.
_MOVES = (MoveAgent, MoveAgentForward, TurnAgent)
# Deeds that always change what a chef is holding.
_HANDS_ON = ("pick_up", "take_from_storage", "place", "combine", "deliver", "discard")


class LaneSegment(FrozenSimulatorModel):
    """Consecutive steps one chef spent doing the same thing."""

    first: int
    last: int
    kind: LaneKind
    # A word short enough to print on the segment, such as "Take" or "Chop".
    label: str = ""
    # One character that stands for the label where a word will not fit.
    mark: str = ""
    # The same thing as a phrase, for a tooltip.
    detail: str = ""
    # What the chef was carrying or handling.
    sprite: Sprite | None = None

    @property
    def steps(self) -> int:
        return self.last - self.first + 1


class ActionLane(FrozenSimulatorModel):
    """One chef's recent history, under the number their badge shows."""

    number: int
    agent_id: str
    segments: list[LaneSegment] = Field(default_factory=list)


class ActionsView(FrozenSimulatorModel):
    """The action history, one lane per chef."""

    lanes: list[ActionLane] = Field(default_factory=list)
    # The step in the first column, and the step the kitchen is showing.
    first_step: int = 1
    current_step: int = 0
    window: int = DEFAULT_WINDOW
    empty_label: str = "Nothing yet"


class _Moment(FrozenSimulatorModel):
    """What one chef did on one step."""

    kind: LaneKind
    label: str = ""
    mark: str = ""
    detail: str = ""
    sprite: Sprite | None = None


_IDLE = _Moment(kind="idle", detail="waits")


def actions_view(
    recording: Recording,
    environment: Environment,
    *,
    order: list[str] | None = None,
    window: int = DEFAULT_WINDOW,
) -> ActionsView:
    """Return each chef's last ``window`` steps, up to ``environment``.

    Replay scrubs backwards, so the history stops at the environment being
    shown and never reaches past it.
    """
    index = environment_index_for(recording, environment)
    if index is None:
        return ActionsView(window=window)

    agent_ids = order or [agent.id for agent in badge_order(environment)]
    last = min(index, len(recording.mutations) - 1)
    first = max(1, last - window + 1)
    return ActionsView(
        lanes=[
            ActionLane(
                number=number,
                agent_id=agent_id,
                segments=_segments(recording, agent_id, first, last),
            )
            for number, agent_id in enumerate(agent_ids, start=1)
        ],
        first_step=first,
        current_step=last,
        window=window,
    )


def _segments(
    recording: Recording,
    agent_id: str,
    first: int,
    last: int,
) -> list[LaneSegment]:
    """Join steps on which the chef did the same thing into one segment."""
    segments: list[LaneSegment] = []
    for step in range(first, last + 1):
        moment = _moment(
            recording.environments[step - 1],
            recording.environments[step],
            recording.mutations[step],
            agent_id,
        )
        previous = segments[-1] if segments else None
        if previous is not None and (
            previous.kind,
            previous.label,
            previous.sprite,
        ) == (moment.kind, moment.label, moment.sprite):
            segments[-1] = previous.copy_with(last=step)
            continue
        segments.append(
            LaneSegment(
                first=step,
                last=step,
                kind=moment.kind,
                label=moment.label,
                mark=moment.mark,
                detail=moment.detail,
                sprite=moment.sprite,
            )
        )
    return segments


def _moment(
    before: Environment,
    after: Environment,
    mutations: Sequence[Mutation],
    agent_id: str,
) -> _Moment:
    """Say what a chef did on a step, from the kitchen either side of it."""
    mine = [
        mutation
        for mutation in mutations
        if getattr(mutation, "agent_id", None) == agent_id
    ]
    was = before.get_entity_as(agent_id, Agent)
    now = after.get_entity_as(agent_id, Agent)
    if not mine or was is None or now is None:
        return _IDLE

    state = after.get_first_entity_of_type(OvercookedState)
    deed = next(
        (
            mutation
            for mutation in mine
            if isinstance(mutation, AgentMutation) and not isinstance(mutation, _MOVES)
        ),
        None,
    )
    if deed is None:
        if not now.held_item_id:
            return _Moment(kind="walk", detail="walks")
        return _Moment(
            kind="walk",
            detail=f"carries {held_label(after, now).lower()}",
            sprite=held_sprite(after, state, now),
        )

    took = was.hands_free and not now.hands_free
    let_go = not was.hands_free and now.hands_free
    in_hand = held_label(before, was).lower()
    in_hand_sprite = held_sprite(before, state, was)

    kind = _deed_kind(deed, after, now, took=took, let_go=let_go)
    if kind in _HANDS_ON and (was.held_item_id, in_hand) == (
        now.held_item_id,
        held_label(after, now).lower(),
    ):
        # Play mode records a key the kitchen refused, and a deed that left
        # the chef's hands exactly as they were did not happen.
        return _IDLE

    if kind in ("pick_up", "take_from_storage"):
        return _Moment(
            kind="act",
            label="Take",
            mark="↑",
            detail=f"takes {held_label(after, now).lower()}",
            sprite=held_sprite(after, state, now),
        )
    if kind == "place":
        return _Moment(
            kind="act",
            label="Place",
            mark="↓",
            detail=f"places {in_hand}",
            sprite=in_hand_sprite,
        )
    if kind == "combine":
        return _Moment(
            kind="act",
            label="Combine",
            mark="+",
            detail=f"combines {in_hand}",
            sprite=in_hand_sprite,
        )
    if kind == "deliver":
        return _Moment(
            kind="serve",
            label="Serve",
            detail=f"serves {in_hand}",
            sprite=in_hand_sprite,
        )
    if kind == "discard":
        return _Moment(
            kind="act",
            label="Bin",
            mark="×",
            detail=f"bins {in_hand}",
            sprite=in_hand_sprite,
        )
    if kind == "wash":
        return _Moment(kind="work", label="Wash", detail="washes up")
    if kind == "cook":
        verb = _station_verb(after, state, now)
        return _Moment(kind="work", label=verb, detail=f"works the station: {verb}")
    return _IDLE


def _deed_kind(
    deed: AgentMutation,
    after: Environment,
    now: Agent,
    *,
    took: bool,
    let_go: bool,
) -> str:
    """Name what a deed did, seeing through the two that stand for several.

    A person at the keyboard presses one key to interact and one to pick up,
    place or combine, and the kitchen decides which of those it was.
    """
    if isinstance(deed, Interact):
        target = interaction_at(after, *now.looking_at)
        return target.model_fields["kind"].default if target else ""
    if isinstance(deed, PickUpOrPlace):
        if took:
            return "pick_up"
        if let_go:
            return "place"
        # Hands that were empty and still are did nothing at all.
        return "" if now.hands_free else "combine"
    return str(getattr(deed, "kind", ""))


def _station_verb(
    environment: Environment,
    state: OvercookedState | None,
    agent: Agent,
) -> str:
    """Return the verb of the station a chef is facing, such as "Chop".

    Where stations share a cell, the one holding food is the one being used.
    """
    stations = get_equipments_top_first(environment, *agent.looking_at)
    station = next(
        (station for station in stations if station.held_item_id),
        next(iter(stations), None),
    )
    if station is None or state is None:
        return "Cook"
    return state.get_equipment_verb(station.name)


def environment_index_for(
    recording: Recording,
    environment: Environment,
) -> int | None:
    for index, candidate in enumerate(recording.environments):
        if candidate == environment:
            return index
    return None

"""Build the agent inspector view."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from pydantic import Field

from simulator.entities import (
    Agent,
    Entity,
    Equipment,
    Food,
    OvercookedState,
    Plate,
    game_objects,
    team_label,
)
from simulator.entities.equipment import equipment_held_item_sprite
from simulator.entities.plate import plate_parts
from simulator.entities.sprite import Sprite, SpriteFrame, SpriteFramePart
from simulator.environment import Environment
from simulator.models import FrozenSimulatorModel
from simulator.mutations import Mutation, VirtualInput
from simulator.view.controller_status import ControllerView, controller_view
from simulator.view.orders import food_label
from simulator.view.sprite_canvas import seat_on_cell

if TYPE_CHECKING:
    from simulator.controller import Controller


class AgentView(FrozenSimulatorModel):
    number: int
    agent_id: str
    position: str
    facing: str
    orientation: str
    held_label: str
    held_sprite: Sprite | None = None
    # Score earned by this agent.
    score: int = 0
    # Team assigned to this agent, if any.
    team: str = ""
    team_label: str = ""
    selected: bool = False
    controller: ControllerView | None = None
    # Inputs this agent used on the last step.
    pressed: list[VirtualInput] = Field(default_factory=list)


class AgentsView(FrozenSimulatorModel):
    agents: list[AgentView] = Field(default_factory=list)
    selected_index: int = 0


def agents_view(
    environment: Environment,
    *,
    order: list[str],
    selected_agent_id: str | None = None,
    controller: Controller | None = None,
    mutations: Sequence[Mutation] | None = None,
) -> AgentsView:
    state = environment.get_first_entity_of_type(OvercookedState)
    views: list[AgentView] = []

    for number, agent_id in enumerate(order, start=1):
        agent = environment.get_entity_as(agent_id, Agent)
        if agent is None:
            continue
        views.append(
            AgentView(
                number=number,
                agent_id=agent_id,
                position=f"({agent.x}, {agent.y})",
                facing=_facing(environment, agent),
                orientation=agent.orientation.upper(),
                held_label=_held_label(environment, agent),
                held_sprite=_held_sprite(environment, state, agent),
                score=state.score_for(agent_id) if state is not None else 0,
                team=agent.team or "",
                team_label=team_label(agent.team) if agent.team else "",
                selected=agent_id == selected_agent_id,
                controller=controller_view(controller, agent_id, environment),
                pressed=pressed_inputs(environment, mutations or [], agent_id),
            )
        )

    selected_index = next(
        (index for index, view in enumerate(views) if view.selected),
        0,
    )
    return AgentsView(agents=views, selected_index=selected_index)


def pressed_inputs(
    environment: Environment,
    mutations: Sequence[Mutation],
    agent_id: str,
) -> list[VirtualInput]:
    """Return the pad inputs used by one agent in a step.

    Use the environment after the step. A movement key may produce both a turn
    and a move, which represent one input.
    """
    pressed: list[VirtualInput] = []
    for mutation in mutations:
        if getattr(mutation, "agent_id", None) != agent_id:
            continue
        button = mutation.virtual_input(environment)
        if button is not None and button not in pressed:
            pressed.append(button)
    return pressed


def _facing(environment: Environment, agent: Agent) -> str:
    target_x, target_y = agent.looking_at
    facing = [
        entity
        for entity in game_objects(environment)
        if entity.x == target_x and entity.y == target_y and entity.id != agent.id
    ]
    if not facing:
        return "-"
    return ", ".join(entity.__class__.__name__ for entity in facing)


def _held_label(environment: Environment, agent: Agent) -> str:
    if not agent.held_item_id:
        return "Empty"
    held = environment.get_entity(agent.held_item_id)
    if held is None:
        return "Missing"

    label = food_label(getattr(held, "name", held.__class__.__name__))
    # Include the contents of held equipment in the label.
    contents = environment.get_entity(getattr(held, "held_item_id", None) or "")
    if contents is not None:
        return f"{label} / {food_label(getattr(contents, 'name', ''))}"
    return label


def _held_sprite(
    environment: Environment,
    state: OvercookedState | None,
    agent: Agent,
) -> Sprite | None:
    if not agent.held_item_id or state is None:
        return None
    held = environment.get_entity(agent.held_item_id)
    if held is None:
        return None
    parts = _item_parts(environment, state, held)
    if not parts:
        return None
    return Sprite(loop_cycle_animation=[SpriteFrame(parts=parts)])


def _item_parts(
    environment: Environment,
    state: OvercookedState,
    item: Entity,
) -> list[SpriteFramePart]:
    """Return sprite parts for a carried item.

    Plates and equipment may contain another entity, so their parts are composed
    from both sprites.
    """
    if isinstance(item, Food):
        definition = state.get_food_sprite(item.name)
        return list(definition.as_parts()) if definition else []

    if isinstance(item, Plate):
        return seat_on_cell(plate_parts(environment, item))

    if isinstance(item, Equipment):
        # Leave unknown equipment blank in the panel and show its label.
        definition = state.get_equipment_sprite(item.name)
        if definition is None:
            return []
        food_parts, _ = equipment_held_item_sprite(
            environment, item, definition, callout=False
        )
        return seat_on_cell([*definition.as_parts(), *food_parts])

    return []

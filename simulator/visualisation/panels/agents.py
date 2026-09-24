"""One chef at a time: what they are holding, what they pressed, who drives."""

from __future__ import annotations

from nicegui import ui

from simulator.view import AgentsView, AgentView, ControllerView, sprite_icon
from simulator.visualisation.panels.common import panel_head, row
from simulator.visualisation.panels.gamepad import gamepad
from simulator.visualisation.theme import (
    ACCENT,
    ACCENT_EDGE,
    ACCENT_OVER,
    CHIP,
    INK_DIM,
    INK_FAINT,
    LABEL,
    PALETTE,
    PANEL_BODY,
    PANEL_FRAME,
    PANEL_HEAD,
    ROUND_SMALL,
    RULE,
    SECTION_ROW,
    SLOT_HELD,
    SPRITE_SCALE,
    SURFACE_SUNK,
    TEXT,
    TEXT_SMALL,
    TRACK,
    TRACK_FILL,
    team_tone,
)


def agents_panel(view: AgentsView) -> None:
    with ui.column().classes(PANEL_FRAME + " w-full"):
        if not view.agents:
            panel_head("Agents")
            with ui.column().classes(PANEL_BODY):
                ui.label("No agents").classes(f"{TEXT} {INK_FAINT}")
            return

        # Agent tabs form the panel header.
        with ui.row().classes(PANEL_HEAD):
            for agent in view.agents:
                tab = f"{TEXT} {ROUND_SMALL} w-6 h-6 flex items-center justify-center leading-none border-2 "
                tab += (
                    f"{ACCENT_EDGE} {ACCENT_OVER} {ACCENT}"
                    if agent.selected
                    else f"{RULE} {INK_FAINT} {SURFACE_SUNK}"
                )
                ui.label(str(agent.number)).classes(tab)

        with ui.column().classes(PANEL_BODY):
            _agent_detail(view.agents[view.selected_index])


def _agent_detail(agent: AgentView) -> None:
    with ui.row().classes("items-center gap-1.5 flex-nowrap"):
        with ui.element("div").classes(SLOT_HELD):
            if agent.held_sprite is not None:
                sprite_icon(agent.held_sprite, scale=SPRITE_SCALE)
        ui.label("Held").classes(LABEL)
        ui.label(agent.held_label).classes(f"{TEXT} break-words min-w-0")

    if agent.team_label:
        with ui.row().classes("w-full items-center justify-between gap-2 flex-nowrap"):
            ui.label("Team").classes(LABEL)
            ui.label(agent.team_label).classes(
                f"{CHIP} {team_tone(agent.team)} truncate"
            )

    row("Pos", agent.position)
    row("Facing", f"{agent.orientation} / {agent.facing}")
    row("Tips", str(agent.score))

    with ui.row().classes(SECTION_ROW):
        ui.label("Input").classes(LABEL)
        with ui.element("div").classes("ml-auto"):
            gamepad(agent.pressed)

    if agent.controller is not None:
        _controller_block(agent.controller)


def _controller_block(controller: ControllerView) -> None:
    with ui.row().classes(SECTION_ROW):
        ui.label("Controller").classes(LABEL)
        ui.label(controller.label).classes(
            f"{CHIP} border-sky-500 text-sky-300 ml-auto truncate"
        )

    dot = "bg-emerald-400" if controller.active else f"bg-[{PALETTE.ink_ghost}]"
    with ui.row().classes("items-center gap-1.5 flex-nowrap"):
        ui.element("div").classes(f"w-2 h-2 rounded-full {dot}")
        ui.label(controller.status_label).classes(f"{TEXT} {INK_DIM}")

    progress = controller.progress
    if progress is not None:
        ui.label(f"plan {controller.plan_done} / {controller.plan_total}").classes(
            f"{TEXT_SMALL} {INK_FAINT}"
        )
        with ui.element("div").classes(TRACK):
            ui.element("div").classes(f"{TRACK_FILL} bg-sky-400").style(
                f"width: {progress * 100:.1f}%"
            )

    budget = controller.budget_progress
    if budget is not None:
        ui.label(f"budget {controller.budget_label}").classes(
            f"{TEXT_SMALL} {INK_FAINT}"
        )
        # The budget bar empties as time is used.
        fill = "bg-teal-400"
        if controller.out_of_time:
            fill = "bg-rose-500"
        elif budget <= 0.25:
            fill = "bg-amber-400"
        with ui.element("div").classes(TRACK):
            ui.element("div").classes(f"{TRACK_FILL} {fill}").style(
                f"width: {budget * 100:.1f}%"
            )

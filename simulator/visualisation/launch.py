"""Build the visualiser page and connect run-mode callbacks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nicegui import ui
from nicegui.events import KeyEventArguments

from simulator.entities import Bounds, OvercookedState, Shadows
from simulator.environment import Environment
from simulator.mutations import Mutation
from simulator.view import (
    ActionsView,
    AgentsView,
    MusicBox,
    SoundBoard,
    TimelineView,
    agents_view,
    badge_order,
    cues_for_step,
    orders_view,
    scene_layers,
    score_view,
    timeline_view,
)
from simulator.visualisation import theme
from simulator.visualisation.badges import AgentBadges
from simulator.visualisation.cues import interface_cues
from simulator.visualisation.keys import (
    AGENT_CYCLE_KEY,
    HUD_TOGGLE_KEY,
    MUSIC_TOGGLE_KEY,
    with_global_keys,
)
from simulator.visualisation.panels import (
    bottom_bar,
    left_rail,
    pad_preloads,
    summary_panel,
    top_bar,
)
from simulator.visualisation.panels.bottom_bar import controls_bar
from simulator.visualisation.server import serve
from simulator.visualisation.types import (
    ActionsFactory,
    AgentSelected,
    HudSection,
    HudSectionFactory,
    KeyHandler,
    QuitHandler,
    SummaryFactory,
    TickHandler,
    TimelineFactory,
    empty_section,
    resolve_section,
)
from simulator.visualisation.world import world_stack

if TYPE_CHECKING:
    from simulator.controller import Controller


def launch(
    environment: Environment,
    *,
    key_handler: KeyHandler | None = None,
    tick_handler: TickHandler | None = None,
    tick_interval_ms: int | None = None,
    title: str = "Too Many Chefs",
    controls: HudSection | None = None,
    actions: ActionsFactory | None = None,
    info: HudSection | HudSectionFactory | None = None,
    timeline: TimelineFactory | None = None,
    summary: SummaryFactory | None = None,
    on_quit: QuitHandler | None = None,
    controller: Controller | None = None,
    mode: str = "",
    level_label: str = "",
    on_select_agent: AgentSelected | None = None,
    show_controls: bool = True,
    show_agents: bool = True,
    show_actions: bool = True,
    show_info: bool = True,
    show_orders: bool = True,
    show_badges: bool = False,
    sound: bool = True,
    volume: float = 0.6,
    open_window: bool = True,
    background: bool = False,
) -> None:
    bounds = environment.get_first_entity_of_type(Bounds)
    if not bounds:
        raise ValueError("Cannot launch visualisation without a Bounds entity")
    if not environment.get_first_entity_of_type(Shadows):
        raise ValueError("Cannot launch visualisation without a Shadows entity")

    # Capture badge order once so labels remain stable while agents move.
    agent_order = [agent.id for agent in badge_order(environment)]

    # Selected agent shared by badges, panels, and input handling.
    selection: dict[str, str | None] = {
        "agent_id": agent_order[0] if agent_order else None
    }
    if on_select_agent is not None and selection["agent_id"] is not None:
        on_select_agent(selection["agent_id"])

    # Store the latest environment and mutations for refresh callbacks.
    current: dict[str, Any] = {"environment": environment, "mutations": []}

    def active() -> Environment:
        return current["environment"]

    # Interface-only actions are detected from view changes.
    last: dict[str, Any] = {"seen": False, "selected": None, "status": None}

    # Music is the visualiser's own state, so no run mode is told about it.
    music_state = {"muted": False}

    def resolve_timeline() -> TimelineView:
        return timeline(active()) if timeline else timeline_view(active())

    def resolve_agents() -> AgentsView:
        return agents_view(
            active(),
            order=agent_order,
            selected_agent_id=selection["agent_id"],
            controller=controller,
            mutations=current["mutations"],
        )

    def resolve_actions() -> ActionsView:
        return actions(active()) if actions else ActionsView()

    def resolve_info() -> HudSection:
        return resolve_section(info, active()) or empty_section("Info")

    def resolve_controls() -> HudSection:
        return with_global_keys(
            controls or empty_section("Controls"),
            agent_cycling=len(agent_order) > 1,
            sound=sound,
            muted=music_state["muted"],
        )

    def build_root() -> None:
        ui.colors(primary=theme.PALETTE.accent)
        ui.add_css(theme.page_css())

        with ui.element("div").classes(
            f"relative w-screen h-screen overflow-hidden {theme.INK}"
        ):
            sound_board = SoundBoard(environment, volume=volume) if sound else None
            # The browser owns soundtrack playback after initialization.
            music_box = MusicBox(environment, volume=volume) if sound else None

            # World layer.
            world = world_stack(
                environment, bounds, selected_agent_id=selection["agent_id"]
            )

            # Shade the viewport edges without dimming the HUD or catching input.
            ui.element("div").classes(
                "absolute inset-0 pointer-events-none viewport-vignette"
            ).props('aria-hidden="true"')

            # HUD layers, which can be hidden together.
            hud_layers: list[ui.element] = []
            hud_visible = {"visible": True}

            # Agent badges follow interpolated sprites.
            badges: AgentBadges | None = None
            if show_badges:
                with ui.element("div").classes(
                    "absolute inset-0 pointer-events-none"
                ) as badge_layer:
                    badges = AgentBadges(
                        agent_order, selected_agent_id=selection["agent_id"]
                    )
                hud_layers.append(badge_layer)

            # Screen-space HUD.
            with ui.element("div").classes(
                "absolute inset-0 pointer-events-none p-2"
                " flex flex-col flex-nowrap gap-2"
            ) as hud_layer:

                @ui.refreshable
                def top() -> None:
                    level_state = active().get_first_entity_of_type(OvercookedState)
                    top_bar(
                        level_name=level_state.name if level_state else None,
                        description=level_state.description if level_state else None,
                        level_label=level_label or title,
                        timeline=resolve_timeline(),
                        score=score_view(active()),
                    )

                @ui.refreshable
                def left() -> None:
                    left_rail(
                        orders=orders_view(active()) if show_orders else None,
                    )

                @ui.refreshable
                def bottom() -> None:
                    bottom_bar(
                        info=resolve_info() if show_info else None,
                        actions=resolve_actions() if show_actions else None,
                        agents=resolve_agents() if show_agents else None,
                    )

                @ui.refreshable
                def footer() -> None:
                    controls_bar(
                        mode=mode,
                        controls=resolve_controls() if show_controls else None,
                    )

                top()
                # The left rail fills the height beside the bottom controls.
                with ui.row().classes(
                    "flex-1 flex-nowrap items-stretch min-h-0 w-full"
                ):
                    left()
                    with ui.column().classes(
                        "flex-1 min-w-0 min-h-0 self-stretch justify-end"
                    ):
                        bottom()
                footer()

            hud_layers.append(hud_layer)

            # Keep the ending card visible when the HUD is hidden.
            @ui.refreshable
            def ending() -> None:
                view = summary() if summary is not None else None
                if view is None:
                    return
                summary_panel(view, on_quit=on_quit or (lambda: None))

            ending()

        def refresh_hud() -> list[str]:
            """Refresh the panels and return interface audio cues."""
            selected = selection["agent_id"]
            if badges is not None:
                badges.select(selected)
            top.refresh()
            left.refresh()
            bottom.refresh()
            footer.refresh()
            ending.refresh()
            return interface_cues(last, resolve_timeline(), selected)

        def refresh_scene(
            active_environment: Environment,
            mutations: list[Mutation] | None = None,
        ) -> None:
            # Compare the old and new environments for delivery and expiry cues.
            step_cues = (
                cues_for_step(current["environment"], active_environment, mutations)
                if sound_board is not None
                else []
            )
            current["mutations"] = list(mutations or [])
            current["environment"] = active_environment
            world.draw(
                scene_layers(
                    active_environment,
                    mutations or [],
                    selected_agent_id=selection["agent_id"],
                )
            )
            cues = refresh_hud()

            if sound_board is not None:
                sound_board.play_all(step_cues + cues)

        def cycle_agent() -> None:
            # Selecting an agent does not change the environment.
            if len(agent_order) < 2:
                return
            selected = selection["agent_id"]
            index = agent_order.index(selected) if selected in agent_order else -1
            chosen = agent_order[(index + 1) % len(agent_order)]
            selection["agent_id"] = chosen
            if on_select_agent is not None:
                on_select_agent(chosen)
            # The selection marker is part of the world layer.
            world.draw_objects(
                scene_layers(
                    active(),
                    current["mutations"],
                    selected_agent_id=chosen,
                )
            )
            cues = refresh_hud()
            if sound_board is not None:
                sound_board.play_all(cues)

        def toggle_music() -> None:
            muted = not music_state["muted"]
            music_state["muted"] = muted
            if music_box is not None:
                music_box.set_muted(muted)
            # Redraw the controls panel so it shows the new state. Nothing else
            # changed, so the refresh reports no cues to play.
            refresh_hud()

        def toggle_hud() -> None:
            hud_visible["visible"] = not hud_visible["visible"]
            for layer in hud_layers:
                layer.set_visibility(hud_visible["visible"])

        def handle_key(event: KeyEventArguments) -> None:
            # Handle global keys before mode-specific input.
            if event.action.keydown and event.key.code == AGENT_CYCLE_KEY:
                cycle_agent()
                return
            if event.action.keydown and event.key.code == HUD_TOGGLE_KEY:
                toggle_hud()
                return
            if sound and event.action.keydown and event.key.code == MUSIC_TOGGLE_KEY:
                toggle_music()
                return
            if key_handler is not None:
                key_handler(event, refresh_scene)

        ui.keyboard(on_key=handle_key, repeating=False)

        if tick_handler and tick_interval_ms is not None:
            handle_tick = tick_handler
            ui.timer(tick_interval_ms / 1000, lambda: handle_tick(refresh_scene))

    serve(
        build_root,
        title=title,
        preloads=pad_preloads(),
        open_window=open_window,
        background=background,
    )

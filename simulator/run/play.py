from __future__ import annotations

from nicegui.events import KeyEventArguments

from simulator.configuration import Configuration, load
from simulator.entities import (
    Agent,
    Orientation,
)
from simulator.mutations import (
    Interact,
    MoveAgentForward,
    Mutation,
    PickUpOrPlace,
    TurnAgent,
)
from simulator.recording import Recording
from simulator.view import actions_view, timeline_view
from simulator.visualisation import RefreshScene, launch

from .common import PLAY_CONTROLS, OnStep, ordered_agents
from .episode import Episode


def run_play_mode(
    configuration: Configuration,
    *,
    on_step: OnStep | None = None,
    level_label: str = "",
    open_window: bool = True,
) -> Recording:
    episode = Episode(load(configuration), on_step=on_step)
    queued_mutations: list[Mutation] = []
    agents = ordered_agents(episode.environment)
    selected_agent_id = agents[0].id if agents else None

    def select_agent(agent_id: str) -> None:
        """Select the agent chosen by the visualiser."""
        nonlocal selected_agent_id
        selected_agent_id = agent_id

    def get_selected_agent() -> Agent | None:
        if selected_agent_id is not None:
            selected_agent = episode.environment.get_entity_as(selected_agent_id, Agent)
            if selected_agent is not None:
                return selected_agent
        agents = ordered_agents(episode.environment)
        return agents[0] if agents else None

    def step_environment(refresh_scene: RefreshScene) -> None:
        if not queued_mutations:
            return

        mutations = queued_mutations.copy()
        queued_mutations.clear()
        # Keep presses that did nothing, so the pad still lights up for them.
        step = episode.advance(mutations, keep_illegal=True)
        refresh_scene(step.current, step.mutations)

    def wait(refresh_scene: RefreshScene) -> None:
        """Let a step pass without any chef acting."""
        step = episode.advance([])
        refresh_scene(step.current, [])

    def queue_direction(orientation: Orientation, refresh_scene: RefreshScene) -> None:
        agent = get_selected_agent()
        if not agent:
            return

        queued_mutations.append(TurnAgent(agent_id=agent.id, orientation=orientation))
        queued_mutations.append(MoveAgentForward(agent_id=agent.id))
        step_environment(refresh_scene)

    def queue_interact(refresh_scene: RefreshScene) -> None:
        agent = get_selected_agent()
        if not agent:
            return

        queued_mutations.append(Interact(agent_id=agent.id))
        step_environment(refresh_scene)

    def queue_pick_up_or_place(refresh_scene: RefreshScene) -> None:
        agent = get_selected_agent()
        if not agent:
            return

        queued_mutations.append(PickUpOrPlace(agent_id=agent.id))
        step_environment(refresh_scene)

    def handle_key(event: KeyEventArguments, refresh_scene: RefreshScene) -> None:
        if not event.action.keydown:
            return

        if event.key.code == "Enter":
            queue_interact(refresh_scene)
            return

        if event.key.code == "Space":
            queue_pick_up_or_place(refresh_scene)
            return

        if event.key.code == "Period":
            wait(refresh_scene)
            return

        orientation_map: dict[str, Orientation] = {
            "ArrowUp": "n",
            "ArrowDown": "s",
            "ArrowLeft": "w",
            "ArrowRight": "e",
        }
        orientation = orientation_map.get(event.key.code)
        if not orientation:
            return

        queue_direction(orientation, refresh_scene)

    launch(
        episode.environment,
        key_handler=handle_key,
        title="Too Many Chefs - Play",
        controls=PLAY_CONTROLS,
        actions=lambda current_environment: actions_view(
            episode.recording,
            current_environment,
            order=episode.agent_order,
        ),
        timeline=lambda current_environment: timeline_view(
            current_environment,
            rate_label="1 step / key",
        ),
        mode="Play mode",
        level_label=level_label,
        on_select_agent=select_agent,
        show_info=False,
        open_window=open_window,
    )
    return episode.recording

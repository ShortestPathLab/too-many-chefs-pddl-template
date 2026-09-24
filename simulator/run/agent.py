from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from simulator.configuration import Configuration, load
from simulator.context import Context
from simulator.controller import (
    Controller,
    wait_for_controllers,
    warm_up_controllers,
)
from simulator.entities import OvercookedState
from simulator.recording import Recording

from .common import (
    AGENT_CONTROLS,
    VISUAL_STEP_INTERVAL_MS,
    OnStep,
)
from .end_conditions import EndConditions
from .episode import Episode
from .reason import TerminationReason
from .result import RunError, SimulationResult
from .setup import RunSetup

if TYPE_CHECKING:
    from nicegui.events import KeyEventArguments

    from simulator.visualisation import RefreshScene

OnResult = Callable[[SimulationResult], None]

# What a run turns into an ``error`` result instead of letting it end the
# program. ``SystemExit`` is included so that a controller calling
# ``sys.exit()`` still gets a result. Ctrl+C is not, and stops the program.
RUN_ERRORS = (Exception, SystemExit)


def run_agent_mode(
    configuration: Configuration,
    controller: Controller,
    *,
    headless: bool = False,
    context: Context | None = None,
    on_step: OnStep | None = None,
    end_conditions: EndConditions | None = None,
    on_result: OnResult | None = None,
    setup: RunSetup | None = None,
    level_label: str = "",
    open_window: bool = True,
) -> Recording:
    runtime_context = context or Context()
    conditions = end_conditions or EndConditions()
    warm_up_error: BaseException | None = None
    try:
        # Before the episode, so its clock does not charge worker start-up to
        # a time limit or a planning budget.
        warm_up_controllers(controller)
    except RUN_ERRORS as error:
        warm_up_error = error
    except BaseException:
        controller.shutdown()
        raise
    episode = Episode(load(configuration), on_step=on_step)
    recording = episode.recording
    is_running = False
    has_started = False
    # Keep the final result for the ending card and JSON output.
    result: SimulationResult | None = None

    def nothing_left_to_do() -> TerminationReason:
        """Return the result for a controller with no more actions."""
        state = episode.environment.get_first_entity_of_type(OvercookedState)
        if state is None:
            return "completed"
        outstanding = state.visible_orders or state.order_queue.pending
        return "gave_up" if outstanding else "completed"

    def waiting_on_kitchen() -> bool:
        """Return whether time should pass for a controller with no actions.

        A controller that is still planning costs no timesteps. One that is
        only waiting, for example on food cooking in a station, would otherwise
        stop the clock it is waiting on.
        """
        return not controller.is_busy() and episode.environment.has_pending_effects()

    def end_reached() -> TerminationReason | None:
        return episode.end_reason(conditions, controller)

    def finish(reason: TerminationReason, error: BaseException | None = None) -> None:
        """Stop the run, store its result, and report it once."""
        nonlocal is_running, result
        is_running = False
        if result is not None:
            return
        result = episode.result(
            reason,
            setup=setup,
            error=RunError.from_exception(error) if error is not None else None,
        )
        if on_result is not None:
            on_result(result)

    try:
        if warm_up_error is not None:
            finish("error", warm_up_error)

        if headless:
            try:
                while result is None:
                    ended = end_reached()
                    if ended is not None:
                        finish(ended)
                        break
                    actions = controller.get_actions(
                        episode.environment, runtime_context
                    )
                    if not actions and controller.has_finished(episode.environment):
                        finish(nothing_left_to_do())
                        break
                    if not actions and not waiting_on_kitchen():
                        wait_for_controllers(controller, 0.01)
                        continue
                    episode.advance(actions)
            except RUN_ERRORS as error:
                # With a result stored, the error came from reporting it.
                if result is not None:
                    raise
                finish("error", error)
            return recording

        # Only a run with a window needs the visualiser, which is slow to import.
        from simulator.view import actions_view, summary_view, timeline_view
        from simulator.visualisation import launch, request_shutdown

        def tick(refresh_scene: RefreshScene) -> None:
            if not has_started or not is_running:
                return
            try:
                step_on_tick(refresh_scene)
            except RUN_ERRORS as error:
                # With a result stored, the error came from reporting it.
                if result is not None:
                    raise
                finish("error", error)
                refresh_scene(episode.environment, [])

        def step_on_tick(refresh_scene: RefreshScene) -> None:
            ended = end_reached()
            if ended is not None:
                finish(ended)
                refresh_scene(episode.environment, [])
                return

            actions = controller.get_actions(episode.environment, runtime_context)
            if not actions and controller.has_finished(episode.environment):
                finish(nothing_left_to_do())
                refresh_scene(episode.environment, [])
                return
            if not actions and not waiting_on_kitchen():
                refresh_scene(episode.environment, [])
                return

            step = episode.advance(actions)
            refresh_scene(step.current, step.mutations)

        def handle_key(event: KeyEventArguments, refresh_scene: RefreshScene) -> None:
            nonlocal has_started, is_running
            if not event.action.keydown:
                return

            if event.key.code != "Space":
                return

            # A finished run cannot be started again.
            if result is not None:
                return

            has_started = True
            is_running = not is_running
            refresh_scene(episode.environment, [])

        launch(
            episode.environment,
            key_handler=handle_key,
            tick_handler=tick,
            tick_interval_ms=VISUAL_STEP_INTERVAL_MS,
            title="Too Many Chefs - Agent",
            controls=AGENT_CONTROLS,
            actions=lambda current_environment: actions_view(
                recording,
                current_environment,
                order=episode.agent_order,
            ),
            timeline=lambda current_environment: timeline_view(
                current_environment,
                # A known end time gives the timeline a fixed range.
                total=conditions.max_timesteps,
                rate_label=f"Auto / {VISUAL_STEP_INTERVAL_MS}ms",
                status=_timeline_status(result, is_running),
            ),
            summary=lambda: summary_view(result) if result is not None else None,
            on_quit=request_shutdown,
            controller=controller,
            mode="Agent mode",
            level_label=level_label,
            show_info=False,
            open_window=open_window,
        )
        # A closed window without another end condition is a stopped run.
        finish("stopped")
        return recording
    finally:
        controller.shutdown()


def _timeline_status(result: SimulationResult | None, is_running: bool) -> str:
    if result is not None:
        return "Finished"
    return "Running" if is_running else "Paused"

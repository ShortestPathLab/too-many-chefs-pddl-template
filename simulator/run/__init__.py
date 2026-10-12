from typing import TYPE_CHECKING, Any

from .agent import RUN_ERRORS, OnResult, run_agent_mode
from .end_conditions import EndConditions, every_order_delivered
from .episode import Episode, Step
from .reason import TerminationReason
from .result import ErrorStage, RunError, SimulationResult, build_simulation_result
from .setup import ControllerAssignment, RunSetup

if TYPE_CHECKING:
    from .live import LiveFeed, LiveFrame, LiveViewer, run_live_mode
    from .play import run_play_mode
    from .replay import run_replay_mode

# These modes always open the visualiser, which takes most of a second to
# import. A headless run never needs it, so they load on first use.
_WINDOWED = {
    "LiveFeed": ".live",
    "LiveFrame": ".live",
    "LiveViewer": ".live",
    "run_live_mode": ".live",
    "run_play_mode": ".play",
    "run_replay_mode": ".replay",
}


def __getattr__(name: str) -> Any:
    module = _WINDOWED.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    return getattr(import_module(module, __name__), name)


__all__ = [
    "RUN_ERRORS",
    "ControllerAssignment",
    "EndConditions",
    "Episode",
    "ErrorStage",
    "LiveFeed",
    "LiveFrame",
    "LiveViewer",
    "OnResult",
    "RunError",
    "RunSetup",
    "SimulationResult",
    "Step",
    "TerminationReason",
    "build_simulation_result",
    "every_order_delivered",
    "run_agent_mode",
    "run_live_mode",
    "run_play_mode",
    "run_replay_mode",
]

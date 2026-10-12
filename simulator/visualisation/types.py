from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from nicegui.events import KeyEventArguments

from simulator.environment import Environment
from simulator.mutations import Mutation
from simulator.view import ActionsView, SummaryView, TimelineView

# What a run mode hands the visualiser and what the visualiser hands back.
RefreshScene = Callable[[Environment, list[Mutation] | None], None]
KeyHandler = Callable[[KeyEventArguments, RefreshScene], None]
TickHandler = Callable[[RefreshScene], None]
AgentSelected = Callable[[str], None]
TimelineFactory = Callable[[Environment], TimelineView]
ActionsFactory = Callable[[Environment], ActionsView]
# The summary describes the run, not the current frame.
SummaryFactory = Callable[[], SummaryView | None]
QuitHandler = Callable[[], None]

# A label/value list a mode wants shown in the right-hand rail. Either the list
# itself, for something fixed, or a factory called against whatever environment
# is current.
HudSection = dict[str, Any]
HudSectionFactory = Callable[[Environment], HudSection]


def resolve_section(
    section: HudSection | HudSectionFactory | None,
    environment: Environment,
) -> HudSection | None:
    if section is None:
        return None
    # A callable value is treated as a section factory.
    if callable(section):
        return cast(HudSectionFactory, section)(environment)
    return section


def empty_section(title: str) -> HudSection:
    return {"title": title, "items": []}

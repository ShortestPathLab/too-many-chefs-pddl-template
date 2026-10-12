"""Keys handled by the visualiser before mode-specific handlers."""

from __future__ import annotations

from simulator.visualisation.types import HudSection

# Key used to select the next agent.
AGENT_CYCLE_KEY = "KeyA"
AGENT_CYCLE_HINT = {"key": "A", "action": "Next agent"}
# Key used to show or hide the HUD.
HUD_TOGGLE_KEY = "KeyH"
HUD_TOGGLE_HINT = {"key": "H", "action": "Show / hide UI"}
# Key used to turn the music on and off.
MUSIC_TOGGLE_KEY = "KeyM"


def music_hint(muted: bool) -> dict[str, str]:
    """Return the M key hint, which doubles as the music indicator.

    The hint reads as the state the music is in rather than as the verb the key
    performs, so the panel answers whether music is playing or turned off.
    """
    return {"key": "M", "action": "Music: off" if muted else "Music: on"}


def with_global_keys(
    section: HudSection,
    *,
    agent_cycling: bool,
    sound: bool = False,
    muted: bool = False,
) -> HudSection:
    """Add global key hints to a mode's control list."""
    hints = [AGENT_CYCLE_HINT] if agent_cycling else []
    if sound:
        hints.append(music_hint(muted))
    return {**section, "items": [*section.get("items", []), *hints, HUD_TOGGLE_HINT]}

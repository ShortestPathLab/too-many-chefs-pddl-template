"""Locate the project's static assets.

Resolve paths relative to this package so the command works from any working
directory.
"""

from __future__ import annotations

from pathlib import Path

ASSETS_DIRECTORY = Path(__file__).resolve().parent.parent / "assets"
SPRITES_DIRECTORY = ASSETS_DIRECTORY / "sprites"
AUDIO_DIRECTORY = ASSETS_DIRECTORY / "audio"

# URL prefix used by the asset route.
ASSETS_URL = "/assets"


def asset_url(path: Path) -> str:
    """Return the URL for an asset path."""
    return f"{ASSETS_URL}/{path.relative_to(ASSETS_DIRECTORY).as_posix()}"

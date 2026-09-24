"""2v2 matches between separate controllers, as Part 4's competition plays them.

Each chef is driven by its own controller in its own process, a *seat*, and
the host steps the kitchen with whatever the seats send in time. ``host.py``
is the host, ``protocol.py`` is how the two talk, and the seat itself is
``controllers.open.seat``. ``cook match`` plays a set on one machine; the
contest server plays the same sets with each seat in its own container.

The numbers here are the competition's rules.
"""

from .host import (
    GAMES,
    MAX_TIMESTEPS,
    SIDES,
    STARTUP_SECONDS,
    TICK_SECONDS,
    GameReport,
    MatchSetupError,
    Seat,
    SeatReport,
    SetReport,
    Side,
    play_set,
    teams_of,
)
from .protocol import Connection, ConnectionClosed, ProtocolError, connect, listen

__all__ = [
    "GAMES",
    "MAX_TIMESTEPS",
    "SIDES",
    "STARTUP_SECONDS",
    "TICK_SECONDS",
    "Connection",
    "ConnectionClosed",
    "GameReport",
    "MatchSetupError",
    "ProtocolError",
    "Seat",
    "SeatReport",
    "SetReport",
    "Side",
    "connect",
    "listen",
    "play_set",
    "teams_of",
]

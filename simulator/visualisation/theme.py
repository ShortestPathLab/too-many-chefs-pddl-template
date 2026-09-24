"""Shared visualisation tokens and CSS values."""

from __future__ import annotations

from dataclasses import dataclass

from simulator.view import CanvasBackdrop


@dataclass(frozen=True)
class Palette:
    """Colours used by the visualisation's structural elements."""

    # Panel, inset, and progress-track surfaces.
    face: str
    sunk: str
    groove: str
    # Highlight used by panel bevels.
    sheen: str
    # Panel and internal borders.
    edge: str
    rule: str
    rule_light: str
    # Text colours from strongest to weakest.
    ink: str
    ink_dim: str
    ink_faint: str
    ink_ghost: str
    # Accent colours for selection, controls, and status elements.
    accent: str
    accent_ink: str
    accent_edge: str
    accent_over: str


# Neutral grey palette.
GREY = Palette(
    face="#1f2937",
    sunk="#111827",
    groove="#030712",
    sheen="#3a465c",
    edge="#374151",
    rule="#4b5563",
    rule_light="#6b7280",
    ink="#f9fafb",
    ink_dim="#d6d3d1",
    ink_faint="#a8a29e",
    ink_ghost="#78716c",
    accent="#0f766e",
    accent_ink="#5eead4",
    accent_edge="#2dd4bf",
    accent_over="#f9fafb",
)
# Dark wood palette.
WALNUT = Palette(
    face="#463325",
    sunk="#322418",
    groove="#241a11",
    sheen="#5f4632",
    edge="#8a6540",
    rule="#614631",
    rule_light="#7d5c3e",
    ink="#f4e8d5",
    ink_dim="#d9c3a4",
    ink_faint="#b99f7d",
    ink_ghost="#8f7a5e",
    accent="#2f6f60",
    accent_ink="#7fd3bd",
    accent_edge="#3f9c85",
    accent_over="#f4e8d5",
)
# Dark red wood palette.
EMBER = Palette(
    face="#3d281f",
    sunk="#2c1c15",
    groove="#1d120d",
    sheen="#563a2c",
    edge="#96633a",
    rule="#5c3f2c",
    rule_light="#7a5539",
    ink="#f2e0cb",
    ink_dim="#d8b898",
    ink_faint="#bb9673",
    ink_ghost="#8f7052",
    accent="#2f6f60",
    accent_ink="#7fd3bd",
    accent_edge="#3f9c85",
    accent_over="#f4e8d5",
)
# Light palette for visual testing. Order tickets and scores use fixed colours.
PARCHMENT = Palette(
    face="#e6cfa8",
    sunk="#d3b98c",
    groove="#b89b6c",
    sheen="#f8eed6",
    edge="#6b4a29",
    rule="#9c7c50",
    rule_light="#8a6a42",
    ink="#2d1b0b",
    ink_dim="#533418",
    ink_faint="#6b4524",
    ink_ghost="#98683e",
    accent="#1f5a4c",
    accent_ink="#1f5a4c",
    accent_edge="#1f5a4c",
    accent_over="#f0e2c4",
)

# Warm kraft palette.
KRAFT = Palette(
    face="#daa462",
    sunk="#c79457",
    groove="#aa783c",
    sheen="#f0cf9c",
    edge="#623818",
    rule="#935e2f",
    rule_light="#b1783e",
    ink="#2a1a0a",
    ink_dim="#402711",
    ink_faint="#5e3b1c",
    ink_ghost="#7f542f",
    accent="#1c5346",
    accent_ink="#12463a",
    accent_edge="#12463a",
    accent_over="#f7ead0",
)

# Active palette.
PALETTE = EMBER

HUD_FONT = "monogram"
HUD_FONT_URL = "/assets/fonts/monogram-extended.ttf"
HUD_FONT_FORMAT = "truetype"
HUD_FONT_WEIGHT = 400

BACKDROP = CanvasBackdrop(fill="#000000")
SHADOW_OPACITY = 0.2

# Shared text sizes.
TEXT_SMALL = "text-sm"
TEXT = "text-base"
TITLE = "text-lg"

# Shared corner sizes.
ROUND = "rounded-lg"
ROUND_SMALL = "rounded-sm"
# Partial corner rounding for panel headers and recipe labels.
ROUND_TOP = "rounded-t-sm"
ROUND_FOOT = "rounded-b-sm"

# Palette values exposed as utility classes.
SURFACE = f"bg-[{PALETTE.face}]"
SURFACE_SUNK = f"bg-[{PALETTE.sunk}]"
SURFACE_GROOVE = f"bg-[{PALETTE.groove}]"
EDGE = f"border-[{PALETTE.edge}]"
RULE = f"border-[{PALETTE.rule}]"
RULE_LIGHT = f"border-[{PALETTE.rule_light}]"
INK = f"text-[{PALETTE.ink}]"
INK_DIM = f"text-[{PALETTE.ink_dim}]"
INK_FAINT = f"text-[{PALETTE.ink_faint}]"
INK_GHOST = f"text-[{PALETTE.ink_ghost}]"
ACCENT = f"bg-[{PALETTE.accent}]"
ACCENT_INK = f"text-[{PALETTE.accent_ink}]"
ACCENT_EDGE = f"border-[{PALETTE.accent_edge}]"
ACCENT_OVER = f"text-[{PALETTE.accent_over}]"

# Inset panel highlight and shadow.
BEVEL = "bevel"
BEVEL_PX = "4px"
# Panel shadow cast onto the world.
BEVEL_CAST = "bevel-cast"
CAST_PX = "6px"
CAST_COLOUR = "rgba(0, 0, 0, 0.35)"

# Fixed rail width.
RAIL = "w-84"
# Center column width.
CENTRE = "w-full max-w-xl mx-auto"
SPACER = f"{RAIL} shrink-0"
PANEL = f"{ROUND} {BEVEL_CAST} border-3 {EDGE} {SURFACE} p-2 gap-2 pointer-events-auto"
# Panel frame with separate header and body.
PANEL_FRAME = (
    f"{ROUND} {BEVEL_CAST} border-3 {EDGE} {SURFACE} "
    "pointer-events-auto flex flex-nowrap flex-col min-h-0 gap-0 p-0"
)
PANEL_HEAD = f"{ROUND_TOP} {BEVEL} {SURFACE_SUNK} sticky top-0 left-0 w-full shrink-0 items-center gap-1 px-2 h-10 border-b-2 {RULE}"
PANEL_BODY = "w-full px-2 py-1.5 gap-1 min-h-0"
# Scrollable panel body.
PANEL_SCROLL = "overflow-y-auto overscroll-contain"
# Preserve child heights in flex columns.
KEEPS_HEIGHT = "shrink-0"
# Section header row.
SECTION_ROW = "w-full items-center gap-2 flex-nowrap border-t-2 {RULE} pt-1.5 mt-0.5"
# Shared label style.
LABEL = f"{TEXT_SMALL} {INK_FAINT} uppercase tracking-widest"
# Display sizes for score and timestep values.
DISPLAY = "text-3xl leading-none"
COUNTER_TEXT = "text-2xl"
# Fixed-width counter formatting.
COUNTER_DIGITS = 4
LEADING_ZEROS = INK_GHOST
KEYCAP = (
    f"{TEXT} {ROUND_SMALL} {SURFACE_SUNK} px-1.5 leading-tight border-2 {RULE_LIGHT}"
)
CHIP = f"{TEXT_SMALL} {ROUND_SMALL} uppercase px-1.5 py-0.5 border-2"
# Team text and border colours.
TEAM_INK: dict[str, str] = {
    "red": "text-rose-300",
    "blue": "text-sky-300",
    "green": "text-emerald-300",
    "yellow": "text-amber-300",
    "purple": "text-violet-300",
    "orange": "text-orange-300",
}
TEAM_EDGE: dict[str, str] = {
    "red": "border-rose-500",
    "blue": "border-sky-500",
    "green": "border-emerald-500",
    "yellow": "border-amber-500",
    "purple": "border-violet-500",
    "orange": "border-orange-500",
}
# Fallback colours for unknown team names.
TEAM_INK_UNKNOWN = INK_DIM
TEAM_EDGE_UNKNOWN = RULE_LIGHT
# Button style.
BUTTON = (
    f"{ROUND} px-3 {TEXT} border-4 {ACCENT} "
    f"*:text-[{PALETTE.accent_over}] border-[{PALETTE.groove}]"
)
# Overlay used by the end-of-run screen.
SCRIM = (
    "absolute inset-0 flex items-center justify-center bg-black/70 pointer-events-auto"
)
# Fixed sprite slots.
SLOT_SHAPE = f"{ROUND_SMALL} flex items-center justify-center shrink-0 border-2 p-px"
SLOT = f"{SLOT_SHAPE} {RULE} {SURFACE_SUNK}"
# Large and small sprite slots and their integer scales.
SLOT_LARGE = "w-14 h-14"
SLOT_SMALL = "w-9 h-9"
SPRITE_SCALE_LARGE = 3
SPRITE_SCALE = 2
SLOT_HELD = f"{SLOT} {SLOT_SMALL}"
# Shared progress-track styles.
TRACK_SHAPE = f"{ROUND_SMALL} relative w-full h-2"
TRACK = f"{TRACK_SHAPE} {SURFACE_GROOVE}"
TRACK_FILL = f"{ROUND_SMALL} h-full"

# Order ticket colours.
PAPER = "#daa462"
# Order ticket text colours.
PAPER_INK = "#412710"
PAPER_INK_DIM = "#533113"
PAPER_INK_FAINT = "#754b1f"
# Order reward colour.
PAPER_REWARD = "#ffd230"
# Order card borders.
PAPER_EDGE = "#ac7539"
# Order ticket sprite slot colours.
PAPER_SLOT_EDGE = "#a77035"
PAPER_SLOT_FILL = "#ca8e49"
# Order expiry-track background.
PAPER_CHANNEL = "#ca8e49"
# Order expiry colours.
PAPER_EXPIRY_CALM = PAPER_INK_DIM
PAPER_EXPIRY_WARM = "#814f04"
PAPER_EXPIRY_CRITICAL = "#93220b"

# Order card layout.
ORDER_CARD = (
    f"{ROUND} border-2 border-[{PAPER_INK}] bg-[{PAPER}] text-[{PAPER_INK}] {KEEPS_HEIGHT} "
    "w-full p-0 gap-0 overflow-hidden"
)
ORDER_CARD_EDGE = f"border-[{PAPER_INK}]"
ORDER_CARD_EDGE_NEXT = f"border-[{PAPER_INK}]"
# Order reward layout.
ORDER_REWARD = (
    f"{TEXT} {ROUND_SMALL} shrink-0 self-start ml-auto px-1.5 leading-tight "
    f"bg-[{PAPER_INK}] text-[{PAPER_REWARD}]"
)
# Order header layout.
ORDER_DISH = "w-full items-center gap-2 flex-nowrap px-2 py-1.5"
# Order detail band layout.
ORDER_BAND = "w-full items-start gap-1 px-2 py-1.5 min-w-0"
# Order detail separator.
ORDER_RULE = f"w-full h-px shrink-0 bg-[{PAPER_INK_FAINT}]"
_PAPER_SLOT = f"{SLOT_SHAPE} border-[{PAPER_SLOT_EDGE}] bg-[{PAPER_SLOT_FILL}]"
# Large slot for the requested dish.
PAPER_SLOT_DISH = f"{_PAPER_SLOT} {SLOT_LARGE} *:translate-y-2"
# Minimum size for recipe-step slots.
PAPER_SLOT_STEP = f"{_PAPER_SLOT} min-w-9 h-9"
# Recipe-step layout. Labels span the sprite width and stretch narrow sprites
# when the station label is longer.
RECIPE_STEP = "inline-flex flex-col items-stretch"
RECIPE_PARTS = "flex items-center justify-center gap-0.5 flex-wrap"
# Recipe-step label band.
PAPER_BAND = (
    f"{TEXT_SMALL} {ROUND_FOOT} leading-none h-3 -mt-3 self-stretch whitespace-nowrap "
    f"flex items-center justify-center bg-[{PAPER_INK}] text-[{PAPER}] px-0.5"
)
PAPER_TRACK = f"{TRACK_SHAPE} bg-[{PAPER_CHANNEL}]"
BADGE = f"{TEXT_SMALL} {ROUND_SMALL} {SURFACE_SUNK} leading-none px-1.5 py-0.5 border-2"
BADGE_IDLE = f"{BADGE} {RULE_LIGHT} {INK}"
BADGE_SELECTED = f"{BADGE} {ACCENT_EDGE} {ACCENT_INK}"
# Badge offset below an agent sprite.
BADGE_DROP_CELLS = 0.55

# Shared scrollbar dimensions and colours.
SCROLLBAR_SIZE = "8px"
# Scrollbar thumb radius.
SCROLLBAR_RADIUS = "2px"
SCROLLBAR_TRACK = PALETTE.groove
SCROLLBAR_THUMB = PALETTE.rule
SCROLLBAR_THUMB_HOVER = PALETTE.rule_light
SCROLLBAR_THUMB_ACTIVE = PALETTE.ink_ghost

# Press animation timings.
PAD_HOLD_MS = 130
PAD_PULSE_MS = 120


def team_ink(name: str) -> str:
    """A side's colour as text, for a line that is only ever words."""
    return TEAM_INK.get(name, TEAM_INK_UNKNOWN)


def team_tone(name: str) -> str:
    """A side's colour as a chip: an outline and the ink to go inside it."""
    return f"{TEAM_EDGE.get(name, TEAM_EDGE_UNKNOWN)} {team_ink(name)}"


def head_html(*, preloads: str = "") -> str:
    """Return the document head markup, including the local HUD font."""
    return f"""<!--html-->
        <style>
            @font-face {{
                font-family: '{HUD_FONT}';
                src: url('{HUD_FONT_URL}') format('{HUD_FONT_FORMAT}');
                font-weight: {HUD_FONT_WEIGHT};
                font-style: normal;
                font-display: block;
            }}
        </style>
        {preloads}
    """


def page_css() -> str:
    # Reuse the inset shadow for both panel styles.
    _inset = f"inset {BEVEL_PX} {BEVEL_PX} 0 0 {PALETTE.groove}"
    return f"""/*css*/
            body {{
                margin: 0;
                background: {PALETTE.groove};
                overflow: hidden;
                font-family: '{HUD_FONT}', ui-monospace, monospace;
                /* Prevent ligatures in the pixel font. */
                font-variant-ligatures: none;
                letter-spacing: 0.02em;
            }}

            .nicegui-content {{
                padding: 0;
            }}

            .viewport-vignette {{
                box-shadow: inset 0 0 18vmin 5vmin rgba(0, 0, 0, 0.55);
            }}

            /* Standard scrollbar properties for Firefox and newer Chromium. */
            * {{
                scrollbar-width: thin;
                scrollbar-color: {SCROLLBAR_THUMB} {SCROLLBAR_TRACK};
            }}

            /* Inset panel bevel. */
            .{BEVEL} {{
                box-shadow: {_inset};
            }}

            .{BEVEL_CAST} {{
                box-shadow: {_inset}, {CAST_PX} {CAST_PX} 0 0 {CAST_COLOUR};
            }}

            /* Scrollbar track and thumb. */
            ::-webkit-scrollbar {{
                width: {SCROLLBAR_SIZE};
                height: {SCROLLBAR_SIZE};
            }}

            ::-webkit-scrollbar-track {{
                background: {SCROLLBAR_TRACK};
            }}

            ::-webkit-scrollbar-thumb {{
                background: {SCROLLBAR_THUMB};
                border-radius: {SCROLLBAR_RADIUS};
            }}

            ::-webkit-scrollbar-thumb:hover {{
                background: {SCROLLBAR_THUMB_HOVER};
            }}

            ::-webkit-scrollbar-thumb:active {{
                background: {SCROLLBAR_THUMB_ACTIVE};
            }}

            /* Scrollbar intersection. */
            ::-webkit-scrollbar-corner {{
                background: {SCROLLBAR_TRACK};
            }}

            /* Hide scrollbar buttons. */
            ::-webkit-scrollbar-button {{
                display: none;
            }}

            /* Brief press animation. */
            @keyframes pad-press {{
                from {{ transform: scale(1); }}
                to   {{ transform: scale(1); }}
            }}

            .pad-press {{
                animation: pad-press {PAD_PULSE_MS}ms ease-out;
            }}

            /* Hold animation for a pressed button. */
            @keyframes pad-hold {{
                from {{ opacity: 1; }}
                to   {{ opacity: 0; }}
            }}

            .pad-hold {{
                animation: pad-hold {PAD_HOLD_MS}ms steps(1, end) forwards;
            }}

            @media (prefers-reduced-motion: reduce) {{
                .pad-press {{ animation: none; }}
                .pad-hold {{ animation-duration: {PAD_HOLD_MS}ms; }}
            }}
            """

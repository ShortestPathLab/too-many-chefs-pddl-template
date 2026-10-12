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


@dataclass(frozen=True)
class LayerFilters:
    """The CSS filter each layer of the kitchen is shown through.

    The fields are the layers of ``SceneLayers``, and an empty one leaves its
    layer as drawn. The browser applies a filter to a layer once the whole
    layer is painted, so a drop shadow follows the outline of everything on the
    layer and the sprites on it cast nothing on one another.
    """

    background: str = ""
    shadows: str = ""
    objects: str = ""


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
# The last thing done to each layer of the kitchen before it reaches the screen.
LAYER_FILTERS = LayerFilters(
    background="contrast(0.9) brightness(1.1)",
    # How dark a shadow lies on the floor.
    shadows="opacity(0.2)",
    # Counters, stations, food and chefs sit a little darker and sharper than
    # the room, and lift off the floor.
    objects="contrast(1.1) drop-shadow(rgba(0, 0, 0, 0.1) 0px 4px 0px)",
)

# Shared text sizes. monogram draws one pixel for every sixteenth of an em, so
# it only lands on the screen's pixels at 16px and whole multiples of that.
# Anything in between is resampled and blurs.
TEXT_SMALL = "text-base"
TEXT = "text-base"
# Names, such as the level's and a dish's. 16px is too small for them and 32px
# too large, so they take the one size off the grid and a heavier stroke, which
# the browser synthesises because monogram has a single weight. The line is
# shorter than the type so a name that wraps stays together.
TITLE = "text-[24px] leading-4"

# The HUD's own art pixel. Any smaller and the browser's smoothing rounds a
# stair off into a plain curve.
PIXEL_PX = 3
# Corners are cut away in stairs of whole art pixels, the way a sprite's would
# be, rather than curved. Each number is how far one row of pixels stops short
# of the side, from the outermost row inwards.
CORNER_STEPS = (2, 1)
CORNER_STEPS_SMALL = (1,)

# Shared corner sizes.
ROUND = "stepped"
ROUND_SMALL = "stepped-small"
# Small corners along the foot only, for the verb band under a recipe step.
ROUND_FOOT = "stepped-small-foot"

# Bars are two art pixels tall, and a whole art pixel off each corner would cut
# the end off square. Their corners step by a smaller pixel of their own.
BAR_PIXEL_PX = 2
ROUND_BAR = "stepped-bar"
# A bar that runs into a handle keeps the end that meets it square.
ROUND_BAR_START = "stepped-bar-start"

# Panels are made of things from the kitchen, and neighbours differ, so the
# eye can tell one from the next with no outline between them. They all sit at
# the lightness of the palette's wood and stay muted, so one set of inks reads
# on each of them.
WOOD = "wood"
STEEL = "steel"
SLATE = "slate"
IRON = "iron"
MATERIALS: dict[str, str] = {
    # The palette's own panel face: the pass where the order tickets hang, the
    # level's name and the chefs.
    WOOD: PALETTE.face,
    # The kitchen clock.
    STEEL: "#292f33",
    # The board the tips are chalked on.
    SLATE: "#262e29",
    # The range, where the log of each chef's deeds runs.
    IRON: "#322d29",
}
# How much of the face's colour a sunk fill and a groove keep, as the
# palette's own sunk and groove do of its face.
SUNK_SHADE = 0.72
GROOVE_SHADE = 0.47

# Panel fills. A material sets them for everything inside its panel, so a chip
# or a slot is sunk into whatever it sits on. Outside a panel they are the
# palette's.
SURFACE = "bg-[color:var(--face)]"
SURFACE_SUNK = "bg-[color:var(--sunk)]"
SURFACE_GROOVE = "bg-[color:var(--groove)]"
INK = f"text-[{PALETTE.ink}]"
INK_DIM = f"text-[{PALETTE.ink_dim}]"
INK_FAINT = f"text-[{PALETTE.ink_faint}]"
INK_GHOST = f"text-[{PALETTE.ink_ghost}]"
ACCENT = f"bg-[{PALETTE.accent}]"
ACCENT_INK = f"text-[{PALETTE.accent_ink}]"
ACCENT_OVER = f"text-[{PALETTE.accent_over}]"

# The results slip's shadow on the kitchen.
CAST_PX = "6px"
CAST_COLOUR = "rgba(0, 0, 0, 0.35)"

# Fixed rail width.
RAIL = "w-72"
# Center column width.
CENTRE = "w-full max-w-xl mx-auto"
SPACER = f"{RAIL} shrink-0"
# Panels are flat fills with no outline or shadow. The fill against the
# kitchen and the stepped corners are enough to set one apart.
PANEL = f"{ROUND} {SURFACE} p-2.5 gap-2 pointer-events-auto"
# The level's name and description, at the foot of the left rail.
CAPTION = f"{PANEL} {WOOD} w-full shrink-0 mt-auto"
# Panel frame with separate header and body.
PANEL_FRAME = (
    f"{ROUND} {SURFACE} pointer-events-auto flex flex-nowrap flex-col min-h-0 gap-0 p-0"
)
PANEL_HEAD = (
    f"{SURFACE} sticky top-0 left-0 w-full shrink-0 items-center gap-1 px-2.5 pt-1 h-10"
)
PANEL_BODY = "w-full px-2.5 pb-2.5 gap-1 min-h-0"
# Scrollable panel body.
PANEL_SCROLL = "overflow-y-auto overscroll-contain"
# Preserve child heights in flex columns.
KEEPS_HEIGHT = "shrink-0"
# Section header row. Space alone separates it from the rows above.
SECTION_ROW = "w-full items-center gap-2 flex-nowrap pt-3"
# Shared label style.
# Two of the font's pixels between letters, for the same reason as the sizes.
LABEL = f"{TEXT_SMALL} {INK_FAINT} uppercase tracking-[0.125em]"
# Display sizes for score and timestep values.
DISPLAY = "text-[32px] leading-none"
# Display-size words that may wrap, such as the verdict on the results slip.
# monogram's letters are 18px tall at this size, so a 24px line keeps two lines
# together.
HEADLINE = "text-[32px] leading-4"
COUNTER_TEXT = "text-[32px] leading-none"
# Fixed-width counter formatting.
COUNTER_DIGITS = 4
LEADING_ZEROS = INK_GHOST
KEYCAP = f"{TEXT} {ROUND_SMALL} {SURFACE_SUNK} px-2 py-0.5 leading-tight"
# A short tag. It is always the sunk fill, and its ink says what kind of tag
# it is: a team's colour, or the accent for a mode or a status.
CHIP = f"{TEXT_SMALL} {ROUND_SMALL} {SURFACE_SUNK} uppercase px-2 py-1"
# Team text colours.
TEAM_INK: dict[str, str] = {
    "red": "text-rose-300",
    "blue": "text-sky-300",
    "green": "text-emerald-300",
    "yellow": "text-amber-300",
    "purple": "text-violet-300",
    "orange": "text-orange-300",
}
# Team colours dark enough to print on paper.
TEAM_PAPER_INK: dict[str, str] = {
    "red": "text-rose-900",
    "blue": "text-sky-900",
    "green": "text-emerald-900",
    "yellow": "text-amber-900",
    "purple": "text-violet-900",
    "orange": "text-orange-900",
}
# Fallback colour for unknown team names.
TEAM_INK_UNKNOWN = INK_DIM
# Button style.
BUTTON = f"{ROUND} px-4 py-1 {TEXT} {ACCENT} *:text-[{PALETTE.accent_over}]"
# Overlay used by the end-of-run screen.
# The kitchen stays readable behind it, since the end of a run is when its final
# state is worth a look.
SCRIM = (
    "absolute inset-0 flex flex-col items-center justify-center gap-4 "
    "bg-black/50 pointer-events-auto"
)
# Fixed sprite slots.
SLOT_SHAPE = f"{ROUND_SMALL} flex items-center justify-center shrink-0 p-px"
SLOT = f"{SLOT_SHAPE} {SURFACE_SUNK}"
# Large and small sprite slots and their integer scales.
SLOT_LARGE = "w-14 h-14"
SLOT_SMALL = "w-9 h-9"
SPRITE_SCALE_LARGE = 3
SPRITE_SCALE = 2
SLOT_HELD = f"{SLOT} {SLOT_SMALL}"
# Shared progress-track styles.
TRACK_SHAPE = f"{ROUND_BAR} w-full h-1.5"
TRACK = f"{TRACK_SHAPE} relative {SURFACE_GROOVE}"
TRACK_FILL = f"{ROUND_BAR} h-full"
# The timeline's fill ends at its handle.
TRACK_FILL_TO_HANDLE = f"{ROUND_BAR_START} h-full"
# A status light. It is as small as a bar is thin, so it takes a bar's corners;
# an art pixel off each corner would leave a cross.
DOT = f"w-2 h-2 shrink-0 {ROUND_BAR}"

# Order ticket colours.
PAPER = "#daa462"
# Order ticket text colours.
PAPER_INK = "#412710"
PAPER_INK_DIM = "#533113"
PAPER_INK_FAINT = "#754b1f"
# Order reward colour.
PAPER_REWARD = "#ffd230"
# Order ticket sprite slot colour.
PAPER_SLOT_FILL = "#ca8e49"
# Order expiry-track background.
PAPER_CHANNEL = "#ca8e49"
# Order expiry colours.
PAPER_EXPIRY_CALM = PAPER_INK_DIM
PAPER_EXPIRY_WARM = "#814f04"
PAPER_EXPIRY_CRITICAL = "#93220b"

# Paper torn from a roll has a toothed edge where it came away. A ticket and
# the results slip wear one top and bottom in place of a border.
FRINGE = "fringe w-full shrink-0"
FRINGE_PX = "4px"
# A sheet of paper with its two fringes, and the paper between them.
PAPER_SHEET = f"{KEEPS_HEIGHT} w-full p-0 gap-0"
PAPER_FILL = f"bg-[{PAPER}] text-[{PAPER_INK}]"
PAPER_BODY = f"{PAPER_FILL} w-full p-0 gap-0"
# Tickets sit further apart than rows in other panels so their teeth do not mesh.
ORDER_LIST = "w-full px-2.5 pt-0 pb-2.5 gap-2 min-h-0"

# The results slip: a longer sheet of the same paper, printed like a receipt.
PAPER_CAST = "paper-cast"
RECEIPT = f"{PAPER_CAST} w-80 p-0 gap-0"
RECEIPT_BODY = f"{PAPER_FILL} w-full px-5 py-4 gap-0.5 items-stretch"
RECEIPT_CAPTION = (
    f"{TEXT_SMALL} text-[{PAPER_INK_DIM}] uppercase tracking-[0.125em] text-center"
)
RECEIPT_HEADLINE = f"{HEADLINE} text-center break-words py-1"
RECEIPT_LINE = f"{TEXT} leading-tight text-[{PAPER_INK_DIM}] text-center break-words"
RECEIPT_RULE = (
    f"w-full shrink-0 border-t-2 border-dashed border-[{PAPER_INK_FAINT}] my-1.5"
)
RECEIPT_ROW = f"{TEXT} leading-tight w-full items-baseline gap-2 flex-nowrap"
# The row of dots that leads the eye from a label to its figure.
RECEIPT_LEADER = (
    f"flex-1 min-w-4 -translate-y-1 border-b-2 border-dotted border-[{PAPER_INK_FAINT}]"
)
# The stripe across the head of the ticket that has to go out next, where the
# order of the queue matters. It is printed in a darker shade of the paper
# with bare paper above it. A stripe in the ink colour matches the panel behind
# the ticket and reads as a gap between the fringe and the paper.
ORDER_NEXT = (
    f"{TEXT_SMALL} w-full text-center uppercase tracking-[0.125em] leading-none py-1 "
    f"mt-1 bg-[{PAPER_SLOT_FILL}] text-[{PAPER_INK}]"
)
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
_PAPER_SLOT = f"{SLOT_SHAPE} bg-[{PAPER_SLOT_FILL}]"
# Large slot for the requested dish.
PAPER_SLOT_DISH = f"{_PAPER_SLOT} {SLOT_LARGE} *:translate-y-2"
# Minimum size for recipe-step slots. A slot is taller than its sprite so that
# one with a verb band across its foot can hold the sprite at the top, where the
# band covers a third of it and no more.
_PAPER_SLOT_STEP = (
    f"{ROUND_SMALL} flex justify-center shrink-0 p-px "
    f"bg-[{PAPER_SLOT_FILL}] min-w-9 h-10"
)
PAPER_SLOT_STEP = f"{_PAPER_SLOT_STEP} items-center"
PAPER_SLOT_STEP_BANDED = f"{_PAPER_SLOT_STEP} items-start"
# Recipe-step layout. Labels span the sprite width and stretch narrow sprites
# when the station label is longer.
RECIPE_STEP = "inline-flex flex-col items-stretch"
RECIPE_PARTS = "flex items-center justify-center gap-0.5 flex-wrap"
# Recipe-step label band.
PAPER_BAND = (
    f"{TEXT_SMALL} {ROUND_FOOT} leading-none h-4 -mt-4 self-stretch whitespace-nowrap "
    f"flex items-center justify-center bg-[{PAPER_INK}] text-[{PAPER}] px-0.5"
)
PAPER_TRACK = f"{TRACK_SHAPE} relative bg-[{PAPER_CHANNEL}]"
BADGE = f"{TEXT_SMALL} {ROUND_SMALL} leading-none px-2 py-1"
BADGE_IDLE = f"{BADGE} {SURFACE_SUNK} {INK}"
BADGE_SELECTED = f"{BADGE} {ACCENT} {ACCENT_OVER}"
# Badge offset below an agent sprite.
BADGE_DROP_CELLS = 0.55

# The numbered tab that stands for a chef, in the agent panel and beside a lane.
TAB = (
    f"{TEXT} {ROUND_SMALL} w-6 h-6 shrink-0 flex items-center justify-center "
    "leading-none"
)
TAB_IDLE = f"{TAB} {INK_FAINT} {SURFACE_SUNK}"
TAB_SELECTED = f"{TAB} {ACCENT_OVER} {ACCENT}"

# Action history. Each lane is a grid with one column per step.
LANE = "w-full items-center gap-2 flex-nowrap"
LANE_TRACK = "flex-1 min-w-0 grid items-center h-6"
# Inset that lines the step labels up with the tracks above them.
LANE_INSET = "pl-8"
LANE_SEGMENT = "min-w-0 mx-px flex items-center gap-0.5"
# Walking is a bar and waiting is a dotted line, so deeds stand out as boxes.
LANE_WALK = f"flex-1 h-1.5 {ROUND_BAR} bg-[{PALETTE.rule_light}]"
LANE_IDLE = "lane-idle flex-1 h-0.5"
# The newest step is always at the right edge. Until a run is as long as the
# lane, the columns to its left are dotted as waiting is, only fainter.
LANE_PAD = f"{LANE_IDLE} opacity-40"
LANE_BOX = (
    f"{TEXT} {ROUND_SMALL} h-6 px-0.5 justify-center overflow-hidden "
    "whitespace-nowrap leading-none"
)
# With no outlines, the fill tells the kinds apart: plain deeds sit in the
# sunk fill, work at a station glows amber, and a delivery is paid in the
# reward's gold.
LANE_ACT = f"{LANE_BOX} {SURFACE_SUNK} {INK}"
LANE_WORK = f"{LANE_BOX} bg-amber-900 text-amber-200"
LANE_SERVE = f"{LANE_BOX} bg-[{PAPER_REWARD}] text-[{PAPER_INK}]"
LANE_STEP = f"{TEXT} {INK_FAINT} leading-none whitespace-nowrap"
LANE_STEP_NOW = f"{TEXT} text-amber-400 leading-none whitespace-nowrap text-right"
IDLE_DASH_PX = "4px"

# The tips board, the slate a kitchen chalks its takings on. Teams write on
# their own boards in their own colours.
CHALK = "#ebe8dc"
CHALK_DIM = "#a3aa9f"
# Tips are written in yellow chalk, the nearest chalk comes to the gold of an
# order's reward.
CHALK_GOLD = "#f0d47a"
BOARD = f"{SLATE} {SURFACE} {ROUND} p-2.5 gap-0 pointer-events-auto"
BOARD_LABEL = f"{TEXT_SMALL} uppercase tracking-[0.125em] truncate"
# Boards stand to the right of the timeline, one per team in a contest.
BOARDS = "w-full justify-end gap-2"
BOARD_SOLO = "w-1/2"
# Two boards to a row, so they share the rail between them.
BOARD_TEAM = "w-[calc(50%-0.25rem)]"

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


def team_colour(name: str) -> str:
    """The colour a side's name stands for.

    Levels tend to name their sides as nouns, "reds" against "blues", where the
    command line takes the bare colour.
    """
    colour = name.strip().lower()
    return colour if colour in TEAM_INK else colour.removesuffix("s")


def team_ink(name: str) -> str:
    """A side's colour as text, for a line that is only ever words."""
    return TEAM_INK.get(team_colour(name), TEAM_INK_UNKNOWN)


def team_paper_ink(name: str) -> str:
    """A side's colour as text on paper, or the paper's own ink without one."""
    return TEAM_PAPER_INK.get(team_colour(name), "")


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


def shade(colour: str, amount: float) -> str:
    """``colour`` darkened towards black, keeping ``amount`` of each channel."""
    channels = (int(colour[index : index + 2], 16) for index in (1, 3, 5))
    return "#" + "".join(f"{round(channel * amount):02x}" for channel in channels)


def stepped_corners(
    steps: tuple[int, ...],
    *,
    pixel: int = PIXEL_PX,
    top: bool = True,
    right: bool = True,
) -> str:
    """A ``clip-path`` that cuts a box's corners away in stairs of art pixels.

    ``steps`` is a corner's profile, as ``CORNER_STEPS`` describes it, and the
    same profile is turned to fit each corner. ``pixel`` is the size of one
    step. Turning off ``top`` or ``right`` leaves the two corners on that side
    square.

    Each cut stops at the middle of the box, so a box too small for its
    corners comes out as a lozenge rather than tangling its outline.
    """
    # The top left corner, from the left side up to the top edge.
    corner = [(0, len(steps))]
    for row in reversed(range(len(steps))):
        corner += [(steps[row], row + 1), (steps[row], row)]
    corner = [
        point for index, point in enumerate(corner) if point not in corner[:index]
    ]

    def near(pixels: int) -> str:
        return f"min({pixels * pixel}px, 50%)" if pixels else "0"

    def far(pixels: int) -> str:
        return f"max(calc(100% - {pixels * pixel}px), 50%)" if pixels else "100%"

    # Clockwise from the top left.
    points: list[tuple[str, str]] = []
    if top:
        points += [(near(x), near(y)) for x, y in corner]
    else:
        points += [("0", "0")]
    if top and right:
        points += [(far(x), near(y)) for x, y in reversed(corner)]
    else:
        points += [("100%", "0")]
    if right:
        points += [(far(x), far(y)) for x, y in corner]
    else:
        points += [("100%", "100%")]
    points += [(near(x), far(y)) for x, y in reversed(corner)]
    return "polygon(" + ", ".join(f"{x} {y}" for x, y in points) + ")"


def page_css() -> str:
    bar = stepped_corners(CORNER_STEPS_SMALL, pixel=BAR_PIXEL_PX)
    bar_start = stepped_corners(CORNER_STEPS_SMALL, pixel=BAR_PIXEL_PX, right=False)
    materials = "\n".join(
        f".{name} {{ --face: {face}; --sunk: {shade(face, SUNK_SHADE)};"
        f" --groove: {shade(face, GROOVE_SHADE)}; }}"
        for name, face in MATERIALS.items()
    )
    return f"""/*css*/
            body {{
                margin: 0;
                background: {PALETTE.groove};
                /* The fills of anything that sits on no panel, such as the
                   footer's chips and keys. */
                --face: {PALETTE.face};
                --sunk: {PALETTE.sunk};
                --groove: {PALETTE.groove};
                overflow: hidden;
                font-family: '{HUD_FONT}', ui-monospace, monospace;
                /* Prevent ligatures in the pixel font. */
                font-variant-ligatures: none;
                /* monogram's letters fill little more than half an em, so
                   lines one em apart already have room between them. This is
                   the line height Tailwind gives 16px text unless a class
                   asks for another. */
                --text-base--line-height: 1;
            }}

            .nicegui-content {{
                padding: 0;
            }}

            /* Soft light darkens the kitchen's own colours towards the edges
               where a flat black would grey them out. */
            .viewport-vignette {{
                box-shadow: inset 0 0 18vmin 5vmin rgb(0, 0, 0);
                mix-blend-mode: soft-light;
            }}

            /* Standard scrollbar properties for Firefox and newer Chromium. */
            * {{
                scrollbar-width: thin;
                scrollbar-color: {SCROLLBAR_THUMB} {SCROLLBAR_TRACK};
            }}

            /* Corners cut in stairs of art pixels. */
            .{ROUND} {{
                clip-path: {stepped_corners(CORNER_STEPS)};
            }}

            .{ROUND_SMALL} {{
                clip-path: {stepped_corners(CORNER_STEPS_SMALL)};
            }}

            .{ROUND_FOOT} {{
                clip-path: {stepped_corners(CORNER_STEPS_SMALL, top=False)};
            }}

            .{ROUND_BAR} {{
                clip-path: {bar};
            }}

            .{ROUND_BAR_START} {{
                clip-path: {bar_start};
            }}

            /* Paper's shadow follows its teeth, which a box shadow would not. */
            .{PAPER_CAST} {{
                filter: drop-shadow({CAST_PX} {CAST_PX} 0 {CAST_COLOUR});
            }}

            /* Each panel's material, and the fills sunk into it. */
            {materials}

            /* The tips board's slate is written on in chalk. */
            .{SLATE} {{
                color: {CHALK};
            }}

            /* The torn edge of a sheet of paper: a row of square teeth. */
            .fringe {{
                height: {FRINGE_PX};
                background: repeating-linear-gradient(
                    90deg,
                    {PAPER} 0 {FRINGE_PX},
                    transparent {FRINGE_PX} calc({FRINGE_PX} * 2)
                );
            }}

            /* A waiting chef's lane: a dotted line in the rule colour. */
            .lane-idle {{
                background: repeating-linear-gradient(
                    90deg,
                    {PALETTE.rule_light} 0 {IDLE_DASH_PX},
                    transparent {IDLE_DASH_PX} calc({IDLE_DASH_PX} * 2)
                );
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

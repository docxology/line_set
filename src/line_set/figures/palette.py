"""Colors, shapes, and display maps for the Line Set plates.

Nothing here reads a sibling package or decides anything about a reading. It
holds the visual vocabulary the plates draw with, and the short glosses that
name what each declared code and status means.

Two rules shape every map below.

**No distinction is carried by color alone.** Every line, every read code, and
every set status is drawn with a shape *and* labeled with its own name, so a
grayscale print and a color print say the same thing. The inks are chosen so
their luminances differ as well, which helps, but the shape and the label are
what actually carry the distinction.

**A new color must not need an edit here.** :func:`line_fill` and
:func:`line_ink` prefer the named colors already declared and fall back to a
deterministic accent for anything else. :func:`shape_for` cycles through a
finite set of redundant markers; written identities remain authoritative.
An appended registry entry therefore renders without touching this module.
Maps keyed by an enumeration this package owns must stay exhaustive;
:func:`verify_coverage` fails the build when one of those falls behind.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from typing import TypeVar

from ..models import ReadCode, SetStatus
from ..reader import READER_STAGES

PAPER = "#f4f1ea"
PANEL = "#e9e4d9"
CARD = "#fbf9f4"
INK = "#22201d"
MUTED = "#6c655c"
RULE = "#c6bdae"
ACCENT = "#2f5d62"
WARN = "#9a2f26"
GOOD = "#33604a"
OCHRE = "#7a5a2a"

#: Fills and inks for the colors the set declares today.
#:
#: The white line cannot be drawn in white on paper, so its swatch is a very
#: light fill carried by a dark outline and its ink is a slate that reads at
#: the same weight as the others in grayscale.
LINE_FILL: dict[str, str] = {
    "red": "#d9a49d",
    "black": "#b8b2a8",
    "golden": "#e8c98a",
    "white": "#fbfaf7",
    "silver": "#d9dde2",
    "violet": "#dfcdf7",
    "blue": "#c6d9ef",
    "green": "#c8dfc9",
    "copper": "#ead0b8",
    "iron": "#d1d6dc",
    "colorless": "#ece8e0",
}
LINE_INK: dict[str, str] = {
    "red": "#9a2f26",
    "black": "#22201d",
    "golden": "#8a6512",
    "white": "#5c7079",
    "silver": "#565d66",
    "violet": "#6d28a6",
    "blue": "#245b9f",
    "green": "#246b37",
    "copper": "#743e20",
    "iron": "#343e4b",
    "colorless": "#6c655c",
}

#: Stroke colors for the cover plate, one per declared line color.
#:
#: Cover strokes are presentation choices, not measurements of sibling behavior.
#: The white stroke needs the thin dark under-stroke drawn by the cover plate.
COVER_STROKE: dict[str, str] = {
    "black": "#2d2d2d",
    "golden": "#b47a16",
    "white": "#ffffff",
    "silver": "#9a9a9a",
    "violet": "#7c3aed",
    "blue": "#3465a4",
    "green": "#1a7a3a",
    "copper": "#99562e",
    "iron": "#505b69",
}

#: Cover layout order, deliberately separate from the declaration's working order.
#: An unknown color follows the known ones by working position.
COVER_ORDER: tuple[str, ...] = (
    "black",
    "golden",
    "red",
    "white",
    "silver",
    "violet",
    "blue",
    "green",
    "copper",
    "iron",
)

#: Fill/ink pairs handed to a color this module has never seen.
#:
#: The choice is deterministic — a digest of the color name picks the pair —
#: so a given new color always draws the same way, on any machine and in any
#: run order.
ACCENT_CYCLE: tuple[tuple[str, str], ...] = (
    ("#a9c6c0", "#2f5d62"),
    ("#c8bcd8", "#4a3a6b"),
    ("#d8c3a5", "#7a5a2a"),
    ("#b6c9a0", "#3f5a2a"),
    ("#cfc3b0", "#5c5044"),
)

#: Distinct markers cover the declared set and its wrapper, including one extension.
#: Labels remain authoritative if a larger declaration exhausts the cycle.
SHAPE_CYCLE: tuple[str, ...] = (
    "circle",
    "square",
    "triangle",
    "diamond",
    "pentagon",
    "hexagon",
    "star",
    "cross",
    "bar",
    "chevron",
    "shield",
    "hourglass",
)

#: Stroke dash patterns, cycled by working position for the order connectors.
DASH_CYCLE: tuple[str, ...] = ("", "12 8", "3 7", "18 6 3 6", "7 7", "22 8")

READ_CODE_INK: dict[ReadCode, str] = {
    ReadCode.RESOLVED: GOOD,
    ReadCode.NOT_INSTALLED: MUTED,
    ReadCode.IMPORT_FAILED: WARN,
    ReadCode.NO_VOCABULARY: OCHRE,
}
READ_CODE_SHAPE: dict[ReadCode, str] = {
    ReadCode.RESOLVED: "circle",
    ReadCode.NOT_INSTALLED: "square",
    ReadCode.IMPORT_FAILED: "triangle",
    ReadCode.NO_VOCABULARY: "diamond",
}
#: Whether a code's marker is drawn solid. Only a read line is solid.
READ_CODE_SOLID: dict[ReadCode, bool] = {
    ReadCode.RESOLVED: True,
    ReadCode.NOT_INSTALLED: False,
    ReadCode.IMPORT_FAILED: False,
    ReadCode.NO_VOCABULARY: False,
}
READ_CODE_GLOSS: dict[ReadCode, str] = {
    ReadCode.RESOLVED: "imported, and its exported enum members were read",
    ReadCode.NOT_INSTALLED: "the import system found no such package",
    ReadCode.IMPORT_FAILED: "the package was found but raised on import",
    ReadCode.NO_VOCABULARY: "imported, but its package root exports no enum",
}

SET_STATUS_INK: dict[SetStatus, str] = {
    SetStatus.SET_COLLIDING: WARN,
    SetStatus.SET_UNDECLARED: OCHRE,
    SetStatus.SET_PARTIAL: MUTED,
    SetStatus.SET_LEGIBLE: GOOD,
}
SET_STATUS_SHAPE: dict[SetStatus, str] = {
    SetStatus.SET_COLLIDING: "square",
    SetStatus.SET_UNDECLARED: "triangle",
    SetStatus.SET_PARTIAL: "diamond",
    SetStatus.SET_LEGIBLE: "circle",
}
SET_STATUS_CONDITION: dict[SetStatus, str] = {
    SetStatus.SET_COLLIDING: "if any collision is not covered by a declaration",
    SetStatus.SET_UNDECLARED: "else if a resolved package is not declared",
    SetStatus.SET_PARTIAL: "else if a declared line could not be read",
    SetStatus.SET_LEGIBLE: "else",
}
SET_STATUS_GLOSS: dict[SetStatus, str] = {
    SetStatus.SET_COLLIDING: "two lines carry one token and nothing declares it",
    SetStatus.SET_UNDECLARED: "a line package resolved that the declaration omits",
    SetStatus.SET_PARTIAL: "some declared vocabulary was unread or unavailable",
    SetStatus.SET_LEGIBLE: "all read; no unexempted published-name collision",
}

STAGE_GLOSS: dict[str, str] = {
    "resolve": "ask the resolver for each declared package and record what it answered",
    "bind": (
        "read the version, registry size, and digest each resolved package "
        "publishes, and collect the enum member names it exports"
    ),
    "collide": (
        "map every token to the lines carrying it, then split the multi-line "
        "tokens into declared exemptions and everything else"
    ),
    "declare": (
        "ask the resolver which line packages it can see, and name any that "
        "resolved without appearing in the declaration"
    ),
    "status": "take the first condition that matches, in precedence order",
}
STAGE_NOTE: dict[str, str] = {
    "resolve": "an absent or failing line is an ordinary outcome, not an error",
    "bind": "no version, size, or digest is invented for a package that did not resolve",
    "collide": (
        "an exemption must match the token exactly, over exactly the lines that "
        "carry it, with a meaning recorded for each"
    ),
    "declare": (
        "a resolver that cannot enumerate says so; it does not report an empty finding"
    ),
    "status": "set_legible is reached only when nothing above it matched",
}


def _accent_for(color: str) -> tuple[str, str]:
    """Pick a stable fill/ink pair for a color name this module does not know."""
    digest = hashlib.sha256(color.encode("utf-8")).digest()
    return ACCENT_CYCLE[digest[0] % len(ACCENT_CYCLE)]


def line_fill(color: str) -> str:
    """Swatch fill for a declared color name."""
    known = LINE_FILL.get(color)
    return known if known is not None else _accent_for(color)[0]


def line_ink(color: str) -> str:
    """Stroke and label ink for a declared color name."""
    known = LINE_INK.get(color)
    return known if known is not None else _accent_for(color)[1]


def cover_stroke(color: str) -> str:
    """Cover stroke for a declared color name.

    Falls back to the same deterministic ink the other plates use, so a
    color the cover map has never seen still draws, the same way, everywhere.
    """
    known = COVER_STROKE.get(color)
    return known if known is not None else line_ink(color)


def shape_for(working_position: int) -> str:
    """Marker shape for a line, cycled by its working position."""
    return SHAPE_CYCLE[(int(working_position) - 1) % len(SHAPE_CYCLE)]


def dash_for(working_position: int) -> str:
    """Connector dash pattern for a line, cycled by its working position."""
    return DASH_CYCLE[(int(working_position) - 1) % len(DASH_CYCLE)]


_K = TypeVar("_K")
_V = TypeVar("_V")


def _require_exact(mapping: Mapping[_K, _V], members: Iterable[_K], what: str) -> None:
    """Fail the build when a display map has drifted from its source of truth."""
    have = set(mapping)
    want = set(members)
    if have == want:
        return
    missing = sorted(str(item) for item in want - have)
    extra = sorted(str(item) for item in have - want)
    raise ValueError(
        f"{what} must cover exactly its source of truth; "
        f"missing={missing} unexpected={extra}"
    )


def verify_coverage() -> None:
    """Check that every enumeration-keyed display map is still exhaustive.

    Called before any plate is drawn. A new ``ReadCode``, ``SetStatus``, or
    reader stage therefore fails the figure build instead of silently
    disappearing from a plate that claims to show all of them.
    """
    _require_exact(READ_CODE_INK, ReadCode, "READ_CODE_INK")
    _require_exact(READ_CODE_SHAPE, ReadCode, "READ_CODE_SHAPE")
    _require_exact(READ_CODE_SOLID, ReadCode, "READ_CODE_SOLID")
    _require_exact(READ_CODE_GLOSS, ReadCode, "READ_CODE_GLOSS")
    _require_exact(SET_STATUS_INK, SetStatus, "SET_STATUS_INK")
    _require_exact(SET_STATUS_SHAPE, SetStatus, "SET_STATUS_SHAPE")
    _require_exact(SET_STATUS_CONDITION, SetStatus, "SET_STATUS_CONDITION")
    _require_exact(SET_STATUS_GLOSS, SetStatus, "SET_STATUS_GLOSS")
    _require_exact(STAGE_GLOSS, READER_STAGES, "STAGE_GLOSS")
    _require_exact(STAGE_NOTE, READER_STAGES, "STAGE_NOTE")


__all__ = [
    "ACCENT",
    "ACCENT_CYCLE",
    "CARD",
    "COVER_ORDER",
    "COVER_STROKE",
    "DASH_CYCLE",
    "GOOD",
    "INK",
    "LINE_FILL",
    "LINE_INK",
    "MUTED",
    "OCHRE",
    "PANEL",
    "PAPER",
    "READ_CODE_GLOSS",
    "READ_CODE_INK",
    "READ_CODE_SHAPE",
    "READ_CODE_SOLID",
    "RULE",
    "SET_STATUS_CONDITION",
    "SET_STATUS_GLOSS",
    "SET_STATUS_INK",
    "SET_STATUS_SHAPE",
    "SHAPE_CYCLE",
    "STAGE_GLOSS",
    "STAGE_NOTE",
    "WARN",
    "cover_stroke",
    "dash_for",
    "line_fill",
    "line_ink",
    "shape_for",
    "verify_coverage",
]

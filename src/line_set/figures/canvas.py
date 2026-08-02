"""SVG primitives for the Line Set plates. No plate meaning lives here.

Every primitive is deterministic by construction. Coordinates are formatted to
one decimal place, so the small floating-point differences a trigonometric
polygon can carry never reach the file; no primitive consults a clock, a
random source, or the environment; and nothing here measures rendered text, so
the same call always emits the same bytes.

:func:`text` refuses to draw below :data:`MIN_TEXT_UNITS`. Raising rather than
quietly clamping keeps the floor structural: a label cannot be added at an
unreadable size and then pass because the primitive rewrote it.

The floor is stated in canvas units relative to :data:`WIDTH`, which is not the
unit a reader cares about. What a canvas unit becomes in printed points depends
on the width the manuscript declares for the embed and on the page geometry, and
:mod:`line_set.figures.legibility` derives that number rather than assuming it.
:data:`MIN_TEXT_UNITS` is chosen so that the smallest label clears
:data:`line_set.figures.legibility.MIN_LEGIBLE_PT` at the widths this
manuscript actually embeds; a canvas floor alone would be a unit the page never
sees, so both gates run and the rendered one is the binding one.
"""

from __future__ import annotations

import math

from .palette import CARD, INK, MUTED, PAPER, RULE

#: The design width, in canvas units, shared by every Line Set plate.
WIDTH = 1600

#: The left and right margin, in canvas units.
MARGIN = 110

#: The right edge available to plate content.
CONTENT_RIGHT = WIDTH - MARGIN

#: The smallest font size, in canvas units, any label may use.
#:
#: Kept at the minimal integer that clears the rendered-point floor when the
#: plate is embedded at full text width, so it is a floor rather than a
#: gratuitous margin. Re-derived against the manuscript's declared geometry
#: (``0.33in`` side margins -> a 566.6pt text block): ``17 * 566.597 / 1600
#: = 6.02pt`` against a floor of 6.0, and one unit lower would not clear it.
#: Lowering the floor, widening the canvas, or changing the page geometry all
#: move this number, so re-derive it (and the tightness check in
#: ``tests/test_figure_legibility.py``) in the same patch rather than editing
#: one in isolation.
MIN_TEXT_UNITS = 17

#: Header baselines, so every plate opens the same way.
KICKER_Y = 88
TITLE_Y = 137
SUBTITLE_Y = 176
NOTE_Y = 208
CONTENT_TOP = 250

_POLYGON_SIDES: dict[str, int] = {
    "triangle": 3,
    "diamond": 4,
    "pentagon": 5,
    "hexagon": 6,
}


def _n(value: float) -> str:
    """Format one coordinate; fixed precision keeps output byte-stable."""
    return f"{float(value):.1f}"


def escape_text(value: str) -> str:
    """Escape text placed between SVG tags."""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def text(
    x: float,
    y: float,
    value: str,
    size: int,
    fill: str = INK,
    weight: str = "400",
    anchor: str = "start",
) -> str:
    """Return one text run, refusing any size below the legibility floor."""
    if size < MIN_TEXT_UNITS:
        raise ValueError(
            f"figure text size {size} is below the legibility floor "
            f"MIN_TEXT_UNITS={MIN_TEXT_UNITS} (value: {value!r})"
        )
    return (
        f'<text x="{_n(x)}" y="{_n(y)}" font-family="Arial, sans-serif" '
        f'font-size="{size}px" font-weight="{weight}" fill="{fill}" '
        f'text-anchor="{anchor}">{escape_text(value)}</text>'
    )


def rect(
    x: float,
    y: float,
    width: float,
    height: float,
    fill: str = CARD,
    stroke: str = RULE,
    stroke_width: float = 1.5,
    rx: float = 0,
    dash: str = "",
) -> str:
    """Return one rectangle."""
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<rect x="{_n(x)}" y="{_n(y)}" width="{_n(width)}" height="{_n(height)}" '
        f'rx="{_n(rx)}" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="{_n(stroke_width)}"{dash_attr}/>'
    )


def line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    stroke: str = RULE,
    stroke_width: float = 1.5,
    dash: str = "",
) -> str:
    """Return one straight segment."""
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{_n(x1)}" y1="{_n(y1)}" x2="{_n(x2)}" y2="{_n(y2)}" '
        f'stroke="{stroke}" stroke-width="{_n(stroke_width)}"{dash_attr}/>'
    )


def path(
    d: str,
    stroke: str,
    stroke_width: float = 2,
    fill: str = "none",
    dash: str = "",
) -> str:
    """Return one path."""
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<path d="{d}" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="{_n(stroke_width)}" stroke-linecap="round" '
        f'stroke-linejoin="round"{dash_attr}/>'
    )


def glyph(
    shape: str,
    cx: float,
    cy: float,
    r: float,
    fill: str,
    stroke: str,
    stroke_width: float = 2,
) -> str:
    """Return one marker of the named shape.

    An unknown shape raises. The shapes are how a plate stays readable without
    colour, so a silent fallback to a circle would quietly merge two things the
    figure claims to distinguish.
    """
    if shape == "circle":
        return (
            f'<circle cx="{_n(cx)}" cy="{_n(cy)}" r="{_n(r)}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{_n(stroke_width)}"/>'
        )
    if shape == "square":
        side = r * 1.72
        return rect(
            cx - side / 2,
            cy - side / 2,
            side,
            side,
            fill=fill,
            stroke=stroke,
            stroke_width=stroke_width,
        )
    sides = _POLYGON_SIDES.get(shape)
    if sides is None:
        raise ValueError(f"unknown marker shape {shape!r}")
    points = " ".join(
        f"{_n(cx + r * math.cos(math.radians(-90 + 360 * index / sides)))},"
        f"{_n(cy + r * math.sin(math.radians(-90 + 360 * index / sides)))}"
        for index in range(sides)
    )
    return (
        f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="{_n(stroke_width)}"/>'
    )


def hatch_defs(pattern_id: str, stroke: str) -> str:
    """Return a diagonal hatch pattern, used to mark a row that was not read."""
    return (
        f'<defs><pattern id="{pattern_id}" width="10" height="10" '
        'patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        f'<line x1="0" y1="0" x2="0" y2="10" stroke="{stroke}" '
        'stroke-width="3" opacity="0.35"/></pattern></defs>'
    )


def open_canvas(width: int, height: int) -> list[str]:
    """Open a plate canvas on the shared paper ground."""
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="{PAPER}"/>',
    ]


def header(
    kicker: str,
    title: str,
    subtitle: str,
    note: str = "",
    accent: str = MUTED,
) -> list[str]:
    """Return the shared four-line plate header."""
    parts = [
        text(MARGIN, KICKER_Y, kicker, 24, accent, "700"),
        text(MARGIN, TITLE_Y, title, 40, INK, "700"),
        text(MARGIN, SUBTITLE_Y, subtitle, 20, MUTED),
    ]
    if note:
        parts.append(text(MARGIN, NOTE_Y, note, 18, accent, "700"))
    return parts


def close_canvas() -> str:
    """Close a plate canvas."""
    return "</svg>"


def wrap(value: str, width: int) -> list[str]:
    """Greedy character-count wrap; returns at least one line."""
    words = str(value).split()
    if not words:
        return [""]
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    # ``words`` is non-empty here and ``split()`` yields no empty word, so
    # ``current`` always holds the tail. No guard, because a guard nothing can
    # falsify is a branch that reads as caution and tests as noise.
    lines.append(current)
    return lines


#: Endings that take ``-es`` rather than ``-s``.
_SIBILANT_ENDINGS = ("s", "x", "z", "ch", "sh")


def plural(count: int, noun: str) -> str:
    """Count phrase whose plural form follows the live count.

    Appending a bare ``s`` is wrong for two of the nouns the plates actually
    count. ``status`` became ``statuss`` and ``entry`` became ``entrys``, and
    both reached a shipped figure caption and its alt text, which is the copy a
    screen reader speaks. The rule below is the ordinary English one for the
    regular cases, which is all a count phrase over these nouns needs; a noun
    with an irregular plural does not belong in a generated caption, because
    nothing here can know it.
    """
    if count == 1:
        return f"{count} {noun}"
    head, separator, last = noun.rpartition(" ")
    if last.endswith(_SIBILANT_ENDINGS):
        inflected = f"{last}es"
    elif len(last) > 1 and last.endswith("y") and last[-2] not in "aeiou":
        inflected = f"{last[:-1]}ies"
    else:
        inflected = f"{last}s"
    return f"{count} {head}{separator}{inflected}"


__all__ = [
    "CONTENT_RIGHT",
    "CONTENT_TOP",
    "KICKER_Y",
    "MARGIN",
    "MIN_TEXT_UNITS",
    "NOTE_Y",
    "SUBTITLE_Y",
    "TITLE_Y",
    "WIDTH",
    "close_canvas",
    "escape_text",
    "glyph",
    "hatch_defs",
    "header",
    "line",
    "open_canvas",
    "path",
    "plural",
    "rect",
    "text",
    "wrap",
]

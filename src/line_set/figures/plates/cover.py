"""The cover plate: the set's own title-page figure.

The cover is drawn from the declaration alone, exactly like the declaration
plates: the strokes are laid out from ``len(entries)`` and each stroke wears
the color its own book draws it in (``palette.COVER_STROKE``), labeled with
its declared color name. Nothing here names an individual line, so a color
appended to the declaration appears on the cover without an edit in this
module.

The canvas matches the sibling covers' title-page proportions, with labels
authored above :data:`line_set.figures.canvas.MIN_TEXT_UNITS`. The rendered
print floor is qualified separately at each source or compiled placement's
actual geometry; a source label size alone does not certify a cover placement.
"""

from __future__ import annotations

from ...models import LineEntry
from ..canvas import (
    close_canvas,
    escape_text,
    exact_lines,
    line,
    open_canvas,
    rect,
    text,
)
from ..palette import COVER_ORDER, INK, MUTED, RULE, cover_stroke

#: The cover canvas. Wider than the plate design width on purpose: this is the
#: title-page plate, and it matches the proportions the sibling covers use.
WIDTH = 1800
HEIGHT = 1100

#: The white stroke is invisible on paper by itself, so it is drawn over a
_WHITE_UNDER_WIDTH = 12.0

#: Maximum stroke length; actual strokes reserve a gap inside their slot.
_STROKE_LENGTH = 110.0
_SLOT_GAP = 24.0
_REGISTER_LEFT = 230.0
_REGISTER_SPAN = 1340.0
_LABEL_SIZE = 30
_MAX_COLUMNS = 10

#: Register rows grow with the declaration; the reader follows the last row.
_REGISTER_TOP = 390.0

#: Words for the subtitle's count; numerals past the table.
_NUMBER_WORDS = (
    "ZERO",
    "ONE",
    "TWO",
    "THREE",
    "FOUR",
    "FIVE",
    "SIX",
    "SEVEN",
    "EIGHT",
    "NINE",
    "TEN",
    "ELEVEN",
    "TWELVE",
)


def _number_word(count: int) -> str:
    """The subtitle's number word for a set of this size."""
    return _NUMBER_WORDS[count] if count < len(_NUMBER_WORDS) else str(count)


def _stroke(
    entry: LineEntry,
    center: float,
    stroke_y: float,
    slot_width: float,
) -> tuple[list[str], float]:
    """One separate stroke and full label within its actual slot."""
    parts = [f'<g data-cover-color="{escape_text(entry.color)}">']
    length = min(_STROKE_LENGTH, slot_width - _SLOT_GAP)
    stroke = cover_stroke(entry.color)
    if entry.color == "white":
        parts.append(
            line(
                center - length / 2,
                stroke_y,
                center + length / 2,
                stroke_y,
                INK,
                _WHITE_UNDER_WIDTH,
            )
        )
    parts.append(
        line(center - length / 2, stroke_y, center + length / 2, stroke_y, stroke, 6.0)
    )
    label_rows = exact_lines(entry.color, slot_width - _SLOT_GAP, _LABEL_SIZE)
    for index, label in enumerate(label_rows):
        parts.append(
            text(
                center,
                stroke_y + 70 + index * 36,
                label,
                _LABEL_SIZE,
                MUTED,
                "700",
                "middle",
            )
        )
    parts.append("</g>")
    return parts, stroke_y + 70 + 36 * len(label_rows)


def _display_order(entries: tuple[LineEntry, ...]) -> tuple[LineEntry, ...]:
    """The strokes in the cover's canonical color sequence.

    Known colors take their :data:`palette.COVER_ORDER` place; a color the
    sequence does not know follows them, by working position, so an appended
    color still draws in a stable place without an edit here.
    """
    return tuple(
        sorted(
            entries,
            key=lambda entry: (
                COVER_ORDER.index(entry.color)
                if entry.color in COVER_ORDER
                else len(COVER_ORDER),
                entry.working_position,
            ),
        )
    )


def cover_svg(entries: tuple[LineEntry, ...]) -> str:
    """Render registry-sized slots in rows, with gaps and full written labels.

    Ordinary declared names get a full-size slot instead of artificial word
    fragments. Oversized names wrap losslessly; the canvas grows vertically,
    never by shrinking a label. Physical page legibility is measured separately.
    """
    ordered = _display_order(entries)
    label_width = max((len(entry.color) for entry in ordered), default=1) * _LABEL_SIZE
    columns = max(
        1,
        min(
            _MAX_COLUMNS,
            len(ordered),
            int(_REGISTER_SPAN / (label_width + _SLOT_GAP)),
        ),
    )
    step = _REGISTER_SPAN / columns
    parts: list[str] = []
    cursor = _REGISTER_TOP
    for start in range(0, len(ordered), columns):
        bottom = cursor
        for index, entry in enumerate(ordered[start : start + columns]):
            strokes, label_bottom = _stroke(
                entry,
                _REGISTER_LEFT + (index + 0.5) * step,
                cursor,
                step,
            )
            parts.extend(strokes)
            bottom = max(bottom, label_bottom)
        cursor = bottom + 80
    reader_y = max(790.0, cursor + 40)
    height = max(HEIGHT, int(reader_y + 310))
    body = open_canvas(WIDTH, height)
    body.append(rect(60, 60, WIDTH - 120, height - 120, "none", INK, 2.5))
    body.append(text(120, 168, "THE LINE SET", 44, INK, "700"))
    body.append(
        text(
            WIDTH - 100,
            height - 110,
            f"A READER FOR {_number_word(len(ordered))} INSTRUMENTS",
            30,
            MUTED,
            "400",
            "end",
        )
    )
    if not ordered:
        body.append(
            text(
                WIDTH / 2,
                HEIGHT / 2,
                "the set declares no lines to hold",
                30,
                MUTED,
                "400",
                "middle",
            )
        )
        body.append(close_canvas())
        return "".join(body)
    body.append(
        rect(
            _REGISTER_LEFT - 80,
            _REGISTER_TOP - 130,
            _REGISTER_SPAN + 160,
            cursor - _REGISTER_TOP + 130,
            "none",
            RULE,
            2.5,
            dash="2 8",
        )
    )
    body.extend(parts)
    body.append(
        line(
            _REGISTER_LEFT - 110,
            reader_y,
            _REGISTER_LEFT + _REGISTER_SPAN + 110,
            reader_y,
            MUTED,
            3.0,
        )
    )
    body.append(close_canvas())
    return "".join(body)


__all__ = ["cover_svg"]

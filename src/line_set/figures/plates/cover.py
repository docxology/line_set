"""The cover plate: the set's own title-page figure.

The cover is drawn from the declaration alone, exactly like the declaration
plates: the strokes are laid out from ``len(entries)`` and each stroke wears
the colour its own book draws it in (``palette.COVER_STROKE``), labelled with
its declared colour name. Nothing here names an individual line, so a colour
appended to the declaration appears on the cover without an edit in this
module.

The canvas matches the sibling covers' title-page proportions. Because the
cover prints at a declared fraction of the text width rather than as a
full-width embed, its smallest label is authored well above
:data:`line_set.figures.canvas.MIN_TEXT_UNITS`, so a label still clears the
six-point print floor through the ``width=70%`` embed the volume's part
headings use.
"""

from __future__ import annotations

from ...models import LineEntry
from ..canvas import close_canvas, line, open_canvas, rect, text
from ..palette import COVER_ORDER, INK, MUTED, RULE, cover_stroke

#: The cover canvas. Wider than the plate design width on purpose: this is the
#: title-page plate, and it matches the proportions the sibling covers use.
WIDTH = 1800
HEIGHT = 1100

#: The white stroke is invisible on paper by itself, so it is drawn over a
_WHITE_UNDER_WIDTH = 12.0

#: Length of one line's stroke, and the vertical metrics of the row.
_STROKE_LENGTH = 110.0
_STROKE_Y = 470.0
_LABEL_Y = 575.0

#: The reader's stroke sits below the register and spans past it.
_READER_Y = 790.0

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


def _stroke(entry: LineEntry, center: float) -> list[str]:
    """One line's stroke and its name, or the empty list for no entries."""
    parts: list[str] = []
    stroke = cover_stroke(entry.color)
    if entry.color == "white":
        parts.append(
            line(
                center - _STROKE_LENGTH / 2,
                _STROKE_Y,
                center + _STROKE_LENGTH / 2,
                _STROKE_Y,
                INK,
                _WHITE_UNDER_WIDTH,
            )
        )
    parts.append(
        line(
            center - _STROKE_LENGTH / 2,
            _STROKE_Y,
            center + _STROKE_LENGTH / 2,
            _STROKE_Y,
            stroke,
            6.0,
        )
    )
    parts.append(
        text(center, _LABEL_Y, entry.color.upper(), 30, MUTED, "700", "middle")
    )
    return parts


def _display_order(entries: tuple[LineEntry, ...]) -> tuple[LineEntry, ...]:
    """The strokes in the cover's canonical colour sequence.

    Known colours take their :data:`palette.COVER_ORDER` place; a colour the
    sequence does not know follows them, by working position, so an appended
    colour still draws in a stable place without an edit here.
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
    """Render the cover: one stroke per declared line in one dotted register.

    The stroke centers divide the row into ``len(entries)`` equal slots, and
    each stroke is shorter than its slot, so two strokes cannot meet whatever
    the set's size. The reader's stroke beneath spans past the register: it is
    what holds the set, and it holds nothing by being a colour.
    """
    ordered = _display_order(entries)
    body = open_canvas(WIDTH, HEIGHT)
    body.append(rect(60, 60, WIDTH - 120, HEIGHT - 120, "none", INK, 2.5))
    body.append(text(120, 168, "THE LINE SET", 44, INK, "700"))
    body.append(
        text(
            WIDTH - 100,
            HEIGHT - 110,
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
    left, span = 230.0, 1340.0
    step = span / len(ordered)
    body.append(
        rect(
            left - 80,
            _STROKE_Y - 130,
            span + 160,
            _LABEL_Y - _STROKE_Y + 210,
            "none",
            RULE,
            2.5,
            dash="2 8",
        )
    )
    for slot, entry in enumerate(ordered):
        body.extend(_stroke(entry, left + slot * step + step / 2))
    body.append(
        line(left - 110, _READER_Y, left + span + 110, _READER_Y, MUTED, 3.0)
    )
    body.append(close_canvas())
    return "".join(body)


__all__ = ["cover_svg"]

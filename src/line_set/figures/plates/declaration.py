"""Plates drawn from the declaration alone. No sibling package is read here.

``set_compass`` and ``two_orders`` take the declared lines as an argument and
compute every position from them, so appending a colour to
:data:`line_set.registry.LINE_SET` changes both plates without an edit in this
module. Neither plate says anything about whether a line works, only about
what the declaration says the line is for.
"""

from __future__ import annotations

import math

from ...invariants import check_orders_diverge
from ...models import OPUS_STAGE_ORDER, LineEntry
from ..canvas import (
    CONTENT_RIGHT,
    MARGIN,
    close_canvas,
    glyph,
    header,
    line,
    open_canvas,
    path,
    plural,
    rect,
    text,
    wrap,
)
from ..palette import (
    ACCENT,
    CARD,
    INK,
    MUTED,
    PANEL,
    PAPER,
    RULE,
    WARN,
    dash_for,
    line_fill,
    line_ink,
    shape_for,
)

_CARD_LEFT = MARGIN
_CARD_WIDTH = CONTENT_RIGHT - MARGIN
_TEXT_LEFT = MARGIN + 116
_CONTENT_TOP = 300


def _row_lines(entry: LineEntry) -> tuple[list[str], list[str], list[str]]:
    """Wrap one entry's three sentences at the widths the card allows."""
    return (
        wrap(f"asks — {entry.question}", 104),
        wrap(f"does — {entry.job}", 118),
        wrap(f"must not become — {entry.must_not_become}", 118),
    )


def _row_height(entry: LineEntry) -> int:
    """Card height derived from how much text the entry actually carries."""
    asks, does, avoids = _row_lines(entry)
    return 122 + 28 * len(asks) + 24 * len(does) + 24 * len(avoids)


def _draw_card(
    entry: LineEntry,
    top: int,
    height: int,
    *,
    dashed: bool,
    corner_note: str,
    marker_position: int | None = None,
) -> list[str]:
    """Draw one line's card: marker, names, and its three declared sentences.

    ``marker_position`` overrides which shape the marker takes. The wrapper's
    card uses it: its declared ``working_position`` was fixed when the module
    was written, so a set that has since grown would give it the same shape as
    a real line. Passing one past the end of the drawn set keeps every marker
    on the plate distinct however many lines the declaration holds.
    """
    ink = line_ink(entry.color)
    fill = line_fill(entry.color)
    marker = shape_for(
        entry.working_position if marker_position is None else marker_position
    )
    parts = [
        rect(
            _CARD_LEFT,
            top,
            _CARD_WIDTH,
            height,
            CARD,
            ink if not dashed else MUTED,
            2 if not dashed else 1.5,
            rx=10,
            dash="10 8" if dashed else "",
        ),
        rect(_CARD_LEFT, top, 12, height, ink, ink, 0, rx=0),
        glyph(marker, _CARD_LEFT + 62, top + 50, 24, fill, ink, 3),
        text(_CARD_LEFT + 62, top + 96, corner_note, 18, MUTED, "700", "middle"),
        text(_TEXT_LEFT, top + 52, entry.color, 26, ink, "700"),
        text(
            _TEXT_LEFT,
            top + 80,
            f"package {entry.package_name} · keeps {entry.registry_noun} "
            f"· emits {entry.verdict_noun}",
            18,
            MUTED,
        ),
        text(
            CONTENT_RIGHT - 24,
            top + 52,
            f"opus stage · {entry.opus_stage}" if entry.opus_stage else "no opus stage",
            18,
            ink if entry.opus_stage else MUTED,
            "700",
            "end",
        ),
    ]
    asks, does, avoids = _row_lines(entry)
    cursor = top + 118
    for row in asks:
        parts.append(text(_TEXT_LEFT, cursor, row, 20, INK, "700"))
        cursor += 28
    for row in does:
        parts.append(text(_TEXT_LEFT, cursor, row, 18, MUTED))
        cursor += 24
    for row in avoids:
        parts.append(text(_TEXT_LEFT, cursor, row, 18, WARN, "700"))
        cursor += 24
    return parts


def _compass_rose(entries: tuple[LineEntry, ...], cx: int, cy: int) -> list[str]:
    """Draw one needle per declared line, at equal bearings around a dial.

    The needles are the declared lines and nothing else: their count, order,
    markers, and inks all come from the entries passed in. The dial is a motif,
    not a measurement — a bearing's angle carries no meaning.
    """
    radius = 54
    parts = [
        f'<circle cx="{cx}" cy="{cy}" r="{radius + 30}" fill="{PAPER}" '
        f'stroke="{RULE}" stroke-width="1.5"/>',
    ]
    count = len(entries)
    for index, entry in enumerate(entries):
        angle = math.radians(-90 + 360 * index / max(count, 1))
        tip_x = cx + radius * math.cos(angle)
        tip_y = cy + radius * math.sin(angle)
        ink = line_ink(entry.color)
        parts.append(
            path(
                f"M{cx} {cy} L{tip_x:.1f} {tip_y:.1f}",
                ink,
                2.5,
                dash=dash_for(entry.working_position),
            )
        )
        parts.append(
            glyph(
                shape_for(entry.working_position),
                tip_x,
                tip_y,
                12,
                line_fill(entry.color),
                ink,
                2.5,
            )
        )
        label_x = cx + (radius + 22) * math.cos(angle)
        label_y = cy + (radius + 22) * math.sin(angle) + 5
        parts.append(
            text(
                label_x, label_y, str(entry.working_position), 18, ink, "700", "middle"
            )
        )
    # The hub is drawn last so the needle origins do not show through it.
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="11" fill="{PAPER}" stroke="{MUTED}" '
        'stroke-width="2"/>'
    )
    parts.append(
        text(cx, cy + radius + 62, "working positions", 18, MUTED, "700", "middle")
    )
    return parts


def set_compass(lines: tuple[LineEntry, ...], wrapper: LineEntry) -> str:
    """Draw every declared line with its question, job, and boundary.

    The card order is the working order. The number in the dial and under each
    marker is the entry's declared ``working_position``, which the structural
    checks pin to a contiguous ``1..N``.
    """
    entries = tuple(sorted(lines, key=lambda entry: entry.working_position))
    heights = [_row_height(entry) for entry in entries]
    wrapper_height = _row_height(wrapper)
    body = sum(height + 22 for height in heights)
    height = _CONTENT_TOP + body + 96 + wrapper_height + 132
    parts = open_canvas(1600, height)
    parts += header(
        "THE SET COMPASS",
        "Which question sends you to which line",
        "Each card is one declared line: the question it answers, the job it "
        "does, and the thing it must not become.",
        f"DRAWN FROM THE DECLARATION · {plural(len(entries), 'line').upper()} · "
        "NO LINE RANKS ABOVE ANOTHER",
        ACCENT,
    )
    parts += _compass_rose(entries, 1400, 150)

    cursor = _CONTENT_TOP
    for entry, card_height in zip(entries, heights):
        parts += _draw_card(
            entry,
            cursor,
            card_height,
            dashed=False,
            corner_note=f"#{entry.working_position}",
        )
        cursor += card_height + 22

    cursor += 24
    parts.append(line(MARGIN, cursor, CONTENT_RIGHT, cursor, RULE, 2))
    parts.append(
        text(
            MARGIN,
            cursor + 30,
            "BELOW THE RULE — NOT A LINE IN THE SET",
            18,
            MUTED,
            "700",
        )
    )
    parts.append(
        text(
            CONTENT_RIGHT,
            cursor + 30,
            "the wrapper declares no refusal, method, aspiration, or absence",
            18,
            MUTED,
            "400",
            "end",
        )
    )
    cursor += 50
    parts += _draw_card(
        wrapper,
        cursor,
        wrapper_height,
        dashed=True,
        corner_note="wrapper",
        marker_position=len(entries) + 1,
    )
    cursor += wrapper_height + 42
    parts.append(
        text(
            MARGIN,
            cursor,
            "A card states what its line is for. It is not evidence that the "
            "line does it, and no card is a score.",
            18,
            INK,
        )
    )
    parts.append(close_canvas())
    return "".join(parts)


_ORDER_NOTES = (
    "The working order is functional. The opus order is a borrowed set of "
    "stage names. The two deliberately do not line up.",
    "Citrinitas is kept as a stage of its own. This set does not perform the "
    "later collapse of the yellowing into the reddening.",
    "No telos is borrowed and nothing is ranked. A stage name is a label, not "
    "a claim that a line is final, complete, or above another.",
)


def two_orders(lines: tuple[LineEntry, ...]) -> str:
    """Draw the working order against the opus order, with their crossings.

    The right-hand column holds only the entries that declare a stage in
    :data:`line_set.models.OPUS_STAGE_ORDER`; an entry with no stage keeps its
    place on the left and is connected to an explicit note instead. The
    divergence sentence under the columns is the live result of
    :func:`line_set.invariants.check_orders_diverge`, not a claim typed here.
    """
    working = tuple(sorted(lines, key=lambda entry: entry.working_position))
    staged = tuple(
        sorted(
            (entry for entry in working if entry.opus_stage in OPUS_STAGE_ORDER),
            key=lambda entry: OPUS_STAGE_ORDER.index(entry.opus_stage),
        )
    )
    unstaged = tuple(entry for entry in working if entry not in staged)
    divergence = check_orders_diverge(lines)

    row_h = 118
    box_h = 92
    box_w = 540
    left_x = MARGIN
    right_x = CONTENT_RIGHT - box_w
    top = 306
    rows = max(len(working), len(staged), 1)
    unstaged_block = 0 if not unstaged else 84 + 30 * len(unstaged)
    height = top + rows * row_h + unstaged_block + 250
    parts = open_canvas(1600, height)
    parts += header(
        "TWO ORDERS",
        "The working order is not the opus order",
        "Left: the sequence the instruments are used in. Right: the borrowed "
        "stage names, in their own sequence.",
        "THE CROSSINGS ARE THE POINT · THE DIVERGENCE IS DELIBERATE",
        ACCENT,
    )
    parts.append(text(left_x, top - 26, "WORKING ORDER", 18, ACCENT, "700"))
    parts.append(
        text(left_x + 200, top - 26, "refuse → method → aspire → absence", 18, MUTED)
    )
    parts.append(text(right_x, top - 26, "OPUS ORDER", 18, ACCENT, "700"))
    parts.append(
        text(
            right_x + 150,
            top - 26,
            " → ".join(OPUS_STAGE_ORDER),
            18,
            MUTED,
        )
    )

    left_centre: dict[str, float] = {}
    for index, entry in enumerate(working):
        y = top + index * row_h
        ink = line_ink(entry.color)
        parts.append(rect(left_x, y, box_w, box_h, CARD, ink, 2, rx=8))
        parts.append(rect(left_x, y, 10, box_h, ink, ink, 0))
        parts.append(
            glyph(
                shape_for(entry.working_position),
                left_x + 52,
                y + box_h / 2,
                18,
                line_fill(entry.color),
                ink,
                2.5,
            )
        )
        parts.append(text(left_x + 92, y + 40, entry.color, 22, ink, "700"))
        parts.append(
            text(left_x + 92, y + 68, f"position {entry.working_position}", 18, MUTED)
        )
        parts.append(
            text(
                left_x + box_w - 20,
                y + 40,
                entry.question,
                18,
                MUTED,
                "400",
                "end",
            )
        )
        left_centre[entry.id] = y + box_h / 2

    right_centre: dict[str, float] = {}
    for index, entry in enumerate(staged):
        y = top + index * row_h
        ink = line_ink(entry.color)
        stage = entry.opus_stage
        assert stage is not None  # staged filters to entries with an opus stage
        parts.append(rect(right_x, y, box_w, box_h, PANEL, ink, 2, rx=8))
        parts.append(rect(right_x + box_w - 10, y, 10, box_h, ink, ink, 0))
        parts.append(
            glyph(
                shape_for(entry.working_position),
                right_x + box_w - 52,
                y + box_h / 2,
                18,
                line_fill(entry.color),
                ink,
                2.5,
            )
        )
        parts.append(text(right_x + 24, y + 40, stage, 22, ink, "700"))
        parts.append(
            text(
                right_x + 24,
                y + 68,
                f"stage {OPUS_STAGE_ORDER.index(stage) + 1} · the {entry.color} line",
                18,
                MUTED,
            )
        )
        right_centre[entry.id] = y + box_h / 2

    for entry in working:
        start_y = left_centre[entry.id]
        end_y = right_centre.get(entry.id)
        ink = line_ink(entry.color)
        if end_y is None:
            continue
        start_x = left_x + box_w
        end_x = right_x
        mid = (start_x + end_x) / 2
        parts.append(
            path(
                f"M{start_x} {start_y:.1f} C {mid:.1f} {start_y:.1f}, "
                f"{mid:.1f} {end_y:.1f}, {end_x} {end_y:.1f}",
                ink,
                3,
                dash=dash_for(entry.working_position),
            )
        )
        parts.append(glyph("circle", start_x + 8, start_y, 6, ink, ink, 1.5))
        parts.append(glyph("circle", end_x - 8, end_y, 6, PAPER, ink, 2.5))

    cursor = top + rows * row_h + 24
    if unstaged:
        parts.append(
            rect(
                right_x,
                cursor,
                box_w,
                60 + 30 * len(unstaged),
                PANEL,
                MUTED,
                1.5,
                rx=8,
                dash="8 7",
            )
        )
        parts.append(
            text(right_x + 24, cursor + 34, "NO OPUS STAGE DECLARED", 18, MUTED, "700")
        )
        for index, entry in enumerate(unstaged):
            parts.append(
                text(
                    right_x + 24,
                    cursor + 62 + index * 30,
                    f"the {entry.color} line keeps its working position and "
                    "borrows no stage name",
                    18,
                    MUTED,
                )
            )
            parts.append(
                path(
                    f"M{left_x + box_w} {left_centre[entry.id]:.1f} C "
                    f"{(left_x + box_w + right_x) / 2:.1f} "
                    f"{left_centre[entry.id]:.1f}, "
                    f"{(left_x + box_w + right_x) / 2:.1f} {cursor + 30}, "
                    f"{right_x} {cursor + 30}",
                    MUTED,
                    2,
                    dash="4 7",
                )
            )
        cursor += unstaged_block

    parts.append(line(MARGIN, cursor + 10, CONTENT_RIGHT, cursor + 10, RULE, 2))
    parts.append(
        text(
            MARGIN,
            cursor + 46,
            f"LIVE CHECK · {divergence.name} · "
            f"{'holds' if divergence.passed else 'does not hold'}",
            18,
            ACCENT,
            "700",
        )
    )
    parts.append(text(MARGIN, cursor + 74, divergence.detail, 18, INK))
    for index, note in enumerate(_ORDER_NOTES):
        parts.append(
            text(MARGIN, cursor + 112 + index * 32, f"{index + 1}.", 18, MUTED, "700")
        )
        parts.append(text(MARGIN + 32, cursor + 112 + index * 32, note, 18, INK))
    parts.append(close_canvas())
    return "".join(parts)


__all__ = ["set_compass", "two_orders"]

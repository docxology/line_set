"""Plates drawn from the declaration alone. No sibling package is read here.

``set_compass`` and ``two_orders`` take the declared lines as an argument and
compute every position from them, so appending a color to
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
    exact_lines,
    text_block,
    wrap_to_width,
    escape_text,
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

_COMPASS_WIDTH = 2400
_CARD_LEFT = MARGIN
_CARD_RIGHT = _COMPASS_WIDTH - MARGIN
_CARD_WIDTH = _CARD_RIGHT - _CARD_LEFT
_TEXT_LEFT = MARGIN + 116
_IDENTITY_WIDTH = 700
_SENTENCE_LEFT = _TEXT_LEFT + _IDENTITY_WIDTH + 28
_SENTENCE_WIDTH = _CARD_RIGHT - _SENTENCE_LEFT - 24
_CONTENT_TOP = 300


def _row_lines(entry: LineEntry) -> tuple[list[str], list[str], list[str]]:
    """Wrap one entry's three sentences at the widths the card allows."""
    return (
        wrap_to_width(f"asks — {entry.question}", _SENTENCE_WIDTH, 29),
        wrap_to_width(f"does — {entry.job}", _SENTENCE_WIDTH, 28),
        wrap_to_width(
            f"must not become — {entry.must_not_become}", _SENTENCE_WIDTH, 29
        ),
    )


def _row_height(entry: LineEntry) -> int:
    """Height of the taller identity or question/job/boundary column."""
    asks, does, avoids = _row_lines(entry)
    identity_height = sum(
        (size + 4) * len(exact_lines(value, _IDENTITY_WIDTH, size))
        for value, size in (
            (entry.color, 29),
            (
                f"package {entry.package_name} · keeps {entry.registry_noun} "
                f"· emits {entry.verdict_noun}",
                28,
            ),
            (
                f"opus stage · {entry.opus_stage}"
                if entry.opus_stage
                else "no opus stage",
                28,
            ),
        )
    )
    sentence_height = 33 * len(asks) + 32 * len(does) + 33 * len(avoids)
    return 30 + max(identity_height, sentence_height) + 8


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

    The wider card puts exact identity metadata beside the three sentences,
    rather than stacking both bands and scaling the entire plate down.

    ``marker_position`` places the wrapper after the entries actually drawn,
    rather than reusing its position in the unextended declaration. Current
    entries and a single-entry extension have distinct markers; larger sets
    may exhaust the finite shape cycle and still retain full written identities.
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
        glyph(marker, _CARD_LEFT + 62, top + 30, 28, fill, ink, 3),
        text(_CARD_LEFT + 62, top + 76, corner_note, 28, MUTED, "700", "middle"),
    ]
    cursor: float = top + 30
    for value, size, color, weight in (
        (entry.color, 29, ink, "700"),
        (
            f"package {entry.package_name} · keeps {entry.registry_noun} "
            f"· emits {entry.verdict_noun}",
            28,
            MUTED,
            "400",
        ),
        (
            f"opus stage · {entry.opus_stage}" if entry.opus_stage else "no opus stage",
            28,
            ink if entry.opus_stage else MUTED,
            "700",
        ),
    ):
        drawn, cursor = text_block(
            _TEXT_LEFT, cursor, value, _IDENTITY_WIDTH, size, color, weight
        )
        parts.extend(drawn)
    cursor = top + 30
    asks, does, avoids = _row_lines(entry)
    for rows, value, size, color, weight in (
        (asks, f"asks — {entry.question}", 29, INK, "700"),
        (does, f"does — {entry.job}", 28, MUTED, "400"),
        (avoids, f"must not become — {entry.must_not_become}", 29, WARN, "700"),
    ):
        escaped = escape_text(value)
        parts.append(f'<g aria-label="{escaped}" data-full-text="{escaped}">')
        for row in rows:
            parts.append(text(_SENTENCE_LEFT, cursor, row, size, color, weight))
            cursor += size + 4
        parts.append("</g>")
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
                label_x, label_y, str(entry.working_position), 28, ink, "700", "middle"
            )
        )
    # The hub is drawn last so the needle origins do not show through it.
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="11" fill="{PAPER}" stroke="{MUTED}" '
        'stroke-width="2"/>'
    )
    parts.append(
        text(cx, cy + radius + 62, "working positions", 28, MUTED, "700", "middle")
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
    body = sum(height + 8 for height in heights)
    # Footer baseline is 156 units below the cards; retain 30 units below it.
    height = _CONTENT_TOP + body + wrapper_height + 186
    parts = open_canvas(_COMPASS_WIDTH, height)
    parts += header(
        "THE SET COMPASS",
        "Which question sends you to which line",
        "Each card is one declared line: the question it answers, the job it "
        "does, and the thing it must not become.",
        f"DRAWN FROM THE DECLARATION · {plural(len(entries), 'line').upper()} · "
        "NO LINE RANKS ABOVE ANOTHER",
        ACCENT,
    )
    parts += _compass_rose(entries, _CARD_RIGHT - 90, 150)

    cursor = _CONTENT_TOP
    for entry, card_height in zip(entries, heights):
        parts += _draw_card(
            entry,
            cursor,
            card_height,
            dashed=False,
            corner_note=f"#{entry.working_position}",
        )
        cursor += card_height + 8

    cursor += 24
    parts.append(line(MARGIN, cursor, _CARD_RIGHT, cursor, RULE, 2))
    parts.append(
        text(
            MARGIN,
            cursor + 30,
            "BELOW THE RULE — NOT A LINE IN THE SET",
            28,
            MUTED,
            "700",
        )
    )
    parts.append(
        text(
            MARGIN,
            cursor + 62,
            "the wrapper adds no instrument and no cross-line score",
            28,
            MUTED,
            "400",
            "start",
        )
    )
    cursor += 90
    parts += _draw_card(
        wrapper,
        cursor,
        wrapper_height,
        dashed=True,
        corner_note="—",
        marker_position=len(entries) + 1,
    )
    cursor += wrapper_height + 42
    parts.append(
        text(
            MARGIN,
            cursor,
            "A card states what its line is for. It is not evidence that the "
            "line does it, and no card is a score.",
            28,
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
    Working cards retain twelve units below their last question baseline;
    their height uses the same wrapped name and question rows that are drawn.
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

    box_w = 540
    questions = {
        entry.id: wrap_to_width(entry.question, box_w - 112, 26) for entry in working
    }
    names = {entry.id: exact_lines(entry.color, box_w - 112, 26) for entry in working}
    # The last question baseline is 32 + 30 * names + 28 * questions.
    box_heights = {
        entry.id: 44 + 30 * len(names[entry.id]) + 28 * len(questions[entry.id])
        for entry in working
    }
    gap = 12
    left_x = MARGIN
    right_x = CONTENT_RIGHT - box_w
    top = 342
    left_bottom = top + sum(box_heights[entry.id] + gap for entry in working)
    parts: list[str] = []
    parts += header(
        "TWO ORDERS",
        "The working order is not the opus order",
        "Left: the sequence the instruments are used in. Right: the borrowed "
        "stage names, in their own sequence.",
        "THE CROSSINGS ARE THE POINT · THE DIVERGENCE IS DELIBERATE",
        ACCENT,
    )
    parts.append(text(left_x, top - 26, "WORKING ORDER", 28, ACCENT, "700"))
    parts.append(text(right_x, top - 26, "OPUS ORDER", 28, ACCENT, "700"))

    left_center: dict[str, float] = {}
    y = top
    for entry in working:
        box_h = box_heights[entry.id]
        ink = line_ink(entry.color)
        parts.append(rect(left_x, y, box_w, box_h, CARD, ink, 2, rx=8))
        parts.append(rect(left_x, y, 10, box_h, ink, ink, 0))
        parts.append(
            glyph(
                shape_for(entry.working_position),
                left_x + 52,
                y + box_h / 2,
                28,
                line_fill(entry.color),
                ink,
                2.5,
            )
        )
        for row, name in enumerate(names[entry.id]):
            parts.append(text(left_x + 92, y + 30 + row * 30, name, 26, ink, "700"))
        parts.append(
            text(
                left_x + 92,
                y + 30 + 30 * len(names[entry.id]),
                f"position {entry.working_position}",
                24,
                MUTED,
            )
        )
        for row, question in enumerate(questions[entry.id]):
            parts.append(
                text(
                    left_x + 92,
                    y + 60 + 30 * len(names[entry.id]) + row * 28,
                    question,
                    26,
                    MUTED,
                )
            )
        left_center[entry.id] = y + box_h / 2
        y += box_h + gap

    right_center: dict[str, float] = {}
    y = top
    for entry in staged:
        stage_detail = f"stage {OPUS_STAGE_ORDER.index(entry.opus_stage) + 1} · the {entry.color} line"
        stage_rows = exact_lines(stage_detail, box_w - 112, 28)
        box_h = 72 + 32 * len(stage_rows)
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
                28,
                line_fill(entry.color),
                ink,
                2.5,
            )
        )
        parts.append(text(right_x + 24, y + 40, stage, 26, ink, "700"))
        for row, value in enumerate(stage_rows):
            parts.append(text(right_x + 24, y + 72 + row * 32, value, 28, MUTED))
        right_center[entry.id] = y + box_h / 2
        y += box_h + gap

    for entry in working:
        start_y = left_center[entry.id]
        end_y = right_center.get(entry.id)
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

    cursor = y + 24
    if unstaged:
        labels = [
            f"{entry.color} · position {entry.working_position}" for entry in unstaged
        ]
        row_counts = [len(exact_lines(value, box_w - 48, 28)) for value in labels]
        panel_height = 70 + 32 * sum(row_counts)
        parts.append(
            rect(
                right_x,
                cursor,
                box_w,
                panel_height,
                PANEL,
                MUTED,
                1.5,
                rx=8,
                dash="8 7",
            )
        )
        parts.append(
            text(right_x + 24, cursor + 34, "NO OPUS STAGE DECLARED", 28, MUTED, "700")
        )
        label_y: float = cursor + 68
        for entry, label in zip(unstaged, labels):
            drawn, label_y = text_block(
                right_x + 24, label_y, label, box_w - 48, 28, MUTED
            )
            parts.extend(drawn)
            parts.append(
                path(
                    f"M{left_x + box_w} {left_center[entry.id]:.1f} C "
                    f"{(left_x + box_w + right_x) / 2:.1f} {left_center[entry.id]:.1f}, "
                    f"{(left_x + box_w + right_x) / 2:.1f} {cursor + 30}, "
                    f"{right_x} {cursor + 30}",
                    MUTED,
                    2,
                    dash="4 7",
                )
            )
        cursor += panel_height + 24

    cursor = max(cursor, left_bottom) + 24
    parts.append(line(MARGIN, cursor + 10, CONTENT_RIGHT, cursor + 10, RULE, 2))
    parts.append(
        text(
            MARGIN,
            cursor + 46,
            f"LIVE CHECK · {divergence.name} · "
            f"{'holds' if divergence.passed else 'does not hold'}",
            28,
            ACCENT,
            "700",
        )
    )
    cursor += 74
    for sentence in wrap_to_width(divergence.detail, CONTENT_RIGHT - MARGIN, 26):
        parts.append(text(MARGIN, cursor, sentence, 26, INK))
        cursor += 28
    cursor += 18
    for index, note in enumerate(_ORDER_NOTES):
        for sentence in wrap_to_width(
            f"{index + 1}. {note}", CONTENT_RIGHT - MARGIN, 26
        ):
            parts.append(text(MARGIN, cursor, sentence, 26, INK))
            cursor += 28
        cursor += 8
    return "".join([*open_canvas(1600, cursor + 40), *parts, close_canvas()])


__all__ = ["set_compass", "two_orders"]

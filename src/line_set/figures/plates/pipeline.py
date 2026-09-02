"""The reader's stages and its exit ladder, drawn from the reader's own tuples.

Both sequences are read from :mod:`line_set.reader`: the stage column is
:data:`line_set.reader.READER_STAGES` and the ladder is
:data:`line_set.reader.STATUS_PRECEDENCE`. A stage added to the reader, or a
status reordered in it, changes this plate; a stage that lost its gloss fails
the build through :func:`line_set.figures.palette.verify_coverage` rather than
vanishing from a figure that claims to show all of them.

The plate draws the contract, not a reading. It says how a status is chosen,
never that any particular set is legible.
"""

from __future__ import annotations

from ...models import SetStatus
from ...reader import READER_STAGES, STATUS_PRECEDENCE
from ..canvas import (
    CONTENT_RIGHT,
    MARGIN,
    close_canvas,
    glyph,
    header,
    line,
    open_canvas,
    path,
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
    SET_STATUS_CONDITION,
    SET_STATUS_GLOSS,
    SET_STATUS_INK,
    SET_STATUS_SHAPE,
    STAGE_GLOSS,
    STAGE_NOTE,
    verify_coverage,
)

_STAGE_LEFT = MARGIN
_STAGE_WIDTH = 860
_LADDER_LEFT = MARGIN + _STAGE_WIDTH + 60
_LADDER_WIDTH = CONTENT_RIGHT - _LADDER_LEFT
_TOP = 320


def _stage_lines(stage: str) -> tuple[list[str], list[str]]:
    """Wrap one stage's gloss and its narrower note."""
    return wrap(STAGE_GLOSS[stage], 82), wrap(STAGE_NOTE[stage], 88)


def _stage_height(stage: str) -> int:
    """Stage box height derived from the text that stage actually carries."""
    gloss, note = _stage_lines(stage)
    return 72 + 26 * len(gloss) + 24 * len(note)


def _rung_lines(status: SetStatus) -> list[str]:
    """Wrap one ladder rung's gloss."""
    return wrap(SET_STATUS_GLOSS[status], 44)


def _rung_height(status: SetStatus) -> int:
    """Rung height derived from the gloss it carries."""
    return 92 + 22 * len(_rung_lines(status))


def set_reading_pipeline() -> str:
    """Draw the five reader stages beside the status precedence ladder."""
    verify_coverage()
    stage_heights = [_stage_height(stage) for stage in READER_STAGES]
    rung_heights = [_rung_height(status) for status in STATUS_PRECEDENCE]
    column = sum(height + 26 for height in stage_heights)
    ladder = sum(height + 20 for height in rung_heights)
    height = _TOP + max(column, ladder + 46) + 190
    parts = open_canvas(1600, height)
    parts += header(
        "READING THE SET",
        "Five stages, then the first condition that matches",
        "Each stage records what it did into the reading's derivation, so a "
        "reading can be re-read rather than trusted.",
        f"{len(READER_STAGES)} STAGES · "
        f"{len(STATUS_PRECEDENCE)} EXITS · THE FIRST MATCH WINS",
        ACCENT,
    )
    parts.append(
        text(_STAGE_LEFT, _TOP - 26, "THE STAGES, IN ORDER", 24, ACCENT, "700")
    )
    parts.append(text(_LADDER_LEFT, _TOP - 26, "THE EXIT LADDER", 24, ACCENT, "700"))

    cursor = _TOP
    for index, stage in enumerate(READER_STAGES):
        box_height = stage_heights[index]
        parts.append(
            rect(_STAGE_LEFT, cursor, _STAGE_WIDTH, box_height, CARD, RULE, 2, rx=10)
        )
        parts.append(rect(_STAGE_LEFT, cursor, 10, box_height, ACCENT, ACCENT, 0))
        parts.append(
            glyph("circle", _STAGE_LEFT + 52, cursor + 44, 21, PAPER, ACCENT, 2.5)
        )
        parts.append(
            text(
                _STAGE_LEFT + 52,
                cursor + 50,
                str(index + 1),
                24,
                ACCENT,
                "700",
                "middle",
            )
        )
        parts.append(text(_STAGE_LEFT + 92, cursor + 44, stage, 24, INK, "700"))
        gloss, note = _stage_lines(stage)
        row = cursor + 78
        for entry in gloss:
            parts.append(text(_STAGE_LEFT + 92, row, entry, 24, INK))
            row += 26
        for entry in note:
            parts.append(text(_STAGE_LEFT + 92, row, entry, 24, MUTED))
            row += 24
        if index < len(READER_STAGES) - 1:
            arrow_top = cursor + box_height
            parts.append(
                path(
                    f"M{_STAGE_LEFT + 52} {arrow_top + 2} "
                    f"L{_STAGE_LEFT + 52} {arrow_top + 20}",
                    MUTED,
                    2.5,
                )
            )
            parts.append(
                f'<path d="M{_STAGE_LEFT + 46} {arrow_top + 16} '
                f"L{_STAGE_LEFT + 52} {arrow_top + 25} "
                f'L{_STAGE_LEFT + 58} {arrow_top + 16} Z" fill="{MUTED}"/>'
            )
        cursor += box_height + 26

    # The bridge leaves the last stage and enters the ladder at its top rung:
    # the ladder is read downward, so the arrow must arrive at the first
    # condition tested, not at the last one.
    status_stage_top = _TOP + sum(height + 26 for height in stage_heights[:-1])
    bridge_y = status_stage_top + stage_heights[-1] / 2
    elbow_x = _LADDER_LEFT - 34
    entry_y = _TOP + 42
    parts.append(
        path(
            f"M{_STAGE_LEFT + _STAGE_WIDTH} {bridge_y:.1f} "
            f"L{elbow_x} {bridge_y:.1f} L{elbow_x} {entry_y} "
            f"L{_LADDER_LEFT - 8} {entry_y}",
            MUTED,
            2.5,
        )
    )
    parts.append(
        f'<path d="M{_LADDER_LEFT - 12} {entry_y - 6} '
        f"L{_LADDER_LEFT - 1} {entry_y} "
        f'L{_LADDER_LEFT - 12} {entry_y + 6} Z" fill="{MUTED}"/>'
    )

    rung_top = _TOP
    for index, status in enumerate(STATUS_PRECEDENCE):
        box_height = rung_heights[index]
        ink = SET_STATUS_INK[status]
        parts.append(
            rect(
                _LADDER_LEFT, rung_top, _LADDER_WIDTH, box_height, PANEL, ink, 2, rx=10
            )
        )
        parts.append(
            glyph(
                SET_STATUS_SHAPE[status],
                _LADDER_LEFT + 40,
                rung_top + 42,
                17,
                PAPER,
                ink,
                3,
            )
        )
        parts.append(
            text(_LADDER_LEFT + 72, rung_top + 40, status.value, 26, ink, "700")
        )
        parts.append(
            text(
                _LADDER_LEFT + 72,
                rung_top + 66,
                SET_STATUS_CONDITION[status],
                24,
                MUTED,
                "700",
            )
        )
        row = rung_top + 92
        for entry in _rung_lines(status):
            parts.append(text(_LADDER_LEFT + 72, row, entry, 24, INK))
            row += 22
        parts.append(
            text(
                _LADDER_LEFT + _LADDER_WIDTH - 16,
                rung_top + 40,
                f"exit {index + 1}",
                24,
                MUTED,
                "700",
                "end",
            )
        )
        if index < len(STATUS_PRECEDENCE) - 1:
            parts.append(
                path(
                    f"M{_LADDER_LEFT + 40} {rung_top + box_height + 2} "
                    f"L{_LADDER_LEFT + 40} {rung_top + box_height + 16}",
                    MUTED,
                    2,
                    dash="3 5",
                )
            )
        rung_top += box_height + 20
    parts.append(
        text(
            _LADDER_LEFT,
            rung_top + 26,
            "read downward · no condition below is tested",
            24,
            MUTED,
            "700",
        )
    )
    parts.append(
        text(
            _LADDER_LEFT,
            rung_top + 50,
            "once one above it has matched",
            24,
            MUTED,
            "700",
        )
    )

    footer = _TOP + max(column, ladder + 46) + 40
    parts.append(line(MARGIN, footer, CONTENT_RIGHT, footer, RULE, 2))
    parts.append(
        text(MARGIN, footer + 36, "WHAT AN EXIT ESTABLISHES", 24, ACCENT, "700")
    )
    parts.append(
        text(
            MARGIN,
            footer + 68,
            "An exit reports what the reader found in the declared names. It is "
            "not a finding about how any line behaves, and no exit grades a line.",
            24,
            INK,
        )
    )
    parts.append(
        text(
            MARGIN,
            footer + 98,
            "A line that could not be read contributes no version, no registry "
            "size, and no digest; those stay empty rather than being filled in.",
            24,
            MUTED,
        )
    )
    parts.append(close_canvas())
    return "".join(parts)


__all__ = ["set_reading_pipeline"]

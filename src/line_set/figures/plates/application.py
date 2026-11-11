"""The wrapper under its own rule, drawn from a reading that includes it.

This plate takes the reading :func:`line_set.reader.read_set` produced over the
declaration *plus* the wrapper's own entry, and shows the two sides the check
compares: the vocabulary this package publishes at its own root, and the
vocabulary each declared line publishes at its. The verdict at the bottom is
:func:`line_set.invariants.self_disjointness_from_reading` over the same
reading, so the plate cannot report a different answer from the check.

It refuses to be vacuous. With no line vocabulary to compare against, the
comparison set is empty and the plate says the property is unestablished
instead of drawing two columns that happen not to touch.

A verdict that holds establishes that this package's own status names are not
any line's status names. It does not establish that the wrapper stayed out of
the siblings' business, and no row on it is a finding about a line.
"""

from __future__ import annotations

from math import ceil

from ...invariants import SoundnessResult, self_disjointness_from_reading
from ...models import LineEntry, LineObservation, SetReading
from ..canvas import (
    CONTENT_RIGHT,
    MARGIN,
    close_canvas,
    glyph,
    header,
    line,
    open_canvas,
    plural,
    rect,
    text,
    exact_lines,
    text_block,
    wrap_to_width,
)
from ..palette import (
    ACCENT,
    CARD,
    GOOD,
    INK,
    MUTED,
    PANEL,
    PAPER,
    READ_CODE_INK,
    READ_CODE_SHAPE,
    READ_CODE_SOLID,
    RULE,
    WARN,
    line_fill,
    line_ink,
    shape_for,
)

#: Marker shape and word for a line that carries none of the wrapper's tokens,
#: and for one that carries some. Shape, fill, and label all differ.
DISJOINT_SHAPE = "circle"
OVERLAP_SHAPE = "square"

_CONTENT_WIDTH = CONTENT_RIGHT - MARGIN
_TOP = 300


def _wrapper_observation(
    reading: SetReading, wrapper: LineEntry
) -> LineObservation | None:
    """The observation recorded for the wrapper's own entry, if there is one."""
    for observation in reading.observations:
        if observation.line_id == wrapper.id:
            return observation
    return None


def _line_observations(
    reading: SetReading, wrapper: LineEntry
) -> tuple[LineObservation, ...]:
    """Every observation except the wrapper's, in the reading's own order."""
    return tuple(
        observation
        for observation in reading.observations
        if observation.line_id != wrapper.id
    )


def _unestablished(
    lines: tuple[LineEntry, ...],
    wrapper: LineEntry,
    reading: SetReading,
    verdict: SoundnessResult,
    reason: str,
) -> str:
    """Draw the honest replacement for a comparison that could not be made."""
    detail_lines = wrap_to_width(verdict.detail, _CONTENT_WIDTH, 24)
    observations = _line_observations(reading, wrapper)
    parts: list[str] = []
    parts += header(
        "THE WRAPPER UNDER ITS OWN RULE",
        "The comparison could not be made",
        reason,
        "NOT A RESULT · SELF-DISJOINTNESS IS UNESTABLISHED HERE",
        WARN,
    )
    parts.append(rect(MARGIN, _TOP, _CONTENT_WIDTH, 100, PANEL, WARN, 2.5, rx=10))
    parts.append(
        text(MARGIN + 28, _TOP + 44, f"{verdict.name} · does not hold", 22, WARN, "700")
    )
    parts.append(
        text(
            MARGIN + 28,
            _TOP + 78,
            "This plate is not evidence that the wrapper's vocabulary is "
            "disjoint. It was not compared.",
            24,
            INK,
        )
    )
    cursor = _TOP + 132
    for observation in observations:
        code = observation.code
        name_rows = exact_lines(observation.line_id, 240, 24)
        row_height = max(36, 12 + 28 * len(name_rows))
        parts.append(
            rect(MARGIN, cursor, _CONTENT_WIDTH, row_height, CARD, RULE, 1.5, rx=6)
        )
        parts.append(
            glyph(
                READ_CODE_SHAPE[code],
                MARGIN + 26,
                cursor + 18,
                11,
                READ_CODE_INK[code] if READ_CODE_SOLID[code] else PAPER,
                READ_CODE_INK[code],
                2,
            )
        )
        drawn, _ = text_block(
            MARGIN + 52, cursor + 24, observation.line_id, 240, 24, INK, "700"
        )
        parts.extend(drawn)
        parts.append(
            text(MARGIN + 320, cursor + 24, code.value, 24, READ_CODE_INK[code], "700")
        )
        parts.append(
            text(
                MARGIN + 560,
                cursor + 24,
                f"{plural(len(observation.tokens), 'token')} read",
                24,
                MUTED,
            )
        )
        cursor += row_height + 8
    parts.append(line(MARGIN, cursor + 18, CONTENT_RIGHT, cursor + 18, RULE, 2))
    for index, detail in enumerate(detail_lines):
        parts.append(text(MARGIN, cursor + 54 + index * 26, detail, 24, INK))
    parts.append(
        text(
            MARGIN,
            cursor + 62 + 26 * len(detail_lines),
            f"The declaration holds {plural(len(lines), 'line')}; install them "
            "and rebuild to make the comparison.",
            24,
            MUTED,
        )
    )
    return "".join(
        [
            *open_canvas(1600, cursor + 122 + 26 * len(detail_lines)),
            *parts,
            close_canvas(),
        ]
    )


def self_application(
    lines: tuple[LineEntry, ...],
    wrapper: LineEntry,
    reading: SetReading,
) -> str:
    """Draw the wrapper's vocabulary against the lines', with the live verdict.

    ``reading`` must be a reading over the declaration *with* the wrapper
    appended — the same reading
    :func:`line_set.invariants.check_self_disjointness` takes. The verdict
    panel is that function's pure half run over this reading, not a second
    judgment made here.
    """
    verdict = self_disjointness_from_reading(reading, wrapper)
    observation = _wrapper_observation(reading, wrapper)
    if observation is None or not observation.tokens:
        return _unestablished(
            lines,
            wrapper,
            reading,
            verdict,
            "The wrapper's own vocabulary could not be read, so there was "
            "nothing to compare from.",
        )
    observations = _line_observations(reading, wrapper)
    compared = tuple(item for item in observations if item.tokens)
    if not compared:
        return _unestablished(
            lines,
            wrapper,
            reading,
            verdict,
            "No line supplied a vocabulary, so the comparison set was empty.",
        )

    declared = {entry.id: entry for entry in lines}
    tokens = tuple(observation.tokens)
    hits = {
        collision.token
        for collision in (*reading.collisions, *reading.exempted_collisions)
        if wrapper.id in collision.lines
    }
    # Column count is bounded by usable token width, not token count. Overflow
    # goes downward; no new token can squeeze an existing label.
    preferred_width = min(_CONTENT_WIDTH, max(300, max(map(len, tokens)) * 24 + 54))
    columns = max(1, min(4, int(_CONTENT_WIDTH / preferred_width)))
    column_width = _CONTENT_WIDTH / columns
    token_rows = [exact_lines(token, column_width - 70, 24) for token in tokens]
    row_heights = [
        max(len(rows) for rows in token_rows[start : start + columns]) * 28 + 8
        for start in range(0, len(tokens), columns)
    ]
    identity = (
        f"{wrapper.package_name} · {wrapper.color} · "
        f"{plural(len(tokens), 'enum member name')} exported at its root"
    )
    identity_rows = exact_lines(identity, _CONTENT_WIDTH - 56, 26)
    token_top = _TOP + 32 + 30 * len(identity_rows)
    vocabulary_height = token_top - _TOP + sum(row_heights) + 18
    detail_lines = wrap_to_width(verdict.detail, _CONTENT_WIDTH - 98, 24)
    rule_lines = wrap_to_width(
        "A declared exemption does not help here. The wrapper is not a line and "
        "has no standing to share a token with one, so an exempted collision "
        "involving it counts against it exactly like an undeclared one. What "
        "holds is a fact about spellings: this package's own status names are "
        "not any line's status names. It is not a finding that the wrapper has "
        "kept its other boundaries, which a person reads.",
        _CONTENT_WIDTH,
        24,
    )
    parts: list[str] = []
    parts += header(
        "THE WRAPPER UNDER ITS OWN RULE",
        "The package that checks for shared tokens, checked for shared tokens",
        "Above: the vocabulary this package publishes at its own root. Below: "
        "what each declared line publishes, and whether any of it is the same.",
        f"{plural(len(tokens), 'wrapper token').upper()} AGAINST "
        f"{plural(len(compared), 'legible line').upper()} · "
        f"{plural(len(hits), 'shared spelling').upper()}",
        WARN if hits else ACCENT,
    )

    parts.append(
        text(MARGIN, _TOP - 24, "THE WRAPPER'S OWN VOCABULARY", 24, ACCENT, "700")
    )
    parts.append(
        rect(MARGIN, _TOP, _CONTENT_WIDTH, vocabulary_height, CARD, MUTED, 2, rx=10)
    )
    drawn, _ = text_block(
        MARGIN + 28, _TOP + 32, identity, _CONTENT_WIDTH - 56, 26, INK, "700"
    )
    parts.extend(drawn)
    y: float = token_top
    for start in range(0, len(tokens), columns):
        for column, token in enumerate(tokens[start : start + columns]):
            x = MARGIN + 28 + column * column_width
            carried = token in hits
            parts.append(
                glyph(
                    OVERLAP_SHAPE if carried else DISJOINT_SHAPE,
                    x + 8,
                    y - 6,
                    7,
                    WARN if carried else PAPER,
                    WARN if carried else MUTED,
                    2,
                )
            )
            drawn, _ = text_block(
                x + 26,
                y,
                token,
                column_width - 70,
                24,
                WARN if carried else INK,
                "700" if carried else "400",
            )
            parts.extend(drawn)
        y += row_heights[start // columns]
    cursor: float = _TOP + vocabulary_height + 76
    parts.append(
        text(MARGIN, cursor - 26, "AGAINST EACH DECLARED LINE", 24, ACCENT, "700")
    )
    for item in observations:
        overlap = sorted(frozenset(item.tokens) & set(tokens))
        readable = bool(item.tokens)
        ink = WARN if overlap else (GOOD if readable else MUTED)
        shape = OVERLAP_SHAPE if overlap else DISJOINT_SHAPE
        entry = declared.get(item.line_id)
        entry_ink = MUTED if entry is None else line_ink(entry.color)
        entry_fill = PAPER if entry is None else line_fill(entry.color)
        marker = "circle" if entry is None else shape_for(entry.working_position)
        name = item.line_id
        state = (
            f"{plural(len(item.tokens), 'token')} read"
            if readable
            else f"no vocabulary read · {item.code.value}"
        )
        comparison = (
            f"shares {', '.join(overlap)} with the wrapper"
            if overlap
            else "shares no spelling with the wrapper"
            if readable
            else "was not read, so nothing was compared"
        )
        content = []
        y = cursor + 30
        for value, size, color, weight in (
            (name, 26, INK, "700"),
            (state, 24, MUTED if readable else WARN, "400"),
            (comparison, 24, ink, "700"),
        ):
            drawn, y = text_block(
                MARGIN + 78, y, value, _CONTENT_WIDTH - 110, size, color, weight
            )
            content.extend(drawn)
        row_height = y - cursor + 10
        parts.append(
            rect(MARGIN, cursor, _CONTENT_WIDTH, row_height, CARD, RULE, 1.5, rx=8)
        )
        parts.append(rect(MARGIN, cursor, 10, row_height, entry_ink, entry_ink, 0))
        parts.append(
            glyph(marker, MARGIN + 46, cursor + 32, 15, entry_fill, entry_ink, 2.5)
        )
        parts.append(
            glyph(
                shape,
                MARGIN + 46,
                cursor + 64,
                10,
                WARN if overlap else PAPER,
                ink,
                2.5,
            )
        )
        parts.extend(content)
        cursor += row_height + 12

    status_ink = GOOD if verdict.passed else WARN
    parts.append(
        rect(
            MARGIN,
            cursor + 12,
            _CONTENT_WIDTH,
            104 + 26 * len(detail_lines),
            PANEL,
            status_ink,
            2.5,
            rx=10,
        )
    )
    parts.append(
        glyph(
            DISJOINT_SHAPE if verdict.passed else OVERLAP_SHAPE,
            MARGIN + 40,
            cursor + 56,
            17,
            PAPER,
            status_ink,
            3,
        )
    )
    parts.append(
        text(
            MARGIN + 74,
            cursor + 62,
            f"{verdict.name} · {'holds' if verdict.passed else 'does not hold'}",
            24,
            status_ink,
            "700",
        )
    )
    for index, detail in enumerate(detail_lines):
        parts.append(text(MARGIN + 74, cursor + 96 + index * 26, detail, 24, INK))

    footer = cursor + 142 + 26 * len(detail_lines)
    parts.append(line(MARGIN, footer, CONTENT_RIGHT, footer, RULE, 2))
    parts.append(text(MARGIN, footer + 34, "READING RULE", 24, ACCENT, "700"))
    for index, row_text in enumerate(rule_lines):
        parts.append(text(MARGIN, footer + 66 + index * 26, row_text, 24, INK))
    return "".join(
        [
            *open_canvas(1600, ceil(footer + 96 + 26 * len(rule_lines))),
            *parts,
            close_canvas(),
        ]
    )


__all__ = [
    "DISJOINT_SHAPE",
    "OVERLAP_SHAPE",
    "self_application",
]

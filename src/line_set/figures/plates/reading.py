"""Plates drawn from a live reading. Every cell here comes from the reader.

``vocabulary_matrix`` and ``installation_surface`` take a
:class:`~line_set.models.SetReading` and draw exactly what it holds. Neither
plate recomputes anything, and neither fills a gap: a line the reader could not
read is drawn as unread, with its version, registry size, and digest left
empty, because that is what the reading says.

Both plates refuse to be vacuous. A matrix over fewer than two legible
vocabularies has found no overlap for the uninteresting reason, and it says so
in place of an empty grid that would read like a clean result.
"""

from __future__ import annotations

from dataclasses import dataclass

from ...models import LineEntry, ReadCode, SetReading
from ..canvas import (
    CONTENT_RIGHT,
    MARGIN,
    close_canvas,
    glyph,
    hatch_defs,
    header,
    line,
    open_canvas,
    plural,
    rect,
    text,
    wrap,
    wrap_to_width,
    escape_text,
)
from ..palette import (
    ACCENT,
    CARD,
    INK,
    MUTED,
    OCHRE,
    PANEL,
    PAPER,
    READ_CODE_GLOSS,
    READ_CODE_INK,
    READ_CODE_SHAPE,
    READ_CODE_SOLID,
    RULE,
    SET_STATUS_GLOSS,
    SET_STATUS_INK,
    SET_STATUS_SHAPE,
    WARN,
    line_fill,
    line_ink,
    shape_for,
    verify_coverage,
)

#: How many hex characters of a digest a plate shows. A prefix is enough to
#: spot disagreement between two people holding the same artifact; it is not
#: offered as proof of anything.
DIGEST_PREFIX = 12

#: The marker shape and label that separate a declared exemption from an
#: undeclared collision. The two differ in shape, in fill, and in words, so the
#: distinction survives a greyscale print.
EXEMPT_SHAPE = "diamond"
COLLISION_SHAPE = "square"
EXEMPT_LABEL = "EXEMPT — declared meanings"
COLLISION_LABEL = "COLLISION — no matching exemption"

_TOKEN_LABEL_SIZE = 24
_GLOSS_WRAP = 30

_CONTENT_WIDTH = CONTENT_RIGHT - MARGIN
_TOP = 300


def _tokens_by_line(reading: SetReading) -> dict[str, frozenset[str]]:
    """Map each observed line id to the token set the reader recorded for it."""
    return {
        observation.line_id: frozenset(observation.tokens)
        for observation in reading.observations
    }


def _codes_by_line(reading: SetReading) -> dict[str, ReadCode]:
    """Map each observed line id to its read code."""
    return {
        observation.line_id: observation.code for observation in reading.observations
    }


def _ordered(lines: tuple[LineEntry, ...]) -> tuple[LineEntry, ...]:
    """Declared entries in working order."""
    return tuple(sorted(lines, key=lambda entry: entry.working_position))


def _legend(
    entries: tuple[LineEntry, ...],
    carried: dict[str, frozenset[str]],
    codes: dict[str, ReadCode],
    top: int,
) -> tuple[list[str], int]:
    columns = max(1, min(len(entries), int(_CONTENT_WIDTH / 300)))
    gap = 12
    chip_w = (_CONTENT_WIDTH - gap * (columns - 1)) / columns
    parts: list[str] = []
    for index, entry in enumerate(entries):
        x = MARGIN + (index % columns) * (chip_w + gap)
        y = top + (index // columns) * 68
        ink = line_ink(entry.color)
        code = codes.get(entry.id)
        tokens = carried.get(entry.id, frozenset())
        parts.append(rect(x, y, chip_w, 60, CARD, ink, 2, rx=6))
        parts.append(
            glyph(
                shape_for(entry.working_position),
                x + 24,
                y + 21,
                12,
                line_fill(entry.color),
                ink,
                2,
            )
        )
        parts.append(
            text(x + 46, y + 28, f"{entry.working_position} {entry.id}", 24, ink, "700")
        )
        detail = (
            f"{plural(len(tokens), 'token')} · {code.value if code else 'observed'}"
            if tokens
            else f"not read · {code.value if code else 'not observed'}"
        )
        parts.append(text(x + 14, y + 52, detail, 24, MUTED))
    rows = (len(entries) + columns - 1) // columns
    return parts, top + rows * 68


def _empty_matrix(
    entries: tuple[LineEntry, ...],
    codes: dict[str, ReadCode],
    legible: int,
) -> str:
    """Draw the honest replacement for a matrix nothing could be put into.

    An empty grid would look like a clean sheet. It is not one: a comparison
    that had fewer than two vocabularies to compare established nothing, and
    this plate says that in the place where the grid would have been.
    """
    height = _TOP + 132 + 46 * len(entries) + 110
    parts = open_canvas(1600, height)
    parts += header(
        "THE VOCABULARY MATRIX",
        "Nothing could be compared",
        "The matrix needs at least two legible vocabularies. This reading did "
        "not supply them.",
        "NOT A RESULT · AN OVERLAP CHECK WITH NOTHING TO CHECK",
        WARN,
    )
    parts.append(rect(MARGIN, _TOP, _CONTENT_WIDTH, 96, PANEL, WARN, 2.5, rx=10))
    parts.append(
        text(
            MARGIN + 28,
            _TOP + 42,
            f"{plural(legible, 'line')} yielded a vocabulary; two are needed "
            "before any overlap can be found",
            26,
            WARN,
            "700",
        )
    )
    parts.append(
        text(
            MARGIN + 28,
            _TOP + 74,
            "This plate is not evidence that the declared vocabularies are "
            "disjoint. They were not compared.",
            24,
            INK,
        )
    )
    cursor = _TOP + 132
    for entry in entries:
        code = codes.get(entry.id)
        ink = READ_CODE_INK[code] if code is not None else MUTED
        parts.append(rect(MARGIN, cursor, _CONTENT_WIDTH, 38, CARD, RULE, 1.5, rx=6))
        parts.append(
            glyph(
                shape_for(entry.working_position),
                MARGIN + 26,
                cursor + 19,
                12,
                line_fill(entry.color),
                line_ink(entry.color),
                2,
            )
        )
        parts.append(text(MARGIN + 52, cursor + 25, entry.color, 24, INK, "700"))
        parts.append(
            text(
                MARGIN + 200,
                cursor + 25,
                code.value if code is not None else "not observed",
                24,
                ink,
                "700",
            )
        )
        parts.append(
            text(
                MARGIN + 420,
                cursor + 25,
                READ_CODE_GLOSS[code] if code is not None else "no observation",
                24,
                MUTED,
            )
        )
        cursor += 46
    parts.append(line(MARGIN, cursor + 20, CONTENT_RIGHT, cursor + 20, RULE, 2))
    parts.append(
        text(
            MARGIN,
            cursor + 56,
            "Install the declared line packages and rebuild to compare them. "
            "Until then the set's non-overlap contract is unchecked, not held.",
            24,
            INK,
        )
    )
    parts.append(close_canvas())
    return "".join(parts)


@dataclass(frozen=True)
class _TokenRow:
    token: str
    fragments: tuple[str, ...]
    positions: str
    kind: str

    @property
    def height(self) -> int:
        return 25 * len(self.fragments) + 6


def _token_fragments(token: str, budget: int) -> tuple[str, ...]:
    fragments = []
    while len(token) > budget:
        split = token.rfind("_", 0, budget) + 1
        split = split if split else budget
        fragments.append(token[:split])
        token = token[split:]
    return (*fragments, token)


def _token_panels(
    rows: tuple[_TokenRow, ...], columns: int
) -> tuple[tuple[_TokenRow, ...], ...]:
    prefix = [0]
    for row in rows:
        prefix.append(prefix[-1] + row.height)
    cuts = [0]
    for column in range(1, columns):
        candidates = range(cuts[-1] + 1, len(rows) - (columns - column) + 1)
        cuts.append(
            min(
                candidates,
                key=lambda index: abs(prefix[index] - prefix[-1] * column / columns),
            )
        )
    cuts.append(len(rows))
    return tuple(rows[left:right] for left, right in zip(cuts, cuts[1:]))


def vocabulary_matrix(
    lines: tuple[LineEntry, ...],
    reading: SetReading,
) -> str:
    """Draw every observed name and its carriers as a faceted sparse matrix.

    Carrier numbers are declaration working positions. Unread entries remain
    unknown in the key; an omitted carrier is never evidence about an unread line.
    """
    verify_coverage()
    entries = _ordered(lines)
    carried = _tokens_by_line(reading)
    codes = _codes_by_line(reading)
    legible = sum(1 for entry in entries if carried.get(entry.id))
    tokens = sorted({token for values in carried.values() for token in values})
    if legible < 2 or not tokens:
        return _empty_matrix(entries, codes, legible)

    flags = {
        item.token: item.exempted
        for item in (*reading.collisions, *reading.exempted_collisions)
    }
    positions = {
        token: ",".join(
            str(entry.working_position)
            for entry in entries
            if token in carried.get(entry.id, ())
        )
        for token in tokens
    }
    columns = min(3, len(tokens))
    gap = 24
    column_width = (_CONTENT_WIDTH - gap * (columns - 1)) / columns
    carrier_width = max(
        144, max(len(value) for value in positions.values()) * 24 * 0.6 + 14
    )
    token_width = column_width - carrier_width - 50
    budget = max(1, int(token_width / _TOKEN_LABEL_SIZE))
    rows = tuple(
        _TokenRow(
            token,
            _token_fragments(token, budget),
            positions[token],
            "exempted"
            if flags.get(token) is True
            else "collision"
            if flags.get(token) is False
            else "unique",
        )
        for token in tokens
    )
    panels = _token_panels(rows, columns)
    parts: list[str] = []
    parts += header(
        "THE VOCABULARY MATRIX",
        "Every observed name and its carrying lines",
        "Names include enum aliases. Positions refer to the declaration key below; only observed carriers are listed.",
        f"LIVE READING · {plural(len(tokens), 'name').upper()} · {legible} OF {len(entries)} VOCABULARIES READ",
        ACCENT,
    )
    legend, key_end = _legend(entries, carried, codes, 280)
    parts += legend
    summary = (
        f"{len(reading.exempted_collisions)} exempted collisions · "
        f"{len(reading.collisions)} unexempted collisions"
    )
    if not flags:
        summary = "No token in the grid below is carried by two lines."
    parts.append(text(MARGIN, key_end + 26, summary, 24, ACCENT, "700"))
    for x, shape, label, ink in (
        (MARGIN, EXEMPT_SHAPE, EXEMPT_LABEL, OCHRE),
        (MARGIN + _CONTENT_WIDTH / 2, COLLISION_SHAPE, COLLISION_LABEL, WARN),
    ):
        parts.append(glyph(shape, x + 10, key_end + 48, 7, PAPER, ink, 2))
        parts.append(text(x + 28, key_end + 56, label, 24, ink, "700"))
    table_top = key_end + 108
    bottoms = []
    for column, panel in enumerate(panels):
        left = MARGIN + column * (column_width + gap)
        right = left + column_width
        parts.append(text(left + 26, table_top - 14, "TOKEN", 24, ACCENT, "700"))
        parts.append(
            text(right - 12, table_top - 14, "POSITIONS", 24, ACCENT, "700", "end")
        )
        cursor = table_top
        for row in panel:
            ink = (
                OCHRE
                if row.kind == "exempted"
                else WARN
                if row.kind == "collision"
                else INK
            )
            parts.append(
                f'<g data-token="{escape_text(row.token)}" data-kind="{row.kind}" '
                f'data-carriers="{row.positions}" role="group" '
                f'aria-label="{escape_text(row.token)}; observed positions {row.positions}; {row.kind}">'
            )
            parts.append(
                rect(left, cursor, column_width, row.height, CARD, RULE, 0.7, rx=3)
            )
            if row.kind != "unique":
                parts.append(
                    glyph(
                        EXEMPT_SHAPE if row.kind == "exempted" else COLLISION_SHAPE,
                        left + 10,
                        cursor + 13,
                        6,
                        PAPER if row.kind == "exempted" else ink,
                        ink,
                        2,
                    )
                )
            parts.append('<g class="token-name">')
            for index, fragment in enumerate(row.fragments):
                parts.append(
                    text(
                        left + 26,
                        cursor + 22 + index * 25,
                        fragment,
                        _TOKEN_LABEL_SIZE,
                        ink,
                        "700" if row.kind != "unique" else "400",
                    )
                )
            parts.append('</g><g class="token-carriers">')
            parts.append(
                text(right - 12, cursor + 22, row.positions, 24, INK, "700", "end")
            )
            parts.append("</g></g>")
            cursor += row.height
        bottoms.append(cursor)
    cursor = max(bottoms) + 28
    parts.append(line(MARGIN, cursor, CONTENT_RIGHT, cursor, RULE, 2))
    cursor += 34
    parts.append(text(MARGIN, cursor, "READING BOUNDARY", 24, ACCENT, "700"))
    cursor += 30
    for paragraph in (
        "Numbers are working positions. Only observed carriers are listed; unread lines remain unknown.",
        "This display compares spellings. It establishes neither conceptual separation nor sibling correctness.",
    ):
        for value in wrap_to_width(paragraph, _CONTENT_WIDTH, 24):
            parts.append(text(MARGIN, cursor, value, 24, INK))
            cursor += 26
        cursor += 8
    return "".join([*open_canvas(1600, cursor + 24), *parts, close_canvas()])


def _surface_row_height(detail_lines: int) -> int:
    """Row height derived from how much detail the observation carries."""
    return 112 + 24 * detail_lines


def installation_surface(
    lines: tuple[LineEntry, ...],
    reading: SetReading,
) -> str:
    """Draw what was actually found on this machine for each declared line.

    A row that resolved reports the version, registry size, token count, and
    digest prefix its package published. A row that did not resolve is hatched,
    is labelled with the code that explains it, and shows an em dash in every
    metric: no value is carried over, defaulted, or guessed.
    """
    verify_coverage()
    entries = _ordered(lines)
    observations = {
        observation.line_id: observation for observation in reading.observations
    }
    details = {
        entry.id: wrap_to_width(
            observations[entry.id].detail
            if entry.id in observations and observations[entry.id].detail
            else "no detail was recorded",
            _CONTENT_WIDTH - 130,
            24,
        )
        for entry in entries
    }
    heights = [_surface_row_height(len(details[entry.id])) for entry in entries]
    declare_stage = next(
        (stage for stage in reading.derivation if stage.name == "declare"), None
    )
    summary_lines = wrap_to_width(
        declare_stage.detail if declare_stage is not None else "no declare stage ran",
        _CONTENT_WIDTH - 98,
        24,
    )
    summary_height = 210 + 24 * len(summary_lines)
    height = _TOP + sum(item + 20 for item in heights) + summary_height + 90
    unread = [
        entry.id
        for entry in entries
        if entry.id not in observations
        or observations[entry.id].code is not ReadCode.RESOLVED
    ]

    parts = open_canvas(1600, height)
    parts.append(hatch_defs("notread", WARN))
    parts += header(
        "THE INSTALLATION SURFACE",
        "What this machine could actually read",
        "One row per declared line: whether it resolved, what version it "
        "publishes, how large its registry is, and the prefix of its digest.",
        f"LIVE READING · {plural(len(entries), 'declared line').upper()} · "
        f"{plural(len(unread), 'line').upper()} NOT READ",
        WARN if unread else ACCENT,
    )

    cursor = _TOP
    for entry, row_height in zip(entries, heights):
        observation = observations.get(entry.id)
        code = observation.code if observation is not None else ReadCode.NOT_INSTALLED
        code_ink = READ_CODE_INK[code]
        resolved = code is ReadCode.RESOLVED
        ink = line_ink(entry.color)
        parts.append(
            rect(MARGIN, cursor, _CONTENT_WIDTH, row_height, CARD, ink, 2, rx=10)
        )
        parts.append(rect(MARGIN, cursor, 12, row_height, ink, ink, 0))
        if not resolved:
            parts.append(
                f'<rect x="{MARGIN + 12}" y="{cursor + 1}" '
                f'width="{_CONTENT_WIDTH - 13}" height="{row_height - 2}" '
                'fill="url(#notread)" stroke="none"/>'
            )
        parts.append(
            glyph(
                shape_for(entry.working_position),
                MARGIN + 60,
                cursor + 46,
                26,
                line_fill(entry.color),
                ink,
                3,
            )
        )
        parts.append(text(MARGIN + 106, cursor + 40, entry.color, 26, ink, "700"))
        parts.append(
            text(MARGIN + 106, cursor + 68, entry.package_name, 24, MUTED, "700")
        )
        parts.append(
            glyph(
                READ_CODE_SHAPE[code],
                MARGIN + 400,
                cursor + 34,
                13,
                code_ink if READ_CODE_SOLID[code] else PAPER,
                code_ink,
                2.5,
            )
        )
        parts.append(text(MARGIN + 424, cursor + 40, code.value, 24, code_ink, "700"))
        # Wrapped narrow enough that the widest gloss line stops short of the
        # stat blocks to its right. The room is CONTENT_RIGHT - 20 - four stat
        # blocks - this column's left edge; a wider wrap ran the gloss under
        # the version value.
        for index, gloss in enumerate(wrap(READ_CODE_GLOSS[code], _GLOSS_WRAP)):
            parts.append(text(MARGIN + 424, cursor + 68 + index * 22, gloss, 24, MUTED))
        stats = (
            (
                "VERSION",
                observation.version
                if observation is not None and observation.version
                else "—",
            ),
            (
                "SIZE",
                str(observation.registry_size)
                if observation is not None and observation.registry_size is not None
                else "—",
            ),
            (
                "TOKENS",
                str(len(observation.tokens))
                if observation is not None and observation.tokens
                else "—",
            ),
            (
                "DIGEST",
                observation.registry_digest[:DIGEST_PREFIX]
                if observation is not None and observation.registry_digest
                else "—",
            ),
        )
        block_w = 158
        first_x = CONTENT_RIGHT - 20 - block_w * len(stats)
        for index, (label, value) in enumerate(stats):
            bx = first_x + index * block_w
            parts.append(text(bx, cursor + 38, label, 24, MUTED, "700"))
            parts.append(
                text(
                    bx,
                    cursor + 66,
                    value,
                    26,
                    INK if value != "—" else MUTED,
                    "700",
                )
            )
            if value == "—":
                parts.append(text(bx, cursor + 88, "not read", 24, code_ink, "700"))
        for index, row in enumerate(details[entry.id]):
            parts.append(text(MARGIN + 106, cursor + 104 + index * 24, row, 24, MUTED))
        cursor += row_height + 20

    status_ink = SET_STATUS_INK[reading.status]
    parts.append(
        rect(
            MARGIN,
            cursor,
            _CONTENT_WIDTH,
            summary_height - 40,
            PANEL,
            status_ink,
            2.5,
            rx=10,
        )
    )
    parts.append(
        glyph(
            SET_STATUS_SHAPE[reading.status],
            MARGIN + 40,
            cursor + 44,
            24,
            PAPER,
            status_ink,
            3,
        )
    )
    parts.append(
        text(MARGIN + 74, cursor + 50, reading.status.value, 26, status_ink, "700")
    )
    parts.append(
        text(
            MARGIN + 74,
            cursor + 80,
            SET_STATUS_GLOSS[reading.status],
            24,
            INK,
        )
    )
    counts = reading.counts()
    tally = " · ".join(f"{code.value} {counts[code.value]}" for code in ReadCode)
    parts.append(text(MARGIN + 74, cursor + 112, tally, 24, MUTED, "700"))
    parts.append(
        text(
            MARGIN + 74,
            cursor + 144,
            f"declaration digest {reading.set_digest[:DIGEST_PREFIX]} · "
            f"undeclared lines: {', '.join(reading.undeclared_lines) or 'none reported'}",
            24,
            MUTED,
        )
    )
    for index, row in enumerate(summary_lines):
        parts.append(text(MARGIN + 74, cursor + 176 + index * 24, row, 24, MUTED))
    footer_lines = wrap_to_width(
        "A row marked not read is a fact about this machine's installation, not about the line. Nothing on that row is filled in from memory, a default, or a previous build.",
        _CONTENT_WIDTH,
        24,
    )
    for index, value in enumerate(footer_lines):
        parts.append(
            text(MARGIN, cursor + summary_height + 4 + index * 26, value, 24, INK)
        )
    parts.append(close_canvas())
    return "".join(parts)


__all__ = [
    "COLLISION_LABEL",
    "COLLISION_SHAPE",
    "DIGEST_PREFIX",
    "EXEMPT_LABEL",
    "EXEMPT_SHAPE",
    "installation_surface",
    "vocabulary_matrix",
]

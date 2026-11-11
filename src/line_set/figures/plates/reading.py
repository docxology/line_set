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
#: distinction survives a grayscale print.
EXEMPT_SHAPE = "diamond"
COLLISION_SHAPE = "square"
EXEMPT_LABEL = "EXEMPT — declared meanings"
COLLISION_LABEL = "COLLISION — no matching exemption"

_TOKEN_LABEL_SIZE = 24

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
    width: int,
) -> tuple[list[str], int]:
    columns = max(1, min(len(entries), int(width / 300)))
    gap = 12
    chip_w = (width - gap * (columns - 1)) / columns
    parts: list[str] = []
    cursor = top
    for start in range(0, len(entries), columns):
        group = entries[start : start + columns]
        chips = []
        for entry in group:
            code = codes.get(entry.id)
            tokens = carried.get(entry.id, frozenset())
            title = f"{entry.working_position} {entry.id}"
            detail = (
                f"{plural(len(tokens), 'token')} · {code.value if code else 'observed'}"
                if tokens
                else f"not read · {code.value if code else 'not observed'}"
            )
            chips.append((entry, title, detail))
        row_height = max(
            20
            + 28
            * (
                len(exact_lines(title, chip_w - 60, 24))
                + len(exact_lines(detail, chip_w - 60, 24))
            )
            for _, title, detail in chips
        )
        for index, (entry, title, detail) in enumerate(chips):
            x = MARGIN + index * (chip_w + gap)
            ink = line_ink(entry.color)
            parts.append(rect(x, cursor, chip_w, row_height, CARD, ink, 2, rx=6))
            parts.append(
                glyph(
                    shape_for(entry.working_position),
                    x + 24,
                    cursor + 21,
                    12,
                    line_fill(entry.color),
                    ink,
                    2,
                )
            )
            drawn, next_y = text_block(
                x + 46, cursor + 28, title, chip_w - 60, 24, ink, "700"
            )
            parts.extend(drawn)
            drawn, _ = text_block(x + 46, next_y, detail, chip_w - 60, 24, MUTED)
            parts.extend(drawn)
        cursor += row_height + gap
    return parts, cursor


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
    parts: list[str] = []
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
        name_rows = exact_lines(entry.color, 124, 24)
        row_height = max(38, 10 + 28 * len(name_rows))
        parts.append(
            rect(MARGIN, cursor, _CONTENT_WIDTH, row_height, CARD, RULE, 1.5, rx=6)
        )
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
        drawn, _ = text_block(
            MARGIN + 52, cursor + 25, entry.color, 124, 24, INK, "700"
        )
        parts.extend(drawn)
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
        cursor += row_height + 8
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
    return "".join([*open_canvas(1600, cursor + 100), *parts, close_canvas()])


@dataclass(frozen=True)
class _TokenRow:
    token: str
    fragments: tuple[str, ...]
    positions: str
    kind: str
    carrier_fragments: tuple[str, ...]
    carrier_width: float

    @property
    def height(self) -> int:
        return 25 * max(len(self.fragments), len(self.carrier_fragments)) + 3


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
    The key and up to four height-balanced facets share one available-width budget;
    every token fragment and carrier contributes its full drawn row height.
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
    # Four facets retain the original token width while shortening the full
    # live corpus; the wider canvas still keeps authored 24-unit labels above
    # the page's six-point floor when width-bound.
    canvas_width = 2100
    content_right = canvas_width - MARGIN
    content_width = content_right - MARGIN
    columns = min(4, len(tokens))
    gap = 24
    column_width = (content_width - gap * (columns - 1)) / columns
    # Reserve only this name's actual carrier list, not the longest list in
    # the entire reading. Shared names must not force every unique name to wrap.
    carrier_widths = {
        token: min(column_width / 2, max(24, len(value) * 24))
        for token, value in positions.items()
    }
    budgets = {
        token: max(
            1, int((column_width - carrier_widths[token] - 64) / _TOKEN_LABEL_SIZE)
        )
        for token in tokens
    }
    rows = tuple(
        _TokenRow(
            token,
            _token_fragments(token, budgets[token]),
            positions[token],
            "exempted"
            if flags.get(token) is True
            else "collision"
            if flags.get(token) is False
            else "unique",
            tuple(exact_lines(positions[token], carrier_widths[token], 24)),
            carrier_widths[token],
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
    legend, key_end = _legend(entries, carried, codes, 280, content_width)
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
        (MARGIN + content_width / 2, COLLISION_SHAPE, COLLISION_LABEL, WARN),
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
            for index, fragment in enumerate(row.carrier_fragments):
                parts.append(
                    text(
                        right - 12 - row.carrier_width,
                        cursor + 22 + index * 25,
                        fragment,
                        24,
                        INK,
                        "700",
                    )
                )
            parts.append("</g></g>")
            cursor += row.height
        bottoms.append(cursor)
    cursor = max(bottoms) + 28
    parts.append(line(MARGIN, cursor, content_right, cursor, RULE, 2))
    cursor += 34
    parts.append(text(MARGIN, cursor, "READING BOUNDARY", 24, ACCENT, "700"))
    cursor += 30
    for paragraph in (
        "Numbers are working positions. Only observed carriers are listed; unread lines remain unknown.",
        "This display compares spellings. It establishes neither conceptual separation nor sibling correctness.",
    ):
        for value in wrap_to_width(paragraph, content_width, 24):
            parts.append(text(MARGIN, cursor, value, 24, INK))
            cursor += 26
        cursor += 8
    return "".join([*open_canvas(canvas_width, cursor + 24), *parts, close_canvas()])


def installation_surface(
    lines: tuple[LineEntry, ...],
    reading: SetReading,
) -> str:
    """Draw exact published values, or explicit unavailability, at fixed size.

    Cards run in working order across each pair, then down the page. Identity
    and status share a band; the four metrics form a two-by-two field group.
    Every band advances from its tallest exact wrapped block. The declaration
    digest retains its documented display prefix.
    """
    verify_coverage()
    entries = _ordered(lines)
    observations = {item.line_id: item for item in reading.observations}
    unread = [
        entry
        for entry in entries
        if entry.id not in observations
        or observations[entry.id].code is not ReadCode.RESOLVED
    ]
    canvas_width = 2000
    content_right = canvas_width - MARGIN
    content_width = content_right - MARGIN
    gap = 12
    card_width = (content_width - gap) / 2
    text_width = card_width - 102
    field_gap = 16
    field_width = (text_width - field_gap) / 2
    parts = [hatch_defs("notread", WARN)]
    parts += header(
        "THE INSTALLATION SURFACE",
        "What this machine could actually read",
        "One card per declared line: whether it resolved and the values its package publishes.",
        f"LIVE READING · {plural(len(entries), 'declared line').upper()} · "
        f"{plural(len(unread), 'line').upper()} NOT READ",
        WARN if unread else ACCENT,
    )
    cursor: float = _TOP
    for start in range(0, len(entries), 2):
        bottoms = []
        for column, entry in enumerate(entries[start : start + 2]):
            left = MARGIN + column * (card_width + gap)
            text_left = left + 82
            observation = observations.get(entry.id)
            code = (
                observation.code if observation is not None else ReadCode.NOT_INSTALLED
            )
            ink = line_ink(entry.color)
            content: list[str] = []
            top = cursor + 30
            drawn, identity_y = text_block(
                text_left, top, entry.color, field_width, 26, ink, "700"
            )
            content.extend(drawn)
            drawn, identity_y = text_block(
                text_left, identity_y, entry.package_name, field_width, 24, MUTED, "700"
            )
            content.extend(drawn)
            drawn, status_y = text_block(
                text_left + field_width + field_gap,
                top,
                code.value,
                field_width,
                24,
                READ_CODE_INK[code],
                "700",
            )
            content.extend(drawn)
            y = max(identity_y, status_y)
            drawn, y = text_block(
                text_left, y, READ_CODE_GLOSS[code], text_width, 24, MUTED
            )
            content.extend(drawn)
            metrics = (
                ("VERSION", observation.version if observation is not None else None),
                (
                    "SIZE",
                    observation.registry_size if observation is not None else None,
                ),
                (
                    "TOKENS",
                    len(observation.tokens)
                    if observation is not None and observation.tokens
                    else None,
                ),
                (
                    "DIGEST",
                    observation.registry_digest[:DIGEST_PREFIX]
                    if observation is not None and observation.registry_digest
                    else None,
                ),
            )
            for offset in (0, 2):
                metric_bottoms = []
                for index, (name, value) in enumerate(metrics[offset : offset + 2]):
                    drawn, bottom = text_block(
                        text_left + index * (field_width + field_gap),
                        y,
                        f"{name} · {value if value is not None else '— not read'}",
                        field_width,
                        26,
                        INK if value is not None else MUTED,
                        "700",
                    )
                    content.extend(drawn)
                    metric_bottoms.append(bottom)
                y = max(metric_bottoms)
            drawn, y = text_block(
                text_left,
                y,
                observation.detail
                if observation is not None and observation.detail
                else "no detail was recorded",
                text_width,
                24,
                MUTED,
            )
            content.extend(drawn)
            row_height = y - cursor + 12
            parts.append(
                rect(left, cursor, card_width, row_height, CARD, ink, 2, rx=10)
            )
            if code is not ReadCode.RESOLVED:
                parts.append(
                    rect(
                        left + 12,
                        cursor + 1,
                        card_width - 13,
                        row_height - 2,
                        "url(#notread)",
                        "none",
                        0,
                    )
                )
            parts.append(rect(left, cursor, 12, row_height, ink, ink, 0))
            parts.append(
                glyph(
                    shape_for(entry.working_position),
                    left + 36,
                    cursor + 30,
                    24,
                    line_fill(entry.color),
                    ink,
                    3,
                )
            )
            parts.append(
                glyph(
                    READ_CODE_SHAPE[code],
                    left + 36,
                    cursor + 84,
                    13,
                    READ_CODE_INK[code] if READ_CODE_SOLID[code] else PAPER,
                    READ_CODE_INK[code],
                    2.5,
                )
            )
            parts.extend(content)
            bottoms.append(cursor + row_height)
        cursor = max(bottoms) + gap
    status_ink = SET_STATUS_INK[reading.status]
    content = []
    drawn, y = text_block(
        MARGIN + 74,
        cursor + 40,
        reading.status.value,
        content_width - 98,
        26,
        status_ink,
        "700",
    )
    content.extend(drawn)
    declare_stage = next(
        (stage for stage in reading.derivation if stage.name == "declare"), None
    )
    values = (
        SET_STATUS_GLOSS[reading.status],
        " · ".join(f"{code.value} {reading.counts()[code.value]}" for code in ReadCode),
        f"declaration digest {reading.set_digest[:DIGEST_PREFIX]}",
        f"undeclared lines: {', '.join(reading.undeclared_lines) or 'none reported'}",
        declare_stage.detail if declare_stage is not None else "no declare stage ran",
    )
    for value in values:
        drawn, y = text_block(MARGIN + 74, y, value, content_width - 98, 24, MUTED)
        content.extend(drawn)
    parts.append(
        rect(
            MARGIN,
            cursor,
            content_width,
            y - cursor + 12,
            PANEL,
            status_ink,
            2.5,
            rx=10,
        )
    )
    parts.append(
        glyph(
            SET_STATUS_SHAPE[reading.status],
            MARGIN + 36,
            cursor + 34,
            22,
            PAPER,
            status_ink,
            3,
        )
    )
    parts.extend(content)
    drawn, y = text_block(
        MARGIN,
        y + 48,
        "A card marked not read is a fact about this machine's installation, not about the line. "
        "Nothing on that card is filled in from memory, a default, or a previous build.",
        content_width,
        24,
        INK,
    )
    parts.extend(drawn)
    return "".join([*open_canvas(canvas_width, int(y + 24)), *parts, close_canvas()])


__all__ = [
    "COLLISION_LABEL",
    "COLLISION_SHAPE",
    "DIGEST_PREFIX",
    "EXEMPT_LABEL",
    "EXEMPT_SHAPE",
    "installation_surface",
    "vocabulary_matrix",
]

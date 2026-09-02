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
EXEMPT_LABEL = "EXEMPT — declared, with one meaning per line"
COLLISION_LABEL = "COLLISION — no declaration covers it"

#: Side of the dark pip drawn inside a carried grid cell.
_PIP = 8

#: Font size of a token label in the grid, in canvas units.
_COLLISION_ROW_HEIGHT = 104
_TOKEN_LABEL_SIZE = 26

#: Distance from a column's left edge to the start of its token labels.
_TOKEN_LABEL_INSET = 22

#: Clear space between the end of the label gutter and a column's cell block.
_TOKEN_CELL_GAP = 26

#: Character-count wrap for a read-code gloss on the installation surface.
_GLOSS_WRAP = 30

#: Worst-case advance, in em, of any character a token label can contain.
#:
#: Tokens are enum member names, so they are ASCII uppercase, digits, and
#: underscores. In the Arial face these plates declare, the widest glyph in
#: that set is ``W`` at 0.9438 em; every other character is narrower. Sizing
#: the label gutter from this bound rather than from the text's measured width
#: is what lets the plate stay byte-reproducible — no primitive in this package
#: opens a font — while still guaranteeing that no label can reach the cells of
#: its own column. The cost is a gutter wider than most labels need.
_WIDEST_TOKEN_GLYPH_EM = 0.9438

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
) -> list[str]:
    """Draw the column key: one chip per declared line, marker plus count."""
    chip_w = _CONTENT_WIDTH / max(len(entries), 1)
    parts: list[str] = []
    for index, entry in enumerate(entries):
        x = MARGIN + index * chip_w
        ink = line_ink(entry.color)
        code = codes.get(entry.id)
        tokens = carried.get(entry.id, frozenset())
        parts.append(rect(x + 4, top, chip_w - 8, 78, CARD, ink, 2, rx=8))
        parts.append(
            glyph(
                shape_for(entry.working_position),
                x + 38,
                top + 30,
                16,
                line_fill(entry.color),
                ink,
                2.5,
            )
        )
        parts.append(text(x + 66, top + 36, entry.color, 26, ink, "700"))
        parts.append(
            text(
                x + 20,
                top + 64,
                plural(len(tokens), "token")
                if tokens
                else f"no vocabulary read · {code.value if code else 'not observed'}",
                26,
                MUTED if tokens else WARN,
                "700",
            )
        )
    return parts


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


def _collision_rows(
    reading: SetReading,
    entries: tuple[LineEntry, ...],
    carried: dict[str, frozenset[str]],
    top: int,
) -> tuple[list[str], int]:
    """Draw the collision band; returns its parts and the y it ends at."""
    parts: list[str] = []
    found = tuple(reading.collisions) + tuple(reading.exempted_collisions)
    parts.append(
        text(
            MARGIN,
            top,
            f"TOKENS CARRIED BY MORE THAN ONE LINE · "
            f"{len(reading.collisions)} undeclared · "
            f"{len(reading.exempted_collisions)} declared",
            26,
            ACCENT,
            "700",
        )
    )
    cursor = top + 20
    if not found:
        parts.append(rect(MARGIN, cursor, _CONTENT_WIDTH, 62, PANEL, RULE, 2, rx=8))
        parts.append(
            text(
                MARGIN + 24,
                cursor + 38,
                "No token in the grid below is carried by two lines.",
                26,
                INK,
                "700",
            )
        )
        return parts, cursor + 62
    for collision in sorted(found, key=lambda item: (not item.exempted, item.token)):
        ink = OCHRE if collision.exempted else WARN
        shape = EXEMPT_SHAPE if collision.exempted else COLLISION_SHAPE
        label = EXEMPT_LABEL if collision.exempted else COLLISION_LABEL
        parts.append(rect(MARGIN, cursor, _CONTENT_WIDTH, 96, PANEL, ink, 2.5, rx=8))
        parts.append(
            glyph(
                shape,
                MARGIN + 34,
                cursor + 37,
                15,
                PAPER if collision.exempted else ink,
                ink,
                3,
            )
        )
        parts.append(text(MARGIN + 62, cursor + 34, collision.token, 28, ink, "700"))
        parts.append(text(MARGIN + 62, cursor + 62, label, 26, ink, "700"))
        cell_x = MARGIN + 640
        for index, entry in enumerate(entries):
            x = cell_x + index * 150
            holds = collision.token in carried.get(entry.id, frozenset())
            parts.append(
                glyph(
                    shape_for(entry.working_position),
                    x,
                    cursor + 30,
                    12,
                    line_fill(entry.color) if holds else PAPER,
                    line_ink(entry.color) if holds else RULE,
                    2.5 if holds else 1.5,
                )
            )
            if holds:
                parts.append(
                    glyph("circle", x, cursor + 30, 4, line_ink(entry.color), "none", 0)
                )
            parts.append(
                text(
                    x,
                    cursor + 78,
                    f"{entry.color} · {'carries' if holds else 'does not'}",
                    26,
                    line_ink(entry.color) if holds else MUTED,
                    "700" if holds else "400",
                    "middle",
                )
            )
        cursor += 104
    return parts, cursor


def vocabulary_matrix(
    lines: tuple[LineEntry, ...],
    reading: SetReading,
) -> str:
    """Draw every token the reader collected against the lines carrying it.

    Tokens run across the top as rotated column labels; the declared lines run
    down the side as rows, so the plate's height does not grow with the size
    of the vocabulary and its width does not grow with the size of the set.
    A filled cell means that line exported that token; an outlined cell means
    it did not. A token carried by more than one line also appears in the band
    below the header, where a declared exemption and an undeclared collision
    are separated by marker shape, by fill, and by the words on the row.
    """
    verify_coverage()
    entries = _ordered(lines)
    carried = _tokens_by_line(reading)
    codes = _codes_by_line(reading)
    legible = sum(1 for entry in entries if carried.get(entry.id))
    tokens = sorted({token for values in carried.values() for token in values})
    if legible < 2 or not tokens:
        return _empty_matrix(entries, codes, legible)

    collision_tokens = {
        collision.token: collision.exempted
        for collision in (*reading.collisions, *reading.exempted_collisions)
    }
    cell = 12
    column_pitch = 12
    # Column labels are drawn rotated 90 degrees, so a label's width on the
    # canvas is its rendered *height*: one label pitch of 12 units per token
    # plus a label lane tall enough for the longest token in the reading,
    # bounded by the widest advance any character may claim. Deriving the lane
    # from a bound rather than measuring rendered text keeps the plate
    # byte-reproducible: no primitive in this package consults a font.
    label_lane = (
        max(len(token) for token in tokens) * (_WIDEST_TOKEN_GLYPH_EM * _TOKEN_LABEL_SIZE)
        + 30
    )
    grid_width = len(tokens) * column_pitch
    height = (
        _TOP
        + 108
        + 8 * _COLLISION_ROW_HEIGHT
        + 62
        + label_lane
        + len(entries) * 56
        + 210
    )
    grid_left = MARGIN + max(
        0, (_CONTENT_WIDTH - grid_width) // 2
    )

    rule_lines = wrap(
        "A grid with no undeclared collision says the declared names do not "
        "overlap. It does not say the lines do not overlap: two lines can spell "
        "nothing alike and still be asking the same question. A declared "
        "exemption records that one spelling carries two different senses; it "
        "is not permission to merge them.",
        140,
    )

    parts = open_canvas(1600, height)
    parts += header(
        "THE VOCABULARY MATRIX",
        "Which line spells which token",
        "Tokens are the enum member names each package exports from its root. "
        "A name defined but not re-exported is not here.",
        f"LIVE READING · {plural(len(tokens), 'token').upper()} ACROSS "
        f"{plural(legible, 'legible line').upper()}",
        ACCENT,
    )
    parts += _legend(entries, carried, codes, _TOP)
    band_top = _TOP + 108
    band_parts, _band_end = _collision_rows(reading, entries, carried, band_top)
    parts += band_parts

    grid_top = band_top + 8 * _COLLISION_ROW_HEIGHT + 62
    parts.append(
        text(
            MARGIN,
            grid_top - 24,
            "THE FULL GRID · filled cell = that line exports that token · "
            "labels read bottom to top",
            26,
            ACCENT,
            "700",
        )
    )
    label_top = grid_top
    rows_top = label_top + label_lane
    # The token columns, labels rotated so the plate stays one page wide.
    for index, token in enumerate(tokens):
        x = grid_left + index * column_pitch + column_pitch / 2
        exempted = collision_tokens.get(token)
        label_ink = INK if exempted is None else (OCHRE if exempted else WARN)
        weight = "400" if exempted is None else "700"
        if exempted is not None:
            parts.append(
                glyph(
                    EXEMPT_SHAPE if exempted else COLLISION_SHAPE,
                    x,
                    label_top + 14,
                    8,
                    PAPER if exempted else label_ink,
                    label_ink,
                    2,
                )
            )
        parts.append(
            f'<text x="{x}" y="{label_top + label_lane - 12}" '
            f'font-family="Arial, sans-serif" font-size="{_TOKEN_LABEL_SIZE}px" '
            f'font-weight="{weight}" fill="{label_ink}" '
            f'text-anchor="start" '
            f'transform="rotate(-90 {x} {label_top + label_lane - 12})">'
            f"{escape_text(token)}</text>"
        )
    # The declared lines as rows down the side.
    for row_index, entry in enumerate(entries):
        y = rows_top + 24 + row_index * 56
        parts.append(
            text(
                MARGIN,
                y + 6,
                f"{entry.color} · {entry.package_name}",
                26,
                line_ink(entry.color),
                "700",
            )
        )
        holds_code = codes.get(entry.id)
        if holds_code is not None:
            parts.append(
                text(MARGIN + 340, y + 6, holds_code.value, 26, MUTED, "700")
            )
        for column_index, token in enumerate(tokens):
            x = grid_left + column_index * column_pitch
            holds = token in carried.get(entry.id, frozenset())
            parts.append(
                rect(
                    x,
                    y - 10,
                    cell,
                    cell,
                    line_fill(entry.color) if holds else PAPER,
                    line_ink(entry.color) if holds else RULE,
                    2 if holds else 1,
                    rx=2,
                )
            )
            if holds:
                # A carried cell also gets a dark pip in the line's ink. The
                # white line's fill is nearly the paper colour, so fill alone
                # would make its row unreadable in greyscale.
                parts.append(
                    rect(
                        x + (cell - _PIP) / 2,
                        y - 10 + (cell - _PIP) / 2,
                        _PIP,
                        _PIP,
                        line_ink(entry.color),
                        line_ink(entry.color),
                        0,
                        rx=1,
                    )
                )

    footer = rows_top + 24 + len(entries) * 56 + 34
    parts.append(line(MARGIN, footer, CONTENT_RIGHT, footer, RULE, 2))
    parts.append(text(MARGIN, footer + 34, "READING RULE", 26, ACCENT, "700"))
    for index, rule in enumerate(rule_lines):
        parts.append(text(MARGIN, footer + 66 + index * 26, rule, 26, INK))
    parts.append(
        text(
            MARGIN,
            footer + 74 + len(rule_lines) * 26,
            "Cells are drawn from this build's reading; a line that was not read "
            "contributes no row content and is marked in the key above.",
            26,
            MUTED,
        )
    )
    parts.append(close_canvas())
    return "".join(parts)
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
        entry.id: wrap(
            observations[entry.id].detail
            if entry.id in observations and observations[entry.id].detail
            else "no detail was recorded",
            168,
        )
        for entry in entries
    }
    heights = [_surface_row_height(len(details[entry.id])) for entry in entries]
    declare_stage = next(
        (stage for stage in reading.derivation if stage.name == "declare"), None
    )
    summary_lines = wrap(
        declare_stage.detail if declare_stage is not None else "no declare stage ran",
        150,
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
                # "REGISTRY ENTRIES" no longer fits one stat block at the
                # legibility floor, and it is the manuscript's own wording that
                # matters here: the number is the registry's size.
                "REGISTRY SIZE",
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
    parts.append(
        text(
            MARGIN,
            cursor + summary_height + 4,
            "A row marked not read is a fact about this machine's installation, "
            "not about the line. Nothing on that row is filled in from memory, "
            "a default, or a previous build.",
            24,
            INK,
        )
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

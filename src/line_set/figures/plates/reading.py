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

import math

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
_TOKEN_LABEL_SIZE = 18

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
        parts.append(text(x + 66, top + 36, entry.color, 20, ink, "700"))
        parts.append(
            text(
                x + 20,
                top + 64,
                plural(len(tokens), "token")
                if tokens
                else f"no vocabulary read · {code.value if code else 'not observed'}",
                18,
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
            22,
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
            18,
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
        parts.append(text(MARGIN + 52, cursor + 25, entry.color, 18, INK, "700"))
        parts.append(
            text(
                MARGIN + 200,
                cursor + 25,
                code.value if code is not None else "not observed",
                18,
                ink,
                "700",
            )
        )
        parts.append(
            text(
                MARGIN + 420,
                cursor + 25,
                READ_CODE_GLOSS[code] if code is not None else "no observation",
                18,
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
            18,
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
            18,
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
                19,
                INK,
                "700",
            )
        )
        return parts, cursor + 62
    for collision in sorted(found, key=lambda item: (not item.exempted, item.token)):
        ink = OCHRE if collision.exempted else WARN
        shape = EXEMPT_SHAPE if collision.exempted else COLLISION_SHAPE
        label = EXEMPT_LABEL if collision.exempted else COLLISION_LABEL
        parts.append(rect(MARGIN, cursor, _CONTENT_WIDTH, 74, PANEL, ink, 2.5, rx=8))
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
        parts.append(text(MARGIN + 62, cursor + 32, collision.token, 21, ink, "700"))
        parts.append(text(MARGIN + 62, cursor + 58, label, 18, ink, "700"))
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
                    cursor + 62,
                    f"{entry.color} · {'carries' if holds else 'does not'}",
                    18,
                    line_ink(entry.color) if holds else MUTED,
                    "700" if holds else "400",
                    "middle",
                )
            )
        cursor += 82
    return parts, cursor


def vocabulary_matrix(
    lines: tuple[LineEntry, ...],
    reading: SetReading,
) -> str:
    """Draw every token the reader collected against the lines carrying it.

    Rows are the tokens in the reading, sorted. A filled cell means that line
    exported that token; an outlined cell means it did not. A token carried by
    two lines also appears in the band above the grid, where a declared
    exemption and an undeclared collision are separated by marker shape, by
    fill, and by the words on the row.
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
    cell = 18
    pitch = 22
    # The label gutter is sized from the longest token actually in this
    # reading, at the worst-case advance any character a token may contain can
    # have, so a label can never reach the cells of its own column. Deriving it
    # from a bound rather than measuring the rendered text keeps the plate
    # byte-reproducible: no primitive in this package consults a font.
    label_room = _TOKEN_LABEL_INSET + max(len(token) for token in tokens) * (
        _WIDEST_TOKEN_GLYPH_EM * _TOKEN_LABEL_SIZE
    )
    # Then take the most columns whose group is still wide enough to hold that
    # gutter plus one cell block. One column always qualifies, because the
    # content width exceeds the widest label a token this long can produce.
    affordable = int(
        _CONTENT_WIDTH // (label_room + _TOKEN_CELL_GAP + pitch * len(entries))
    )
    columns = max(1, min(4, math.ceil(len(tokens) / 26), affordable))
    per_column = math.ceil(len(tokens) / columns)
    group_w = _CONTENT_WIDTH / columns
    # Sit the cells just past the label gutter, not at the far edge of a wide
    # group, so a cell stays next to the token it belongs to.
    cells_offset = min(
        label_room + _TOKEN_CELL_GAP,
        group_w - _TOKEN_CELL_GAP - pitch * len(entries),
    )
    row_h = 24

    legend_top = _TOP
    band_top = legend_top + 108
    band_parts, band_end = _collision_rows(reading, entries, carried, band_top)
    grid_top = band_end + 62
    grid_height = 44 + per_column * row_h
    rule_lines = wrap(
        "A grid with no undeclared collision says the declared names do not "
        "overlap. It does not say the lines do not overlap: two lines can spell "
        "nothing alike and still be asking the same question. A declared "
        "exemption records that one spelling carries two different senses; it "
        "is not permission to merge them.",
        140,
    )
    height = grid_top + grid_height + 140 + 26 * len(rule_lines)

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
    parts += _legend(entries, carried, codes, legend_top)
    parts += band_parts

    parts.append(
        text(
            MARGIN,
            grid_top - 24,
            "THE FULL GRID · filled cell = that line exports that token",
            18,
            ACCENT,
            "700",
        )
    )
    for column in range(columns):
        gx = MARGIN + column * group_w
        cells_x = gx + cells_offset
        for index, entry in enumerate(entries):
            parts.append(
                glyph(
                    shape_for(entry.working_position),
                    cells_x + index * pitch + cell / 2,
                    grid_top + 14,
                    8,
                    line_fill(entry.color),
                    line_ink(entry.color),
                    2,
                )
            )
        chunk = tokens[column * per_column : (column + 1) * per_column]
        for row, token in enumerate(chunk):
            y = grid_top + 34 + row * row_h
            exempted = collision_tokens.get(token)
            if exempted is None:
                label_ink = INK
                weight = "400"
            else:
                label_ink = OCHRE if exempted else WARN
                weight = "700"
                parts.append(
                    glyph(
                        EXEMPT_SHAPE if exempted else COLLISION_SHAPE,
                        gx + 8,
                        y - 5,
                        7,
                        PAPER if exempted else label_ink,
                        label_ink,
                        2,
                    )
                )
            parts.append(
                text(
                    gx + _TOKEN_LABEL_INSET,
                    y,
                    token,
                    _TOKEN_LABEL_SIZE,
                    label_ink,
                    weight,
                )
            )
            for index, entry in enumerate(entries):
                holds = token in carried.get(entry.id, frozenset())
                parts.append(
                    rect(
                        cells_x + index * pitch,
                        y - 13,
                        cell,
                        cell,
                        line_fill(entry.color) if holds else PAPER,
                        line_ink(entry.color) if holds else RULE,
                        2 if holds else 1,
                        rx=3,
                    )
                )
                if holds:
                    # A carried cell also gets a dark pip in the line's ink. The
                    # white line's fill is nearly the paper colour, so fill
                    # alone would make its column unreadable in greyscale.
                    parts.append(
                        rect(
                            cells_x + index * pitch + (cell - _PIP) / 2,
                            y - 13 + (cell - _PIP) / 2,
                            _PIP,
                            _PIP,
                            line_ink(entry.color),
                            line_ink(entry.color),
                            0,
                            rx=1,
                        )
                    )

    footer = grid_top + grid_height + 34
    parts.append(line(MARGIN, footer, CONTENT_RIGHT, footer, RULE, 2))
    parts.append(text(MARGIN, footer + 34, "READING RULE", 18, ACCENT, "700"))
    for index, rule in enumerate(rule_lines):
        parts.append(text(MARGIN, footer + 66 + index * 26, rule, 18, INK))
    parts.append(
        text(
            MARGIN,
            footer + 74 + len(rule_lines) * 26,
            "Cells are drawn from this build's reading; a line that was not read "
            "contributes no column content and is marked in the key above.",
            18,
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
                22,
                line_fill(entry.color),
                ink,
                3,
            )
        )
        parts.append(text(MARGIN + 106, cursor + 40, entry.color, 22, ink, "700"))
        parts.append(
            text(MARGIN + 106, cursor + 68, entry.package_name, 18, MUTED, "700")
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
        parts.append(text(MARGIN + 424, cursor + 40, code.value, 18, code_ink, "700"))
        # Wrapped narrow enough that the widest gloss line stops short of the
        # stat blocks to its right. The room is CONTENT_RIGHT - 20 - four stat
        # blocks - this column's left edge; a wider wrap ran the gloss under
        # the version value.
        for index, gloss in enumerate(wrap(READ_CODE_GLOSS[code], _GLOSS_WRAP)):
            parts.append(text(MARGIN + 424, cursor + 68 + index * 22, gloss, 18, MUTED))
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
            parts.append(text(bx, cursor + 38, label, 18, MUTED, "700"))
            parts.append(
                text(
                    bx,
                    cursor + 66,
                    value,
                    19,
                    INK if value != "—" else MUTED,
                    "700",
                )
            )
            if value == "—":
                parts.append(text(bx, cursor + 88, "not read", 18, code_ink, "700"))
        for index, row in enumerate(details[entry.id]):
            parts.append(text(MARGIN + 106, cursor + 104 + index * 24, row, 18, MUTED))
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
            18,
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
            18,
            INK,
        )
    )
    counts = reading.counts()
    tally = " · ".join(f"{code.value} {counts[code.value]}" for code in ReadCode)
    parts.append(text(MARGIN + 74, cursor + 112, tally, 18, MUTED, "700"))
    parts.append(
        text(
            MARGIN + 74,
            cursor + 144,
            f"declaration digest {reading.set_digest[:DIGEST_PREFIX]} · "
            f"undeclared lines: {', '.join(reading.undeclared_lines) or 'none reported'}",
            18,
            MUTED,
        )
    )
    for index, row in enumerate(summary_lines):
        parts.append(text(MARGIN + 74, cursor + 176 + index * 24, row, 18, MUTED))
    parts.append(
        text(
            MARGIN,
            cursor + summary_height + 4,
            "A row marked not read is a fact about this machine's installation, "
            "not about the line. Nothing on that row is filled in from memory, "
            "a default, or a previous build.",
            18,
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

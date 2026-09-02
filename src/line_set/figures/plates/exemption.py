"""The exemption gate, drawn from what the production matcher actually did.

Every cell on this plate is the return value of
:func:`line_set.reader.exemption_for` over an input
:func:`line_set.probes.exemption_probes` built by weakening a declared
exemption. Nothing is typed in: the token on each row is the declared token as
that probe altered it, the lines are the lines that probe asked about, and the
outcome column is what came back. A matcher that started accepting a looser
input would change this plate rather than leave it standing.

The plate shows detection over the six weakenings the probe set names. It is
not evidence that every looser input is refused, and a refused input is not a
finding about the set — it is a fact about the matcher.
"""

from __future__ import annotations

from ...models import LineEntry, SharedToken
from ...probes import ExemptionProbe, exemption_probes, probes_hold
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
    wrap,
)
from ..palette import ACCENT, CARD, GOOD, INK, MUTED, PANEL, PAPER, RULE, WARN

#: Marker shape and word for a probe the matcher honoured, and for one it
#: refused. The pair differs in shape, in fill, and in the word on the row, so
#: the distinction survives a greyscale print.
HONOURED_SHAPE = "circle"
REFUSED_SHAPE = "square"

#: Character-count wrap for a condition sentence at the card's text size.
_CONDITION_WRAP = 112

_CONTENT_WIDTH = CONTENT_RIGHT - MARGIN
_TOP = 306


def _condition_lines(probe: ExemptionProbe) -> list[str]:
    """Wrap one probe's condition at the width its card allows."""
    return wrap(probe.condition, _CONDITION_WRAP)


def _row_height(probe: ExemptionProbe) -> int:
    """Card height derived from the condition that probe actually carries."""
    return 126 + 24 * len(_condition_lines(probe))


def _empty_gate() -> str:
    """The honest replacement for a gate with nothing to put through it."""
    height = _TOP + 232
    parts = open_canvas(1600, height)
    parts += header(
        "THE EXEMPTION GATE",
        "Nothing could be put through it",
        "The gate weakens a declared exemption and reports what the matcher "
        "does with each weakening. This declaration has none to weaken.",
        "NOT A RESULT · A DEMONSTRATION WITH NOTHING TO DEMONSTRATE ON",
        WARN,
    )
    parts.append(rect(MARGIN, _TOP, _CONTENT_WIDTH, 118, PANEL, WARN, 2.5, rx=10))
    parts.append(
        text(
            MARGIN + 28,
            _TOP + 46,
            "the exemption table is empty, so no probe was run",
            26,
            WARN,
            "700",
        )
    )
    parts.append(
        text(
            MARGIN + 28,
            _TOP + 80,
            "An empty table is refused by the structural battery as well. A gate "
            "that passed here would have passed on nothing.",
            24,
            INK,
        )
    )
    parts.append(close_canvas())
    return "".join(parts)


def exemption_gate(
    lines: tuple[LineEntry, ...],
    shared: tuple[SharedToken, ...],
) -> str:
    """Draw each weakened exemption beside what the matcher returned for it.

    The first row is the positive control — the declaration as written, asked
    for exactly the lines it names — and it must be honoured. The rows below it
    are refusals. Both directions are on the plate because a gate that only
    showed refusals would read the same whether the matcher were careful or
    simply broken.
    """
    probes = exemption_probes(lines, shared)
    if not probes:
        return _empty_gate()

    heights = [_row_height(probe) for probe in probes]
    honoured = sum(1 for probe in probes if probe.matched)
    refused = len(probes) - honoured
    diverged = tuple(probe.name for probe in probes if not probe.holds)
    rule_lines = wrap(
        "A refusal leaves the collision standing, which is the cheap direction: "
        "a missed exemption costs a visible colliding reading that a person "
        "then fixes by writing the declaration properly, while a generous match "
        "costs a guarantee that stopped holding without anyone being told. What "
        "this plate shows is detection over the weakenings named on it, and "
        "nothing about weakenings nobody wrote down.",
        132,
    )
    height = _TOP + sum(item + 20 for item in heights) + 226 + 26 * len(rule_lines)

    parts = open_canvas(1600, height)
    parts += header(
        "THE EXEMPTION GATE",
        "What a declared exemption has to survive",
        "Each row weakens the declaration or the query one way and reports what "
        "the matcher the reader uses returned for it.",
        f"{plural(len(probes), 'probe').upper()} · {honoured} HONOURED · "
        f"{refused} REFUSED · {len(diverged)} DIVERGED FROM SPECIFICATION",
        WARN if diverged else ACCENT,
    )

    cursor = _TOP
    for probe, row_height in zip(probes, heights):
        ink = GOOD if probe.matched else WARN
        shape = HONOURED_SHAPE if probe.matched else REFUSED_SHAPE
        parts.append(
            rect(MARGIN, cursor, _CONTENT_WIDTH, row_height, CARD, ink, 2, rx=10)
        )
        parts.append(rect(MARGIN, cursor, 10, row_height, ink, ink, 0))
        parts.append(
            glyph(
                shape,
                MARGIN + 48,
                cursor + 40,
                16,
                ink if probe.matched else PAPER,
                ink,
                3,
            )
        )
        parts.append(text(MARGIN + 80, cursor + 46, probe.name, 26, INK, "700"))
        parts.append(
            text(
                CONTENT_RIGHT - 20,
                cursor + 40,
                probe.outcome,
                26,
                ink,
                "700",
                "end",
            )
        )
        parts.append(
            text(
                CONTENT_RIGHT - 20,
                cursor + 66,
                "as specified" if probe.holds else "DIVERGED FROM SPECIFICATION",
                24,
                MUTED if probe.holds else WARN,
                "700",
                "end",
            )
        )
        row = cursor + 74
        for entry in _condition_lines(probe):
            parts.append(text(MARGIN + 80, row, entry, 24, MUTED))
            row += 24
        parts.append(
            text(
                MARGIN + 80,
                row + 16,
                f"table: {plural(probe.declarations, 'declaration')} · "
                f"{probe.declared_token} over {', '.join(probe.declared_lines)} "
                f"· {plural(probe.declared_meanings, 'meaning')}",
                24,
                ACCENT,
                "700",
            )
        )
        parts.append(
            text(
                CONTENT_RIGHT - 20,
                row + 16,
                f"asked: {probe.query_token} over {', '.join(probe.query_lines)}",
                24,
                MUTED,
                "700",
                "end",
            )
        )
        cursor += row_height + 20

    summary_ink = WARN if diverged else ACCENT
    parts.append(
        rect(MARGIN, cursor, _CONTENT_WIDTH, 96, PANEL, summary_ink, 2.5, rx=10)
    )
    parts.append(
        text(
            MARGIN + 28,
            cursor + 42,
            "every probe agreed with its specification"
            if probes_hold(probes)
            else f"probes that diverged: {', '.join(diverged)}",
            26,
            GOOD if probes_hold(probes) else WARN,
            "700",
        )
    )
    parts.append(
        text(
            MARGIN + 28,
            cursor + 74,
            f"{plural(honoured, 'probe')} honoured and {refused} refused, all "
            "decided by the matcher the reader calls rather than by a second "
            "copy of its rules.",
            24,
            INK,
        )
    )

    footer = cursor + 132
    parts.append(line(MARGIN, footer, CONTENT_RIGHT, footer, RULE, 2))
    parts.append(text(MARGIN, footer + 34, "READING RULE", 24, ACCENT, "700"))
    for index, row_text in enumerate(rule_lines):
        parts.append(text(MARGIN, footer + 66 + index * 26, row_text, 24, INK))
    parts.append(close_canvas())
    return "".join(parts)


__all__ = ["HONOURED_SHAPE", "REFUSED_SHAPE", "exemption_gate"]

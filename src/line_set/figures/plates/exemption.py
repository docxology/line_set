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
from ...probes import ExemptionProbe, exemption_probes
from ..canvas import (
    CONTENT_RIGHT,
    MARGIN,
    close_canvas,
    glyph,
    header,
    open_canvas,
    rect,
    text,
)
from ..palette import ACCENT, GOOD, INK, MUTED, PANEL, PAPER, WARN

#: Marker shape and word for a probe the matcher honoured, and for one it
#: refused. The pair differs in shape, in fill, and in the word on the row, so
#: the distinction survives a greyscale print.
HONOURED_SHAPE = "circle"
REFUSED_SHAPE = "square"

_CONTENT_WIDTH = CONTENT_RIGHT - MARGIN
_TOP = 306


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
    probes = exemption_probes(lines, shared)
    if not probes:
        return _empty_gate()
    groups: dict[str, list[ExemptionProbe]] = {}
    for probe in probes:
        groups.setdefault(probe.declared_token, []).append(probe)
    columns = max(len(group) for group in groups.values())
    legend = next(iter(groups.values()))
    legend_lines = [f"{index + 1}. {probe.name}" for index, probe in enumerate(legend)]
    legend_top = _TOP + 66 + 64 * len(groups)
    parts = open_canvas(1600, legend_top + 70 + 34 * len(legend_lines) + 100)
    parts += header(
        "THE EXEMPTION GATE",
        "Every declared exemption, every named mutation",
        "Circle: honoured. Square: refused. The word PASS means the observed result matched the specified result.",
        f"{len(groups)} TOKENS · {len(probes)} INPUTS · {sum(not p.holds for p in probes)} DIVERGENCES",
        ACCENT,
    )
    left = MARGIN + 390
    step = (CONTENT_RIGHT - left) / columns
    for index in range(columns):
        parts.append(
            text(
                left + step * (index + 0.5),
                _TOP + 30,
                str(index + 1),
                26,
                INK,
                "700",
                "middle",
            )
        )
    for row, (token, group) in enumerate(sorted(groups.items())):
        y = _TOP + 90 + row * 64
        parts.append(text(MARGIN, y, token, 26, INK, "700"))
        for column, probe in enumerate(group):
            x = left + step * (column + 0.5)
            ink = GOOD if probe.holds else WARN
            parts.append(
                glyph(
                    HONOURED_SHAPE if probe.matched else REFUSED_SHAPE,
                    x - 24,
                    y - 9,
                    9,
                    ink if probe.matched else PAPER,
                    ink,
                    2,
                )
            )
            parts.append(
                text(x + 3, y, "PASS" if probe.holds else "FAIL", 24, ink, "700")
            )
    for index, label in enumerate(legend_lines):
        parts.append(text(MARGIN, legend_top + 52 + index * 34, label, 26, MUTED))
    parts.append(
        text(
            MARGIN,
            legend_top + 90 + 34 * len(legend_lines),
            "Finite mutation evidence only. A refusal leaves the collision unexempted.",
            26,
            INK,
        )
    )
    parts.append(close_canvas())
    return "".join(parts)


__all__ = ["HONOURED_SHAPE", "REFUSED_SHAPE", "exemption_gate"]

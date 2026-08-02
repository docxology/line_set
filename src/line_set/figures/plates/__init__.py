"""Assemble the Line Set plates and their declared provenance.

:func:`figure_plates` is a function rather than a module-level tuple on
purpose. Three of the seven plates are drawn from a live reading, and a reading
means importing sibling packages; building the plate list lazily keeps
``import line_set.figures`` free of that side effect and lets each reading be
computed once and handed to every plate that needs it.

Two readings are taken, not one. ``reading`` is over the declaration, which is
what the vocabulary matrix and the installation surface report on.
``self_reading`` is the reading the self-check itself runs — over the
declaration *with* the wrapper appended — because the wrapper's own row is the
whole subject of the self-application plate, and a plate that recomputed that
comparison from the first reading would be a second implementation of the check
free to disagree with it.

Every caption number below is read from the declaration or from the reading it
describes. None of them is typed in, so a caption cannot drift away from the
plate it sits under.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Callable

from ...invariants import self_disjointness_from_reading
from ...models import LineEntry, ReadCode, SetReading, SharedToken
from ...probes import exemption_probes
from ...reader import READER_STAGES, STATUS_PRECEDENCE
from ..canvas import plural
from .application import self_application
from .declaration import set_compass, two_orders
from .exemption import exemption_gate
from .pipeline import set_reading_pipeline
from .reading import installation_surface, vocabulary_matrix


@dataclass(frozen=True)
class FigurePlate:
    """One generated plate and the provenance declared for it."""

    name: str
    render: Callable[[], str]
    label: str
    caption: str
    alt: str
    source: str


def _legible_count(reading: SetReading) -> int:
    """How many observed lines yielded a vocabulary at all."""
    return sum(1 for observation in reading.observations if observation.tokens)


def _token_count(reading: SetReading) -> int:
    """How many distinct tokens the reading collected across all lines."""
    return len(
        {token for observation in reading.observations for token in observation.tokens}
    )


def figure_plates(
    lines: tuple[LineEntry, ...],
    shared: tuple[SharedToken, ...],
    reading: SetReading,
    wrapper: LineEntry,
    self_reading: SetReading,
) -> tuple[FigurePlate, ...]:
    """Build the plate list for one declaration and the two readings of it.

    ``reading`` covers the declared lines. ``self_reading`` covers the declared
    lines with the wrapper appended, which is what the self-application plate
    and the self-check both read.
    """
    probes = exemption_probes(lines, shared)
    verdict = self_disjointness_from_reading(self_reading, wrapper)
    wrapper_tokens = sum(
        len(observation.tokens)
        for observation in self_reading.observations
        if observation.line_id == wrapper.id
    )
    staged = sum(1 for entry in lines if entry.opus_stage)
    unstaged = len(lines) - staged
    resolved = sum(
        1
        for observation in reading.observations
        if observation.code is ReadCode.RESOLVED
    )
    unread = len(reading.observations) - resolved
    legible = _legible_count(reading)
    tokens = _token_count(reading)
    exempted = tuple(
        sorted(collision.token for collision in reading.exempted_collisions)
    )
    undeclared = tuple(sorted(collision.token for collision in reading.collisions))
    exemptions = tuple(sorted(entry.token for entry in shared))

    return (
        FigurePlate(
            "set_compass",
            partial(set_compass, lines, wrapper),
            "fig:set-compass",
            f"The {plural(len(lines), 'declared line')} in working order, each "
            "card carrying the question that sends you to it, the job it does, "
            "and the thing it must not become. Cards, markers, and the dial's "
            "bearings are all generated from the declaration, so a line added "
            "to it appears here without a change to the builder. The dashed "
            "card below the rule is this package's own entry, drawn there "
            "because it is not a line in the set. A card states what a line is "
            "for; it is not evidence that the line does it, and no card ranks "
            "above another.",
            f"{plural(len(lines), 'card')} in working order, each with a "
            "distinct marker shape, its declared question, job, and "
            "must-not-become, above a dashed card marked as not a line in the "
            "set; a small dial repeats one bearing per line.",
            "line_set.registry.LINE_SET and WRAPPER_LINE",
        ),
        FigurePlate(
            "two_orders",
            partial(two_orders, lines),
            "fig:two-orders",
            "The working order set against the borrowed opus order, with a "
            "connector per line. The two sequences deliberately do not line "
            f"up: {plural(staged, 'entry')} of the declaration "
            f"{'carries' if staged == 1 else 'carry'} an opus stage and "
            f"{unstaged} {'does' if unstaged == 1 else 'do'} not. "
            "Citrinitas is kept as a stage of "
            "its own, so the set does not perform the later collapse of the "
            "yellowing into the reddening. The divergence sentence under the "
            "columns is the live result of the structural check, not a claim "
            "typed into the figure. Stage names are labels; the set borrows no "
            "telos from the opus and ranks nothing.",
            "Two ordered columns joined by crossing connectors, each connector "
            "dashed differently and tipped with its line's marker, above the "
            "live divergence check result and three caveats about what the "
            "borrowed stage names do not mean.",
            "line_set.registry.LINE_SET, models.OPUS_STAGE_ORDER, and "
            "invariants.check_orders_diverge",
        ),
        FigurePlate(
            "vocabulary_matrix",
            partial(vocabulary_matrix, lines, reading),
            "fig:vocabulary-matrix",
            (
                f"Every token this build's reading collected — {plural(tokens, 'token')} "
                f"across {plural(legible, 'legible line')} — against the lines "
                "that export it, with a filled cell for carried and an outlined "
                "cell for not. The band above the grid holds the tokens more "
                f"than one line carries: {len(undeclared)} covered by no "
                f"declaration and {len(exempted)} covered by one"
                + (f" ({', '.join(exempted)})" if exempted else "")
                + f". The declaration records {plural(len(exemptions), 'exemption')}"
                + (f" ({', '.join(exemptions)})" if exemptions else "")
                + ". A declared exemption and an undeclared collision are "
                "separated by marker shape, by fill, and by the words on the "
                "row, so the distinction survives a greyscale print. A grid "
                "with no undeclared collision says the declared names do not "
                "overlap; it does not say the lines do not."
            )
            if legible >= 2
            else (
                f"The matrix could not be drawn: {plural(legible, 'line')} "
                "yielded a vocabulary and two are needed before any overlap can "
                "be found. The plate reports that instead of showing an empty "
                "grid, because a comparison with nothing to compare is not "
                "evidence that the declared vocabularies are disjoint."
            ),
            (
                f"A key of {plural(len(lines), 'line')} with per-line token "
                "counts, a band of multi-line tokens marked by shape and label "
                "as declared or undeclared, and a multi-column grid of token "
                "rows with one filled or outlined cell per line."
            )
            if legible >= 2
            else (
                "A panel stating that fewer than two vocabularies were legible, "
                "listing each declared line with the read code that explains it."
            ),
            "line_set.reader.read_set() over the installed line packages",
        ),
        FigurePlate(
            "set_reading_pipeline",
            set_reading_pipeline,
            "fig:set-reading-pipeline",
            f"The reader's {plural(len(READER_STAGES), 'stage')} — "
            f"{', '.join(READER_STAGES)} — beside the exit ladder of "
            f"{plural(len(STATUS_PRECEDENCE), 'status')} in precedence order. "
            "Both sequences are read from the reader itself, and each stage's "
            "gloss is checked against it before the plate is drawn, so a stage "
            "or status added to the reader fails this build rather than "
            "quietly disappearing from a figure that claims to show all of "
            "them. The ladder is read downward and the first matching "
            "condition wins. The plate draws the contract, not a reading.",
            f"A numbered column of {len(READER_STAGES)} stage boxes with an "
            f"arrow into a ladder of {len(STATUS_PRECEDENCE)} status rungs, "
            "each rung carrying its own marker shape, its condition, and its "
            "gloss, ordered so the first match wins.",
            "line_set.reader.READER_STAGES and STATUS_PRECEDENCE",
        ),
        FigurePlate(
            "installation_surface",
            partial(installation_surface, lines, reading),
            "fig:installation-surface",
            f"What this build's machine could actually read: {resolved} of "
            f"{len(reading.observations)} declared lines resolved and {unread} "
            f"did not, giving the reading {reading.status.value}. A resolved "
            "row reports the version, registry size, token count, and digest "
            "prefix its package published. An unresolved row is hatched, "
            "carries the code that explains it, and shows an em dash in every "
            "metric — nothing is carried over, defaulted, or guessed. The "
            "digest prefix detects disagreement with a digest someone already "
            "holds; it is not tamper evidence, and a row is a fact about this "
            "installation rather than about the line.",
            f"{plural(len(reading.observations), 'row')}, one per declared "
            f"line, each with a marker, a read-code marker and label, and four "
            f"metric blocks; {plural(unread, 'row')} "
            f"{'is' if unread == 1 else 'are'} hatched with every metric "
            "shown as an em dash, above a summary panel holding the set status "
            "and the per-code tally.",
            "line_set.reader.read_set() over the installed line packages",
        ),
        FigurePlate(
            "exemption_gate",
            partial(exemption_gate, lines, shared),
            "fig:exemption-gate",
            (
                "The exemption matcher run over "
                f"{plural(len(probes), 'input')}: "
                "the declaration as written, asked for exactly the lines it "
                f"names, and {len(probes) - 1} weakenings of it. Every outcome "
                "column is what `exemption_for` returned, not a claim typed "
                "into the plate, and the first row is the positive control "
                "without which the refusals below would be equally consistent "
                "with a matcher that refuses everything. A refusal leaves the "
                "collision standing, which is the direction the matcher is "
                "written to fail in. The plate shows detection over these "
                "inputs and says nothing about inputs nobody wrote down."
            )
            if probes
            else (
                "The gate could not be drawn: the exemption table is empty, so "
                "there was no declaration to weaken. That is reported here "
                "rather than shown as a clean sheet, because a demonstration "
                "that ran over no input demonstrated nothing."
            ),
            (
                f"{plural(len(probes), 'row')}, each with a marker and a word "
                "for honoured or refused, the condition it varies, the token "
                "and lines it asked about, and whether the matcher agreed with "
                "the specification, above a summary panel and a reading rule."
            )
            if probes
            else (
                "A panel stating that the exemption table is empty and that no "
                "probe was run."
            ),
            "line_set.probes.exemption_probes() over line_set.reader.exemption_for",
        ),
        FigurePlate(
            "self_application",
            partial(self_application, lines, wrapper, self_reading),
            "fig:self-application",
            (
                "This package's own "
                f"{plural(wrapper_tokens, 'exported enum member name')} "
                f"set against what each of {plural(len(lines), 'declared line')} "
                "publishes, and the live verdict of the self-check underneath. "
                f"The check reports `{verdict.name}` as "
                f"{'holding' if verdict.passed else 'not holding'} here, and "
                "the panel prints its own detail rather than a paraphrase. A "
                "declared exemption cannot rescue the wrapper: it is not a line "
                "and has no standing to share a token with one. A verdict that "
                "holds is a fact about spellings, not evidence that the wrapper "
                "has kept its other boundaries."
            )
            if wrapper_tokens
            else (
                "The comparison could not be made: the wrapper's own vocabulary "
                "was not read from this reading, so there was nothing to compare "
                "from. The plate reports that instead of drawing two columns "
                "that happen not to touch."
            ),
            (
                f"A panel of {plural(wrapper_tokens, 'wrapper token')} in "
                "columns, each marked as shared or not, then one row per "
                "declared line carrying its marker, its token count, and a "
                "shape-and-word statement of whether it shares any spelling, "
                "above a verdict panel and a reading rule."
            )
            if wrapper_tokens
            else (
                "A panel stating that the wrapper's vocabulary could not be "
                "read, listing each declared line with the read code that "
                "explains it."
            ),
            "line_set.invariants.self_disjointness_from_reading() over a "
            "reading of the declaration with the wrapper appended",
        ),
    )


__all__ = ["FigurePlate", "figure_plates"]

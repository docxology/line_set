"""The declaration of the line set.

``LINE_SET`` is the whole declaration: four lines in working order, each with
the question it answers, the job it does, and the thing it must not become.
``SHARED_TOKENS`` is the exemption table — the tokens two lines are allowed to
share, with a distinct meaning recorded per line.

Adding a fifth colour to the set means appending one :class:`LineEntry` here.
The reader, the checks, and the serialization take the declaration as an
argument and do not name any line individually, so nothing else has to change.

The wrapper's own entry, ``WRAPPER_LINE``, is kept out of ``LINE_SET``. It is
not a fifth instrument; it exists so the wrapper's own vocabulary can be put
through the wrapper's own collision check.
"""

from __future__ import annotations

from .models import LineEntry, SharedToken

LINE_SET: tuple[LineEntry, ...] = (
    LineEntry(
        id="red_line",
        color="red",
        question="What must I refuse?",
        job="Security boundary and explicit No document",
        must_not_become="A complete ethics system or an enforcement mechanism",
        opus_stage="rubedo",
        working_position=1,
        package_name="red_line",
        registry_noun="red lines",
        verdict_noun="classification",
    ),
    LineEntry(
        id="black_line",
        color="black",
        question="How do I do strong work?",
        job="Positive wire for concise, rigorous research and engineering",
        must_not_become="Permission to cross Red Line",
        opus_stage="nigredo",
        working_position=2,
        package_name="black_line",
        registry_noun="practices",
        verdict_noun="assessment status",
    ),
    LineEntry(
        id="golden_line",
        color="golden",
        question="What is worth reaching toward?",
        job="Aspirational thread and long-horizon direction",
        must_not_become="A compliance score or proof of virtue",
        opus_stage="citrinitas",
        working_position=3,
        package_name="golden_line",
        registry_noun="aspirations",
        verdict_noun="horizon status",
    ),
    LineEntry(
        id="white_line",
        color="white",
        question="What is absent or unknowable?",
        job=(
            "Epistemic gaps, ethical restraint, omission, silence, and negative space"
        ),
        must_not_become="Evidence that an absent thing is safe or true",
        opus_stage="albedo",
        working_position=4,
        package_name="white_line",
        registry_noun="absence records",
        verdict_noun="absence state",
    ),
)

#: The wrapper's own entry, for self-application only.
#:
#: It is deliberately colourless and carries no opus stage: it names no
#: refusal, method, aspiration, or absence, and it is not a stage of anything.
#: Its ``working_position`` continues the sequence so that appending it to
#: ``LINE_SET`` still yields a contiguous ``1..N``.
WRAPPER_LINE: LineEntry = LineEntry(
    id="line_set",
    color="colourless",
    question="How does a growing set of instruments stay separate?",
    job="Declare the set, read it, check non-overlap, admit new colours",
    must_not_become=(
        "A meta-evaluator, a fifth substantive instrument, a merge of the "
        "four, or a ranking of them"
    ),
    opus_stage=None,
    working_position=len(LINE_SET) + 1,
    package_name="line_set",
    registry_noun="line entries",
    verdict_noun="set status",
)

SHARED_TOKENS: tuple[SharedToken, ...] = (
    SharedToken(
        token="OUTSIDE_SCOPE",
        lines=("red_line", "black_line"),
        meanings=(
            (
                "red_line",
                "a complete, evidenced intake that implicates no red line",
            ),
            (
                "black_line",
                "an attempt outside the discipline's evaluation scope",
            ),
        ),
        rationale=(
            "Both lines needed a name for work their own question does not "
            "reach, and the two senses are not the same sense. Red Line is "
            "saying it looked and found no prohibition; Black Line is saying "
            "it did not look, because the attempt is not the kind of thing "
            "its practices evaluate. The shared spelling is recorded here so "
            "the overlap is a declaration rather than an accident."
        ),
    ),
)


def line_ids(lines: tuple[LineEntry, ...] = LINE_SET) -> tuple[str, ...]:
    """Return the declared line ids in working order."""
    return tuple(entry.id for entry in lines)


def find_line(
    line_id: str, lines: tuple[LineEntry, ...] = LINE_SET
) -> LineEntry | None:
    """Return the entry with ``line_id``, or ``None`` if it is not declared."""
    for entry in lines:
        if entry.id == line_id:
            return entry
    return None

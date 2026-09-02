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
    LineEntry(
        id="silver_line",
        color="silver",
        question="What do I keep, and how does it outlive me?",
        job=(
            "Memory and succession: what is preserved, what is entrusted to "
            "whom, what is allowed to lapse"
        ),
        must_not_become=(
            "An immortality project, an infallible archive, or a guarantee of "
            "persistence"
        ),
        opus_stage=None,
        working_position=5,
        package_name="silver_line",
        registry_noun="keepsakes",
        verdict_noun="succession verdict",
    ),
    LineEntry(
        id="violet_line",
        color="violet",
        question="Who else is affected, and have they agreed?",
        job=(
            "Consent ledger of affected parties per project; absence of "
            "consent recorded, never inferred"
        ),
        must_not_become=(
            "A proxy for anyone's consent or a permission-scraping mechanism"
        ),
        opus_stage=None,
        working_position=6,
        package_name="violet_line",
        registry_noun="consent rules",
        verdict_noun="ledger status",
    ),
    LineEntry(
        id="blue_line",
        color="blue",
        question="What must I keep working?",
        job=(
            "Stewardship of maintained commitments: systems, obligations, "
            "and relationships to past work"
        ),
        must_not_become=(
            "A warranty, SLA, availability guarantee, or proof of maintenance"
        ),
        opus_stage=None,
        working_position=7,
        package_name="blue_line",
        registry_noun="commitments",
        verdict_noun="stewardship status",
    ),
    LineEntry(
        id="green_line",
        color="green",
        question="What is still growing?",
        job=(
            "Capacity under development: apprenticeships, skills deliberately "
            "not yet mastered, with marker/counter-signal staging"
        ),
        must_not_become="A resume, a competence certification, or a virtue signal",
        opus_stage=None,
        working_position=8,
        package_name="green_line",
        registry_noun="growth records",
        verdict_noun="growth status",
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
        lines=("red_line", "black_line", "blue_line", "green_line", "silver_line"),
        meanings=(
            ("red_line", "a complete, evidenced intake that implicates no red line"),
            ("black_line", "an attempt outside the discipline's evaluation scope"),
            ("blue_line", "a submission that names no keepable commitment"),
            ("green_line", "an attempt outside the growth-marker vocabulary"),
            ("silver_line", "a submission outside the succession vocabulary"),
        ),
        rationale=(
            "Five instruments each needed a name for input their own question "
            "does not reach. The sense is parallel but each line says it about "
            "its own intake: a refusal scope, a practice scope, a commitment "
            "scope, a growth scope, and a succession scope are five different "
            "scopes. Violet Line deliberately spells its token OUT_OF_SCOPE "
            "instead, so it is not carried here."
        ),
    ),
    SharedToken(
        token="NEEDS_REWORK",
        lines=("black_line", "green_line", "silver_line"),
        meanings=(
            ("black_line", "an attempt whose declared evidence fails the discipline's checks"),
            ("green_line", "a cultivation attempt whose staged markers do not yet support the claim"),
            ("silver_line", "a keepsake whose declared custody fails the succession checks"),
        ),
        rationale=(
            "Three lines each need a rework verdict, but the material being "
            "reworked differs: a practice attempt, a growth claim, and a "
            "succession declaration. A rework of one is not a rework of the "
            "others, so the shared spelling is declared rather than accidental."
        ),
    ),
    SharedToken(
        token="KEPT",
        lines=("silver_line", "violet_line"),
        meanings=(
            ("silver_line", "declared custody of a keepsake read as adequate at the review date"),
            ("violet_line", "a consent record accepted into the ledger at the review date"),
        ),
        rationale=(
            "Silver Line is about custody of what persists; Violet Line is "
            "about recording what affected parties said. A KEPT keepsake and "
            "a KEPT consent record are different facts about different "
            "objects, and neither implies the other."
        ),
    ),
    SharedToken(
        token="STALE",
        lines=("blue_line", "white_line"),
        meanings=(
            ("blue_line", "a maintained commitment whose declared care signals fall outside the freshness window"),
            ("white_line", "an absence record whose review horizon has lapsed"),
        ),
        rationale=(
            "Blue Line's staleness is about care-signal freshness for living "
            "commitments; White Line's is about the age of a recorded absence "
            "against its own review horizon. Both mark time passed, but over "
            "different objects with different consequences."
        ),
    ),
    SharedToken(
        token="METHOD",
        lines=("black_line", "green_line"),
        meanings=(
            ("black_line", "a family of disciplined practices in the practice registry"),
            ("green_line", "a family of method capacities in the growth-marker vocabulary"),
        ),
        rationale=(
            "Black Line enumerates established practice families; Green Line "
            "enumerates domains where capacity is still growing. The same "
            "family name labels a discipline held in Black Line and a "
            "discipline still being built in Green Line."
        ),
    ),
    SharedToken(
        token="VERIFICATION",
        lines=("black_line", "green_line"),
        meanings=(
            ("black_line", "a family of verification practices in the practice registry"),
            ("green_line", "a family of verification capacities in the growth-marker vocabulary"),
        ),
        rationale=(
            "Same divergence as METHOD: an established verification practice "
            "in Black Line versus verification still under cultivation in "
            "Green Line. Declared here so the shared spelling stays a "
            "declaration."
        ),
    ),
    SharedToken(
        token="COMMUNICATION",
        lines=("black_line", "green_line"),
        meanings=(
            ("black_line", "a family of communication practices in the practice registry"),
            ("green_line", "a family of communication capacities in the growth-marker vocabulary"),
        ),
        rationale=(
            "Same divergence as METHOD and VERIFICATION, for communication: "
            "established practice families in Black Line, domains of "
            "deliberately incomplete capacity in Green Line."
        ),
    ),
    SharedToken(
        token="STEWARDSHIP",
        lines=("black_line", "green_line"),
        meanings=(
            ("black_line", "a family of stewardship practices in the practice registry"),
            ("green_line", "a family of stewardship capacities in the growth-marker vocabulary"),
        ),
        rationale=(
            "Same divergence as the other shared family names: Black Line's "
            "stewardship is a practised discipline, Green Line's is a "
            "capacity still growing. The exemption records the overlap so "
            "the collision check can distinguish declaration from accident."
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

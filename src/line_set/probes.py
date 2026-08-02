"""Deliberately weakened exemptions, put through the production matcher.

The paper claims that :func:`line_set.reader.exemption_for` fails closed: a
truncated token, a case-folded one, a query naming a line the exemption does
not, a declaration naming a line that does not carry the token, a missing
per-line meaning, and two declarations of one token are each refused, and each
refusal leaves the collision unexempted. This module is where that claim is
derived instead of asserted. Every probe is built by weakening a *declared*
exemption rather than by writing a literal, hands the result to the matcher the
reader actually uses, and reports what came back.

Nothing here checks anything. A probe reports detection over the inputs named
below and over nothing else: it is not evidence that no other looser input
would be accepted, it says nothing about whether a declared exemption is
correct, and a probe that matched as intended is not a finding about the set.

Two probes need a line id the shipped exemption does not name.
:func:`spare_line_id` takes one from the declaration when the declaration has a
spare, and otherwise derives a name from an id that is there. Both cases are
recorded on the probe, because "a third line adopted the word" and "no third
line was available so one was named" are different demonstrations.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .models import LineEntry, SharedToken
from .reader import exemption_for

#: Suffix given to a derived line id when the declaration has no spare.
DERIVED_LINE_SUFFIX: str = "_adopter"


@dataclass(frozen=True)
class ExemptionProbe:
    """One input handed to the matcher, and what the matcher did with it.

    ``expected_match`` is the specification — whether this input *should* be
    honoured — and ``matched`` is what :func:`line_set.reader.exemption_for`
    actually returned. The two are kept apart on purpose: a probe holds only
    when they agree, and the figure and the suite both compare them rather than
    reprinting one of them twice.
    """

    name: str
    condition: str
    query_token: str
    query_lines: tuple[str, ...]
    declared_token: str
    declared_lines: tuple[str, ...]
    declared_meanings: int
    declarations: int
    expected_match: bool
    matched: bool

    @property
    def holds(self) -> bool:
        """Whether the matcher did what the specification says it must."""
        return self.matched is self.expected_match

    @property
    def outcome(self) -> str:
        """What this probe left behind, in the reader's own terms."""
        return "exempted" if self.matched else "left unexempted"


def spare_line_id(
    lines: tuple[LineEntry, ...], taken: tuple[str, ...]
) -> tuple[str, bool]:
    """A declared line id outside ``taken``, or one derived from ``taken``.

    Returns the id and whether it came from the declaration. A derived id is
    used only when every declared line already carries the token, which is a
    state the four-line set does not currently reach; it exists so the probe
    set does not silently shrink on a declaration that does.
    """
    for entry in sorted(lines, key=lambda item: item.working_position):
        if entry.id not in taken:
            return entry.id, True
    return f"{sorted(taken)[0]}{DERIVED_LINE_SUFFIX}", False


def _probe(
    name: str,
    condition: str,
    shared: tuple[SharedToken, ...],
    token: str,
    carrying: tuple[str, ...],
    *,
    expected_match: bool,
) -> ExemptionProbe:
    """Run one query against one exemption table and record both sides.

    Both the table and the query are recorded, because three of the probes
    below weaken the declaration while asking the ordinary question and three
    weaken the question while leaving the declaration alone. A row that showed
    only the query would make those two families look identical.
    """
    first = shared[0]
    return ExemptionProbe(
        name=name,
        condition=condition,
        query_token=token,
        query_lines=tuple(carrying),
        declared_token=first.token,
        declared_lines=tuple(first.lines),
        declared_meanings=len(first.meanings),
        declarations=len(shared),
        expected_match=expected_match,
        matched=exemption_for(shared, token, carrying) is not None,
    )


def exemption_probes(
    lines: tuple[LineEntry, ...],
    shared: tuple[SharedToken, ...],
) -> tuple[ExemptionProbe, ...]:
    """Weaken the first declared exemption six ways and report each outcome.

    The first probe is the positive control: the shipped declaration, asked for
    exactly the lines it names, must match. Without it the five refusals below
    would be equally consistent with a matcher that refuses everything, and a
    demonstration that cannot distinguish those two cases demonstrates nothing.

    An empty exemption table yields no probes. The caller is expected to treat
    that as an absence rather than as a clean sheet; every gate in this project
    fails on an empty scan set for the same reason.
    """
    declared = tuple(entry for entry in shared if isinstance(entry, SharedToken))
    if not declared:
        return ()
    entry = declared[0]
    token = entry.token
    carrying = tuple(entry.lines)
    table = (entry,)
    third, from_declaration = spare_line_id(lines, carrying)

    probes = [
        _probe(
            "declared",
            "the exemption as declared, asked for exactly the lines it names",
            table,
            token,
            carrying,
            expected_match=True,
        ),
        _probe(
            "truncated token",
            "a proper prefix of the token; no substring test",
            table,
            token[:-1],
            carrying,
            expected_match=False,
        ),
        _probe(
            "case-folded token",
            "the token in another case; no case folding",
            table,
            token.lower() if token.lower() != token else token.upper(),
            carrying,
            expected_match=False,
        ),
        _probe(
            "a third line carries it"
            if from_declaration
            else "a further line carries it",
            "one more line carries the token than the exemption names; no subset test",
            table,
            token,
            (*carrying, third),
            expected_match=False,
        ),
        _probe(
            "declaration names a line that does not carry it",
            "the exemption names one line more than carries the token; no "
            "superset test",
            (replace(entry, lines=(*carrying, third)),),
            token,
            carrying,
            expected_match=False,
        ),
        _probe(
            "a named line has no meaning",
            "a line is named with no meaning recorded for it",
            (replace(entry, meanings=entry.meanings[:-1]),),
            token,
            carrying,
            expected_match=False,
        ),
        _probe(
            "two declarations of one token",
            "the same token declared twice; an ambiguous exemption exempts nothing",
            (entry, entry),
            token,
            carrying,
            expected_match=False,
        ),
    ]
    return tuple(probes)


def probes_hold(probes: tuple[ExemptionProbe, ...]) -> bool:
    """True when every probe agreed with its specification, and there were some.

    An empty probe set is false. A demonstration of detection that ran over no
    input detected nothing, and reporting it as a pass is the failure mode this
    project refuses everywhere else.
    """
    return bool(probes) and all(probe.holds for probe in probes)


__all__ = [
    "DERIVED_LINE_SUFFIX",
    "ExemptionProbe",
    "exemption_probes",
    "probes_hold",
    "spare_line_id",
]

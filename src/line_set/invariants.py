"""Structural checks over the set declaration, plus one live self-check.

Checks one through seven are pure compute over the declaration: they read
``LINE_SET`` and ``SHARED_TOKENS`` and import nothing. They establish that the
declaration is well formed — ids and colours distinct, positions contiguous,
every exemption disambiguated — and nothing at all about whether the lines
themselves are good instruments.

Check eight is different in kind. It applies this package's own collision
check to a declaration that includes this package, which is the property the
whole project exists to hold: a wrapper that checks other packages for shared
tokens has to survive that check itself. It needs the siblings to be
importable, so it lives outside :func:`all_invariants` and reports honestly
when it cannot be run.

Every check fails on an empty scan set. A check that passes because it had
nothing to look at is not evidence of anything, and the failure detail says so
rather than pretending the set was sound.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date

from .binding import PackageResolver
from .models import OPUS_STAGE_ORDER, LineEntry, SetReading, SharedToken
from .reader import exemption_for, read_set
from .registry import LINE_SET, SHARED_TOKENS, WRAPPER_LINE


@dataclass(frozen=True)
class SoundnessResult:
    """One structural check outcome."""

    name: str
    passed: bool
    detail: str


def _entries(lines: tuple[LineEntry, ...]) -> tuple[LineEntry, ...]:
    """Keep only well-typed entries so a check can report the rest."""
    return tuple(entry for entry in lines if isinstance(entry, LineEntry))


def check_distinct_line_ids(
    lines: tuple[LineEntry, ...] = LINE_SET,
) -> SoundnessResult:
    """Line ids must be distinct; a duplicate makes an observation ambiguous."""
    name = "distinct_line_ids"
    entries = tuple(lines)
    if not entries:
        return SoundnessResult(
            name, False, "the declaration is empty; there is nothing to check"
        )
    malformed = [
        index
        for index, entry in enumerate(entries)
        if not isinstance(entry, LineEntry)
        or not isinstance(entry.id, str)
        or not entry.id.strip()
    ]
    ids = [
        entry.id
        for entry in _entries(entries)
        if isinstance(entry.id, str) and entry.id.strip()
    ]
    duplicates = sorted(value for value, count in Counter(ids).items() if count > 1)
    if malformed:
        return SoundnessResult(
            name, False, f"entries with a missing or invalid id: {malformed}"
        )
    ok = not duplicates
    return SoundnessResult(
        name, ok, "ok" if ok else f"duplicate line ids: {duplicates}"
    )


def check_distinct_colours(
    lines: tuple[LineEntry, ...] = LINE_SET,
) -> SoundnessResult:
    """Colours must be distinct; the colour is how a line is named in prose."""
    name = "distinct_colours"
    entries = tuple(lines)
    if not entries:
        return SoundnessResult(
            name, False, "the declaration is empty; there is nothing to check"
        )
    malformed = [
        index
        for index, entry in enumerate(entries)
        if not isinstance(entry, LineEntry)
        or not isinstance(entry.color, str)
        or not entry.color.strip()
    ]
    if malformed:
        return SoundnessResult(
            name, False, f"entries with a missing or invalid colour: {malformed}"
        )
    colours = [entry.color for entry in _entries(entries)]
    duplicates = sorted(value for value, count in Counter(colours).items() if count > 1)
    ok = not duplicates
    return SoundnessResult(name, ok, "ok" if ok else f"duplicate colours: {duplicates}")


def check_distinct_opus_stages(
    lines: tuple[LineEntry, ...] = LINE_SET,
) -> SoundnessResult:
    """Declared opus stages must be distinct and must be real stage names.

    ``None`` is allowed and ignored: an entry may carry no stage. But a set
    in which no entry carries one has nothing to check, and reports that.
    """
    name = "distinct_opus_stages"
    entries = _entries(tuple(lines))
    if not entries:
        return SoundnessResult(
            name, False, "the declaration is empty; there is nothing to check"
        )
    stages = [entry.opus_stage for entry in entries if entry.opus_stage is not None]
    if not stages:
        return SoundnessResult(
            name,
            False,
            "no entry declares an opus stage; distinctness is unestablished",
        )
    unknown = sorted(
        {
            str(stage)
            for stage in stages
            if not isinstance(stage, str) or stage not in OPUS_STAGE_ORDER
        }
    )
    if unknown:
        return SoundnessResult(
            name, False, f"stages that are not opus stages: {unknown}"
        )
    duplicates = sorted(value for value, count in Counter(stages).items() if count > 1)
    ok = not duplicates
    return SoundnessResult(
        name, ok, "ok" if ok else f"duplicate opus stages: {duplicates}"
    )


def check_contiguous_working_positions(
    lines: tuple[LineEntry, ...] = LINE_SET,
) -> SoundnessResult:
    """Working positions must be exactly ``1..N``: no gaps, no duplicates."""
    name = "contiguous_working_positions"
    entries = tuple(lines)
    if not entries:
        return SoundnessResult(
            name, False, "the declaration is empty; there is nothing to check"
        )
    positions: list[int] = []
    malformed: list[int] = []
    for index, entry in enumerate(entries):
        position = getattr(entry, "working_position", None)
        if (
            not isinstance(entry, LineEntry)
            or isinstance(position, bool)
            or not isinstance(position, int)
        ):
            malformed.append(index)
        else:
            positions.append(position)
    if malformed:
        return SoundnessResult(
            name,
            False,
            f"entries with a missing or non-integer position: {malformed}",
        )
    expected = list(range(1, len(entries) + 1))
    ok = sorted(positions) == expected
    return SoundnessResult(
        name,
        ok,
        "ok"
        if ok
        else f"positions {sorted(positions)} are not the contiguous {expected}",
    )


def check_orders_diverge(
    lines: tuple[LineEntry, ...] = LINE_SET,
) -> SoundnessResult:
    """Working order and opus order must not be the same order.

    The divergence is deliberate. The working order is chosen for how the
    instruments actually support the work; the opus order is a borrowed set of
    stage names. If the two ever coincided, the set would read as a
    re-enactment of the opus, which it is not and does not claim to be. This
    check pins the difference so the claim stays true by construction.
    """
    name = "orders_diverge"
    entries = _entries(tuple(lines))
    if not entries:
        return SoundnessResult(
            name, False, "the declaration is empty; there is nothing to check"
        )
    staged = [
        entry
        for entry in entries
        if isinstance(entry.opus_stage, str)
        and entry.opus_stage in OPUS_STAGE_ORDER
        and isinstance(entry.working_position, int)
        and not isinstance(entry.working_position, bool)
    ]
    if len(staged) < 2:
        return SoundnessResult(
            name,
            False,
            "fewer than two entries carry both an opus stage and a working "
            "position; divergence is unestablished",
        )
    by_work = tuple(
        entry.id for entry in sorted(staged, key=lambda entry: entry.working_position)
    )
    by_opus = tuple(
        entry.id
        for entry in sorted(
            staged, key=lambda entry: OPUS_STAGE_ORDER.index(entry.opus_stage)
        )
    )
    ok = by_work != by_opus
    return SoundnessResult(
        name,
        ok,
        f"working order {list(by_work)} differs from opus order {list(by_opus)}"
        if ok
        else f"working order and opus order are identical: {list(by_work)}",
    )


def check_must_not_become_declared(
    lines: tuple[LineEntry, ...] = LINE_SET,
) -> SoundnessResult:
    """Every entry must say what it must not become.

    A line that has not written down the thing it would drift into has no
    stated boundary, and the set's separation is exactly those boundaries.
    """
    name = "must_not_become_declared"
    entries = tuple(lines)
    if not entries:
        return SoundnessResult(
            name, False, "the declaration is empty; there is nothing to check"
        )
    missing = [
        entry.id
        if isinstance(entry, LineEntry) and isinstance(entry.id, str)
        else f"index {index}"
        for index, entry in enumerate(entries)
        if not isinstance(entry, LineEntry)
        or not isinstance(entry.must_not_become, str)
        or not entry.must_not_become.strip()
    ]
    ok = not missing
    return SoundnessResult(
        name,
        ok,
        "ok" if ok else f"entries with no declared must-not-become: {missing}",
    )


def check_shared_tokens_disambiguated(
    lines: tuple[LineEntry, ...] = LINE_SET,
    shared: tuple[SharedToken, ...] = SHARED_TOKENS,
) -> SoundnessResult:
    """Every declared exemption must be one the live matcher would honour.

    The check calls :func:`line_set.reader.exemption_for` rather than
    re-deriving its rules, so it binds to the matcher the reader actually uses
    instead of to a second copy that could drift away from it.

    An empty exemption table fails. That is the uncomfortable direction, and
    it is chosen deliberately: an exemption table that is empty because none
    is needed and one that is empty because it was accidentally cleared look
    the same from here, and only one of them is fine. A set with genuinely no
    shared tokens should say so somewhere a person reads, not by leaving the
    table blank.
    """
    name = "shared_tokens_disambiguated"
    entries = _entries(tuple(lines))
    tokens = tuple(shared)
    if not entries:
        return SoundnessResult(
            name, False, "the declaration is empty; there is nothing to check"
        )
    if not tokens:
        return SoundnessResult(
            name,
            False,
            "no shared tokens are declared; an empty exemption table is not "
            "evidence that no exemption is needed",
        )
    known = {entry.id for entry in entries}
    problems: list[str] = []
    for index, token in enumerate(tokens):
        if not isinstance(token, SharedToken):
            problems.append(f"index {index}: not a SharedToken")
            continue
        label = token.token if isinstance(token.token, str) else f"index {index}"
        try:
            declared_lines = tuple(token.lines)
        except TypeError:
            problems.append(f"{label}: lines is not iterable")
            continue
        if exemption_for(tokens, token.token, declared_lines) is not token:
            problems.append(
                f"{label}: the live matcher would not honour this exemption"
            )
            continue
        unknown = sorted(set(declared_lines) - known)
        if unknown:
            problems.append(f"{label}: names undeclared lines {unknown}")
        if not isinstance(token.rationale, str) or not token.rationale.strip():
            problems.append(f"{label}: no rationale is recorded")
    ok = not problems
    return SoundnessResult(name, ok, "ok" if ok else f"unusable exemptions: {problems}")


def self_disjointness_from_reading(
    reading: SetReading,
    wrapper: LineEntry = WRAPPER_LINE,
) -> SoundnessResult:
    """Decide self-disjointness from a reading that already includes the wrapper.

    The judgement is pure: it imports nothing and reads only what the reading
    holds. It is separated from :func:`check_self_disjointness` so that a plate
    drawing this property draws the same verdict the check reports, rather than
    a second implementation of the same four conditions that could drift away
    from it while both stayed passing.

    Four things are refused, and the order matters because each later one
    presupposes the earlier:

    * the wrapper's own vocabulary could not be read, so there is nothing to
      compare *from*;
    * no other line supplied a vocabulary, so there is nothing to compare
      *against* — an overlap check over an empty comparison set found no
      overlap for the uninteresting reason;
    * a wrapper token turned up in a collision, exempted or not;
    * some line could not be read, so disjointness holds for a subset and is
      unestablished for the set.
    """
    name = "self_disjointness"
    by_id = {observation.line_id: observation for observation in reading.observations}
    wrapper_observation = by_id.get(wrapper.id)
    if wrapper_observation is None or not wrapper_observation.tokens:
        detail = (
            wrapper_observation.detail
            if wrapper_observation is not None
            else "the wrapper entry produced no observation"
        )
        return SoundnessResult(
            name,
            False,
            f"the wrapper's own vocabulary could not be read ({detail}); "
            "disjointness is unestablished",
        )

    compared = sorted(
        observation.line_id
        for observation in reading.observations
        if observation.line_id != wrapper.id and observation.tokens
    )
    unread = sorted(
        observation.line_id
        for observation in reading.observations
        if observation.line_id != wrapper.id and not observation.tokens
    )
    if not compared:
        return SoundnessResult(
            name,
            False,
            "no line vocabulary was available to compare against, so the "
            f"comparison set was empty; unread lines: {unread}",
        )

    hits = sorted(
        collision.token
        for collision in (*reading.collisions, *reading.exempted_collisions)
        if wrapper.id in collision.lines
    )
    if hits:
        return SoundnessResult(
            name,
            False,
            f"the wrapper's own tokens collide with a line's vocabulary: {hits}",
        )
    if unread:
        return SoundnessResult(
            name,
            False,
            f"disjointness holds against {compared}, but {unread} could not be "
            "read, so it is unestablished for the whole set",
        )
    return SoundnessResult(
        name,
        True,
        f"the wrapper's {len(wrapper_observation.tokens)} tokens are disjoint "
        f"from every token declared by {compared}",
    )


def check_self_disjointness(
    lines: tuple[LineEntry, ...] = LINE_SET,
    shared: tuple[SharedToken, ...] = SHARED_TOKENS,
    *,
    wrapper: LineEntry = WRAPPER_LINE,
    resolver: PackageResolver | None = None,
    as_of: str | date | None = None,
) -> SoundnessResult:
    """Apply this package's collision check to a set that includes it.

    This is the project's signature property and the reason the reading
    statuses are ``SET_``-prefixed. The check appends the wrapper's own entry
    to the declaration, runs the ordinary reader over the result, and asks
    whether any token of the wrapper turned up in any collision.

    A declared exemption does not help here. The wrapper is not a line and has
    no standing to share a token with one, so an exempted collision involving
    the wrapper counts against it exactly like an unexempted one.

    The check needs the siblings importable. When they are not, it reports
    ``passed=False`` with a detail naming what could not be read. It never
    passes on an empty comparison set: an overlap check against nothing found
    no overlap for the uninteresting reason.
    """
    reading = read_set(
        tuple(lines) + (wrapper,), shared, resolver=resolver, as_of=as_of
    )
    return self_disjointness_from_reading(reading, wrapper)


_LINE_CHECKS = (
    check_distinct_line_ids,
    check_distinct_colours,
    check_distinct_opus_stages,
    check_contiguous_working_positions,
    check_orders_diverge,
    check_must_not_become_declared,
)


def all_invariants(
    lines: tuple[LineEntry, ...] = LINE_SET,
    shared: tuple[SharedToken, ...] = SHARED_TOKENS,
) -> tuple[SoundnessResult, ...]:
    """Run every offline structural check over the declaration.

    Offline is the point: this battery imports no sibling and passes or fails
    identically whether or not any line package is installed. Self-disjointness
    is not in it, because it cannot be answered without reading the lines; call
    :func:`live_invariants` for that.
    """
    results = [check(lines) for check in _LINE_CHECKS]
    results.append(check_shared_tokens_disambiguated(lines, shared))
    return tuple(results)


def live_invariants(
    lines: tuple[LineEntry, ...] = LINE_SET,
    shared: tuple[SharedToken, ...] = SHARED_TOKENS,
    *,
    resolver: PackageResolver | None = None,
    as_of: str | date | None = None,
) -> tuple[SoundnessResult, ...]:
    """The offline battery plus the self-disjointness check.

    This is the full battery, and it can only pass where the sibling packages
    are importable.
    """
    return (
        *all_invariants(lines, shared),
        check_self_disjointness(lines, shared, resolver=resolver, as_of=as_of),
    )


def registry_sound(
    lines: tuple[LineEntry, ...] = LINE_SET,
    shared: tuple[SharedToken, ...] = SHARED_TOKENS,
) -> bool:
    """True iff every offline structural check passes on the declaration."""
    return all(result.passed for result in all_invariants(lines, shared))

"""Read the declared set and check that no two lines share a status token.

The reader is staged so that a reading can be checked rather than trusted.
Each stage records what it did into the returned ``derivation``: which
packages resolved, what was bound from each, which tokens were carried by
more than one line, which resolved packages were not declared, and how the
status followed from those four facts.

What a reading establishes is narrow. ``SET_LEGIBLE`` says the declared
vocabularies of the lines that could be read did not overlap. It does not say
the lines are correct, complete, consistent, or worth having, and it says
nothing about behaviour: two lines can have entirely disjoint vocabularies and
still overlap conceptually. The reader reads declarations.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from . import binding
from .binding import PackageResolver, candidate_packages, read_vocabulary
from .models import (
    DerivationStage,
    LineEntry,
    LineObservation,
    ReadCode,
    SetReading,
    SetStatus,
    SharedToken,
    TokenCollision,
)
from .registry import LINE_SET, SHARED_TOKENS
from .serialization import registry_digest

#: The reader's stages, in the order they run.
READER_STAGES: tuple[str, ...] = (
    "resolve",
    "bind",
    "collide",
    "declare",
    "status",
)

#: Status precedence, strongest finding first.
#:
#: An unexempted collision outranks everything, because it is the one finding
#: that says the set's contract stopped holding. An undeclared line outranks a
#: partial read, because a line nobody declared is a gap in the declaration
#: rather than a gap in the installation.
STATUS_PRECEDENCE: tuple[SetStatus, ...] = (
    SetStatus.SET_COLLIDING,
    SetStatus.SET_UNDECLARED,
    SetStatus.SET_PARTIAL,
    SetStatus.SET_LEGIBLE,
)


def _review_date(as_of: str | date | None) -> date:
    """Resolve the review date; a string must be a valid ISO date."""
    if as_of is None:
        return date.today()
    if isinstance(as_of, str):
        return date.fromisoformat(as_of)
    if isinstance(as_of, date):
        return as_of
    raise TypeError("as_of must be an ISO date string, a date, or None")


def exemption_for(
    shared: Iterable[SharedToken],
    token: str,
    carrying: Iterable[str],
) -> SharedToken | None:
    """Return the declared exemption for ``token`` over exactly ``carrying``.

    This matcher is the only thing standing between a declared exemption and
    the set's non-overlap guarantee, so it is written so that a too-generous
    match is impossible rather than unlikely. Each condition is an exact
    match, and each failure returns ``None``, which leaves the collision
    unexempted:

    * The token must be equal. No case folding, no normalization, no prefix
      or substring test. A matcher that accepted ``OUTSIDE`` for
      ``OUTSIDE_SCOPE`` would exempt collisions nobody ever declared.
    * The exemption's line set must *equal* the set of lines actually
      carrying the token. A subset test would let an exemption written for
      two lines quietly cover a third line that later adopted the token. A
      superset test would let an exemption naming lines that do not carry the
      token stand in for one that does.
    * Every named line must have a non-blank meaning, and the meanings must
      name no line outside the exemption. An exemption without a per-line
      meaning is a label, not a disambiguation, and a label cannot show that
      two uses of one spelling are actually two different things.
    * Exactly one declared exemption may match the token. Two declarations
      for one token is an ambiguity, and an ambiguous exemption exempts
      nothing.

    Failing closed is the cheap direction. A missed exemption costs a visible
    ``SET_COLLIDING`` reading that a person then fixes by writing the
    declaration properly. A generous match costs a guarantee that stopped
    holding without anyone being told.
    """
    if not isinstance(token, str) or not token:
        return None
    carried = frozenset(str(line_id) for line_id in carrying)
    if len(carried) < 2:
        return None

    matches = [
        entry
        for entry in shared
        if isinstance(entry, SharedToken)
        and isinstance(entry.token, str)
        and entry.token == token
    ]
    if len(matches) != 1:
        return None
    entry = matches[0]

    try:
        declared_lines = tuple(entry.lines)
    except TypeError:
        return None
    if any(
        not isinstance(line_id, str) or not line_id.strip()
        for line_id in declared_lines
    ):
        return None
    if len(set(declared_lines)) != len(declared_lines):
        return None
    if len(declared_lines) < 2:
        return None
    if frozenset(declared_lines) != carried:
        return None

    try:
        pairs = tuple(entry.meanings)
    except TypeError:
        return None
    seen: set[str] = set()
    for pair in pairs:
        if not isinstance(pair, tuple) or len(pair) != 2:
            return None
        line_id, meaning = pair
        if not isinstance(line_id, str) or not isinstance(meaning, str):
            return None
        if not meaning.strip():
            return None
        if line_id in seen:
            return None
        seen.add(line_id)
    # Set equality here rejects both an exemption that omits a meaning for a
    # line it names and one that supplies a meaning for a line it does not.
    if seen != set(declared_lines):
        return None
    return entry


def _observe(entry: LineEntry, resolver: PackageResolver) -> LineObservation:
    """Run the resolve and bind stages for one declared line.

    A resolver that reports ``RESOLVED`` while handing back no module has
    broken its own contract, and the reading is downgraded to
    ``IMPORT_FAILED`` rather than accepted. Keeping the reported code would
    put a line with no vocabulary into the resolved set, where it counts as
    read, contributes no token to the collision scan, and cannot make the
    reading partial — a set of such lines would read ``SET_LEGIBLE`` on the
    strength of having compared nothing. Refusing costs a visible failure with
    the reason attached; accepting costs the contract silently.
    """
    resolution = resolver(entry.package_name)
    if resolution.code is ReadCode.RESOLVED and resolution.module is None:
        return LineObservation(
            line_id=entry.id,
            code=ReadCode.IMPORT_FAILED,
            detail=(
                "the resolver reported this package as resolved but supplied "
                f"no module, so nothing could be read from it: {resolution.detail}"
            ),
        )
    if resolution.code is not ReadCode.RESOLVED:
        return LineObservation(
            line_id=entry.id,
            code=resolution.code,
            detail=resolution.detail,
        )
    # The guards above ensure a RESOLVED reading carries a module: the resolver
    # that reports RESOLVED without one was already downgraded to IMPORT_FAILED.
    assert resolution.module is not None
    vocabulary = read_vocabulary(resolution.module)
    code = ReadCode.RESOLVED if vocabulary.tokens else ReadCode.NO_VOCABULARY
    return LineObservation(
        line_id=entry.id,
        code=code,
        version=vocabulary.version,
        registry_size=vocabulary.registry_size,
        registry_digest=vocabulary.registry_digest,
        tokens=vocabulary.tokens,
        detail=vocabulary.detail,
    )


def _collide(
    observations: tuple[LineObservation, ...],
    shared: tuple[SharedToken, ...],
) -> tuple[tuple[TokenCollision, ...], tuple[TokenCollision, ...]]:
    """Partition cross-line token collisions into exempted and not."""
    carriers: dict[str, set[str]] = {}
    for observation in observations:
        for token in observation.tokens:
            carriers.setdefault(token, set()).add(observation.line_id)

    unexempted: list[TokenCollision] = []
    exempted: list[TokenCollision] = []
    for token in sorted(carriers):
        lines = tuple(sorted(carriers[token]))
        if len(lines) < 2:
            continue
        declared = exemption_for(shared, token, lines)
        if declared is None:
            unexempted.append(TokenCollision(token=token, lines=lines, exempted=False))
        else:
            exempted.append(
                TokenCollision(
                    token=token,
                    lines=lines,
                    exempted=True,
                    rationale=declared.rationale,
                )
            )
    return tuple(unexempted), tuple(exempted)


def read_set(
    lines: tuple[LineEntry, ...] = LINE_SET,
    shared: tuple[SharedToken, ...] = SHARED_TOKENS,
    *,
    resolver: PackageResolver | None = None,
    as_of: str | date | None = None,
) -> SetReading:
    """Read every declared line and report whether the set stayed separate.

    ``resolver`` is the injection point. It is any callable taking a package
    name and returning a :class:`~line_set.binding.Resolution`; a resolver
    that also offers a ``candidates()`` method additionally lets the declare
    stage look for line packages nobody declared. Passing a plain callable is
    how a test exercises an absent, failing, or extra package without any
    mocking framework.

    The collision scan covers the declared lines. A package discovered but
    not declared is reported in ``undeclared_lines``; its vocabulary is not
    folded into the scan, because the finding to act on is that it is
    undeclared, not what it happens to spell.
    """
    resolver = binding.default_resolver if resolver is None else resolver
    line_list = tuple(lines)
    shared_list = tuple(shared)
    read_as_of = _review_date(as_of).isoformat()

    observations = tuple(_observe(entry, resolver) for entry in line_list)
    resolve_stage = DerivationStage(
        name="resolve",
        detail=(
            f"asked the resolver for {len(line_list)} declared "
            f"{'package' if len(line_list) == 1 else 'packages'}"
        ),
        items=tuple(
            sorted(
                f"{observation.line_id}={observation.code.value}"
                for observation in observations
            )
        ),
    )
    bind_stage = DerivationStage(
        name="bind",
        detail=(
            "read version, registry size, digest, and enum member names from "
            "each package that resolved"
        ),
        items=tuple(
            sorted(
                f"{observation.line_id}: {len(observation.tokens)} tokens, "
                f"version={observation.version}, "
                f"registry_size={observation.registry_size}"
                for observation in observations
            )
        ),
    )

    unexempted, exempted = _collide(observations, shared_list)
    collide_stage = DerivationStage(
        name="collide",
        detail=(
            f"{len(unexempted)} unexempted and {len(exempted)} exempted "
            "cross-line token collisions"
        ),
        items=tuple(
            sorted(
                f"{collision.token} over "
                f"{','.join(sorted(collision.lines))} "
                f"({'exempted' if collision.exempted else 'unexempted'})"
                for collision in (*unexempted, *exempted)
            )
        ),
    )

    declared_packages = {entry.package_name for entry in line_list}
    found = candidate_packages(resolver)
    if found is None:
        undeclared: tuple[str, ...] = ()
        declare_detail = (
            "the resolver cannot enumerate installed packages, so undeclared "
            "lines were not scanned for"
        )
    else:
        undeclared = tuple(
            sorted(
                name
                for name in found
                if name not in declared_packages
                and resolver(name).code is ReadCode.RESOLVED
            )
        )
        declare_detail = (
            f"scanned {len(found)} candidate "
            f"{'package' if len(found) == 1 else 'packages'} and found "
            f"{len(undeclared)} that resolved but were not declared"
        )
    declare_stage = DerivationStage(
        name="declare", detail=declare_detail, items=undeclared
    )

    unread = tuple(
        sorted(
            observation.line_id
            for observation in observations
            if observation.code is not ReadCode.RESOLVED
        )
    )
    if unexempted:
        status = SetStatus.SET_COLLIDING
        reason = (
            f"{len(unexempted)} cross-line token collision(s) are not "
            "covered by a declared exemption"
        )
    elif undeclared:
        status = SetStatus.SET_UNDECLARED
        reason = f"{len(undeclared)} resolved package(s) are not in the declaration"
    elif unread:
        status = SetStatus.SET_PARTIAL
        reason = f"{len(unread)} declared line(s) could not be read: {list(unread)}"
    else:
        status = SetStatus.SET_LEGIBLE
        reason = (
            f"all {len(line_list)} declared line(s) were read and their "
            "vocabularies do not overlap"
        )
    status_stage = DerivationStage(
        name="status",
        detail=f"{status.value}: {reason}",
        items=tuple(candidate.value for candidate in STATUS_PRECEDENCE),
    )

    return SetReading(
        status=status,
        observations=observations,
        collisions=unexempted,
        exempted_collisions=exempted,
        undeclared_lines=undeclared,
        set_digest=registry_digest(line_list, shared_list),
        read_as_of=read_as_of,
        derivation=(
            resolve_stage,
            bind_stage,
            collide_stage,
            declare_stage,
            status_stage,
        ),
    )

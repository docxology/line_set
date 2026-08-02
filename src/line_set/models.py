"""Types for the line set's declaration and for one reading of it.

This module declares structure only. Nothing here imports a sibling package,
and no type in it carries a judgement about whether a line is correct,
complete, useful, or worth having. A ``SetReading`` records what the declared
vocabularies were and whether any two of them overlapped; that is the whole
claim, and it is a claim about names, not about behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

#: The classical stages of the alchemical *magnum opus*, in opus order.
#:
#: The set borrows these stage names as labels and nothing else. The order is
#: recorded here so the deliberate divergence between working order and opus
#: order can be checked rather than asserted (see
#: :func:`line_set.invariants.check_orders_diverge`). Citrinitas is kept as a
#: stage of its own and is deliberately not collapsed into rubedo.
OPUS_STAGE_ORDER: tuple[str, ...] = ("nigredo", "albedo", "citrinitas", "rubedo")


class SetStatus(str, Enum):
    """The four outcomes of reading the set.

    Every member name is ``SET_``-prefixed on purpose. This package checks
    that no two lines share a status token, which means the package's own
    tokens have to survive that same check. The prefix is what makes that
    disjointness checkable rather than merely hoped for; the check itself is
    :func:`line_set.invariants.check_self_disjointness`.

    ``SET_LEGIBLE`` means the declared vocabularies did not overlap. It does
    not mean the lines are correct, complete, consistent, or good.
    """

    SET_LEGIBLE = "set_legible"
    SET_PARTIAL = "set_partial"
    SET_COLLIDING = "set_colliding"
    SET_UNDECLARED = "set_undeclared"


class ReadCode(str, Enum):
    """Why one declared line did or did not yield a vocabulary.

    ``NOT_INSTALLED`` and ``IMPORT_FAILED`` are ordinary outcomes, not errors
    to be raised. A line that cannot be read produces no version, no registry
    size, and no digest; those fields stay ``None`` rather than being filled
    with a placeholder.
    """

    RESOLVED = "resolved"
    NOT_INSTALLED = "not_installed"
    IMPORT_FAILED = "import_failed"
    NO_VOCABULARY = "no_vocabulary"


@dataclass(frozen=True)
class LineEntry:
    """One declared line in the set.

    ``id`` is the set-level identity of the line and ``package_name`` is what
    the reader asks the import system for. They coincide today; they are kept
    apart because a line's identity in the declaration should not depend on
    how its code happens to be distributed.

    ``registry_noun`` and ``verdict_noun`` are prose labels for what the line
    keeps and what it emits. They exist for figures and manuscript text; the
    reader never uses them to find anything.
    """

    id: str
    color: str
    question: str
    job: str
    must_not_become: str
    opus_stage: str | None
    working_position: int
    package_name: str
    registry_noun: str
    verdict_noun: str

    def canonical(self) -> dict[str, object]:
        """Order-independent mapping for serialization."""
        return {
            "id": self.id,
            "color": self.color,
            "question": self.question,
            "job": self.job,
            "must_not_become": self.must_not_become,
            "opus_stage": self.opus_stage,
            "working_position": self.working_position,
            "package_name": self.package_name,
            "registry_noun": self.registry_noun,
            "verdict_noun": self.verdict_noun,
        }


@dataclass(frozen=True)
class SharedToken:
    """A deliberately shared token, with a distinct meaning per line.

    ``lines`` names every line that is allowed to carry ``token``, and
    ``meanings`` must supply a non-blank meaning for each of them. A shared
    token without a per-line meaning is a label, not a disambiguation, and
    :func:`line_set.reader.exemption_for` refuses to honour it.
    """

    token: str
    lines: tuple[str, ...]
    meanings: tuple[tuple[str, str], ...]
    rationale: str

    def meaning_for(self, line_id: str) -> str | None:
        """Return the declared meaning for ``line_id``, or ``None``."""
        for declared_id, meaning in self.meanings:
            if declared_id == line_id:
                return meaning
        return None

    def covered_lines(self) -> frozenset[str]:
        """Line ids that carry a non-blank declared meaning."""
        return frozenset(
            declared_id
            for declared_id, meaning in self.meanings
            if isinstance(declared_id, str)
            and isinstance(meaning, str)
            and meaning.strip()
        )

    def canonical(self) -> dict[str, object]:
        """Order-independent mapping for serialization."""
        return {
            "token": self.token,
            "lines": sorted(self.lines),
            "meanings": [
                [declared_id, meaning] for declared_id, meaning in sorted(self.meanings)
            ],
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class LineObservation:
    """What was actually read from one declared line.

    ``tokens`` are enum member names exported from the package root, sorted.
    ``version``, ``registry_size``, and ``registry_digest`` are ``None``
    whenever they could not be read; nothing in this package invents them.
    """

    line_id: str
    code: ReadCode
    version: str | None = None
    registry_size: int | None = None
    registry_digest: str | None = None
    tokens: tuple[str, ...] = ()
    detail: str = ""

    def canonical(self) -> dict[str, object]:
        """Order-independent mapping for serialization."""
        return {
            "line_id": self.line_id,
            "code": self.code.value,
            "version": self.version,
            "registry_size": self.registry_size,
            "registry_digest": self.registry_digest,
            "tokens": sorted(self.tokens),
            "detail": self.detail,
        }


@dataclass(frozen=True)
class TokenCollision:
    """One token carried by more than one line.

    ``exempted`` is true only when a declared :class:`SharedToken` matched the
    token over exactly the lines that carry it, with a meaning for each. An
    unexempted collision is what makes a reading ``SET_COLLIDING``.
    """

    token: str
    lines: tuple[str, ...]
    exempted: bool
    rationale: str = ""

    def canonical(self) -> dict[str, object]:
        """Order-independent mapping for serialization."""
        return {
            "token": self.token,
            "lines": sorted(self.lines),
            "exempted": self.exempted,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class DerivationStage:
    """One recorded stage of a reading.

    The reader is staged so that a reading can be re-read rather than
    trusted. ``items`` holds the stage's own sorted output; ``detail`` is a
    sentence a person can check against it.
    """

    name: str
    detail: str
    items: tuple[str, ...] = ()

    def canonical(self) -> dict[str, object]:
        """Order-independent mapping for serialization."""
        return {
            "name": self.name,
            "detail": self.detail,
            "items": list(self.items),
        }


@dataclass(frozen=True)
class SetReading:
    """One dated reading of the declared set.

    ``set_digest`` identifies the declaration that was read, not the reading.
    ``read_as_of`` is the review date. ``derivation`` records every stage in
    the order the reader ran them.
    """

    status: SetStatus
    observations: tuple[LineObservation, ...]
    collisions: tuple[TokenCollision, ...]
    exempted_collisions: tuple[TokenCollision, ...]
    undeclared_lines: tuple[str, ...]
    set_digest: str
    read_as_of: str
    derivation: tuple[DerivationStage, ...] = ()

    def counts(self) -> dict[str, int]:
        """Tally observations per read code; a summary, not a score."""
        tally = {code.value: 0 for code in ReadCode}
        for observation in self.observations:
            tally[observation.code.value] += 1
        return tally

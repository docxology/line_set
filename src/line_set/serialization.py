"""Deterministic serialization for the set declaration and for a reading.

The digests here are review and drift-detection instruments. Two people, or
two revisions, can compare a short hex string to see whether they are reading
the same declaration or the same reading. A digest carries no safety,
warranty, or attestation semantics: it detects disagreement with a digest
someone already has, and it is not tamper evidence.

Every collection is sorted before it is written, so no ``dict`` or ``set``
iteration order can reach a digest.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date

from .models import LineEntry, SetReading, SharedToken
from .admission import DeclarationError, admit_declaration
from .binding import valid_source_revision


def _admit_shared(shared: tuple[SharedToken, ...]) -> None:
    identities = [item.token for item in shared if isinstance(item, SharedToken)]
    if (
        len(identities) != len(shared)
        or any(not isinstance(t, str) or not t.strip() for t in identities)
        or len(set(identities)) != len(identities)
    ):
        raise DeclarationError(
            "declaration has invalid or duplicate exemption identities"
        )
    for item in shared:
        if (
            not isinstance(item.lines, tuple)
            or any(not isinstance(name, str) for name in item.lines)
            or not isinstance(item.meanings, tuple)
            or any(
                not isinstance(pair, tuple)
                or len(pair) != 2
                or any(not isinstance(value, str) for value in pair)
                for pair in item.meanings
            )
            or not isinstance(item.rationale, str)
        ):
            raise DeclarationError("declaration has malformed exemption fields")


def canonical_registry(
    lines: tuple[LineEntry, ...],
    shared: tuple[SharedToken, ...] = (),
) -> str:
    """Order-independent canonical JSON for the whole declaration.

    The exemption table is part of the declaration, not an annex to it: a set
    whose shared tokens changed is a different set even if its lines did not.
    Both parts are therefore serialized together, and ``shared`` defaults to
    empty only so a caller can digest the lines alone when that is what it
    means to compare.
    """
    admit_declaration(lines)
    _admit_shared(shared)
    payload = {
        "schema_version": "line-set-declaration/2",
        "lines": [
            entry.canonical() for entry in sorted(lines, key=lambda entry: entry.id)
        ],
        "shared_tokens": [
            token.canonical() for token in sorted(shared, key=lambda token: token.token)
        ],
    }
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def registry_digest(
    lines: tuple[LineEntry, ...],
    shared: tuple[SharedToken, ...] = (),
) -> str:
    """SHA-256 of the canonical declaration; a drift-review handle only."""
    return hashlib.sha256(canonical_registry(lines, shared).encode("utf-8")).hexdigest()


def canonical_reading(reading: SetReading) -> str:
    """Order-independent canonical JSON for one reading of the set.

    The derivation is kept in stage order because the stages are a sequence,
    not a set: their order is part of what the reading says.
    """
    validate_reading(reading)
    payload = {
        "schema_version": "line-set-reading/2",
        "discovery": reading.discovery.canonical(),
        "exemptions": [
            item.canonical()
            for item in sorted(reading.exemptions, key=lambda item: item.token)
        ],
        "status": reading.status.value,
        "observations": [
            observation.canonical()
            for observation in sorted(
                reading.observations,
                key=lambda observation: observation.line_id,
            )
        ],
        "collisions": [
            collision.canonical()
            for collision in sorted(
                reading.collisions, key=lambda collision: collision.token
            )
        ],
        "exempted_collisions": [
            collision.canonical()
            for collision in sorted(
                reading.exempted_collisions,
                key=lambda collision: collision.token,
            )
        ],
        "undeclared_lines": sorted(reading.undeclared_lines),
        "counts": reading.counts(),
        "set_digest": reading.set_digest,
        "read_as_of": reading.read_as_of,
        "derivation": [stage.canonical() for stage in reading.derivation],
    }
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def reading_digest(reading: SetReading) -> str:
    """SHA-256 of the canonical reading, for comparing readings."""
    return hashlib.sha256(canonical_reading(reading).encode("utf-8")).hexdigest()


def validate_reading(reading: SetReading) -> None:
    from .reader import _collide
    from .models import ReadCode, SetStatus

    date.fromisoformat(reading.read_as_of)
    _admit_shared(reading.exemptions)
    if any(
        type(value) is not bool
        for collision in reading.collisions + reading.exempted_collisions
        for value in (collision.exempted, collision.fully_observed)
    ):
        raise ValueError("collision flags must be booleans")
    discovery = reading.discovery
    if any(
        type(value) is not bool
        for value in (discovery.capable, discovery.attempted, discovery.completed)
    ):
        raise ValueError("discovery flags must be booleans")
    if discovery.diagnostics and (discovery.completed or not discovery.attempted):
        raise ValueError("discovery failure requires an incomplete recorded attempt")
    if discovery.completed and (not discovery.capable or not discovery.attempted):
        raise ValueError("completed discovery requires capability and an attempt")
    if discovery.capable and not discovery.attempted:
        raise ValueError("capable discovery has no recorded attempt")
    names = discovery.candidates
    if names and not discovery.capable:
        raise ValueError("discovery candidates require enumeration capability")
    if any(
        not isinstance(name, str) or not name.isidentifier() for name in names
    ) or len(set(names)) != len(names):
        raise ValueError("discovery has invalid or duplicate candidate identities")
    outcome_names = [item.package_name for item in discovery.outcomes]
    if len(set(outcome_names)) != len(outcome_names) or not set(outcome_names).issubset(
        names
    ):
        raise ValueError("discovery outcomes have duplicate or unlisted identities")
    declared_packages = {
        item.provenance.requested_package for item in reading.observations
    }
    if set(outcome_names) != set(names) - declared_packages:
        raise ValueError("discovery outcomes do not cover every undeclared candidate")
    if any(
        item.code
        not in (ReadCode.RESOLVED, ReadCode.NOT_INSTALLED, ReadCode.IMPORT_FAILED)
        for item in discovery.outcomes
    ):
        raise ValueError("discovery outcome is not a resolution code")
    found = sorted(
        item.package_name
        for item in discovery.outcomes
        if item.code is ReadCode.RESOLVED
    )
    if sorted(reading.undeclared_lines) != found:
        raise ValueError("undeclared lines disagree with discovery outcomes")
    for item in reading.observations:
        if any(
            value is not None and (not isinstance(value, str) or not value.strip())
            for value in (item.version, item.registry_digest)
        ) or (
            item.registry_size is not None
            and (type(item.registry_size) is not int or item.registry_size < 0)
        ):
            raise ValueError("reading has malformed package metadata")
        revision = item.provenance.source_revision
        if revision is not None and not valid_source_revision(revision):
            raise ValueError("reading provenance has an invalid source revision")
        if (
            not isinstance(item.code, ReadCode)
            or not isinstance(item.tokens, tuple)
            or any(not isinstance(token, str) or not token for token in item.tokens)
            or len(set(item.tokens)) != len(item.tokens)
        ):
            raise ValueError("reading has malformed vocabulary or read code")
        if (item.code is ReadCode.RESOLVED) != bool(item.tokens):
            raise ValueError("reading code disagrees with vocabulary availability")
        if item.code in (ReadCode.IMPORT_FAILED, ReadCode.NOT_INSTALLED) and any(
            value is not None
            for value in (item.version, item.registry_size, item.registry_digest)
        ):
            raise ValueError("unread package has invented metadata")

    ids = [item.line_id for item in reading.observations]
    if (
        not ids
        or any(not isinstance(name, str) or not name.strip() for name in ids)
        or len(set(ids)) != len(ids)
    ):
        raise ValueError("reading has empty, blank or duplicate observation identities")
    collisions, exempted = _collide(reading.observations, reading.exemptions)

    def ordered(items):
        return sorted(
            (item.canonical() for item in items), key=lambda item: item["token"]
        )

    if ordered(collisions) != ordered(reading.collisions) or ordered(
        exempted
    ) != ordered(reading.exempted_collisions):
        raise ValueError(
            "reading collision facts disagree with observed tokens and exemptions"
        )
    status = (
        SetStatus.SET_COLLIDING
        if collisions
        else SetStatus.SET_UNDECLARED
        if reading.undeclared_lines
        else SetStatus.SET_PARTIAL
        if any(
            item.code is not ReadCode.RESOLVED or not item.tokens
            for item in reading.observations
        )
        else SetStatus.SET_LEGIBLE
    )
    if reading.status is not status:
        raise ValueError("reading status disagrees with its observations")


def reading_from_canonical(text: str) -> SetReading:
    from .models import (
        BindingProvenance,
        CandidateOutcome,
        Diagnostic,
        Discovery,
        DerivationStage,
        LineObservation,
        ReadCode,
        SetStatus,
        TokenCollision,
    )

    try:
        payload = json.loads(text)
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != "line-set-reading/2"
        ):
            raise ValueError(
                "unsupported reading schema; historical schemas require a fresh reading"
            )

        def diagnostics(items):
            return tuple(Diagnostic(**item) for item in items)

        def observation(item):
            return LineObservation(
                **dict(
                    item,
                    code=ReadCode(item["code"]),
                    tokens=tuple(item["tokens"]),
                    provenance=BindingProvenance(**item["provenance"]),
                    diagnostics=diagnostics(item["diagnostics"]),
                )
            )

        def collision(item):
            return TokenCollision(
                **dict(
                    item,
                    lines=tuple(item["lines"]),
                    meanings=tuple(tuple(pair) for pair in item["meanings"]),
                    declared_carriers=tuple(item["declared_carriers"]),
                    unread_declared_carriers=tuple(item["unread_declared_carriers"]),
                )
            )

        discovery = payload["discovery"]
        reading = SetReading(
            status=SetStatus(payload["status"]),
            observations=tuple(observation(item) for item in payload["observations"]),
            collisions=tuple(collision(item) for item in payload["collisions"]),
            exempted_collisions=tuple(
                collision(item) for item in payload["exempted_collisions"]
            ),
            undeclared_lines=tuple(payload["undeclared_lines"]),
            set_digest=payload["set_digest"],
            read_as_of=payload["read_as_of"],
            derivation=tuple(
                DerivationStage(**dict(item, items=tuple(item["items"])))
                for item in payload["derivation"]
            ),
            discovery=Discovery(
                **dict(
                    discovery,
                    candidates=tuple(discovery["candidates"]),
                    outcomes=tuple(
                        CandidateOutcome(
                            item["package_name"],
                            ReadCode(item["code"]),
                            diagnostics(item["diagnostics"]),
                        )
                        for item in discovery["outcomes"]
                    ),
                    diagnostics=diagnostics(discovery["diagnostics"]),
                )
            ),
            exemptions=tuple(
                SharedToken(
                    **dict(
                        item,
                        lines=tuple(item["lines"]),
                        meanings=tuple(tuple(pair) for pair in item["meanings"]),
                    )
                )
                for item in payload["exemptions"]
            ),
        )
        validate_reading(reading)
        if canonical_reading(reading) != json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ):
            raise ValueError(
                "reading fields or derived counts disagree with canonical schema"
            )
        return reading
    except (TypeError, KeyError, AttributeError) as exc:
        raise ValueError(
            f"malformed reading record: {type(exc).__name__}: {exc}"
        ) from exc

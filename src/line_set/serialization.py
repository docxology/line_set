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

from .models import LineEntry, SetReading, SharedToken


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
    payload = {
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
    payload = {
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

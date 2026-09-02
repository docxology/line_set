"""Canonical form and digests: stable under reordering, sensitive to content.

A digest is only a review handle if two people who wrote the same declaration
get the same string and two people who wrote different declarations do not. The
first half is shown by reordering the inputs; the second is shown by walking
every declared field, changing it, and requiring the digest to move. A field
that a canonical form forgets is a field a digest cannot notice, so the walk is
driven by ``dataclasses.fields`` rather than by a list kept alongside it.

None of this is tamper evidence. It detects disagreement with a digest someone
already holds, which is all it is used for here.
"""

from __future__ import annotations

import dataclasses
import json

from line_set import (
    LINE_SET,
    SHARED_TOKENS,
    LineEntry,
    SetStatus,
    SharedToken,
    canonical_reading,
    canonical_registry,
    read_set,
    reading_digest,
    registry_digest,
)
from tests.support import absent, canned_resolver


def _mutate(value: object) -> object:
    """Return something a canonical form must serialize differently."""
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, str):
        return f"{value} (changed)"
    if isinstance(value, tuple):
        return (*value, value[-1]) if value else ("changed",)
    return "changed from nothing"


def test_canonical_registry_is_stable_under_input_reordering() -> None:
    forwards = canonical_registry(LINE_SET, SHARED_TOKENS)
    backwards = canonical_registry(
        tuple(reversed(LINE_SET)), tuple(reversed(SHARED_TOKENS))
    )
    assert forwards == backwards
    assert registry_digest(LINE_SET, SHARED_TOKENS) == registry_digest(
        tuple(reversed(LINE_SET)), tuple(reversed(SHARED_TOKENS))
    )


def test_canonical_registry_sorts_lines_and_exemptions_by_identity() -> None:
    payload = json.loads(canonical_registry(LINE_SET, SHARED_TOKENS))
    assert set(payload) == {"lines", "shared_tokens"}
    assert [item["id"] for item in payload["lines"]] == sorted(
        entry.id for entry in LINE_SET
    )
    assert [item["token"] for item in payload["shared_tokens"]] == sorted(
        token.token for token in SHARED_TOKENS
    )
    first = payload["shared_tokens"][0]
    declared = next(
        token for token in SHARED_TOKENS if token.token == first["token"]
    )
    assert first["lines"] == sorted(declared.lines)
    assert first["meanings"] == [list(pair) for pair in sorted(declared.meanings)]


def test_canonical_registry_is_already_in_its_own_canonical_form() -> None:
    """Re-serializing what was parsed must reproduce the text byte for byte."""
    text = canonical_registry(LINE_SET, SHARED_TOKENS)
    assert (
        json.dumps(
            json.loads(text),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        == text
    )


def test_the_exemption_table_is_part_of_the_declaration() -> None:
    """A set whose shared tokens changed is a different set."""
    assert registry_digest(LINE_SET, SHARED_TOKENS) != registry_digest(LINE_SET, ())


def test_registry_digest_is_a_sha256_hex_string() -> None:
    digest = registry_digest(LINE_SET, SHARED_TOKENS)
    assert len(digest) == 64
    assert set(digest) <= set("0123456789abcdef")


def test_changing_any_line_field_changes_the_digest() -> None:
    baseline = registry_digest(LINE_SET, SHARED_TOKENS)
    for field in dataclasses.fields(LineEntry):
        planted = LINE_SET[:-1] + (
            dataclasses.replace(
                LINE_SET[-1], **{field.name: _mutate(getattr(LINE_SET[-1], field.name))}
            ),
        )
        assert registry_digest(planted, SHARED_TOKENS) != baseline, field.name


def test_changing_any_exemption_field_changes_the_digest() -> None:
    baseline = registry_digest(LINE_SET, SHARED_TOKENS)
    for field in dataclasses.fields(SharedToken):
        original = SHARED_TOKENS[-1]
        planted = SHARED_TOKENS[:-1] + (
            dataclasses.replace(
                original, **{field.name: _mutate(getattr(original, field.name))}
            ),
        )
        assert registry_digest(LINE_SET, planted) != baseline, field.name


def test_adding_or_removing_a_line_changes_the_digest() -> None:
    baseline = registry_digest(LINE_SET, SHARED_TOKENS)
    assert registry_digest(LINE_SET[:-1], SHARED_TOKENS) != baseline
    extra = dataclasses.replace(
        LINE_SET[-1],
        id="chartreuse_line",
        color="chartreuse",
        working_position=len(LINE_SET) + 1,
    )
    assert registry_digest(LINE_SET + (extra,), SHARED_TOKENS) != baseline


def _reading(as_of: str = "2026-07-27"):
    """A reading that needs no package installed anywhere."""
    return read_set(
        LINE_SET,
        SHARED_TOKENS,
        resolver=canned_resolver(
            {entry.package_name: absent(entry.package_name) for entry in LINE_SET}
        ),
        as_of=as_of,
    )


def test_canonical_reading_is_deterministic_for_the_same_reading() -> None:
    first = _reading()
    second = _reading()
    assert canonical_reading(first) == canonical_reading(second)
    assert reading_digest(first) == reading_digest(second)


def test_canonical_reading_records_every_part_of_the_reading() -> None:
    reading = _reading()
    payload = json.loads(canonical_reading(reading))
    assert set(payload) == {
        "status",
        "observations",
        "collisions",
        "exempted_collisions",
        "undeclared_lines",
        "counts",
        "set_digest",
        "read_as_of",
        "derivation",
    }
    assert payload["status"] == SetStatus.SET_PARTIAL.value
    assert payload["set_digest"] == registry_digest(LINE_SET, SHARED_TOKENS)
    assert payload["read_as_of"] == "2026-07-27"
    assert [item["line_id"] for item in payload["observations"]] == sorted(
        entry.id for entry in LINE_SET
    )


def test_the_derivation_keeps_stage_order_rather_than_being_sorted() -> None:
    """The stages are a sequence; their order is part of what the reading says."""
    reading = _reading()
    payload = json.loads(canonical_reading(reading))
    recorded = [stage["name"] for stage in payload["derivation"]]
    assert recorded == [stage.name for stage in reading.derivation]
    assert recorded != sorted(recorded)


def test_the_reading_digest_moves_when_the_reading_does() -> None:
    baseline = reading_digest(_reading())
    assert reading_digest(_reading(as_of="2026-07-28")) != baseline
    other_declaration = read_set(
        LINE_SET[:-1],
        SHARED_TOKENS,
        resolver=canned_resolver(
            {entry.package_name: absent(entry.package_name) for entry in LINE_SET}
        ),
        as_of="2026-07-27",
    )
    assert reading_digest(other_declaration) != baseline


def test_canonical_registry_digests_lines_alone_when_asked() -> None:
    lines_only = canonical_registry(LINE_SET)
    assert json.loads(lines_only)["shared_tokens"] == []
    assert registry_digest(LINE_SET) == registry_digest(LINE_SET, ())

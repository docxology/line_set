"""The declaration and reading types: shape, immutability, canonical form.

These types carry no judgement, so there is little behaviour to test. What
there is matters: the canonical mappings feed every digest, so a field that a
mapping forgets is a field a digest cannot notice changing.
"""

from __future__ import annotations

import dataclasses

import pytest

from line_set import (
    OPUS_STAGE_ORDER,
    DerivationStage,
    LineEntry,
    LineObservation,
    ReadCode,
    SetReading,
    SetStatus,
    SharedToken,
    TokenCollision,
)
from line_set.registry import LINE_SET

CANONICAL_TYPES = (
    LineEntry,
    SharedToken,
    LineObservation,
    TokenCollision,
    DerivationStage,
)


def test_set_status_members_are_all_set_prefixed() -> None:
    """The prefix is what makes the wrapper's own tokens checkably separate."""
    assert SetStatus
    for member in SetStatus:
        assert member.name.startswith("SET_"), member.name
        assert member.value == member.name.lower()


def test_read_codes_are_lowercase_values_of_their_names() -> None:
    assert ReadCode
    for member in ReadCode:
        assert member.value == member.name.lower()


def test_status_and_code_vocabularies_do_not_overlap() -> None:
    """Two enums in one package must not spell the same thing twice."""
    assert not {member.name for member in SetStatus} & {
        member.name for member in ReadCode
    }


def test_opus_stage_order_is_four_distinct_stages_keeping_citrinitas() -> None:
    assert len(OPUS_STAGE_ORDER) == len(set(OPUS_STAGE_ORDER))
    assert "citrinitas" in OPUS_STAGE_ORDER
    assert OPUS_STAGE_ORDER.index("citrinitas") < OPUS_STAGE_ORDER.index("rubedo")


@pytest.mark.parametrize("model", CANONICAL_TYPES)
def test_canonical_mapping_covers_every_declared_field(model: type) -> None:
    """No field may be invisible to serialization, and so to a digest."""
    instance = _sample(model)
    assert set(instance.canonical()) == {
        field.name for field in dataclasses.fields(model)
    }


@pytest.mark.parametrize("model", CANONICAL_TYPES)
def test_models_are_frozen(model: type) -> None:
    instance = _sample(model)
    field = dataclasses.fields(model)[0].name
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(instance, field, "rewritten")


def _sample(model: type) -> object:
    """A minimal well-formed instance of each canonical type."""
    if model is LineEntry:
        return LINE_SET[0]
    if model is SharedToken:
        return SharedToken(
            token="TOKEN",
            lines=("one", "two"),
            meanings=(("one", "first sense"), ("two", "second sense")),
            rationale="two senses, one spelling",
        )
    if model is LineObservation:
        return LineObservation(line_id="one", code=ReadCode.RESOLVED)
    if model is TokenCollision:
        return TokenCollision(token="TOKEN", lines=("one", "two"), exempted=False)
    return DerivationStage(name="resolve", detail="asked", items=("one",))


def test_line_entry_canonical_matches_its_own_fields() -> None:
    entry = LINE_SET[0]
    canonical = entry.canonical()
    for field in dataclasses.fields(LineEntry):
        assert canonical[field.name] == getattr(entry, field.name)


def test_shared_token_meaning_for_hit_and_miss() -> None:
    token = _sample(SharedToken)
    assert token.meaning_for("one") == "first sense"
    assert token.meaning_for("absent-line") is None


def test_covered_lines_ignores_blank_and_non_string_meanings() -> None:
    """A blank meaning is a label, not a disambiguation, and does not count."""
    token = SharedToken(
        token="TOKEN",
        lines=("one", "two", "three", "four"),
        meanings=(
            ("one", "a real sense"),
            ("two", "   "),
            ("three", 7),
            (8, "a sense for a line with no name"),
        ),
        rationale="planted",
    )
    assert token.covered_lines() == frozenset({"one"})


def test_shared_token_canonical_is_order_independent() -> None:
    first = SharedToken(
        token="TOKEN",
        lines=("two", "one"),
        meanings=(("two", "second"), ("one", "first")),
        rationale="same content",
    )
    second = SharedToken(
        token="TOKEN",
        lines=("one", "two"),
        meanings=(("one", "first"), ("two", "second")),
        rationale="same content",
    )
    assert first.canonical() == second.canonical()


def test_unresolved_observation_defaults_to_no_measurements() -> None:
    """A line that could not be read reports nothing, not a placeholder."""
    observation = LineObservation(line_id="one", code=ReadCode.NOT_INSTALLED)
    assert observation.version is None
    assert observation.registry_size is None
    assert observation.registry_digest is None
    assert observation.tokens == ()
    canonical = observation.canonical()
    assert canonical["version"] is None
    assert canonical["registry_size"] is None
    assert canonical["registry_digest"] is None
    assert canonical["code"] == ReadCode.NOT_INSTALLED.value


def test_observation_canonical_sorts_tokens() -> None:
    observation = LineObservation(
        line_id="one", code=ReadCode.RESOLVED, tokens=("Z", "A")
    )
    assert observation.canonical()["tokens"] == ["A", "Z"]


def test_collision_and_stage_canonical_forms() -> None:
    collision = TokenCollision(
        token="TOKEN", lines=("two", "one"), exempted=True, rationale="declared"
    )
    assert collision.canonical()["lines"] == ["one", "two"]
    assert collision.canonical()["exempted"] is True
    stage = DerivationStage(name="collide", detail="one finding", items=("b", "a"))
    assert stage.canonical()["items"] == ["b", "a"]


def test_reading_counts_tally_every_code_including_the_unseen() -> None:
    reading = SetReading(
        status=SetStatus.SET_PARTIAL,
        observations=(
            LineObservation("one", ReadCode.RESOLVED, tokens=("A",)),
            LineObservation("two", ReadCode.NOT_INSTALLED),
            LineObservation("three", ReadCode.NOT_INSTALLED),
        ),
        collisions=(),
        exempted_collisions=(),
        undeclared_lines=(),
        set_digest="",
        read_as_of="2026-07-27",
    )
    counts = reading.counts()
    assert set(counts) == {member.value for member in ReadCode}
    assert counts[ReadCode.RESOLVED.value] == 1
    assert counts[ReadCode.NOT_INSTALLED.value] == 2
    assert counts[ReadCode.IMPORT_FAILED.value] == 0
    assert sum(counts.values()) == len(reading.observations)

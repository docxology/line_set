"""The declaration itself: distinct lines, contiguous order, one exemption.

Nothing here is asserted against a copied constant. Every expectation is
derived from the declaration or from the opus stage list, so appending a line
changes what these tests check rather than breaking them.
"""

from __future__ import annotations

import dataclasses

from line_set import (
    LINE_SET,
    OPUS_STAGE_ORDER,
    SHARED_TOKENS,
    WRAPPER_LINE,
    LineEntry,
    SharedToken,
    check_contiguous_working_positions,
    find_line,
    line_ids,
)

TEXT_FIELDS = tuple(
    field.name
    for field in dataclasses.fields(LineEntry)
    if field.name not in {"opus_stage", "working_position"}
)


def test_every_entry_is_a_line_entry_with_a_distinct_identity() -> None:
    assert LINE_SET
    assert all(isinstance(entry, LineEntry) for entry in LINE_SET)
    assert len(set(line_ids())) == len(LINE_SET)
    assert len({entry.color for entry in LINE_SET}) == len(LINE_SET)
    assert len({entry.package_name for entry in LINE_SET}) == len(LINE_SET)


def test_every_text_field_is_non_blank() -> None:
    for entry in LINE_SET:
        for name in TEXT_FIELDS:
            value = getattr(entry, name)
            assert isinstance(value, str) and value.strip(), (entry.id, name)


def test_working_positions_are_the_contiguous_sequence() -> None:
    assert sorted(entry.working_position for entry in LINE_SET) == list(
        range(1, len(LINE_SET) + 1)
    )
    assert tuple(entry.working_position for entry in LINE_SET) == tuple(
        range(1, len(LINE_SET) + 1)
    ), "LINE_SET is written in working order"


def test_the_declared_stages_are_exactly_the_opus_stages() -> None:
    """All four stages are used and citrinitas is not collapsed into rubedo."""
    declared = [entry.opus_stage for entry in LINE_SET if entry.opus_stage is not None]
    assert sorted(declared) == sorted(OPUS_STAGE_ORDER)


def test_working_order_is_not_opus_order() -> None:
    by_work = tuple(
        entry.id for entry in sorted(LINE_SET, key=lambda item: item.working_position)
    )
    by_opus = tuple(
        entry.id
        for entry in sorted(
            LINE_SET, key=lambda item: OPUS_STAGE_ORDER.index(item.opus_stage)
        )
    )
    assert by_work != by_opus


def test_line_ids_defaults_to_the_declaration_and_accepts_another() -> None:
    assert line_ids() == tuple(entry.id for entry in LINE_SET)
    assert line_ids(LINE_SET[:1]) == (LINE_SET[0].id,)


def test_find_line_hit_and_miss() -> None:
    wanted = LINE_SET[-1]
    assert find_line(wanted.id) is wanted
    assert find_line("no-such-line") is None
    assert find_line(wanted.id, LINE_SET[:1]) is None


def test_the_wrapper_entry_is_not_one_of_the_lines() -> None:
    """The wrapper is not a fifth instrument; it only exists to be checked."""
    assert WRAPPER_LINE not in LINE_SET
    assert WRAPPER_LINE.id not in line_ids()
    assert WRAPPER_LINE.opus_stage is None
    assert WRAPPER_LINE.color not in {entry.color for entry in LINE_SET}
    assert WRAPPER_LINE.must_not_become.strip()


def test_appending_the_wrapper_keeps_positions_contiguous() -> None:
    assert WRAPPER_LINE.working_position == len(LINE_SET) + 1
    assert check_contiguous_working_positions(LINE_SET + (WRAPPER_LINE,)).passed


def test_every_shared_token_names_declared_lines_and_gives_each_a_meaning() -> None:
    assert SHARED_TOKENS
    declared = set(line_ids())
    for token in SHARED_TOKENS:
        assert isinstance(token, SharedToken)
        assert len(token.lines) >= 2
        assert set(token.lines) <= declared
        assert token.covered_lines() == set(token.lines)
        assert token.rationale.strip()
        for line_id in token.lines:
            meaning = token.meaning_for(line_id)
            assert isinstance(meaning, str) and meaning.strip()


def test_the_shared_meanings_are_actually_different_from_each_other() -> None:
    """A shared spelling is only defensible if the senses genuinely differ."""
    for token in SHARED_TOKENS:
        meanings = [token.meaning_for(line_id) for line_id in token.lines]
        assert len(set(meanings)) == len(meanings), token.token


def test_shared_token_spellings_are_declared_once_each() -> None:
    spellings = [token.token for token in SHARED_TOKENS]
    assert len(set(spellings)) == len(spellings)

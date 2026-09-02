"""The structural battery: pass on the declaration, reject a planted defect.

Every check gets both directions. A check shown only to accept the real
declaration would be indistinguishable from a check that accepts everything,
so each one below is also handed a registry corrupted in exactly the way it
claims to detect, and is required to reject it and to name the offending item
in its detail.

Each check is also handed an empty registry. Passing on nothing is the failure
mode that makes a whole battery decorative, so an empty scan set must fail.

Check eight, self-disjointness, is not here. It needs to read the lines, and
its tests live in ``test_self_disjointness.py``.
"""

from __future__ import annotations

import dataclasses

import pytest

from line_set import (
    LINE_SET,
    OPUS_STAGE_ORDER,
    SHARED_TOKENS,
    SharedToken,
    all_invariants,
    check_contiguous_working_positions,
    check_distinct_colours,
    check_distinct_line_ids,
    check_distinct_opus_stages,
    check_must_not_become_declared,
    check_orders_diverge,
    check_shared_tokens_disambiguated,
    registry_sound,
)
from line_set.invariants import _LINE_CHECKS

REAL = LINE_SET

OFFLINE_LINE_CHECKS = (
    check_distinct_line_ids,
    check_distinct_colours,
    check_distinct_opus_stages,
    check_contiguous_working_positions,
    check_orders_diverge,
    check_must_not_become_declared,
)


# --------------------------------------------------------------------------
# the battery as a whole
# --------------------------------------------------------------------------


def test_the_battery_passes_on_the_real_declaration() -> None:
    results = all_invariants()
    assert len(results) == len(_LINE_CHECKS) + 1
    assert all(result.passed for result in results), [
        result for result in results if not result.passed
    ]
    names = [result.name for result in results]
    assert len(names) == len(set(names))
    assert registry_sound()


def test_the_battery_defaults_to_the_real_declaration() -> None:
    assert all_invariants() == all_invariants(LINE_SET, SHARED_TOKENS)


def test_the_offline_battery_names_every_check_it_runs() -> None:
    """The battery is the checks, not a hand-kept list beside them."""
    assert {check.__name__ for check in _LINE_CHECKS} == {
        check.__name__ for check in OFFLINE_LINE_CHECKS
    }


@pytest.mark.parametrize("check", OFFLINE_LINE_CHECKS, ids=lambda c: c.__name__)
def test_every_check_fails_on_an_empty_declaration(check) -> None:
    """A check with nothing to look at found nothing, which is not evidence."""
    result = check(())
    assert not result.passed
    assert "nothing to check" in result.detail


def test_the_shared_token_check_fails_on_an_empty_declaration() -> None:
    result = check_shared_tokens_disambiguated((), SHARED_TOKENS)
    assert not result.passed
    assert "nothing to check" in result.detail


def test_all_invariants_and_registry_sound_fail_on_an_empty_declaration() -> None:
    results = all_invariants((), ())
    assert results
    assert not any(result.passed for result in results)
    assert not registry_sound((), ())


# --------------------------------------------------------------------------
# 1. distinct line ids
# --------------------------------------------------------------------------


def test_distinct_line_ids_detects_a_duplicate() -> None:
    assert check_distinct_line_ids(REAL).passed
    planted = REAL + (dataclasses.replace(REAL[0], color="an impostor colour"),)
    result = check_distinct_line_ids(planted)
    assert not result.passed
    assert REAL[0].id in result.detail


def test_distinct_line_ids_detects_a_blank_id() -> None:
    planted = REAL[:-1] + (dataclasses.replace(REAL[-1], id="   "),)
    result = check_distinct_line_ids(planted)
    assert not result.passed
    assert f"[{len(REAL) - 1}]" in result.detail


def test_distinct_line_ids_detects_an_entry_that_is_not_a_line() -> None:
    planted = REAL + (object(),)
    result = check_distinct_line_ids(planted)
    assert not result.passed
    assert f"[{len(REAL)}]" in result.detail


# --------------------------------------------------------------------------
# 2. distinct colours
# --------------------------------------------------------------------------


def test_distinct_colours_detects_a_duplicate() -> None:
    assert check_distinct_colours(REAL).passed
    planted = REAL[:-1] + (dataclasses.replace(REAL[-1], color=REAL[0].color),)
    result = check_distinct_colours(planted)
    assert not result.passed
    assert REAL[0].color in result.detail


def test_distinct_colours_detects_a_blank_and_a_non_string_colour() -> None:
    blank = REAL[:-1] + (dataclasses.replace(REAL[-1], color=" "),)
    assert not check_distinct_colours(blank).passed
    numeric = REAL[:-1] + (dataclasses.replace(REAL[-1], color=7),)
    result = check_distinct_colours(numeric)
    assert not result.passed
    assert f"[{len(REAL) - 1}]" in result.detail


def test_distinct_colours_detects_an_entry_that_is_not_a_line() -> None:
    result = check_distinct_colours(REAL + (object(),))
    assert not result.passed
    assert f"[{len(REAL)}]" in result.detail


# --------------------------------------------------------------------------
# 3. distinct opus stages
# --------------------------------------------------------------------------


def test_distinct_opus_stages_detects_a_repeated_stage() -> None:
    assert check_distinct_opus_stages(REAL).passed
    planted = REAL[:-1] + (
        dataclasses.replace(REAL[-1], opus_stage=REAL[0].opus_stage),
    )
    result = check_distinct_opus_stages(planted)
    assert not result.passed
    assert REAL[0].opus_stage in result.detail


def test_distinct_opus_stages_detects_a_stage_that_is_not_an_opus_stage() -> None:
    planted = REAL[:-1] + (dataclasses.replace(REAL[-1], opus_stage="viriditas"),)
    result = check_distinct_opus_stages(planted)
    assert not result.passed
    assert "viriditas" in result.detail


def test_distinct_opus_stages_detects_a_non_string_stage() -> None:
    planted = REAL[:-1] + (dataclasses.replace(REAL[-1], opus_stage=7),)
    result = check_distinct_opus_stages(planted)
    assert not result.passed
    assert "7" in result.detail


def test_distinct_opus_stages_refuses_a_declaration_where_no_stage_is_claimed() -> None:
    """Distinctness among no stages at all is not distinctness."""
    planted = tuple(dataclasses.replace(entry, opus_stage=None) for entry in REAL)
    result = check_distinct_opus_stages(planted)
    assert not result.passed
    assert "no entry declares an opus stage" in result.detail


def test_distinct_opus_stages_ignores_entries_that_are_not_lines() -> None:
    assert check_distinct_opus_stages(REAL + (object(),)).passed


# --------------------------------------------------------------------------
# 4. contiguous working positions
# --------------------------------------------------------------------------


def test_contiguous_positions_detects_a_gap_and_a_duplicate() -> None:
    assert check_contiguous_working_positions(REAL).passed
    gap = REAL[:-1] + (dataclasses.replace(REAL[-1], working_position=len(REAL) + 3),)
    result = check_contiguous_working_positions(gap)
    assert not result.passed
    assert str(len(REAL) + 3) in result.detail
    twin = REAL[:-1] + (
        dataclasses.replace(REAL[-1], working_position=REAL[0].working_position),
    )
    assert not check_contiguous_working_positions(twin).passed


def test_contiguous_positions_detects_a_non_integer_and_a_boolean_position() -> None:
    """``True`` is an ``int`` in Python and must not read as position one."""
    numeric = REAL[:-1] + (dataclasses.replace(REAL[-1], working_position="4"),)
    result = check_contiguous_working_positions(numeric)
    assert not result.passed
    assert f"[{len(REAL) - 1}]" in result.detail
    boolean = REAL[:-1] + (dataclasses.replace(REAL[-1], working_position=True),)
    assert not check_contiguous_working_positions(boolean).passed


def test_contiguous_positions_detects_an_entry_that_is_not_a_line() -> None:
    result = check_contiguous_working_positions(REAL + (object(),))
    assert not result.passed
    assert f"[{len(REAL)}]" in result.detail


# --------------------------------------------------------------------------
# 5. the two orders diverge
# --------------------------------------------------------------------------


def test_orders_diverge_detects_a_declaration_that_re_enacts_the_opus() -> None:
    """The plant lines the stages up with the working order, and is rejected."""
    assert check_orders_diverge(REAL).passed
    staged = tuple(
        entry
        for entry in REAL
        if entry.opus_stage in OPUS_STAGE_ORDER and entry.working_position is not None
    )
    assert len(staged) <= len(OPUS_STAGE_ORDER)
    in_working_order = sorted(staged, key=lambda entry: entry.working_position)
    planted = tuple(
        dataclasses.replace(entry, opus_stage=OPUS_STAGE_ORDER[index])
        for index, entry in enumerate(in_working_order)
    )
    result = check_orders_diverge(planted)
    assert not result.passed
    assert "identical" in result.detail
    for entry in planted:
        assert entry.id in result.detail


def test_orders_diverge_refuses_a_declaration_with_too_few_staged_entries() -> None:
    planted = tuple(
        dataclasses.replace(entry, opus_stage=None if index else entry.opus_stage)
        for index, entry in enumerate(REAL)
    )
    result = check_orders_diverge(planted)
    assert not result.passed
    assert "fewer than two entries" in result.detail


def test_orders_diverge_ignores_unstaged_and_malformed_entries() -> None:
    planted = REAL + (object(),)
    assert check_orders_diverge(planted).passed
    positionless = REAL[:-1] + (dataclasses.replace(REAL[-1], working_position=True),)
    assert check_orders_diverge(positionless).passed


# --------------------------------------------------------------------------
# 6. every line says what it must not become
# --------------------------------------------------------------------------


def test_must_not_become_detects_a_blank_boundary() -> None:
    assert check_must_not_become_declared(REAL).passed
    planted = REAL[:-1] + (dataclasses.replace(REAL[-1], must_not_become="   "),)
    result = check_must_not_become_declared(planted)
    assert not result.passed
    assert REAL[-1].id in result.detail


def test_must_not_become_detects_a_non_string_boundary() -> None:
    planted = REAL[:-1] + (dataclasses.replace(REAL[-1], must_not_become=7),)
    assert not check_must_not_become_declared(planted).passed


def test_must_not_become_detects_an_entry_that_is_not_a_line() -> None:
    result = check_must_not_become_declared(REAL + (object(),))
    assert not result.passed
    assert f"index {len(REAL)}" in result.detail


# --------------------------------------------------------------------------
# 7. every exemption is one the live matcher would honour
# --------------------------------------------------------------------------


def test_shared_tokens_check_passes_on_the_real_exemption_table() -> None:
    result = check_shared_tokens_disambiguated(REAL, SHARED_TOKENS)
    assert result.passed
    assert result.detail == "ok"


def test_an_empty_exemption_table_is_refused() -> None:
    """Empty by design and empty by accident look the same from in here."""
    result = check_shared_tokens_disambiguated(REAL, ())
    assert not result.passed
    assert "empty exemption table" in result.detail


def test_the_check_detects_an_exemption_missing_one_lines_meaning() -> None:
    real = SHARED_TOKENS[0]
    planted = (dataclasses.replace(real, meanings=real.meanings[:1]),)
    result = check_shared_tokens_disambiguated(REAL, planted)
    assert not result.passed
    assert real.token in result.detail
    assert "would not honour" in result.detail


def test_the_check_detects_an_exemption_naming_a_line_nobody_declared() -> None:
    real = SHARED_TOKENS[0]
    planted = (
        dataclasses.replace(
            real,
            lines=(*real.lines, "chartreuse_line"),
            meanings=(*real.meanings, ("chartreuse_line", "a sense with no line")),
        ),
    )
    result = check_shared_tokens_disambiguated(REAL, planted)
    assert not result.passed
    assert "chartreuse_line" in result.detail
    assert "undeclared lines" in result.detail


def test_the_check_detects_an_exemption_with_no_recorded_rationale() -> None:
    planted = (dataclasses.replace(SHARED_TOKENS[0], rationale="  "),)
    result = check_shared_tokens_disambiguated(REAL, planted)
    assert not result.passed
    assert "no rationale is recorded" in result.detail


def test_the_check_detects_an_entry_that_is_not_a_shared_token() -> None:
    result = check_shared_tokens_disambiguated(REAL, (object(),))
    assert not result.passed
    assert "index 0: not a SharedToken" in result.detail


def test_the_check_detects_an_exemption_whose_lines_are_not_iterable() -> None:
    planted = (dataclasses.replace(SHARED_TOKENS[0], lines=7),)
    result = check_shared_tokens_disambiguated(REAL, planted)
    assert not result.passed
    assert "lines is not iterable" in result.detail


def test_the_check_labels_an_exemption_with_no_usable_spelling_by_position() -> None:
    planted = (dataclasses.replace(SHARED_TOKENS[0], token=7),)
    result = check_shared_tokens_disambiguated(REAL, planted)
    assert not result.passed
    assert "index 0" in result.detail


def test_the_check_detects_a_token_declared_twice() -> None:
    """An ambiguous exemption exempts nothing, and the check agrees."""
    planted = (SHARED_TOKENS[0], SHARED_TOKENS[0])
    result = check_shared_tokens_disambiguated(REAL, planted)
    assert not result.passed
    assert "would not honour" in result.detail


def test_registry_sound_is_false_for_every_planted_defect() -> None:
    for planted_lines, planted_shared in (
        (REAL + (dataclasses.replace(REAL[0], color="impostor"),), SHARED_TOKENS),
        (
            REAL[:-1] + (dataclasses.replace(REAL[-1], must_not_become=""),),
            SHARED_TOKENS,
        ),
        (REAL, ()),
        (REAL, (SharedToken("SHARED", ("one",), (("one", "sense"),), "why"),)),
    ):
        assert not registry_sound(planted_lines, planted_shared)

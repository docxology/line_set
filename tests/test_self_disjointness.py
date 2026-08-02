"""The signature property: the wrapper survives its own collision check.

This package checks that no two lines share a status token. The obvious way to
cheat at that is to exempt yourself from it, so the check is applied to a
declaration that includes this package, and the reading statuses are
``SET_``-prefixed precisely so that application can succeed honestly.

A test that only ran the check and watched it pass would prove nothing about
whether the check can fail. So the plants here are built from the wrapper's own
enum member names, read out of the enums at runtime rather than copied: a line
that adopts one of this package's own spellings must be caught, and a declared
exemption must not be able to launder it.
"""

from __future__ import annotations

from pathlib import Path

import line_set
from line_set import (
    LINE_SET,
    SHARED_TOKENS,
    WRAPPER_LINE,
    LineEntry,
    ReadCode,
    SetStatus,
    SharedToken,
    all_invariants,
    check_self_disjointness,
    live_invariants,
    read_set,
    sibling_path_resolver,
)
from tests.support import (
    absent,
    canned_resolver,
    import_sandbox,
    load_line_package,
    resolved,
    write_line_package,
)

#: The wrapper's own published vocabulary, read from the enums themselves.
WRAPPER_TOKENS = frozenset(member.name for member in SetStatus) | frozenset(
    member.name for member in ReadCode
)


def _line(line_id: str, position: int) -> LineEntry:
    return LineEntry(
        id=line_id,
        color=line_id,
        question=f"what does {line_id} ask?",
        job=f"the job of {line_id}",
        must_not_become=f"whatever {line_id} is not",
        opus_stage=None,
        working_position=position,
        package_name=line_id,
        registry_noun="entries",
        verdict_noun="verdict",
    )


ONE = _line("one_line", 1)
TWO = _line("two_line", 2)


def _wrapper_answer() -> dict[str, object]:
    """The wrapper resolves to this package, which is the point of the check."""
    return {WRAPPER_LINE.package_name: resolved(WRAPPER_LINE.package_name, line_set)}


def test_the_wrapper_publishes_a_vocabulary_worth_checking() -> None:
    """An overlap check over an empty vocabulary would find nothing, cheaply."""
    assert WRAPPER_TOKENS
    assert all(
        token.startswith("SET_") or token in WRAPPER_TOKENS for token in WRAPPER_TOKENS
    )
    assert frozenset(line_set.enum_tokens(line_set)) == WRAPPER_TOKENS


def test_the_check_passes_against_lines_that_share_none_of_its_spellings(
    tmp_path: Path,
) -> None:
    with import_sandbox():
        write_line_package(tmp_path, "one_line", ("ALPHA", "BRAVO"))
        write_line_package(tmp_path, "two_line", ("CHARLIE",))
        answers = _wrapper_answer()
        answers.update(
            {
                name: resolved(name, load_line_package(tmp_path, name))
                for name in ("one_line", "two_line")
            }
        )
        result = check_self_disjointness(
            (ONE, TWO), (), resolver=canned_resolver(answers)
        )

    assert result.passed
    assert result.name == "self_disjointness"
    assert "one_line" in result.detail and "two_line" in result.detail
    assert str(len(WRAPPER_TOKENS)) in result.detail


def test_a_line_that_adopts_one_of_the_wrappers_spellings_is_caught(
    tmp_path: Path,
) -> None:
    """The proof that the check can fail, built from the wrapper's own enum."""
    stolen = sorted(WRAPPER_TOKENS)[0]
    with import_sandbox():
        write_line_package(tmp_path, "one_line", ("ALPHA", stolen))
        answers = _wrapper_answer()
        answers["one_line"] = resolved(
            "one_line", load_line_package(tmp_path, "one_line")
        )
        result = check_self_disjointness((ONE,), (), resolver=canned_resolver(answers))

    assert not result.passed
    assert stolen in result.detail
    assert "collide" in result.detail


def test_an_exemption_cannot_launder_the_wrappers_own_overlap(tmp_path: Path) -> None:
    """The wrapper is not a line and has no standing to share a token.

    The exemption below is well formed and would exempt this collision between
    two ordinary lines. It does not help here, because an exempted collision
    involving the wrapper still counts against the wrapper.
    """
    stolen = sorted(WRAPPER_TOKENS)[0]
    laundering = SharedToken(
        token=stolen,
        lines=("one_line", WRAPPER_LINE.id),
        meanings=(
            ("one_line", "the one_line sense"),
            (WRAPPER_LINE.id, "the wrapper's own reading status"),
        ),
        rationale="an exemption written to excuse the wrapper from its own check",
    )
    with import_sandbox():
        write_line_package(tmp_path, "one_line", ("ALPHA", stolen))
        answers = _wrapper_answer()
        answers["one_line"] = resolved(
            "one_line", load_line_package(tmp_path, "one_line")
        )
        resolver = canned_resolver(answers)
        result = check_self_disjointness((ONE,), (laundering,), resolver=resolver)
        reading = read_set((ONE, WRAPPER_LINE), (laundering,), resolver=resolver)

    assert reading.status is SetStatus.SET_LEGIBLE, "the reader honoured the exemption"
    assert [collision.token for collision in reading.exempted_collisions] == [stolen]
    assert not result.passed, "the self-check does not honour it"
    assert stolen in result.detail


def test_the_check_refuses_to_pass_when_no_line_could_be_read() -> None:
    """Disjointness from nothing is not disjointness."""
    result = check_self_disjointness(
        LINE_SET, SHARED_TOKENS, resolver=canned_resolver(_wrapper_answer())
    )
    assert not result.passed
    assert "comparison set was empty" in result.detail
    for entry in LINE_SET:
        assert entry.id in result.detail


def test_the_check_refuses_to_pass_when_the_wrapper_itself_cannot_be_read(
    tmp_path: Path,
) -> None:
    with import_sandbox():
        write_line_package(tmp_path, "one_line", ("ALPHA",))
        answers = {
            "one_line": resolved("one_line", load_line_package(tmp_path, "one_line")),
            WRAPPER_LINE.package_name: absent(WRAPPER_LINE.package_name),
        }
        result = check_self_disjointness((ONE,), (), resolver=canned_resolver(answers))

    assert not result.passed
    assert "could not be read" in result.detail
    assert "unestablished" in result.detail


def test_a_partly_read_set_leaves_disjointness_unestablished(tmp_path: Path) -> None:
    with import_sandbox():
        write_line_package(tmp_path, "one_line", ("ALPHA",))
        answers = _wrapper_answer()
        answers["one_line"] = resolved(
            "one_line", load_line_package(tmp_path, "one_line")
        )
        answers["two_line"] = absent("two_line")
        result = check_self_disjointness(
            (ONE, TWO), (), resolver=canned_resolver(answers)
        )

    assert not result.passed
    assert "holds against ['one_line']" in result.detail
    assert "two_line" in result.detail


def test_the_live_battery_is_the_offline_battery_plus_this_check() -> None:
    resolver = canned_resolver(_wrapper_answer())
    offline = all_invariants()
    live = live_invariants(resolver=resolver)
    assert live[: len(offline)] == offline
    assert len(live) == len(offline) + 1
    assert live[-1].name == "self_disjointness"


def test_the_wrapper_is_checked_against_the_real_sibling_checkouts() -> None:
    """The declaration including this package, read from the working tree.

    When every declared line is importable the check must pass and no collision
    may involve the wrapper. When a line is not importable the check must refuse
    to pass and must name what it could not read. There is no third outcome: a
    real collision would satisfy neither branch and fail the test.
    """
    with import_sandbox():
        resolver = sibling_path_resolver()
        result = check_self_disjointness(resolver=resolver)
        reading = read_set(LINE_SET + (WRAPPER_LINE,), SHARED_TOKENS, resolver=resolver)

    by_id = {observation.line_id: observation for observation in reading.observations}
    assert frozenset(by_id[WRAPPER_LINE.id].tokens) == WRAPPER_TOKENS
    involving_wrapper = [
        collision.token
        for collision in (*reading.collisions, *reading.exempted_collisions)
        if WRAPPER_LINE.id in collision.lines
    ]
    assert involving_wrapper == []

    unread = sorted(
        observation.line_id
        for observation in reading.observations
        if observation.line_id != WRAPPER_LINE.id and not observation.tokens
    )
    if result.passed:
        assert not unread
        for entry in LINE_SET:
            assert entry.id in result.detail
    else:
        assert unread, result.detail
        assert any(line_id in result.detail for line_id in unread)

"""The staged reader: every status, the precedence between them, and the
fail-closed exemption matcher.

Each resolver here is a plain callable or a small class with a ``candidates``
method. That is the whole mechanism: no patching library is involved, and the
packages the resolvers hand back are real modules imported from real files.

The two properties this module works hardest on are the ones the project
exists for. First, a line that could not be read reports no version, no
registry size, and no digest — a fabricated value there is precisely the
failure this reader is meant to make impossible. Second, an exemption only
exempts when it matches exactly; every near-miss is planted and shown to
leave the collision standing.
"""

from __future__ import annotations

import dataclasses
from datetime import date
from pathlib import Path

import pytest

from line_set import (
    LINE_SET,
    READER_STAGES,
    SHARED_TOKENS,
    STATUS_PRECEDENCE,
    LineEntry,
    ReadCode,
    SetStatus,
    SharedToken,
    exemption_for,
    read_set,
    registry_digest,
)
from line_set.reader import _review_date
from tests.support import (
    ListingResolver,
    absent,
    broken,
    canned_resolver,
    import_sandbox,
    load_line_package,
    resolved,
    write_line_package,
)


def _line(line_id: str, position: int) -> LineEntry:
    """A declared line whose only purpose is to be looked up by name."""
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
THREE = _line("three_line", 3)


def _shared(token: str, *line_ids: str) -> SharedToken:
    """A well-formed exemption covering every line it names."""
    return SharedToken(
        token=token,
        lines=tuple(line_ids),
        meanings=tuple((line_id, f"the {line_id} sense") for line_id in line_ids),
        rationale=f"{token} means something different in each line",
    )


# --------------------------------------------------------------------------
# the review date
# --------------------------------------------------------------------------


def test_review_date_accepts_none_a_string_and_a_date() -> None:
    assert _review_date(None) == date.today()
    assert _review_date("2026-07-27") == date(2026, 7, 27)
    assert _review_date(date(2026, 7, 27)) == date(2026, 7, 27)


def test_review_date_refuses_a_non_date_and_a_non_iso_string() -> None:
    with pytest.raises(TypeError):
        _review_date(20260727)
    with pytest.raises(ValueError):
        _review_date("the twenty-seventh")


def test_the_reading_carries_the_review_date_it_was_given() -> None:
    reading = read_set(
        (ONE,), (), resolver=canned_resolver({}), as_of=date(2026, 7, 27)
    )
    assert reading.read_as_of == "2026-07-27"


# --------------------------------------------------------------------------
# the exemption matcher, one refusal at a time
# --------------------------------------------------------------------------


def test_an_exact_exemption_matches() -> None:
    declared = _shared("SHARED", "one_line", "two_line")
    assert exemption_for((declared,), "SHARED", ("two_line", "one_line")) is declared


def test_the_real_declaration_is_honoured_by_the_live_matcher() -> None:
    for token in SHARED_TOKENS:
        assert exemption_for(SHARED_TOKENS, token.token, token.lines) is token


def test_the_matcher_refuses_a_blank_or_non_string_token() -> None:
    declared = _shared("SHARED", "one_line", "two_line")
    assert exemption_for((declared,), "", ("one_line", "two_line")) is None
    assert exemption_for((declared,), 7, ("one_line", "two_line")) is None


def test_the_matcher_refuses_when_fewer_than_two_lines_carry_the_token() -> None:
    declared = _shared("SHARED", "one_line", "two_line")
    assert exemption_for((declared,), "SHARED", ("one_line",)) is None
    assert exemption_for((declared,), "SHARED", ()) is None


def test_the_matcher_refuses_an_undeclared_and_a_doubly_declared_token() -> None:
    declared = _shared("SHARED", "one_line", "two_line")
    carrying = ("one_line", "two_line")
    assert exemption_for((), "SHARED", carrying) is None
    assert exemption_for((declared,), "OTHER", carrying) is None
    assert exemption_for((declared, declared), "SHARED", carrying) is None


def test_the_matcher_ignores_entries_that_are_not_shared_tokens() -> None:
    declared = _shared("SHARED", "one_line", "two_line")
    entries = (object(), declared)
    assert exemption_for(entries, "SHARED", ("one_line", "two_line")) is declared


def test_the_matcher_refuses_an_exemption_whose_lines_are_unusable() -> None:
    good = _shared("SHARED", "one_line", "two_line")
    carrying = ("one_line", "two_line")
    not_iterable = dataclasses.replace(good, lines=7)
    assert exemption_for((not_iterable,), "SHARED", carrying) is None
    blank_line = dataclasses.replace(good, lines=("one_line", "   "))
    assert exemption_for((blank_line,), "SHARED", carrying) is None
    numeric_line = dataclasses.replace(good, lines=("one_line", 2))
    assert exemption_for((numeric_line,), "SHARED", carrying) is None
    repeated = dataclasses.replace(
        good,
        lines=("one_line", "one_line", "two_line"),
        meanings=(("one_line", "a sense"), ("two_line", "another sense")),
    )
    assert exemption_for((repeated,), "SHARED", carrying) is None
    single = dataclasses.replace(
        good, lines=("one_line",), meanings=(("one_line", "only sense"),)
    )
    assert exemption_for((single,), "SHARED", carrying) is None


def test_an_exemption_naming_a_line_that_does_not_carry_the_token_does_not_exempt(
    tmp_path: Path,
) -> None:
    """Set equality, not a subset or superset test.

    The exemption below is perfectly well formed. It just describes a different
    situation from the one on the ground, and describing a different situation
    is not permission for this one.
    """
    declared = _shared("SHARED", "one_line", "three_line")
    assert exemption_for((declared,), "SHARED", ("one_line", "two_line")) is None

    with import_sandbox():
        write_line_package(tmp_path, "one_line", ("SHARED", "ALPHA"))
        write_line_package(tmp_path, "two_line", ("SHARED", "BRAVO"))
        modules = {
            name: load_line_package(tmp_path, name) for name in ("one_line", "two_line")
        }
        reading = read_set(
            (ONE, TWO),
            (declared,),
            resolver=canned_resolver(
                {name: resolved(name, module) for name, module in modules.items()}
            ),
        )
    assert reading.status is SetStatus.SET_COLLIDING
    assert [collision.token for collision in reading.collisions] == ["SHARED"]
    assert reading.exempted_collisions == ()


def test_an_exemption_that_omits_one_lines_meaning_does_not_exempt(
    tmp_path: Path,
) -> None:
    """A label is not a disambiguation.

    Naming two lines and explaining only one of them leaves the second use of
    the spelling unexplained, which is exactly the thing the exemption was
    supposed to rule out.
    """
    partial = SharedToken(
        token="SHARED",
        lines=("one_line", "two_line"),
        meanings=(("one_line", "the one_line sense"),),
        rationale="only half of this is written down",
    )
    assert exemption_for((partial,), "SHARED", ("one_line", "two_line")) is None

    with import_sandbox():
        write_line_package(tmp_path, "one_line", ("SHARED", "ALPHA"))
        write_line_package(tmp_path, "two_line", ("SHARED", "BRAVO"))
        modules = {
            name: load_line_package(tmp_path, name) for name in ("one_line", "two_line")
        }
        reading = read_set(
            (ONE, TWO),
            (partial,),
            resolver=canned_resolver(
                {name: resolved(name, module) for name, module in modules.items()}
            ),
        )
    assert reading.status is SetStatus.SET_COLLIDING
    assert reading.collisions[0].lines == ("one_line", "two_line")
    assert reading.exempted_collisions == ()


def test_the_matcher_refuses_every_malformed_meanings_table() -> None:
    good = _shared("SHARED", "one_line", "two_line")
    carrying = ("one_line", "two_line")
    for planted, why in (
        (dataclasses.replace(good, meanings=7), "meanings is not iterable"),
        (
            dataclasses.replace(good, meanings=(("one_line",), ("two_line", "b"))),
            "a pair that is not a pair",
        ),
        (
            dataclasses.replace(good, meanings=("one_line", ("two_line", "b"))),
            "an entry that is not a tuple",
        ),
        (
            dataclasses.replace(good, meanings=((7, "a"), ("two_line", "b"))),
            "a non-string line id",
        ),
        (
            dataclasses.replace(good, meanings=(("one_line", 7), ("two_line", "b"))),
            "a non-string meaning",
        ),
        (
            dataclasses.replace(good, meanings=(("one_line", " "), ("two_line", "b"))),
            "a blank meaning",
        ),
        (
            dataclasses.replace(
                good, meanings=(("one_line", "a"), ("one_line", "again"))
            ),
            "a repeated line id",
        ),
        (
            dataclasses.replace(
                good,
                meanings=(("one_line", "a"), ("three_line", "c")),
            ),
            "a meaning for a line the exemption does not name",
        ),
    ):
        assert exemption_for((planted,), "SHARED", carrying) is None, why


# --------------------------------------------------------------------------
# the four statuses
# --------------------------------------------------------------------------


def test_a_fully_read_set_with_no_overlap_is_legible(tmp_path: Path) -> None:
    with import_sandbox():
        write_line_package(
            tmp_path, "one_line", ("ALPHA", "BRAVO"), registry_sizes={"ENTRIES": 2}
        )
        write_line_package(tmp_path, "two_line", ("CHARLIE",))
        resolver = ListingResolver(
            {
                name: resolved(name, load_line_package(tmp_path, name))
                for name in ("one_line", "two_line")
            },
            listed=("one_line", "two_line"),
        )
        reading = read_set((ONE, TWO), (), resolver=resolver)

    assert reading.status is SetStatus.SET_LEGIBLE
    assert reading.collisions == ()
    assert reading.exempted_collisions == ()
    assert reading.undeclared_lines == ()
    assert reading.counts()[ReadCode.RESOLVED.value] == 2
    first = reading.observations[0]
    assert first.tokens == ("ALPHA", "BRAVO")
    assert first.version == "0.0.1"
    assert first.registry_size == 2
    assert first.registry_digest is not None


def test_an_unreadable_line_makes_the_reading_partial_and_measures_nothing() -> None:
    """The failure this project exists to prevent is a value invented here."""
    reading = read_set(
        (ONE, TWO),
        (),
        resolver=canned_resolver(
            {"one_line": absent("one_line"), "two_line": broken("two_line")}
        ),
    )
    assert reading.status is SetStatus.SET_PARTIAL
    for observation in reading.observations:
        assert observation.version is None
        assert observation.registry_size is None
        assert observation.registry_digest is None
        assert observation.tokens == ()
    codes = {
        observation.line_id: observation.code for observation in reading.observations
    }
    assert codes["one_line"] is ReadCode.NOT_INSTALLED
    assert codes["two_line"] is ReadCode.IMPORT_FAILED
    assert "one_line" in reading.derivation[-1].detail


def test_a_resolved_package_with_no_enum_is_read_as_having_no_vocabulary(
    tmp_path: Path,
) -> None:
    with import_sandbox():
        write_line_package(tmp_path, "one_line", enums={}, version="4.2.0")
        module = load_line_package(tmp_path, "one_line")
        reading = read_set(
            (ONE,),
            (),
            resolver=canned_resolver({"one_line": resolved("one_line", module)}),
        )
    observation = reading.observations[0]
    assert observation.code is ReadCode.NO_VOCABULARY
    assert observation.tokens == ()
    assert observation.version == "4.2.0", "a real reading is kept, not discarded"
    assert reading.status is SetStatus.SET_PARTIAL


def test_a_resolution_with_no_module_is_refused_rather_than_believed() -> None:
    """The resolver contract is that a resolved package comes with its module.

    A resolver that breaks it gets no measurements invented on its behalf, and
    it does not get its claim of ``RESOLVED`` honoured either. Honouring it
    would put a line with no vocabulary into the read set, where it counts as
    read, contributes nothing to the collision scan, and cannot make the
    reading partial — so a whole set of them would report ``SET_LEGIBLE`` on
    the strength of having compared nothing. That is the fail-open direction
    and this test is the thing standing in front of it.
    """
    from line_set.binding import Resolution

    reading = read_set(
        (ONE,),
        (),
        resolver=canned_resolver(
            {
                "one_line": Resolution(
                    "one_line", ReadCode.RESOLVED, None, "no module was handed back"
                )
            }
        ),
    )
    observation = reading.observations[0]
    assert observation.version is None
    assert observation.registry_size is None
    assert observation.registry_digest is None
    assert observation.tokens == ()
    assert observation.code is ReadCode.IMPORT_FAILED
    assert "no module" in observation.detail
    assert "no module was handed back" in observation.detail, (
        "the resolver's own explanation must survive the downgrade"
    )
    assert reading.status is SetStatus.SET_PARTIAL, (
        "a line nothing could be read from must not read as legible"
    )


def test_an_undeclared_exemption_makes_the_reading_collide(tmp_path: Path) -> None:
    with import_sandbox():
        write_line_package(tmp_path, "one_line", ("SHARED", "ALPHA"))
        write_line_package(tmp_path, "two_line", ("SHARED", "BRAVO"))
        resolver = canned_resolver(
            {
                name: resolved(name, load_line_package(tmp_path, name))
                for name in ("one_line", "two_line")
            }
        )
        reading = read_set((ONE, TWO), (), resolver=resolver)

    assert reading.status is SetStatus.SET_COLLIDING
    assert len(reading.collisions) == 1
    assert reading.collisions[0].token == "SHARED"
    assert reading.collisions[0].exempted is False
    assert "1 cross-line token collision" in reading.derivation[-1].detail


def test_a_declared_exemption_keeps_the_reading_legible(tmp_path: Path) -> None:
    declared = _shared("SHARED", "one_line", "two_line")
    with import_sandbox():
        write_line_package(tmp_path, "one_line", ("SHARED", "ALPHA"))
        write_line_package(tmp_path, "two_line", ("SHARED", "BRAVO"))
        resolver = ListingResolver(
            {
                name: resolved(name, load_line_package(tmp_path, name))
                for name in ("one_line", "two_line")
            },
            listed=("one_line", "two_line"),
        )
        reading = read_set((ONE, TWO), (declared,), resolver=resolver)

    assert reading.status is SetStatus.SET_LEGIBLE
    assert reading.collisions == ()
    assert [collision.token for collision in reading.exempted_collisions] == ["SHARED"]
    assert reading.exempted_collisions[0].rationale == declared.rationale


def test_a_resolved_package_nobody_declared_is_reported(tmp_path: Path) -> None:
    with import_sandbox():
        for name in ("one_line", "two_line", "extra_line"):
            write_line_package(tmp_path, name, (name.upper(),))
        answers = {
            name: resolved(name, load_line_package(tmp_path, name))
            for name in ("one_line", "two_line", "extra_line")
        }
        resolver = ListingResolver(
            answers, listed=("one_line", "two_line", "extra_line", "ghost_line")
        )
        reading = read_set((ONE, TWO), (), resolver=resolver)

    assert reading.status is SetStatus.SET_UNDECLARED
    assert reading.undeclared_lines == ("extra_line",)
    assert "ghost_line" not in reading.undeclared_lines, (
        "a listed name that does not resolve is not a line"
    )
    assert "scanned 4 candidate packages" in reading.derivation[3].detail


def test_a_resolver_that_cannot_enumerate_says_so_instead_of_finding_nothing() -> None:
    reading = read_set((ONE,), (), resolver=canned_resolver({}))
    declare = reading.derivation[3]
    assert declare.items == ()
    assert "were not scanned for" in declare.detail


# --------------------------------------------------------------------------
# precedence
# --------------------------------------------------------------------------


def test_the_status_precedence_order_is_the_documented_one() -> None:
    assert STATUS_PRECEDENCE == (
        SetStatus.SET_COLLIDING,
        SetStatus.SET_UNDECLARED,
        SetStatus.SET_PARTIAL,
        SetStatus.SET_LEGIBLE,
    )
    assert set(STATUS_PRECEDENCE) == set(SetStatus)


def test_a_collision_outranks_an_undeclared_line_and_a_partial_read(
    tmp_path: Path,
) -> None:
    with import_sandbox():
        write_line_package(tmp_path, "one_line", ("SHARED",))
        write_line_package(tmp_path, "two_line", ("SHARED",))
        write_line_package(tmp_path, "extra_line", ("ECHO",))
        answers = {
            name: resolved(name, load_line_package(tmp_path, name))
            for name in ("one_line", "two_line", "extra_line")
        }
        answers["three_line"] = absent("three_line")
        resolver = ListingResolver(
            answers, listed=("one_line", "two_line", "extra_line")
        )
        reading = read_set((ONE, TWO, THREE), (), resolver=resolver)

    assert reading.collisions and reading.undeclared_lines
    assert any(
        observation.code is not ReadCode.RESOLVED
        for observation in reading.observations
    )
    assert reading.status is SetStatus.SET_COLLIDING


def test_an_undeclared_line_outranks_a_partial_read(tmp_path: Path) -> None:
    with import_sandbox():
        write_line_package(tmp_path, "one_line", ("ALPHA",))
        write_line_package(tmp_path, "extra_line", ("ECHO",))
        answers = {
            name: resolved(name, load_line_package(tmp_path, name))
            for name in ("one_line", "extra_line")
        }
        answers["two_line"] = absent("two_line")
        resolver = ListingResolver(answers, listed=("one_line", "extra_line"))
        reading = read_set((ONE, TWO), (), resolver=resolver)

    assert reading.collisions == ()
    assert reading.undeclared_lines == ("extra_line",)
    assert any(
        observation.code is not ReadCode.RESOLVED
        for observation in reading.observations
    )
    assert reading.status is SetStatus.SET_UNDECLARED


# --------------------------------------------------------------------------
# the derivation and the digest
# --------------------------------------------------------------------------


def test_the_derivation_records_every_stage_in_order() -> None:
    reading = read_set((ONE,), (), resolver=canned_resolver({}))
    assert tuple(stage.name for stage in reading.derivation) == READER_STAGES
    assert reading.derivation[-1].items == tuple(
        status.value for status in STATUS_PRECEDENCE
    )
    assert reading.derivation[-1].detail.startswith(reading.status.value)


def test_the_stage_details_agree_in_number_with_a_single_declared_line() -> None:
    reading = read_set(
        (ONE,), (), resolver=ListingResolver({"one_line": absent("one_line")}, ())
    )
    assert "1 declared package" in reading.derivation[0].detail
    assert "scanned 0 candidate packages" in reading.derivation[3].detail


def test_one_listed_candidate_is_described_in_the_singular(tmp_path: Path) -> None:
    with import_sandbox():
        write_line_package(tmp_path, "one_line", ("ALPHA",))
        resolver = ListingResolver(
            {"one_line": resolved("one_line", load_line_package(tmp_path, "one_line"))},
            listed=("one_line",),
        )
        reading = read_set((ONE,), (), resolver=resolver)
    assert "scanned 1 candidate package and" in reading.derivation[3].detail
    assert "2 declared packages" not in reading.derivation[0].detail


def test_the_reading_carries_the_digest_of_the_declaration_it_read() -> None:
    reading = read_set((ONE, TWO), SHARED_TOKENS, resolver=canned_resolver({}))
    assert reading.set_digest == registry_digest((ONE, TWO), SHARED_TOKENS)
    assert reading.set_digest != registry_digest((ONE, TWO), ())


def test_read_set_defaults_to_the_real_declaration_and_the_default_resolver() -> None:
    """Called with nothing, the reader reads the set this project declares."""
    reading = read_set()
    assert tuple(observation.line_id for observation in reading.observations) == tuple(
        entry.id for entry in LINE_SET
    )
    assert reading.set_digest == registry_digest(LINE_SET, SHARED_TOKENS)
    assert reading.status in set(SetStatus)
    assert reading.read_as_of == date.today().isoformat()


def test_a_token_carried_by_one_line_alone_is_not_a_collision(tmp_path: Path) -> None:
    with import_sandbox():
        write_line_package(tmp_path, "one_line", ("ALPHA", "BRAVO"))
        resolver = canned_resolver(
            {"one_line": resolved("one_line", load_line_package(tmp_path, "one_line"))}
        )
        reading = read_set((ONE,), (), resolver=resolver)
    assert reading.collisions == ()
    assert reading.exempted_collisions == ()
    assert "0 unexempted and 0 exempted" in reading.derivation[2].detail

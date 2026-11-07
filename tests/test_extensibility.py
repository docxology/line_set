"""Exercise extension through real declaration, reader and serializer behavior.

The hypothetical appended entry must preserve structural checks, collision
refusal, exact exemptions and self-application. Tests exercise those public
behaviors rather than counting spellings in implementation source.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from line_set import (
    LINE_SET,
    SHARED_TOKENS,
    WRAPPER_LINE,
    LineEntry,
    ReadCode,
    SetStatus,
    SharedToken,
    all_invariants,
    canonical_registry,
    find_line,
    line_ids,
    read_set,
    registry_digest,
    registry_sound,
)
from tests.support import (
    ListingResolver,
    canned_resolver,
    import_sandbox,
    load_line_package,
    resolved,
    write_line_package,
)


APPENDED = LineEntry(
    id="teal_line",
    color="teal",
    question="What has not been asked yet?",
    job="A color invented for this test and nowhere else",
    must_not_become="Part of the declared set",
    opus_stage=None,
    working_position=len(LINE_SET) + 1,
    package_name="teal_line",
    registry_noun="openings",
    verdict_noun="opening status",
)

EXTENDED = LINE_SET + (APPENDED,)


def test_the_extended_declaration_passes_the_whole_structural_battery() -> None:
    results = all_invariants(EXTENDED, SHARED_TOKENS)
    assert all(result.passed for result in results), [
        result for result in results if not result.passed
    ]
    assert registry_sound(EXTENDED, SHARED_TOKENS)
    assert line_ids(EXTENDED)[-1] == APPENDED.id
    assert find_line(APPENDED.id, EXTENDED) is APPENDED
    assert find_line(APPENDED.id) is None, "the real declaration is untouched"


def test_an_appended_color_with_no_opus_stage_keeps_the_orders_diverging() -> None:
    """Stages stay optional; a new line need not borrow one."""
    assert APPENDED.opus_stage is None
    stages = [entry.opus_stage for entry in EXTENDED if entry.opus_stage is not None]
    assert len(stages) == len(set(stages))


def test_the_reader_reads_the_extended_set_without_being_told_about_it(
    tmp_path: Path,
) -> None:
    with import_sandbox():
        for entry in EXTENDED:
            write_line_package(
                tmp_path,
                entry.package_name,
                (f"{entry.color.upper()}_TOKEN",),
                registry_sizes={"ENTRIES": entry.working_position},
            )
        resolver = ListingResolver(
            {
                entry.package_name: resolved(
                    entry.package_name, load_line_package(tmp_path, entry.package_name)
                )
                for entry in EXTENDED
            },
            listed=tuple(entry.package_name for entry in EXTENDED),
        )
        reading = read_set(EXTENDED, SHARED_TOKENS, resolver=resolver)

    assert reading.status is SetStatus.SET_LEGIBLE
    assert len(reading.observations) == len(EXTENDED)
    assert reading.counts()[ReadCode.RESOLVED.value] == len(EXTENDED)
    assert reading.observations[-1].line_id == APPENDED.id
    assert reading.observations[-1].registry_size == APPENDED.working_position


def test_an_appended_color_that_borrows_a_token_is_still_caught(
    tmp_path: Path,
) -> None:
    """Extending the set does not soften the contract it exists to hold."""
    borrowed = "SHARED_SPELLING"
    with import_sandbox():
        write_line_package(tmp_path, LINE_SET[0].package_name, ("ALPHA", borrowed))
        write_line_package(tmp_path, APPENDED.package_name, (borrowed,))
        resolver = canned_resolver(
            {
                name: resolved(name, load_line_package(tmp_path, name))
                for name in (LINE_SET[0].package_name, APPENDED.package_name)
            }
        )
        reading = read_set((LINE_SET[0], APPENDED), (), resolver=resolver)

    assert reading.status is SetStatus.SET_COLLIDING
    assert reading.collisions[0].token == borrowed
    assert set(reading.collisions[0].lines) == {LINE_SET[0].id, APPENDED.id}


def test_an_appended_color_may_declare_its_own_exemption(tmp_path: Path) -> None:
    borrowed = "SHARED_SPELLING"
    declared = SharedToken(
        token=borrowed,
        lines=(LINE_SET[0].id, APPENDED.id),
        meanings=(
            (LINE_SET[0].id, f"the {LINE_SET[0].id} sense"),
            (APPENDED.id, f"the {APPENDED.id} sense"),
        ),
        rationale="two senses that happen to be spelled the same way",
    )
    with import_sandbox():
        write_line_package(tmp_path, LINE_SET[0].package_name, ("ALPHA", borrowed))
        write_line_package(tmp_path, APPENDED.package_name, (borrowed,))
        resolver = ListingResolver(
            {
                name: resolved(name, load_line_package(tmp_path, name))
                for name in (LINE_SET[0].package_name, APPENDED.package_name)
            },
            listed=(LINE_SET[0].package_name, APPENDED.package_name),
        )
        reading = read_set((LINE_SET[0], APPENDED), (declared,), resolver=resolver)

    assert reading.status is SetStatus.SET_LEGIBLE
    assert [collision.token for collision in reading.exempted_collisions] == [borrowed]


def test_the_serializer_covers_the_appended_line_and_moves_the_digest() -> None:
    extended = canonical_registry(EXTENDED, SHARED_TOKENS)
    assert APPENDED.id in extended
    assert registry_digest(EXTENDED, SHARED_TOKENS) != registry_digest(
        LINE_SET, SHARED_TOKENS
    )
    for field in dataclasses.fields(LineEntry):
        assert field.name in extended


def test_the_wrapper_entry_still_appends_cleanly_to_the_longer_set() -> None:
    """Self-application survives another color, given a renumbered wrapper."""
    renumbered = dataclasses.replace(WRAPPER_LINE, working_position=len(EXTENDED) + 1)
    results = all_invariants(EXTENDED + (renumbered,), SHARED_TOKENS)
    assert all(result.passed for result in results), [
        result for result in results if not result.passed
    ]

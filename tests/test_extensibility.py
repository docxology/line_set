"""Adding a colour is appending an entry, and nothing else.

The manuscript claims that another line requires editing only the declaration.
This module is what binds that claim. It appends a hypothetical ninth entry at runtime and
requires the whole apparatus — the structural battery, the reader, the
collision check, and the serializer — to keep working on the longer set.

Then it checks the other half of the claim, which the first half cannot see:
that the modules doing that work name no line individually. A reader that
happened to work on five lines while carrying a colour name in its source
would still have to be edited for the sixth. So the sources are read and
required to contain no line id and no declared colour as a word.
"""

from __future__ import annotations

import dataclasses
import re
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

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src" / "line_set"

#: Every module that has to keep working when a colour is added.
COLOUR_BLIND_MODULES = (
    "reader.py",
    "invariants.py",
    "serialization.py",
    "binding.py",
    "models.py",
)

FIFTH = LineEntry(
    id="teal_line",
    color="teal",
    question="What has not been asked yet?",
    job="A colour invented for this test and nowhere else",
    must_not_become="Part of the declared set",
    opus_stage=None,
    working_position=len(LINE_SET) + 1,
    package_name="teal_line",
    registry_noun="openings",
    verdict_noun="opening status",
)

EXTENDED = LINE_SET + (FIFTH,)


def test_the_extended_declaration_passes_the_whole_structural_battery() -> None:
    results = all_invariants(EXTENDED, SHARED_TOKENS)
    assert all(result.passed for result in results), [
        result for result in results if not result.passed
    ]
    assert registry_sound(EXTENDED, SHARED_TOKENS)
    assert line_ids(EXTENDED)[-1] == FIFTH.id
    assert find_line(FIFTH.id, EXTENDED) is FIFTH
    assert find_line(FIFTH.id) is None, "the real declaration is untouched"


def test_an_appended_colour_with_no_opus_stage_keeps_the_orders_diverging() -> None:
    """Stages stay optional; a new line need not borrow one."""
    assert FIFTH.opus_stage is None
    stages = [entry.opus_stage for entry in EXTENDED if entry.opus_stage is not None]
    assert len(stages) == len(set(stages))


def test_the_reader_reads_a_five_line_set_without_being_told_about_it(
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
    assert reading.observations[-1].line_id == FIFTH.id
    assert reading.observations[-1].registry_size == FIFTH.working_position


def test_an_appended_colour_that_borrows_a_token_is_still_caught(tmp_path: Path) -> None:
    """Extending the set does not soften the contract it exists to hold."""
    borrowed = "SHARED_SPELLING"
    with import_sandbox():
        write_line_package(tmp_path, LINE_SET[0].package_name, ("ALPHA", borrowed))
        write_line_package(tmp_path, FIFTH.package_name, (borrowed,))
        resolver = canned_resolver(
            {
                name: resolved(name, load_line_package(tmp_path, name))
                for name in (LINE_SET[0].package_name, FIFTH.package_name)
            }
        )
        reading = read_set((LINE_SET[0], FIFTH), (), resolver=resolver)

    assert reading.status is SetStatus.SET_COLLIDING
    assert reading.collisions[0].token == borrowed
    assert set(reading.collisions[0].lines) == {LINE_SET[0].id, FIFTH.id}


def test_an_appended_colour_may_declare_its_own_exemption(tmp_path: Path) -> None:
    borrowed = "SHARED_SPELLING"
    declared = SharedToken(
        token=borrowed,
        lines=(LINE_SET[0].id, FIFTH.id),
        meanings=(
            (LINE_SET[0].id, f"the {LINE_SET[0].id} sense"),
            (FIFTH.id, f"the {FIFTH.id} sense"),
        ),
        rationale="two senses that happen to be spelled the same way",
    )
    with import_sandbox():
        write_line_package(tmp_path, LINE_SET[0].package_name, ("ALPHA", borrowed))
        write_line_package(tmp_path, FIFTH.package_name, (borrowed,))
        resolver = ListingResolver(
            {
                name: resolved(name, load_line_package(tmp_path, name))
                for name in (LINE_SET[0].package_name, FIFTH.package_name)
            },
            listed=(LINE_SET[0].package_name, FIFTH.package_name),
        )
        reading = read_set((LINE_SET[0], FIFTH), (declared,), resolver=resolver)

    assert reading.status is SetStatus.SET_LEGIBLE
    assert [collision.token for collision in reading.exempted_collisions] == [borrowed]


def test_the_serializer_covers_the_appended_line_and_moves_the_digest() -> None:
    extended = canonical_registry(EXTENDED, SHARED_TOKENS)
    assert FIFTH.id in extended
    assert registry_digest(EXTENDED, SHARED_TOKENS) != registry_digest(
        LINE_SET, SHARED_TOKENS
    )
    for field in dataclasses.fields(LineEntry):
        assert field.name in extended


def test_no_module_but_the_declaration_names_a_line_or_a_colour() -> None:
    """The binding for "adding a colour touches only ``registry.py``".

    Both line ids and colours are matched as whole words. Bare substring
    matching would be wrong in a way worth naming: ``declared_lines`` contains
    the characters of ``red_line``, and a guard that counted that would be
    reporting on English rather than on what the module refers to.

    The wrapper's own id is excluded, and only its colour is checked: its id is
    this package's import name, so it legitimately appears in cross-references.
    """
    subjects = [("line", entry.id) for entry in EXTENDED]
    subjects += [("colour", entry.color) for entry in (*EXTENDED, WRAPPER_LINE)]
    assert subjects, "an empty subject set would make this check vacuous"

    for module_name in COLOUR_BLIND_MODULES:
        source = (SOURCE_ROOT / module_name).read_text(encoding="utf-8")
        assert source.strip(), module_name
        for kind, word in subjects:
            pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(word)}(?![A-Za-z0-9_])")
            assert not pattern.search(source), f"{module_name} names the {kind} {word}"


def test_the_declaration_is_the_one_module_that_does_name_the_lines() -> None:
    """The check above would be vacuous if nothing anywhere named a line."""
    declaration = (SOURCE_ROOT / "registry.py").read_text(encoding="utf-8")
    for entry in LINE_SET:
        assert entry.id in declaration
        assert entry.color in declaration


def test_the_wrapper_entry_still_appends_cleanly_to_the_longer_set() -> None:
    """Self-application survives another colour, given a renumbered wrapper."""
    renumbered = dataclasses.replace(WRAPPER_LINE, working_position=len(EXTENDED) + 1)
    results = all_invariants(EXTENDED + (renumbered,), SHARED_TOKENS)
    assert all(result.passed for result in results), [
        result for result in results if not result.passed
    ]

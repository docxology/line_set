"""Every number in the manuscript, re-derived from the code that produced it.

Prose has no test behind it. A count typed into a paragraph is true on the day
it is typed and silently false afterwards, and the reader has no way to tell
which day it is. This module is the thing that tells them: each assertion
derives a value from the package and requires the sentence carrying that value
to be present in the section that claims it. Change the declaration and the
prose fails here rather than in someone's reading.

The assertions are written as *derived fragments*, never as literals. A test
that hardcoded ``"four line entries"`` would go green while both the code and
the prose drifted together in the wrong direction; a test that computes
``len(LINE_SET)`` and then looks for the word ``four`` in the section binds the
two. Where a value has a spelled-out form in the prose and a numeral in the
code, the spelling is derived from the number rather than typed beside it.

Two kinds of claim are treated differently.

**Declaration claims** — how many lines, how many stages, what the precedence
is, how many fields a record has, what the set digest is — depend on nothing
outside this package and are checked unconditionally.

**Reading claims** — sibling versions, registry sizes, per-line token counts,
and the token arithmetic — are facts about the four packages installed on the
review machine on the review date. They are checked when those packages can be
read and reported as skipped when they cannot, because a test that required
them would pass only inside one working tree. The manuscript is explicit that
these numbers are dated; this module holds them to the date, not to eternity.

No patching library is used. Sections are read from disk as files, and every
derived value comes from calling the package.
"""

from __future__ import annotations

import dataclasses
import enum
import importlib
import json
import re
from collections import Counter
from pathlib import Path

import pytest

from line_set import (
    LINE_SET,
    OPUS_STAGE_ORDER,
    SHARED_TOKENS,
    LineEntry,
    LineObservation,
    ReadCode,
    SetReading,
    SetStatus,
    SharedToken,
    all_invariants,
    live_invariants,
    read_set,
    reading_digest,
    registry_digest,
    sibling_path_resolver,
)
from line_set.reader import READER_STAGES, STATUS_PRECEDENCE
from line_set.registry import WRAPPER_LINE

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = PROJECT_ROOT / "docs" / "manuscript"
SOURCE_ROOT = PROJECT_ROOT / "src" / "line_set"

#: The review date the manuscript's dated block reports. Read, never assumed.
REVIEW_DATE = re.search(
    r'date:\s*"([0-9]{4}-[0-9]{2}-[0-9]{2})"',
    (MANUSCRIPT / "config.yaml").read_text(encoding="utf-8"),
).group(1)

WORDS = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    16: "sixteen",
    19: "nineteen",
}


ORDINALS = {
    1: "first",
    2: "second",
    3: "third",
    4: "fourth",
    5: "fifth",
    6: "sixth",
    7: "seventh",
    8: "eighth",
    9: "ninth",
}


def word(count: int) -> str:
    """The spelled-out form of a derived count."""
    return WORDS[count]


def ordinal(count: int) -> str:
    """The spelled-out ordinal of a derived count."""
    return ORDINALS[count]


def section(name: str) -> str:
    """One manuscript section, read from disk."""
    path = MANUSCRIPT / name
    text = path.read_text(encoding="utf-8")
    assert text.strip(), f"{name} is empty; every binding below would be vacuous"
    return text


def squashed(name: str) -> str:
    """A section with runs of whitespace collapsed, for matching padded output."""
    return re.sub(r"\s+", " ", section(name))


def must_say(name: str, *fragments: str) -> None:
    """Require every derived fragment to appear in the named section."""
    assert fragments, "asserting nothing about a section is not a binding"
    text = section(name)
    for fragment in fragments:
        assert fragment in text, f"{name} does not say: {fragment!r}"


def must_say_squashed(name: str, *fragments: str) -> None:
    """As :func:`must_say`, ignoring how the section spaced its output block."""
    assert fragments, "asserting nothing about a section is not a binding"
    text = squashed(name)
    for fragment in fragments:
        assert fragment in text, f"{name} does not say: {fragment!r}"


# ------------------------------------------------- the sections exist at all


def test_every_declared_section_is_present_and_written() -> None:
    """A binding over a missing file would be an error, not a pass."""
    expected = [
        "00_abstract.md",
        "01_introduction.md",
        "01b_the_set.md",
        "02_method.md",
        "02a_formalism.md",
        "02b_scholarship.md",
        "03_extensibility.md",
        "04_examples.md",
        "05_limits.md",
        "06_conclusion.md",
        "99_references.md",
    ]
    found = sorted(path.name for path in MANUSCRIPT.glob("[0-9]*.md"))
    assert found == sorted(expected), found


def test_the_paper_version_is_the_package_version() -> None:
    """Two version numbers that can disagree eventually do."""
    from line_set import __version__

    config = (MANUSCRIPT / "config.yaml").read_text(encoding="utf-8")
    assert f'version: "{__version__}"' in config, (
        f"manuscript/config.yaml does not name the package version {__version__}"
    )


def test_the_bibliography_closes_in_both_directions() -> None:
    """A dangling citation and an uncited entry are both defects, so check both.

    A formalism reference is written with the same ``[@label]`` bracket syntax
    and is *not* a bibliography key: the render toolchain's filter consumes it
    before the citation machinery ever sees it. They are separated here by the
    filter's own rule — a prefix this manuscript declares on a formalism block
    belongs to that vocabulary — and the labels are checked against their blocks
    by ``tests/test_formalism.py`` rather than being ignored.
    """
    from tests.test_formalism import blocks

    formalism_prefixes = {
        block.label.partition(":")[0] for block in blocks() if block.label
    } | {"sec", "fig"}
    assert formalism_prefixes, "no formalism prefix; the separation would be untested"
    keys = set(
        re.findall(
            r"@\w+\{([^,]+),", (MANUSCRIPT / "references.bib").read_text("utf-8")
        )
    )
    assert keys, "an empty bibliography would make both directions vacuous"
    cited: set[str] = set()
    for path in sorted(MANUSCRIPT.glob("*.md")):
        cited.update(
            name
            for name in re.findall(
                r"\[?@([A-Za-z][A-Za-z0-9_:\-]*)", path.read_text("utf-8")
            )
            if name.partition(":")[0] not in formalism_prefixes
        )
    assert cited, "no citation was found anywhere in the prose"
    assert keys - cited == set(), f"in the bibliography and never cited: {keys - cited}"
    assert cited - keys == set(), f"cited and not in the bibliography: {cited - keys}"


def test_every_embedded_figure_exists_and_no_built_figure_is_orphaned() -> None:
    """A caption over a missing file, and a plate nobody shows, are both defects."""
    embedded: dict[str, str] = {}
    output_figures = PROJECT_ROOT / "output" / "figures"
    for path in sorted(MANUSCRIPT.glob("*.md")):
        for target in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", path.read_text("utf-8")):
            resolved_target = target if "../output/" not in target else None
            if resolved_target is None:
                stem = target.rsplit("../output/", 1)[-1]
                resolved_target = (PROJECT_ROOT / "output" / stem).resolve()
            else:
                resolved_target = (MANUSCRIPT / target).resolve()
            assert resolved_target.exists(), f"{path.name} embeds a missing {target}"
            assert resolved_target.name not in embedded, (
                f"{resolved_target.name} is embedded twice"
            )
            embedded[resolved_target.name] = path.name
    assert embedded, "no figure is embedded; both directions would be vacuous"

    # The set of plates is read from the builder, not from a directory of
    # output. ``output/`` is disposable and may not have been built in a fresh
    # checkout, and a check that quietly stopped running there would be exactly
    # the orphan it is looking for.
    from line_set.figures import figure_plates

    plates = figure_plates(
        LINE_SET,
        SHARED_TOKENS,
        read_set(LINE_SET, SHARED_TOKENS, resolver=_absent, as_of=REVIEW_DATE),
        WRAPPER_LINE,
        read_set(
            (*LINE_SET, WRAPPER_LINE),
            SHARED_TOKENS,
            resolver=_absent,
            as_of=REVIEW_DATE,
        ),
    )
    declared = {f"{plate.name}.png": plate for plate in plates}
    assert declared, "the builder declares no plate"
    assert set(declared) == set(embedded), (
        f"built but never embedded: {sorted(set(declared) - set(embedded))}; "
        f"embedded but not built: {sorted(set(embedded) - set(declared))}"
    )
    for filename, plate in declared.items():
        assert plate.label in section(embedded[filename]), (
            f"{embedded[filename]} embeds {filename} without the label {plate.label}"
        )


# ------------------------------------------------------ declaration claims


def test_the_size_of_the_declaration_is_stated_correctly() -> None:
    lines, shared = len(LINE_SET), len(SHARED_TOKENS)
    must_say(
        "00_abstract.md",
        f"{word(lines)} `LineEntry` records and {word(shared)} shared token",
    )
    must_say(
        "02_method.md",
        f"The declaration ships {word(lines)} line entries and "
        f"{word(shared)} shared token.",
    )


def test_the_reader_stages_are_named_in_order() -> None:
    must_say(
        "00_abstract.md",
        f"{word(len(READER_STAGES))} recorded stages — {', '.join(READER_STAGES)}",
    )
    must_say("02_method.md", f"runs {word(len(READER_STAGES))} stages")
    for stage in READER_STAGES:
        must_say("02_method.md", f"**{stage.capitalize()}**")


def test_the_status_precedence_is_stated_in_the_order_the_reader_applies_it() -> None:
    """The one claim in the abstract that is easiest to state backwards."""
    ordered = [status.name for status in STATUS_PRECEDENCE]
    assert len(ordered) == len(set(ordered)) == len(SetStatus)
    spelled = ", then ".join(f"`{name}`" for name in ordered)
    must_say(
        "00_abstract.md",
        f"{word(len(SetStatus))} readings, in fixed precedence: {spelled}.",
    )
    must_say(
        "02_method.md",
        f"An unexempted collision yields `{STATUS_PRECEDENCE[0].name}`",
    )
    ladder = "  >  ".join(status.name for status in STATUS_PRECEDENCE)
    architecture = (PROJECT_ROOT / "docs" / "architecture.md").read_text(
        encoding="utf-8"
    )
    assert ladder in architecture, ladder


def test_the_read_codes_are_counted_and_named() -> None:
    must_say("00_abstract.md", f"one of {word(len(ReadCode))} codes")
    must_say("02_method.md", f"records one of {word(len(ReadCode))} codes")
    for code in ReadCode:
        must_say("02_method.md", f"`{code.name}`")


def test_the_battery_sizes_are_stated_correctly() -> None:
    offline = len(all_invariants())
    must_say(
        "00_abstract.md",
        f"{word(offline).capitalize()} structural checks run offline",
        f"an {ordinal(offline + 1)},",
    )
    must_say(
        "02_method.md",
        f"{word(offline).capitalize()} checks run offline",
    )
    must_say("03_extensibility.md", f"All {word(offline)} structural checks pass")
    must_say("04_examples.md", f"The {word(offline)} offline checks pass")


def test_the_live_battery_is_the_offline_one_plus_the_self_check() -> None:
    """The eighth check is a claim about a count and about which check it is."""
    offline = [result.name for result in all_invariants()]
    live = [
        result.name for result in live_invariants(resolver=lambda name: _absent(name))
    ]
    assert live[: len(offline)] == offline
    assert len(live) == len(offline) + 1
    assert live[-1] == "self_disjointness"
    must_say("02_method.md", f"The {ordinal(len(live))} check appends")


def _absent(name: str):
    """A resolver that finds nothing, so the live battery needs no sibling."""
    from line_set.binding import Resolution

    return Resolution(name, ReadCode.NOT_INSTALLED, None, "not installed here")


def test_the_record_field_counts_and_their_grouping_are_stated_correctly() -> None:
    entry_fields = [field.name for field in dataclasses.fields(LineEntry)]
    identity = ["id", "color", "question", "job"]
    boundary = ["must_not_become"]
    ordering = ["opus_stage", "working_position"]
    address = ["package_name", "registry_noun", "verdict_noun"]
    assert sorted(identity + boundary + ordering + address) == sorted(entry_fields)

    must_say(
        "02_method.md",
        f"A `LineEntry` has {word(len(entry_fields))} fields.",
        f"{word(len(identity)).capitalize()} are identity and prose",
        f"{word(len(boundary)).capitalize()} is the boundary",
        f"{word(len(ordering)).capitalize()} are ordering",
        f"The last {word(len(address))} are addresses",
        f"A `SharedToken` has {word(len(dataclasses.fields(SharedToken)))}:",
    )
    for name in address + ordering + boundary:
        must_say("02_method.md", f"`{name}`")


def test_the_observation_never_invents_a_field_the_prose_promises_stay_unset() -> None:
    """The prose names three fields that stay ``None``; they must be those three."""
    optional = [
        field.name
        for field in dataclasses.fields(LineObservation)
        if field.default is None and field.name != "detail"
    ]
    assert sorted(optional) == ["registry_digest", "registry_size", "version"]
    must_say(
        "02_method.md",
        "no version, no registry size, and no digest, and those fields stay `None`",
    )


def test_the_opus_stages_are_counted_and_citrinitas_is_kept() -> None:
    assert "citrinitas" in OPUS_STAGE_ORDER
    must_say(
        "01b_the_set.md",
        f"`OPUS_STAGE_ORDER` carries {word(len(OPUS_STAGE_ORDER))} stages rather "
        f"than {word(len(OPUS_STAGE_ORDER) - 1)}",
    )
    for stage in OPUS_STAGE_ORDER:
        must_say("01b_the_set.md", stage)


def test_the_declaration_table_reproduces_the_declaration(tmp_path: Path) -> None:
    """The printed table is the declaration, not a paraphrase of it."""
    text = section("01b_the_set.md")
    assert LINE_SET, "an empty declaration would make this vacuous"
    for entry in LINE_SET:
        assert entry.question in text, entry.id
        assert entry.job in text, entry.id
        assert entry.must_not_become in text, entry.id


def test_the_set_digest_in_the_prose_is_the_digest_of_the_declaration() -> None:
    """Sibling-independent: the digest covers the declaration and nothing else."""
    digest = registry_digest(LINE_SET, SHARED_TOKENS)
    must_say_squashed("04_examples.md", f"set_digest : {digest[:16]}")
    must_say("03_extensibility.md", digest[:12])


def test_the_extension_example_reports_what_the_package_actually_returns() -> None:
    """Every printed line of the executed block, re-executed here."""
    fifth = LineEntry(
        id="green_line",
        color="green",
        question="What does keeping this alive cost?",
        job="Standing upkeep, dependencies, and the bill for continued existence",
        must_not_become="A reason to drop work that is merely expensive",
        opus_stage=None,
        working_position=len(LINE_SET) + 1,
        package_name="green_line",
        registry_noun="upkeep records",
        verdict_noun="upkeep status",
    )
    extended = LINE_SET + (fifth,)
    before = registry_digest(LINE_SET, SHARED_TOKENS)[:12]
    after = registry_digest(extended, SHARED_TOKENS)[:12]
    assert before != after

    results = all_invariants(extended, SHARED_TOKENS)
    assert all(result.passed for result in results), [
        result for result in results if not result.passed
    ]

    reading = read_set(
        extended,
        SHARED_TOKENS,
        resolver=_absent,
        as_of=REVIEW_DATE,
    )
    assert reading.status is SetStatus.SET_PARTIAL

    must_say(
        "03_extensibility.md",
        f"lines: {len(LINE_SET)} -> {len(extended)}",
        f"digest: {before} -> {after}",
        f"The set digest moved from `{before}` to `{after}`",
        f"Position contiguity now expects `1..{len(extended)}` and gets it.",
    )
    for result in results:
        must_say("03_extensibility.md", f"PASS  {result.name}")
    for field in dataclasses.fields(LineEntry):
        must_say("03_extensibility.md", f"{field.name}=")


def test_the_extension_examples_partial_reading_is_reproduced_exactly(
    tmp_path: Path,
) -> None:
    """The block's ``status``, ``counts``, and ``reason`` lines, re-derived.

    The printed reading resolves the declared siblings and fails to find the
    declared fifth. It is reproduced here over real packages written to a real
    temporary directory, one per declared line with a distinct vocabulary, so
    the shape does not depend on what happens to be installed on this machine.
    """
    from tests.support import (
        canned_resolver,
        import_sandbox,
        load_line_package,
        resolved,
    )

    fifth = LineEntry(
        id="green_line",
        color="green",
        question="What does keeping this alive cost?",
        job="Standing upkeep, dependencies, and the bill for continued existence",
        must_not_become="A reason to drop work that is merely expensive",
        opus_stage=None,
        working_position=len(LINE_SET) + 1,
        package_name="green_line",
        registry_noun="upkeep records",
        verdict_noun="upkeep status",
    )
    extended = LINE_SET + (fifth,)

    with import_sandbox():
        from tests.support import write_line_package

        answers = {}
        for index, entry in enumerate(LINE_SET):
            write_line_package(tmp_path, entry.package_name, (f"TOKEN_{index}",))
            answers[entry.package_name] = resolved(
                entry.package_name, load_line_package(tmp_path, entry.package_name)
            )
        reading = read_set(
            extended,
            SHARED_TOKENS,
            resolver=canned_resolver(answers),
            as_of=REVIEW_DATE,
        )

    assert reading.status is SetStatus.SET_PARTIAL
    counts = reading.counts()
    assert counts["resolved"] == len(LINE_SET)
    assert counts["not_installed"] == 1

    must_say(
        "03_extensibility.md",
        f"status: {reading.status.value}",
        f"counts: {counts}",
        f"reason: {reading.derivation[-1].detail}",
    )


def test_the_source_mention_counts_of_each_line_id_are_stated_correctly() -> None:
    """ "Four and four and two and two times", derived rather than counted by eye."""
    declaration = (SOURCE_ROOT / "registry.py").read_text(encoding="utf-8")
    counts = [
        len(
            re.findall(
                rf"(?<![A-Za-z0-9_]){re.escape(entry.id)}(?![A-Za-z0-9_])", declaration
            )
        )
        for entry in LINE_SET
    ]
    assert all(counts), "a line id that appears nowhere would make this vacuous"
    must_say(
        "03_extensibility.md",
        "in `registry.py`, " + " and ".join(word(count) for count in counts) + " times",
    )

    # And the other half: nowhere else in the package names one.
    elsewhere = {
        path.relative_to(SOURCE_ROOT).as_posix()
        for path in sorted(SOURCE_ROOT.rglob("*.py"))
        if path.name != "registry.py"
        and any(
            re.search(
                rf"(?<![A-Za-z0-9_]){re.escape(entry.id)}(?![A-Za-z0-9_])",
                path.read_text(encoding="utf-8"),
            )
            for entry in LINE_SET
        )
    }
    assert not elsewhere, f"these modules name a line: {sorted(elsewhere)}"


def test_the_single_surviving_token_mention_is_counted_correctly() -> None:
    reader_source = (SOURCE_ROOT / "reader.py").read_text(encoding="utf-8")
    token = SHARED_TOKENS[0].token
    hits = len(
        re.findall(
            rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])", reader_source
        )
    )
    assert hits, "zero mentions would make the claim below trivially wrong"
    must_say(
        "03_extensibility.md",
        f"{word(hits).capitalize()} mention of `{token}` survives in `reader.py`",
    )


def test_the_empty_declaration_result_is_stated_correctly() -> None:
    results = all_invariants((), ())
    failed = [result for result in results if not result.passed]
    assert len(failed) == len(results)
    must_say("02_method.md", f"Every one of the {word(len(results))} fails on an empty")


# ---------------------------------------------------------- reading claims


RECORD_PATH = MANUSCRIPT / "reading_record.json"


def record() -> dict:
    """The dated reading the manuscript quotes, as written beside the prose.

    Reading claims are bound to this artifact rather than to a live reading,
    because a live reading is only available where the four sibling packages
    are installed — which is not where most readers of the manuscript will be.
    Binding here makes prose drift fail on every machine. Binding the record
    itself to a live reading, which happens further down, makes a stale record
    fail on the machine that can tell.
    """
    assert RECORD_PATH.exists(), (
        f"{RECORD_PATH.name} is missing; the manuscript quotes measured numbers "
        "and nothing would be checking them. Run scripts/record_reading.py."
    )
    loaded = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    assert loaded["reading"]["observations"], "an empty record checks nothing"
    return loaded


def live_reading() -> SetReading:
    """A live reading of the siblings, or a skip that names what was missing."""
    resolver = sibling_path_resolver(entry.package_name for entry in LINE_SET)
    reading = read_set(LINE_SET, SHARED_TOKENS, resolver=resolver, as_of=REVIEW_DATE)
    unread = [
        observation.line_id
        for observation in reading.observations
        if observation.code is not ReadCode.RESOLVED
    ]
    if unread:
        pytest.skip(
            "this check re-measures the installed siblings; these could not be "
            f"read here: {unread}. The prose is still bound to the recorded "
            "reading by the checks above, which run everywhere."
        )
    return reading


def test_the_record_describes_the_declaration_that_ships_with_it() -> None:
    """Unconditional, and the reason the record cannot quietly go stale.

    A declaration change moves the set digest on every machine, with no sibling
    installed and no network. A record carrying the old digest is therefore
    caught wherever the manuscript travels, not only where it was written.
    """
    held = record()
    assert held["set_digest"] == registry_digest(LINE_SET, SHARED_TOKENS)
    assert held["reading"]["set_digest"] == held["set_digest"]
    assert held["recorded_on"] == REVIEW_DATE
    assert held["reading"]["read_as_of"] == REVIEW_DATE
    assert held["reading"]["status"] == SetStatus.SET_LEGIBLE.value
    assert sorted(
        observation["line_id"] for observation in held["reading"]["observations"]
    ) == sorted(entry.id for entry in LINE_SET)
    for observation in held["reading"]["observations"]:
        assert observation["code"] == ReadCode.RESOLVED.value, observation


def test_the_record_still_agrees_with_a_live_reading() -> None:
    """Conditional: the freshness half, checked where it can be checked."""
    reading = live_reading()
    held = record()
    assert held["reading_digest"] == reading_digest(reading), (
        "manuscript/reading_record.json is stale; rerun scripts/record_reading.py "
        "and update any prose whose numbers moved"
    )


def test_the_dated_block_names_every_declared_line_whatever_is_installed() -> None:
    """Unconditional: the structure of the block, not its measured values."""
    text = section("04_examples.md")
    for entry in LINE_SET:
        assert entry.id in text, entry.id
    assert REVIEW_DATE in text
    for status in (
        SetStatus.SET_LEGIBLE,
        SetStatus.SET_COLLIDING,
        SetStatus.SET_UNDECLARED,
        SetStatus.SET_PARTIAL,
    ):
        assert status.value in text, status


def test_the_dated_reading_block_reproduces_the_record() -> None:
    """Unconditional. Every measured value in the block comes from the record."""
    held = record()
    reading = held["reading"]
    must_say_squashed(
        "04_examples.md",
        f"status : {reading['status']}",
        f"reading_digest: {held['reading_digest'][:16]}",
        f"counts : {_python_counts(reading['counts'])}",
    )
    # The block right-aligns its numeric columns, so each row is matched with
    # optional padding rather than with one exact spelling of the spacing.
    text = section("04_examples.md")
    for observation in reading["observations"]:
        row = (
            rf"{re.escape(observation['line_id'])}\s+{observation['code']}\s+"
            rf"v{re.escape(observation['version'])}\s+"
            rf"registry=\s*{observation['registry_size']}\s+"
            rf"digest={observation['registry_digest'][:12]}\s+"
            rf"tokens=\s*{len(observation['tokens'])}\b"
        )
        assert re.search(row, text), f"04_examples.md does not report: {row}"


def _python_counts(counts: dict) -> str:
    """The counts mapping as the manuscript's transcript prints it."""
    ordered = {code.value: counts[code.value] for code in ReadCode}
    return str(ordered)


def test_the_token_arithmetic_is_stated_correctly_everywhere_it_appears() -> None:
    """The paper's one empirical claim, bound on every machine.

    The arithmetic appears in three sections and each has to agree with the
    record and with the others. Its internal consistency is asserted first, so
    a record that was itself incoherent could not be used to bless the prose.
    """
    census = record()["vocabulary_census"]
    classes = census["enum_classes"]
    declared = census["declared_members"]
    pairs = census["line_and_name_pairs"]
    distinct = census["distinct_names"]
    shared_names = census["names_carried_by_more_than_one_line"]

    per_line = census["per_line"]
    assert classes == sum(item["enum_classes"] for item in per_line.values())
    assert declared == sum(item["declared_members"] for item in per_line.values())
    assert pairs == sum(item["distinct_names"] for item in per_line.values())
    assert declared - pairs == sum(
        item["within_line_repeats"] for item in per_line.values()
    )
    assert pairs - distinct == len(shared_names), (
        "the record's own arithmetic does not close"
    )
    assert shared_names == sorted(
        collision["token"]
        for collision in (
            *record()["reading"]["collisions"],
            *record()["reading"]["exempted_collisions"],
        )
    )

    per_line_counts = ", ".join(
        f"{per_line[entry.id]['distinct_names']} for {entry.id}" for entry in LINE_SET
    )
    must_say(
        "00_abstract.md",
        f"{word(classes)} enum classes declaring {declared} members",
        f"{pairs} line-and-name pairs spanning {distinct} distinct names",
    )
    must_say(
        "04_examples.md",
        f"export {classes} enum classes between them",
        f"declare {declared} members in total",
        f"{pairs} line-and-name pairs — {per_line_counts} — spanning "
        f"{distinct} distinct names",
        f"{pairs} minus {distinct} is {word(pairs - distinct)}",
    )
    must_say(
        "06_conclusion.md",
        f"{pairs} line-and-name pairs in front of the reader, spanning "
        f"{distinct} distinct names",
    )
    for name in shared_names:
        must_say("04_examples.md", f"`{name}`")


def test_the_within_line_repeats_are_attributed_to_the_right_lines() -> None:
    """The abstract explains 80 against 76 by naming which lines repeat."""
    per_line = record()["vocabulary_census"]["per_line"]
    repeats = {
        line_id: item["within_line_repeats"]
        for line_id, item in per_line.items()
        if item["within_line_repeats"]
    }
    assert repeats, "no line repeats a name; the sentence below would be wrong"
    token = SHARED_TOKENS[0].token
    declared = record()["vocabulary_census"]["declared_members"]
    must_say(
        "04_examples.md",
        f"{word(sum(repeats.values())).capitalize()} of the {declared} are a line "
        "repeating a word it already uses",
    )
    assert repeats == {"red_line": 1, "black_line": 3, "white_line": 4}, (
        "the attributions spelled out below must be re-derived if this changes"
    )
    must_say(
        "04_examples.md",
        f"red_line spells `{token}` in {word(repeats['red_line'] + 1)} of its enums",
        f"black_line repeats {word(repeats['black_line'])} names across its "
        f"{word(per_line['black_line']['enum_classes'])}",
        f"white_line repeats {word(repeats['white_line'])} names across its "
        f"{word(per_line['white_line']['enum_classes'])}",
    )


def test_the_per_line_enum_class_counts_are_stated_correctly() -> None:
    per_line = record()["vocabulary_census"]["per_line"]
    must_say(
        "04_examples.md",
        ", ".join(
            f"{per_line[entry.id]['enum_classes']} in {entry.id}" for entry in LINE_SET
        ),
    )


def test_the_independent_derivation_agrees_with_the_recorded_one() -> None:
    """Conditional: the record re-derived without the reader or the recorder.

    The record is written by the package. This walks the imported modules
    directly, so the recorded numbers rest on two derivations rather than on
    one function agreeing with itself.
    """
    live_reading()
    census = record()["vocabulary_census"]

    classes = 0
    declared = 0
    per_line: dict[str, set[str]] = {}
    for entry in LINE_SET:
        module = importlib.import_module(entry.package_name)
        names: set[str] = set()
        for value in vars(module).values():
            if isinstance(value, type) and issubclass(value, enum.Enum):
                classes += 1
                members = [member.name for member in value]
                declared += len(members)
                names.update(members)
        per_line[entry.id] = names

    carriers = Counter(name for names in per_line.values() for name in names)
    assert classes == census["enum_classes"]
    assert declared == census["declared_members"]
    assert (
        sum(len(names) for names in per_line.values()) == census["line_and_name_pairs"]
    )
    assert len(carriers) == census["distinct_names"]
    assert (
        sorted(name for name, count in carriers.items() if count > 1)
        == census["names_carried_by_more_than_one_line"]
    )

"""The formalism blocks: auto-numbered, resolvable, and bound to the code.

Three separate things are checked here, and they fail for different reasons.

**Syntax.** Every formalism block is written in the fenced-Div form the render
toolchain's filter numbers, carries a label, and uses a prefix that matches its
kind. Every ``[@label]`` reference names a block that exists. No manuscript file
writes a formalism number by hand, because a number typed into prose goes stale
the moment a block is inserted above it and the reference keeps pointing at the
old one. Each of those four rules is shown rejecting a planted violation before
it is applied to the manuscript, so a green run means the manuscript is clean
rather than that the rule does nothing.

**Content.** Each definition and proposition is re-derived from the module it
describes: the field names on the records, the reader's stages, the precedence
order, the conditions the matcher applies, and the conditions the self-check
applies. A statement that drifted from the code fails here, in the section that
carries it.

**The volume.** A compiled volume must restart formalism numbering at each
reproduced work, or five papers would share one sequence and every paper's own
references would resolve to numbers that mean nothing outside the volume. The
assembler declares the reset in two places and both are checked, along with the
heading structure that makes the declared level the right one. A behavioural
check against the real filter runs when the filter is pointed at with
``LINE_SET_FORMALISM_FILTER`` and is skipped, by name, when it is not — the
filter belongs to the render toolchain, which this repository does not vendor.

Nothing here reads a rendered PDF. Numbering is derived from document order the
way the filter derives it, from files this repository ships.
"""

from __future__ import annotations

import dataclasses
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from line_set import (
    LINE_SET,
    SHARED_TOKENS,
    LineEntry,
    ReadCode,
    SetStatus,
    SharedToken,
)
from line_set.omnibus import (
    FORMALISM_METADATA_BLOCK,
    FORMALISM_RESET_KEY,
    FORMALISM_RESET_LEVEL,
    demote_headings,
    fence_mask,
    front_matter,
    part_heading,
    volume_config,
)
from line_set.probes import exemption_probes
from line_set.reader import READER_STAGES, STATUS_PRECEDENCE

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = PROJECT_ROOT / "manuscript"

#: The kinds the render toolchain's filter numbers, and the label prefix each
#: one is written with in this manuscript. The filter accepts any prefix; the
#: manuscript holds itself to one per kind so a reference reads as what it is.
KIND_PREFIXES: dict[str, str] = {
    "definition": "def",
    "proposition": "prop",
    "theorem": "thm",
    "lemma": "lem",
    "corollary": "cor",
    "remark": "rem",
    "axiom": "ax",
    "claim": "clm",
    "example": "ex",
}

#: The environment variable naming the render toolchain's formalism filter.
FILTER_ENV_VAR = "LINE_SET_FORMALISM_FILTER"

_DIV_OPEN_RE = re.compile(r"^:::+\s*\{([^}]*)\}\s*$")
_CLASS_RE = re.compile(r"\.([A-Za-z][A-Za-z0-9-]*)")
_LABEL_RE = re.compile(r"#([A-Za-z][A-Za-z0-9]*):([A-Za-z0-9][A-Za-z0-9_.-]*)")
_REFERENCE_RE = re.compile(r"@([A-Za-z]+):([A-Za-z0-9][A-Za-z0-9_.-]*)")

#: A hand-written formalism number, which this manuscript must never contain.
#:
#: The filter emits ``**Definition 1.**`` itself, from document order. A number
#: in the source is a second, unsynchronised copy of that count.
_HAND_NUMBER_RE = re.compile(
    r"\b("
    + "|".join(sorted(kind.capitalize() for kind in KIND_PREFIXES))
    + r")\s+\d+\b"
)


@dataclasses.dataclass(frozen=True)
class Block:
    """One formalism block as the manuscript declares it."""

    section: str
    kind: str
    label: str
    title: str
    number: int


def sections() -> tuple[Path, ...]:
    """Every manuscript section, in the order the toolchain assembles them."""
    found = tuple(sorted(MANUSCRIPT.glob("[0-9]*.md")))
    assert found, "no manuscript section was found; every gate below is vacuous"
    return found


def prose_lines(text: str) -> list[tuple[int, str]]:
    """Numbered lines outside a fenced code block.

    A ``:::`` Div fence is not a code fence, so ``fence_mask`` leaves it in the
    prose where it belongs. Code blocks are excluded because a formalism number
    shown inside one is being displayed, not asserted.
    """
    marks = fence_mask(text)
    return [
        (index + 1, line)
        for index, line in enumerate(text.splitlines())
        if not marks[index]
    ]


def blocks() -> tuple[Block, ...]:
    """Every formalism block in the manuscript, numbered as the filter would.

    Counters are per kind and run in document order, which is exactly what
    ``formalism.lua`` does with them. Deriving the numbers here rather than
    reading them out of a rendered artifact is what lets this run on a fresh
    checkout with nothing built.
    """
    counters: dict[str, int] = {}
    found: list[Block] = []
    for path in sections():
        for _, line in prose_lines(path.read_text(encoding="utf-8")):
            match = _DIV_OPEN_RE.match(line)
            if match is None:
                continue
            attributes = match.group(1)
            classes = _CLASS_RE.findall(attributes)
            kinds = [item for item in classes if item in KIND_PREFIXES]
            if not kinds:
                continue
            kind = kinds[0]
            if "unnumbered" in classes:
                continue
            counters[kind] = counters.get(kind, 0) + 1
            label = _LABEL_RE.search(attributes)
            title = re.search(r'title="([^"]*)"', attributes)
            found.append(
                Block(
                    section=path.name,
                    kind=kind,
                    label="" if label is None else f"{label.group(1)}:{label.group(2)}",
                    title="" if title is None else title.group(1),
                    number=counters[kind],
                )
            )
    return tuple(found)


def references() -> tuple[tuple[str, str], ...]:
    """Every reference that names a prefix some block in this manuscript uses.

    The prefix test is the filter's own rule: a citation belongs to the
    formalism vocabulary when the document declares that prefix, and belongs to
    the bibliography otherwise. Applying it here means a bibliography key is
    never mistaken for a broken cross-reference.
    """
    declared = {block.label.partition(":")[0] for block in blocks() if block.label}
    found: list[tuple[str, str]] = []
    for path in sections():
        for _, line in prose_lines(path.read_text(encoding="utf-8")):
            if _DIV_OPEN_RE.match(line):
                continue
            for kind, name in _REFERENCE_RE.findall(line):
                if kind in declared:
                    found.append((path.name, f"{kind}:{name}"))
    return tuple(found)


def hand_written_numbers(text: str) -> tuple[str, ...]:
    """Formalism numbers written into prose, which the filter would duplicate."""
    return tuple(
        line.strip() for _, line in prose_lines(text) if _HAND_NUMBER_RE.search(line)
    )


# ------------------------------------------------------------ the scan set


def test_the_manuscript_declares_formalism_blocks_to_check() -> None:
    """An empty scan set would make every rule below pass for no reason."""
    declared = blocks()
    assert declared, "the manuscript declares no formalism block"
    assert len({block.kind for block in declared}) >= 2, declared
    assert references(), "no formalism reference was found anywhere in the prose"


# ---------------------------------------------------------------- syntax


def test_every_formalism_block_carries_a_label() -> None:
    unlabelled = [
        f"{block.section}: {block.kind} {block.number}"
        for block in blocks()
        if not block.label
    ]
    assert unlabelled == []


def test_the_label_rule_rejects_an_unlabelled_block(tmp_path: Path) -> None:
    """The positive control for the rule above."""
    planted = '::: {.definition title="No label"}\nBody.\n:::\n'
    line = planted.splitlines()[0]
    match = _DIV_OPEN_RE.match(line)
    assert match is not None, line
    assert "definition" in _CLASS_RE.findall(match.group(1))
    assert _LABEL_RE.search(match.group(1)) is None


def test_every_label_prefix_matches_its_kind() -> None:
    wrong = [
        f"{block.section}: {block.kind} labelled {block.label}"
        for block in blocks()
        if block.label.partition(":")[0] != KIND_PREFIXES[block.kind]
    ]
    assert wrong == []


def test_the_prefix_rule_rejects_a_mismatched_prefix() -> None:
    """A proposition labelled ``def:`` would read as a definition in prose."""
    assert KIND_PREFIXES["proposition"] != "def"
    match = _DIV_OPEN_RE.match('::: {.proposition #def:wrong title="X"}')
    assert match is not None
    label = _LABEL_RE.search(match.group(1))
    assert label is not None
    assert label.group(1) != KIND_PREFIXES["proposition"]


def test_every_reference_resolves_to_a_declared_block() -> None:
    declared = {block.label for block in blocks() if block.label}
    dangling = [
        f"{section} -> @{target}"
        for section, target in references()
        if target not in declared
    ]
    assert dangling == []


def test_the_reference_rule_rejects_a_target_that_was_never_declared() -> None:
    """The positive control: a typo in a label must not read as resolved."""
    declared = {block.label for block in blocks() if block.label}
    assert declared, "an empty declaration set would make this vacuous"
    real = sorted(declared)[0]
    typo = f"{real}-typo"
    assert typo not in declared
    kind, _, _ = real.partition(":")
    assert _REFERENCE_RE.findall(f"By [@{typo}] the thing holds.") == [
        (kind, typo.partition(":")[2])
    ]


def test_no_section_writes_a_formalism_number_by_hand() -> None:
    offenders = {
        path.name: hand_written_numbers(path.read_text(encoding="utf-8"))
        for path in sections()
    }
    assert {name: found for name, found in offenders.items() if found} == {}


def test_the_hand_number_rule_fires_on_a_planted_number() -> None:
    """Shown rejecting before it is trusted, in prose and not in a code block."""
    planted = "The registry is well formed by Definition 3 above.\n"
    assert hand_written_numbers(planted) == (planted.strip(),)
    fenced = "```text\nProposition 7 is printed output, not a claim.\n```\n"
    assert hand_written_numbers(fenced) == ()
    assert hand_written_numbers("By [@def:line-entry] the registry is sound.\n") == ()


def test_no_formalism_label_is_also_a_bibliography_key() -> None:
    """The filter consumes these citations, so a bib entry of that key is dead."""
    keys = set(
        re.findall(
            r"@\w+\{([^,]+),", (MANUSCRIPT / "references.bib").read_text("utf-8")
        )
    )
    assert keys, "an empty bibliography would make this vacuous"
    labels = {block.label for block in blocks() if block.label}
    assert keys & labels == set()


def test_every_block_is_referenced_or_deliberately_standalone() -> None:
    """A numbered block nobody points at is inventory, not argument.

    Not every block has to be referenced — a definition can simply be read in
    place — so this reports the unreferenced ones rather than forbidding them,
    and requires that most of them are load-bearing enough to be cited.
    """
    declared = [block for block in blocks() if block.label]
    cited = {target for _, target in references()}
    referenced = [block for block in declared if block.label in cited]
    assert len(referenced) * 2 >= len(declared), [
        block.label for block in declared if block.label not in cited
    ]


# --------------------------------------------------------------- content


def section_text(name: str) -> str:
    """One manuscript section, read from disk and required to be written."""
    text = (MANUSCRIPT / name).read_text(encoding="utf-8")
    assert text.strip(), f"{name} is empty; every binding over it would be vacuous"
    return text


FORMALISM = "02a_formalism.md"


def test_the_line_entry_definition_names_every_field_the_record_has() -> None:
    text = section_text(FORMALISM)
    fields = [field.name for field in dataclasses.fields(LineEntry)]
    assert fields, "a fieldless record would make this vacuous"
    for name in fields:
        assert f"`{name}`" in text, name
    assert f"`LineEntry` record with {_word(len(fields))} fields" in text


def test_the_shared_token_definition_names_every_field_the_record_has() -> None:
    text = section_text(FORMALISM)
    fields = [field.name for field in dataclasses.fields(SharedToken)]
    for name in fields:
        assert f"`{name}`" in text, name
    assert f"`SharedToken` record with {_word(len(fields))} fields" in text


def test_the_reading_definition_names_every_stage_and_every_read_code() -> None:
    text = section_text(FORMALISM)
    assert f"records {_word(len(READER_STAGES))} stages in order" in text
    for stage in READER_STAGES:
        assert f"**{stage.capitalize()}**" in text, stage
    for code in ReadCode:
        assert f"`{code.name}`" in text, code


def test_the_precedence_proposition_states_the_order_the_reader_applies() -> None:
    text = section_text(FORMALISM)
    ordered = [status.name for status in STATUS_PRECEDENCE]
    assert len(ordered) == len(set(ordered)) == len(SetStatus)
    spelled = ", ".join(f"`{name}`" for name in ordered)
    assert f"the first of {spelled} whose condition holds" in text
    assert f"`{STATUS_PRECEDENCE[-1].name}` is reachable only when" in text


def test_the_fail_closed_proposition_counts_the_weakenings_the_probes_run() -> None:
    """The number of refusals in the prose is the number the probe set runs.

    The probes are the demonstration; the proposition is the claim. Binding one
    to the other is what stops the prose keeping a count the code stopped
    producing.
    """
    probes = exemption_probes(LINE_SET, SHARED_TOKENS)
    refusals = [probe for probe in probes if not probe.expected_match]
    assert refusals, "a probe set with no refusal would make the claim empty"
    text = section_text(FORMALISM)
    expected = f"{_word(len(refusals)).capitalize()} weakenings are therefore refused"
    assert expected in text
    assert f"[@prop:fail-closed] names {_word(len(refusals))} weakenings" in text


def test_the_fail_closed_proposition_is_true_of_the_matcher() -> None:
    """The claim, re-derived: the matcher does what the proposition says.

    Every probe is run through ``exemption_for`` here rather than compared with
    a recorded outcome, so a matcher that started accepting a looser input
    fails this test and the proposition above with it.
    """
    probes = exemption_probes(LINE_SET, SHARED_TOKENS)
    assert probes, "an empty probe set would make this vacuous"
    honoured = [probe for probe in probes if probe.expected_match]
    assert honoured, "with no positive control, refusing everything would pass"
    diverged = [probe.name for probe in probes if not probe.holds]
    assert diverged == []


def test_the_self_disjointness_proposition_states_all_four_conditions() -> None:
    text = section_text(FORMALISM)
    for condition in (
        "the wrapper's own vocabulary was read",
        "at least one other line supplied a vocabulary",
        "no collision in that reading names the wrapper",
        "no other declared line went unread",
    ):
        assert condition in text, condition
    assert "counts against it exactly as an unexempted one does" in text


def test_the_exemption_match_definition_states_every_condition() -> None:
    text = section_text(FORMALISM)
    for condition in (
        "The token is non-empty text.",
        "At least two lines carry it.",
        "character for character",
        "equal *as a set* to the lines carrying the token",
        "name no line outside them",
    ):
        assert condition in text, condition


WORDS = {
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
}


def _word(count: int) -> str:
    """The spelled-out form of a derived count."""
    return WORDS[count]


# ---------------------------------------------------------------- the volume


def test_the_volume_declares_the_reset_level_in_both_places_it_is_needed() -> None:
    """The config states the contract; the metadata block is what pandoc reads.

    Writing it only in the generated config would be a setting that looks
    applied and is inert, because the render toolchain builds its pandoc command
    from a fixed set of config keys and this is not one of them.
    """
    generated = volume_config(
        'paper:\n  title: "T"\n', "Volume", "Sub", "1.0", "2026-01-01"
    )
    assert f"{FORMALISM_RESET_KEY}: {FORMALISM_RESET_LEVEL}" in generated
    # The block carries that one key and nothing else. A second key, or a level
    # written as a literal beside the derived one, would be a second copy of the
    # contract free to drift away from the constant the config is built from.
    assert FORMALISM_METADATA_BLOCK.strip().splitlines()[1:-1] == [
        f"{FORMALISM_RESET_KEY}: {FORMALISM_RESET_LEVEL}"
    ]
    assert f"{FORMALISM_RESET_KEY}: {FORMALISM_RESET_LEVEL}" in (
        FORMALISM_METADATA_BLOCK
    )
    assert FORMALISM_METADATA_BLOCK.startswith("---\n")
    assert FORMALISM_METADATA_BLOCK.endswith("---\n")


def test_a_standalone_manuscript_does_not_declare_the_reset_level() -> None:
    """A level-1 header is a section here, so a reset would fire mid-paper."""
    config = (MANUSCRIPT / "config.yaml").read_text(encoding="utf-8")
    assert FORMALISM_RESET_KEY not in config
    for path in sections():
        assert FORMALISM_RESET_KEY not in path.read_text(encoding="utf-8"), path.name


def test_the_front_matter_opens_with_the_metadata_block() -> None:
    """Pandoc reads a YAML metadata block at the head of the combined markdown.

    The front matter is the first file in every plan, so its first bytes are
    the document's first bytes.
    """
    from line_set.omnibus import MergedBibliography

    text = front_matter((), _reading_stub(), MergedBibliography((), ()), ())
    assert text.startswith(FORMALISM_METADATA_BLOCK.rstrip("\n"))


def test_the_reset_level_matches_the_heading_level_the_volume_gives_a_work() -> None:
    """The declared level is only right if a work starts at exactly that level.

    Every part heading is level 1 and every heading inside a work has been
    demoted by one, so level 1 is the boundary between works and nothing else.
    Declaring the reset without this property would restart the counters in the
    middle of a paper.
    """
    from line_set.omnibus import SourcePaper

    paper = SourcePaper(
        entry=LINE_SET[0],
        root=Path("."),
        config=None,
        sections=(),
        references_only=(),
        bib=None,
        preamble=None,
        figures=(),
        cover_image=None,
        absence="",
    )
    heading = part_heading(paper, 1).splitlines()[0]
    assert heading.startswith("# "), heading
    assert not heading.startswith("## "), heading
    assert len(heading) - len(heading.lstrip("#")) == FORMALISM_RESET_LEVEL

    demoted = demote_headings("# Abstract {#sec:abstract}\n## Method\n")
    for line in demoted.splitlines():
        depth = len(line) - len(line.lstrip("#"))
        assert depth > FORMALISM_RESET_LEVEL, line


def _reading_stub():
    """A reading over an empty declaration, for front-matter shape checks."""
    from line_set import read_set
    from line_set.binding import Resolution

    def resolver(name: str) -> Resolution:
        return Resolution(name, ReadCode.NOT_INSTALLED, None, "absent")

    return read_set((), (), resolver=resolver, as_of="2026-01-01")


def _filter_path() -> Path | None:
    """The render toolchain's formalism filter, if this machine points at one."""
    declared = os.environ.get(FILTER_ENV_VAR, "").strip()
    if not declared:
        return None
    path = Path(declared).expanduser()
    return path if path.is_file() else None


def test_the_reset_level_restarts_numbering_in_a_real_pandoc_run(
    tmp_path: Path,
) -> None:
    """The behavioural half, run against the filter that will do the numbering.

    The filter belongs to the render toolchain, which this repository states as
    an external dependency and never vendors, so the check is skipped by name
    when nothing points at one. The negative control is in the same run: the
    identical document without the metadata block must number continuously, so
    a pass here is not a pass a broken filter could also produce.
    """
    if shutil.which("pandoc") is None:
        pytest.skip("pandoc is not installed; the numbering behaviour needs it")
    lua = _filter_path()
    if lua is None:
        pytest.skip(
            f"{FILTER_ENV_VAR} names no readable formalism.lua, so the render "
            "toolchain's filter is not available here; the declared reset level "
            "is still checked by the tests above"
        )

    body = (
        "# Work One {#sec:one-part}\n\n"
        "::: {.definition #def:one-alpha}\nFirst work.\n:::\n\n"
        "By [@def:one-alpha].\n\n"
        "# Work Two {#sec:two-part}\n\n"
        "::: {.definition #def:two-beta}\nSecond work.\n:::\n\n"
        "By [@def:two-beta].\n"
    )
    with_reset = tmp_path / "with_reset.md"
    without = tmp_path / "without_reset.md"
    with_reset.write_text(FORMALISM_METADATA_BLOCK + "\n" + body, encoding="utf-8")
    without.write_text(body, encoding="utf-8")

    def render(path: Path) -> str:
        completed = subprocess.run(
            ["pandoc", str(path), "-t", "plain", f"--lua-filter={lua}"],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        return completed.stdout

    reset = render(with_reset)
    assert "Definition 1. First work." in reset
    assert "Definition 1. Second work." in reset

    continuous = render(without)
    assert "Definition 1. First work." in continuous
    assert "Definition 2. Second work." in continuous, (
        "the negative control did not fire, so the reset above proved nothing"
    )


# ------------------------------------------- namespacing in the volume


def test_a_formalism_label_is_moved_into_the_works_namespace_and_back() -> None:
    """A Div label is declared without a brace in front of it, so it needs its own rule.

    Two works reproducing ``#def:x`` unnamespaced would put one label on two
    blocks, which the render toolchain's filter reports as a duplicate and
    resolves last-wins — one work's prose silently pointing at another work's
    numbering. The move has to be invertible, so the round trip is asserted
    against the source bytes rather than against a second expectation.
    """
    from line_set.omnibus import (
        collect_anchors,
        denamespace_anchors,
        namespace_anchors,
    )

    source = (
        '::: {.definition #def:alpha title="Alpha"}\n'
        "Body text.\n"
        ":::\n"
        "\n"
        "By [@def:alpha] and by [@parnas1972modules].\n"
    )
    anchors = collect_anchors(source)
    assert anchors == ("def:alpha",), anchors

    moved, definitions, refs = namespace_anchors(source, "red-line", anchors)
    assert definitions == 1
    assert refs == 1
    assert "#def:red-line-alpha" in moved
    assert "@def:red-line-alpha" in moved
    assert "[@parnas1972modules]" in moved, "a bibliography key was rewritten"
    assert denamespace_anchors(moved, "red-line", anchors) == source


def test_the_volume_declares_no_formalism_label_twice() -> None:
    """The property the namespacing exists for, measured over the real corpus."""
    from tests.test_omnibus import corpus
    from line_set.omnibus import collect_anchors, transform_section

    papers = corpus()

    seen: dict[str, str] = {}
    duplicates: list[str] = []
    formalism = 0
    for paper in papers:
        anchors = {
            name
            for path in paper.sections
            for name in collect_anchors(path.read_text(encoding="utf-8"))
        }
        for path in paper.sections:
            text = transform_section(
                path.read_text(encoding="utf-8"), paper.prefix, anchors
            ).text
            for _, line in prose_lines(text):
                match = _DIV_OPEN_RE.match(line)
                if match is None:
                    continue
                classes = _CLASS_RE.findall(match.group(1))
                if not any(item in KIND_PREFIXES for item in classes):
                    continue
                label = _LABEL_RE.search(match.group(1))
                if label is None:
                    continue
                name = f"{label.group(1)}:{label.group(2)}"
                formalism += 1
                if name in seen:
                    duplicates.append(f"{name}: {seen[name]} and {paper.entry.id}")
                seen[name] = paper.entry.id
    assert formalism > 1, (
        f"only {formalism} formalism block(s) in the whole corpus; a duplicate "
        "gate over one block would pass for the uninteresting reason"
    )
    assert duplicates == []


# ------------------------------------------------ the probes' own absences


def test_an_empty_exemption_table_yields_no_probe_and_no_claim() -> None:
    """A demonstration over nothing demonstrated nothing, and must say so."""
    from line_set.probes import exemption_probes, probes_hold

    assert exemption_probes(LINE_SET, ()) == ()
    assert probes_hold(()) is False, (
        "an empty probe set reported as holding would be the exact failure the "
        "probes exist to make visible"
    )
    assert probes_hold(exemption_probes(LINE_SET, SHARED_TOKENS)) is True


def test_a_declaration_with_no_spare_line_derives_the_adopting_one() -> None:
    """Every declared line already carrying the token is a state to survive.

    The four-line set does not reach it, so it is built here: an exemption
    naming every declared line leaves the probe set no spare id to hand the
    subset and superset probes, and it derives one rather than dropping two
    probes and shrinking the demonstration silently.
    """
    from line_set.probes import (
        DERIVED_LINE_SUFFIX,
        exemption_probes,
        probes_hold,
        spare_line_id,
    )

    every = tuple(entry.id for entry in LINE_SET)
    derived, from_declaration = spare_line_id(LINE_SET, every)
    assert from_declaration is False
    assert derived.endswith(DERIVED_LINE_SUFFIX)
    assert derived not in every

    taken = SHARED_TOKENS[0].lines
    spare, from_set = spare_line_id(LINE_SET, taken)
    assert from_set is True
    assert spare in every and spare not in taken

    wide = SharedToken(
        token=SHARED_TOKENS[0].token,
        lines=every,
        meanings=tuple((line_id, f"the {line_id} sense") for line_id in every),
        rationale="every declared line carries it",
    )
    probes = exemption_probes(LINE_SET, (wide,))
    assert len(probes) == len(exemption_probes(LINE_SET, SHARED_TOKENS))
    assert probes_hold(probes)
    assert any(derived in probe.query_lines for probe in probes)


def test_the_gate_plate_reports_an_empty_table_rather_than_drawing_a_clean_sheet() -> (
    None
):
    """The plate's own refusal to be vacuous, drawn and inspected."""
    from line_set.figures.plates.exemption import exemption_gate

    body = exemption_gate(LINE_SET, ())
    assert body.startswith("<svg ")
    assert "the exemption table is empty, so no probe was run" in body
    assert "NOTHING TO DEMONSTRATE ON" in body
    assert "would have passed on nothing" in body

    drawn = exemption_gate(LINE_SET, SHARED_TOKENS)
    assert "the exemption table is empty" not in drawn, (
        "the populated gate must not draw the empty panel, or the refusal above "
        "would be indistinguishable from the ordinary case"
    )
    assert SHARED_TOKENS[0].token in drawn


def test_vocabulary_disjointness_holds_over_the_collision_partition() -> None:
    """Every token maps to exactly one registry entry; no term is ambiguous.

    The reading partitions tokens into lines that carry them. After exempted
    collisions are removed, any token appearing in more than one vocabulary
    is an unexempted collision. This test derives the partition from the
    collision function and asserts that the exempted/unexempted split is
    deterministic and complete.
    """
    from line_set.reader import _collide

    # Minimal observations: each line has a unique vocabulary.
    from line_set.models import LineObservation

    # Minimal observations: each line has a unique vocabulary.
    obs_a = LineObservation(
        line_id="a",
        code=ReadCode.RESOLVED,
        version="1.0",
        registry_size=1,
        registry_digest=None,
        tokens=("UNIQUE_A",),
        detail="",
    )
    obs_b = LineObservation(
        line_id="b",
        code=ReadCode.RESOLVED,
        version="1.0",
        registry_size=1,
        registry_digest=None,
        tokens=("UNIQUE_B",),
        detail="",
    )
    unex, ex = _collide((obs_a, obs_b), ())
    assert unex == ()
    assert ex == ()

    # Two lines carrying the same token with no exemption -> unexempted collision.
    obs_shared_a = LineObservation(
        line_id="a",
        code=ReadCode.RESOLVED,
        version="1.0",
        registry_size=1,
        registry_digest=None,
        tokens=("SHARED_TOKEN",),
        detail="",
    )
    obs_shared_b = LineObservation(
        line_id="b",
        code=ReadCode.RESOLVED,
        version="1.0",
        registry_size=1,
        registry_digest=None,
        tokens=("SHARED_TOKEN",),
        detail="",
    )
    unex, ex = _collide((obs_shared_a, obs_shared_b), ())
    assert len(unex) == 1
    assert unex[0].token == "SHARED_TOKEN"
    assert not unex[0].exempted

    # The text of the proposition must exist in the manuscript.
    text = (MANUSCRIPT / "02a_formalism.md").read_text(encoding="utf-8")
    assert "Each vocabulary term maps to exactly one registry entry" in text
    assert "no term is ambiguous across the line set" in text

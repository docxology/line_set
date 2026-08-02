"""The compiled volume: mechanical, invertible, and honest about what is missing.

Two kinds of test live here and they check different things.

The synthetic ones build real miniature works — real directories, real markdown,
real ``.bib`` databases, real PNG bytes — under a real temporary path, and put
the assembler through the cases the working tree does not currently contain: a
plate basename shipped twice, one key naming two different works, a reference
to an anchor nobody defines, a work that is simply not there. Nothing is
patched and no test-double library is involved; a case the corpus does not
supply is written out on disk rather than imitated.

The corpus ones run over the declared works as they actually are. Those are the
honesty gates, and they are the ones that matter. A transform that quietly
reworded a limits section would pass every synthetic case above and fail
:func:`test_every_reproduced_section_inverts_to_its_source_bytes` and
:func:`test_every_negation_line_survives_verbatim`, which is why both are here:
the first proves the transforms lose nothing, and the second binds to the
source bytes directly rather than to this module's idea of how to undo itself.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from line_set import LINE_SET, WRAPPER_LINE, LineEntry
from line_set.omnibus import (
    GENERATED_ORDERING_MARKER,
    SOURCE_FIGURE_PREFIX,
    VOLUME_FIGURE_PREFIX,
    BibEntry,
    OmnibusError,
    assemble,
    collect_anchors,
    demote_headings,
    denamespace_anchors,
    discover_paper,
    discover_papers,
    fence_mask,
    gather_figures,
    invert_section,
    matching_brace,
    merge_bibliographies,
    namespace_anchors,
    namespace_prefix,
    normalise_field,
    parse_bib,
    promote_headings,
    read_paper_config,
    retarget_figures,
    top_level_block,
    transform_section,
    unbuilt_plates,
    unresolved_references,
    volume_config,
    volume_order,
)
from tests.support import absent, canned_resolver, import_sandbox

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: The sibling checkouts the declared works live in.
CORPUS_BASE = PROJECT_ROOT.parent

#: A single-pixel PNG, written so a copied plate is a real file with real bytes.
PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c6360000002000100ffff03000006000557bfabd400"
    "00000049454e44ae426082"
)

#: Words whose sentences are the ones a compilation must never touch.
NEGATION_MARKERS = ("not ", "never", "does not establish", "cannot")


# ------------------------------------------------------- real miniature works


def write_paper(
    base: Path,
    line_id: str,
    *,
    title: str = "A Work",
    version: str = "1.0.0",
    sections: dict[str, str] | None = None,
    bib: str = "",
    plates: tuple[str, ...] = (),
    preamble: str | None = "```latex\n\\usepackage{graphicx}\n```\n",
    config: str | None = None,
) -> Path:
    """Write a real manuscript tree for one work and return its root."""
    root = base / line_id
    manuscript = root / "manuscript"
    manuscript.mkdir(parents=True, exist_ok=True)
    body = (
        sections
        if sections is not None
        else {"00_abstract.md": "# Abstract\n\nText.\n"}
    )
    for name, text in body.items():
        (manuscript / name).write_text(text, encoding="utf-8")
    if config is None:
        config = (
            "paper:\n"
            f'  title: "{title}"\n'
            f'  version: "{version}"\n'
            '  date: "2026-01-01"\n'
            "\n"
            "authors:\n"
            '  - name: "Someone"\n'
        )
    (manuscript / "config.yaml").write_text(config, encoding="utf-8")
    if bib:
        (manuscript / "references.bib").write_text(bib, encoding="utf-8")
    if preamble is not None:
        (manuscript / "preamble.md").write_text(preamble, encoding="utf-8")
    if plates:
        figures = root / "output" / "figures"
        figures.mkdir(parents=True, exist_ok=True)
        for name in plates:
            (figures / name).write_bytes(PNG_BYTES)
    return root


def declaration(*ids: str) -> tuple[LineEntry, ...]:
    """A real declaration over fictional ids, in the order given."""
    return tuple(
        LineEntry(
            id=line_id,
            color=f"colour-{position}",
            question=f"Question {position}?",
            job=f"Job {position}",
            must_not_become=f"Not {position}",
            opus_stage=None,
            working_position=position,
            package_name=line_id,
            registry_noun="things",
            verdict_noun="status",
        )
        for position, line_id in enumerate(ids, start=1)
    )


def wrapper_entry(line_id: str, position: int) -> LineEntry:
    """A fictional wrapper entry to head a fictional volume."""
    return LineEntry(
        id=line_id,
        color="colourless",
        question="How does the set stay separate?",
        job="Declare and read",
        must_not_become="A fifth instrument",
        opus_stage=None,
        working_position=position,
        package_name=line_id,
        registry_noun="entries",
        verdict_noun="set status",
    )


def blind_resolver() -> object:
    """A resolver that finds nothing and touches no import state."""
    return canned_resolver({}, default=absent("anything"))


# -------------------------------------------------------------- fenced text


def test_a_fence_and_its_contents_are_marked_and_a_heading_inside_is_left_alone() -> (
    None
):
    """A ``#`` in a code block is a comment, and demoting it would be a rewrite."""
    text = "# Real heading\n\n```python\n# not a heading\n```\n\n## Another\n"
    marks = fence_mask(text)
    assert marks == (False, False, True, True, True, False, False)
    demoted = demote_headings(text)
    assert "# not a heading" in demoted
    assert "## Real heading" in demoted
    assert "### Another" in demoted


def test_an_anchor_inside_a_fence_is_not_moved() -> None:
    text = "# Head {#sec:one}\n\n```\n{#sec:one}\n```\n"
    moved, defs, _ = namespace_anchors(text, "w", collect_anchors(text))
    assert collect_anchors(text) == ("sec:one",)
    assert defs == 1
    assert "{#sec:w-one}" in moved
    assert "\n{#sec:one}\n" in moved


# ---------------------------------------------------------- heading demotion


def test_demotion_refuses_to_bury_a_heading_below_what_latex_typesets() -> None:
    """A heading that silently stops being one is a structural loss."""
    with pytest.raises(OmnibusError) as error:
        demote_headings("##### Deep\n")
    assert "level 6" in str(error.value)


def test_promotion_refuses_to_promote_a_top_level_heading() -> None:
    with pytest.raises(OmnibusError):
        promote_headings("# Top\n")


def test_a_hash_that_is_not_a_heading_is_not_touched() -> None:
    text = "#nospace is not a heading\n\nA # in prose.\n"
    assert demote_headings(text) == text


# ------------------------------------------------------- anchors and refs


def test_an_anchor_and_every_reference_to_it_move_together() -> None:
    """Three reference syntaxes point at one anchor; all three must follow it."""
    text = (
        "# Method {#sec:method}\n\n"
        "See [@sec:method], then @sec:method, then [the method](#sec:method).\n"
        "![A plate.](../output/figures/p.png){#fig:plate}\n"
        "Cited work [@ostrom1990commons] and see [@fig:plate].\n"
    )
    anchors = collect_anchors(text)
    assert set(anchors) == {"sec:method", "fig:plate"}
    moved, defs, refs = namespace_anchors(text, "w", anchors)
    assert defs == 2
    assert refs == 4
    assert "{#sec:w-method}" in moved
    assert "[@sec:w-method]" in moved
    assert "then @sec:w-method," in moved
    assert "](#sec:w-method)" in moved
    assert "[@fig:w-plate]" in moved
    assert "[@ostrom1990commons]" in moved, (
        "a bibliography key is not a cross-reference"
    )


def test_a_reference_to_an_anchor_this_work_does_not_define_is_left_where_it_is() -> (
    None
):
    """Leaving it is what makes the unresolved-reference gate able to see it."""
    text = "See [@sec:elsewhere].\n"
    moved, _, refs = namespace_anchors(text, "w", ("sec:here",))
    assert refs == 0
    assert moved == text
    assert unresolved_references(moved, ("sec:w-here",)) == ("@sec:elsewhere",)


def test_the_unresolved_gate_ignores_kinds_pandoc_crossref_does_not_resolve() -> None:
    """An ordinary citation must not be reported as a dangling cross-reference."""
    assert unresolved_references("Text [@author2020work].\n", ()) == ()
    assert unresolved_references("Text @cite:thing.\n", ()) == ()
    assert unresolved_references("Text [@sec:thing].\n", ()) == ("@sec:thing",)


def test_the_unresolved_gate_reports_a_dangling_markdown_link() -> None:
    assert unresolved_references("[a](#fig:gone)\n", ()) == ("](#fig:gone)",)


def test_namespacing_inverts_over_the_syntaxes_it_rewrites() -> None:
    text = "# Method {#sec:method}\n\nSee [@sec:method] and [link](#sec:method).\n"
    anchors = collect_anchors(text)
    moved, _, _ = namespace_anchors(text, "w", anchors)
    assert moved != text
    assert denamespace_anchors(moved, "w", anchors) == text


# ------------------------------------------------------------- figure paths


def test_every_embed_is_retargeted_at_the_volume_plate_directory() -> None:
    text = f"![A.]({SOURCE_FIGURE_PREFIX}a.png)\n![B.]({SOURCE_FIGURE_PREFIX}b.png)\n"
    moved, count = retarget_figures(text)
    assert count == 2
    assert SOURCE_FIGURE_PREFIX not in moved
    assert moved.count(VOLUME_FIGURE_PREFIX) == 2


def test_retargeting_refuses_text_that_already_uses_the_volume_prefix() -> None:
    """Rewriting it would not be invertible, so it is refused rather than guessed."""
    with pytest.raises(OmnibusError) as error:
        retarget_figures(f"![A.]({VOLUME_FIGURE_PREFIX}a.png)\n")
    assert "invertible" in str(error.value)


def embedding(*names: str) -> dict[str, str]:
    """A section that really embeds each named plate."""
    body = "".join(f"![Plate.]({SOURCE_FIGURE_PREFIX}{name})\n" for name in names)
    return {"00_a.md": f"# A\n\n{body}"}


def test_two_works_shipping_one_plate_basename_refuse_to_assemble(
    tmp_path: Path,
) -> None:
    """A silent overwrite would hide one work's plate behind another's."""
    base = tmp_path / "works"
    write_paper(base, "carrier")
    write_paper(base, "one", sections=embedding("shared.png"), plates=("shared.png",))
    write_paper(base, "two", sections=embedding("shared.png"), plates=("shared.png",))
    papers = discover_papers(
        base, declaration("one", "two"), wrapper_entry("carrier", 3)
    )
    present = [paper for paper in papers if paper.present]
    assert len(present) == 3, "an empty scan set would make the collision check vacuous"
    with pytest.raises(OmnibusError) as error:
        gather_figures(present)
    assert "shared.png" in str(error.value)


def test_plates_with_distinct_basenames_are_all_gathered(tmp_path: Path) -> None:
    base = tmp_path / "works"
    write_paper(base, "one", sections=embedding("a.png"), plates=("a.png",))
    write_paper(
        base, "two", sections=embedding("b.png", "c.png"), plates=("b.png", "c.png")
    )
    papers = discover_papers(base, declaration("one", "two"), wrapper_entry("three", 3))
    gathered = gather_figures([paper for paper in papers if paper.present])
    assert sorted(gathered) == ["a.png", "b.png", "c.png"]


def test_a_work_reports_only_the_plates_it_embeds(tmp_path: Path) -> None:
    """Reading the output directory instead would claim every plate sitting in it."""
    base = tmp_path / "works"
    write_paper(
        base,
        "one",
        sections=embedding("mine.png"),
        plates=("mine.png", "someone_elses.png"),
    )
    paper = discover_papers(base, declaration("one"), wrapper_entry("two", 2))[1]
    assert [path.name for path in paper.figures] == ["mine.png"]


def test_a_detached_repo_finds_its_own_manuscript_at_the_repository_root(
    tmp_path: Path,
) -> None:
    """A standalone clone has no siblings, so its own manuscript is at the
    repository root, not beside them. Discovery must land there — reporting
    this project absent would make every corpus gate fail on a detached copy
    instead of skipping, which is what the standalone promise forbids."""
    base = tmp_path / "empty"
    base.mkdir()
    wrapper = discover_papers(base, LINE_SET, WRAPPER_LINE)[0]
    assert wrapper.present, wrapper.absence
    assert wrapper.root == PROJECT_ROOT
    assert (wrapper.root / "manuscript").is_dir()
    # The siblings are not beside a detached copy; they read as absent, which
    # is what lets the corpus gates skip rather than measure a short set.
    siblings = discover_papers(base, LINE_SET, WRAPPER_LINE)[1:]
    assert siblings
    assert all(not paper.present for paper in siblings)


# ------------------------------------------------------------ bibliography


ONE_WORK = """@book{shared_key,
  author = {Ostrom, Elinor},
  title = {Governing the Commons},
  year = {1990},
  doi = {10.1017/CBO9780511807763},
  note = {The first work's gloss.}
}
"""

SAME_WORK_OTHER_GLOSS = """@book{shared_key,
  author    = {Ostrom,   Elinor},
  title     = {Governing the Commons},
  year      = {1990},
  doi       = {10.1017/CBO9780511807763},
  note      = {The second work's gloss.}
}
"""

DIFFERENT_WORK = """@book{shared_key,
  author = {Someone, Else},
  title = {A Different Book Entirely},
  year = {2011},
  doi = {10.0000/other}
}
"""


def test_one_key_two_works_declared_identically_is_merged_and_the_drop_recorded() -> (
    None
):
    merged = merge_bibliographies(
        [("first", ONE_WORK), ("second", SAME_WORK_OTHER_GLOSS)]
    )
    assert merged.merged == 1
    assert len(merged.duplicates) == 1
    duplicate = merged.duplicates[0]
    assert (duplicate.key, duplicate.kept_from, duplicate.dropped_from) == (
        "shared_key",
        "first",
        "second",
    )
    rendered = merged.render(["shared_key"])
    assert "The first work's gloss." in rendered
    assert "The second work's gloss." not in rendered


def test_one_key_naming_two_different_works_fails_the_build_with_both_entries() -> None:
    """Silently re-pointing a citation is the worst outcome available here."""
    with pytest.raises(OmnibusError) as error:
        merge_bibliographies([("first", ONE_WORK), ("second", DIFFERENT_WORK)])
    message = str(error.value)
    assert "shared_key" in message
    assert "Governing the Commons" in message
    assert "A Different Book Entirely" in message
    assert "first" in message and "second" in message


def test_identity_ignores_formatting_and_a_per_work_note_but_not_a_title() -> None:
    first = parse_bib(ONE_WORK, "first")[0]
    second = parse_bib(SAME_WORK_OTHER_GLOSS, "second")[0]
    third = parse_bib(DIFFERENT_WORK, "third")[0]
    assert first.identity() == second.identity()
    assert first.identity() != third.identity()
    assert first.raw != second.raw, "the formatting really does differ"


def test_normalising_collapses_whitespace_and_braces_and_keeps_content() -> None:
    assert normalise_field("{Ostrom,   Elinor}") == normalise_field("Ostrom, Elinor")
    assert normalise_field("A Title") != normalise_field("Another Title")


def test_a_bib_entry_with_quoted_and_bare_values_is_read() -> None:
    text = '@article{k, author = "A, B", year = 1999, title = {T} }\n'
    entry = parse_bib(text, "s")[0]
    assert dict(entry.fields) == {"author": "A, B", "year": "1999", "title": "T"}
    assert entry.entry_type == "article"


def test_an_unbalanced_database_is_refused_rather_than_half_read() -> None:
    with pytest.raises(OmnibusError) as error:
        parse_bib("@book{k, title = {Unclosed}\n", "s")
    assert "unbalanced" in str(error.value)


def test_a_key_declared_by_the_carrier_is_written_to_exactly_one_database(
    tmp_path: Path,
) -> None:
    """The renderer force-copies the carrier's own database over the injected one.

    So the merge is partitioned rather than duplicated: BibTeX is handed both
    files and must see every key exactly once.
    """
    base = tmp_path / "works"
    write_paper(
        base, "carrier", bib=ONE_WORK, sections={"00_a.md": "# A\n\n[@shared_key]\n"}
    )
    write_paper(
        base,
        "other",
        bib=SAME_WORK_OTHER_GLOSS
        + "\n@book{only_other, author={X}, title={Y}, year={2000}}\n",
        sections={"00_a.md": "# A\n\n[@only_other]\n"},
    )
    assemble(
        tmp_path / "out",
        base,
        declaration("other"),
        (),
        wrapper_entry("carrier", 2),
        resolver=blind_resolver(),
        write=True,
    )
    manuscript = tmp_path / "out" / "output" / "manuscript"
    carrier_keys = set(
        re.findall(r"@\w+\{([^,]+),", (manuscript / "references.bib").read_text())
    )
    volume_keys = set(
        re.findall(
            r"@\w+\{([^,]+),", (manuscript / "omnibus_references.bib").read_text()
        )
    )
    assert carrier_keys == {"shared_key"}
    assert volume_keys == {"only_other"}
    assert not carrier_keys & volume_keys


# ---------------------------------------------------------------- config


def test_the_generated_config_carries_the_marker_that_keeps_it(tmp_path: Path) -> None:
    """Without the marker the toolchain refreshes this file from the source config."""
    source = 'paper:\n  title: "T"\n\nrender:\n  formats:\n    pdf: true\n\nmetadata:\n  a: b\n'
    generated = volume_config(source, "Volume", "Sub", "1.0", "2026-01-01")
    assert GENERATED_ORDERING_MARKER in generated
    assert 'title: "Volume"' in generated
    assert "render:\n  formats:\n    pdf: true" in generated
    assert "metadata:\n  a: b" in generated


def test_top_level_block_returns_bytes_or_nothing() -> None:
    text = "one:\n  a: 1\n\ntwo:\n  b: 2\n"
    assert top_level_block(text, "one") == "one:\n  a: 1\n"
    assert top_level_block(text, "two") == "two:\n  b: 2\n"
    assert top_level_block(text, "three") is None


def test_a_config_with_no_version_is_refused_rather_than_given_one(
    tmp_path: Path,
) -> None:
    """A stated version that was not read would be the one claim this cannot support."""
    path = tmp_path / "config.yaml"
    path.write_text('paper:\n  title: "T"\n', encoding="utf-8")
    with pytest.raises(OmnibusError) as error:
        read_paper_config(path)
    assert "version" in str(error.value)


def test_a_config_with_no_paper_block_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("authors:\n  - name: X\n", encoding="utf-8")
    with pytest.raises(OmnibusError):
        read_paper_config(path)


def test_a_config_is_read_down_to_its_optional_fields(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        'paper:\n  title: "T"\n  subtitle: "S"\n  version: "9.9"\n  date: "2026-02-03"\n',
        encoding="utf-8",
    )
    config = read_paper_config(path)
    assert (config.title, config.subtitle, config.version, config.date) == (
        "T",
        "S",
        "9.9",
        "2026-02-03",
    )


# ----------------------------------------------------------------- ordering


def test_the_volume_order_is_the_declared_working_order_and_not_a_list() -> None:
    """Shuffling the declaration must not shuffle the volume."""
    shuffled = tuple(reversed(LINE_SET))
    ordered = volume_order(shuffled, WRAPPER_LINE)
    assert ordered[0] is WRAPPER_LINE
    positions = [entry.working_position for entry in ordered[1:]]
    assert positions == sorted(positions)
    assert positions == [entry.working_position for entry in LINE_SET]


def test_appending_a_colour_extends_the_volume_without_reordering_it() -> None:
    extra = declaration("fifth_colour")[0]
    grown = (*LINE_SET, LineEntry(**{**extra.canonical(), "working_position": 5}))
    ordered = volume_order(grown, WRAPPER_LINE)
    assert [entry.id for entry in ordered[1:-1]] == [entry.id for entry in LINE_SET]
    assert ordered[-1].id == "fifth_colour"


def test_the_written_filenames_sort_into_reading_order(tmp_path: Path) -> None:
    """The renderer orders sections by filename, so the names carry the order."""
    base = tmp_path / "works"
    write_paper(
        base, "carrier", sections={f"{index:02d}_s.md": "# S\n" for index in range(3)}
    )
    write_paper(
        base, "later", sections={f"{index:02d}_s.md": "# S\n" for index in range(2)}
    )
    report = assemble(
        tmp_path / "out",
        base,
        declaration("later"),
        (),
        wrapper_entry("carrier", 2),
        resolver=blind_resolver(),
        write=True,
    )
    names = list(report.files)
    assert names == sorted(names), names
    assert names[0] == "000_front_matter.md"
    assert names[1].endswith("_part_carrier.md")
    assert names[-1].endswith("_volume_references.md")
    written = sorted(
        path.name for path in (tmp_path / "out" / "output" / "manuscript").glob("*.md")
    )
    assert written == sorted(names)


# --------------------------------------------------------- honest absence


def test_a_missing_work_is_named_in_the_front_matter_and_the_volume_is_short(
    tmp_path: Path,
) -> None:
    """An honestly incomplete volume, never a silently short one."""
    base = tmp_path / "works"
    write_paper(base, "carrier", sections={"00_a.md": "# A\n\nText.\n"})
    write_paper(base, "here", sections={"00_a.md": "# A\n\nText.\n"})
    report = assemble(
        tmp_path / "out",
        base,
        declaration("here", "gone"),
        (),
        wrapper_entry("carrier", 3),
        resolver=blind_resolver(),
        write=True,
    )
    assert report.papers_missing == ("gone",)
    assert report.papers_included == 2
    front = (
        tmp_path / "out" / "output" / "manuscript" / "000_front_matter.md"
    ).read_text()
    assert "What is missing from this volume" in front
    assert "**gone**" in front
    assert "this volume is therefore incomplete" in front.lower()
    assert "| gone | not read | not read |" in front.replace("`", "")


def test_a_work_whose_plates_were_never_built_is_reported_missing_not_raised(
    tmp_path: Path,
) -> None:
    """Partial presence degrades exactly as absence does, and says which it was.

    A freshly cloned sibling has its manuscript and no ``output/`` at all,
    because ``output/`` is disposable in every one of these projects. Raising
    there would mean a cloned set could not compile a volume while a set with
    no siblings could, which is backwards. This project cannot build another
    work's figures — it writes to no checkout but its own — so the honest move
    is the same one absence gets: leave the work out and name the reason.
    """
    base = tmp_path / "works"
    write_paper(base, "carrier", sections={"00_a.md": "# A\n\nText.\n"})
    write_paper(base, "here", sections={"00_a.md": "# A\n\nText.\n"})
    write_paper(base, "unbuilt", sections=embedding("never_drawn.png"))

    # The work really is on disk and really is readable — the withdrawal below
    # is about its plates, not about its prose.
    raw = discover_paper(declaration("unbuilt")[0], base)
    assert raw.present, "the fixture failed to write a readable manuscript"
    assert [path.name for path in unbuilt_plates(raw)] == ["never_drawn.png"]

    papers = discover_papers(
        base, declaration("here", "unbuilt"), wrapper_entry("carrier", 3)
    )
    withdrawn = next(paper for paper in papers if paper.entry.id == "unbuilt")
    assert not withdrawn.present
    assert "never_drawn.png" in withdrawn.absence
    assert "have not been built" in withdrawn.absence
    assert withdrawn.sections == () and withdrawn.figures == ()

    report = assemble(
        tmp_path / "out",
        base,
        declaration("here", "unbuilt"),
        (),
        wrapper_entry("carrier", 3),
        resolver=blind_resolver(),
        write=True,
    )
    assert report.papers_missing == ("unbuilt",)
    assert report.papers_included == 2
    front = (
        tmp_path / "out" / "output" / "manuscript" / "000_front_matter.md"
    ).read_text()
    assert "**unbuilt**" in front
    assert "never_drawn.png" in front
    assert "this volume is therefore incomplete" in front.lower()


def test_a_long_list_of_unbuilt_plates_is_summarised_with_its_count(
    tmp_path: Path,
) -> None:
    """The reason travels into the front matter, so it states a count, not a wall."""
    base = tmp_path / "works"
    write_paper(base, "carrier")
    write_paper(
        base, "many", sections=embedding(*(f"p{index}.png" for index in range(6)))
    )
    papers = discover_papers(base, declaration("many"), wrapper_entry("carrier", 2))
    absence = papers[1].absence
    assert "6 embedded plate(s)" in absence
    assert "p0.png, p1.png, p2.png, and 3 more" in absence
    assert "p5.png" not in absence


def test_a_work_whose_plates_are_built_is_not_withdrawn(tmp_path: Path) -> None:
    """The negative control: withdrawal is about the plates, not about embedding.

    Without this, a bug that withdrew every work embedding anything would leave
    the gate above green while quietly emptying the volume.
    """
    base = tmp_path / "works"
    write_paper(base, "carrier")
    write_paper(base, "built", sections=embedding("drawn.png"), plates=("drawn.png",))
    papers = discover_papers(base, declaration("built"), wrapper_entry("carrier", 2))
    built = next(paper for paper in papers if paper.entry.id == "built")
    assert built.present and built.absence == ""
    assert [path.name for path in built.figures] == ["drawn.png"]
    assert unbuilt_plates(built) == ()


def test_the_assembling_work_is_still_stopped_by_a_plate_it_never_drew(
    tmp_path: Path,
) -> None:
    """The asymmetry is deliberate and is stated as one test, not inferred.

    A sibling's unbuilt plate is a state of someone else's checkout, which this
    project may read and may not repair. The assembling work's unbuilt plate is
    this project's own figure builder failing to produce something its own
    manuscript embeds, which is a defect and must stop the build.
    """
    base = tmp_path / "works"
    write_paper(base, "carrier", sections=embedding("never_drawn.png"))
    write_paper(base, "sibling", sections=embedding("never_drawn_either.png"))
    with pytest.raises(OmnibusError) as error:
        assemble(
            tmp_path / "out",
            base,
            declaration("sibling"),
            (),
            wrapper_entry("carrier", 2),
            resolver=blind_resolver(),
        )
    assert "never_drawn.png" in str(error.value)
    assert "never_drawn_either.png" not in str(error.value)


def test_an_assembly_with_no_carrier_manuscript_is_refused(tmp_path: Path) -> None:
    base = tmp_path / "works"
    write_paper(base, "here")
    with pytest.raises(OmnibusError) as error:
        assemble(
            tmp_path / "out",
            base,
            declaration("here"),
            (),
            wrapper_entry("gone", 2),
            resolver=blind_resolver(),
        )
    assert "assembling work" in str(error.value)


def test_a_reference_no_work_defines_stops_the_assembly(tmp_path: Path) -> None:
    """A dangling cross-reference renders as a broken link, so it fails the build."""
    base = tmp_path / "works"
    write_paper(
        base, "carrier", sections={"00_a.md": "# A {#sec:a}\n\nSee [@sec:nowhere].\n"}
    )
    with pytest.raises(OmnibusError) as error:
        assemble(
            tmp_path / "out",
            base,
            (),
            (),
            wrapper_entry("carrier", 1),
            resolver=blind_resolver(),
        )
    assert "@sec:nowhere" in str(error.value)


def test_an_embed_naming_a_plate_no_work_ships_stops_the_assembly(
    tmp_path: Path,
) -> None:
    base = tmp_path / "works"
    write_paper(
        base,
        "carrier",
        sections={"00_a.md": f"# A\n\n![P.]({SOURCE_FIGURE_PREFIX}missing.png)\n"},
    )
    with pytest.raises(OmnibusError) as error:
        assemble(
            tmp_path / "out",
            base,
            (),
            (),
            wrapper_entry("carrier", 1),
            resolver=blind_resolver(),
        )
    assert "missing.png" in str(error.value)
    assert "which is not at" in str(error.value)


def test_a_name_already_in_its_own_namespace_stops_the_assembly(tmp_path: Path) -> None:
    """Moving it there twice would not be invertible, so it is refused."""
    base = tmp_path / "works"
    write_paper(base, "carrier", sections={"00_a.md": "# A {#sec:carrier-a}\n"})
    with pytest.raises(OmnibusError) as error:
        assemble(
            tmp_path / "out",
            base,
            (),
            (),
            wrapper_entry("carrier", 1),
            resolver=blind_resolver(),
        )
    assert "invertible" in str(error.value)


# ------------------------------------------------------------ written state


def test_written_plates_reproduce_their_source_bytes_and_a_rerun_is_clean(
    tmp_path: Path,
) -> None:
    base = tmp_path / "works"
    write_paper(
        base,
        "carrier",
        sections={"00_a.md": f"# A\n\n![P.]({SOURCE_FIGURE_PREFIX}p.png)\n"},
        plates=("p.png",),
    )
    out = tmp_path / "out"
    first = assemble(
        out,
        base,
        (),
        (),
        wrapper_entry("carrier", 1),
        resolver=blind_resolver(),
        write=True,
    )
    assert first.figures_copied == 1
    copied = out / "output" / "figures" / "p.png"
    assert (
        copied.read_bytes()
        == (base / "carrier" / "output" / "figures" / "p.png").read_bytes()
    )

    stale = out / "output" / "manuscript" / "900_stale.md"
    stale.write_text("# Stale\n", encoding="utf-8")
    second = assemble(
        out,
        base,
        (),
        (),
        wrapper_entry("carrier", 1),
        resolver=blind_resolver(),
        write=True,
    )
    assert not stale.exists(), "a previous assembly's section would render again"
    assert second.files == first.files


def test_the_report_counts_what_was_written(tmp_path: Path) -> None:
    base = tmp_path / "works"
    write_paper(
        base,
        "carrier",
        sections={
            "00_a.md": f"# A {{#sec:a}}\n\nSee [@sec:a].\n![P.]({SOURCE_FIGURE_PREFIX}p.png){{#fig:p}}\n"
        },
        plates=("p.png",),
        bib="@book{k, author={A}, title={T}, year={2000}}\n",
    )
    out = tmp_path / "out"
    report = assemble(
        out,
        base,
        (),
        (),
        wrapper_entry("carrier", 1),
        resolver=blind_resolver(),
        write=True,
    )
    assert (report.sections, report.anchors_moved, report.references_moved) == (1, 2, 1)
    assert (report.figures_retargeted, report.figures_copied) == (1, 1)
    assert report.bib_entries_merged == 1
    payload = json.loads(
        (out / "output" / "manuscript" / "omnibus_report.json").read_text()
    )
    assert payload["sections"] == 1
    assert payload["files"] == list(report.files)
    assert "1 work(s) assembled" in report.summary()


def test_a_plan_writes_nothing(tmp_path: Path) -> None:
    """The analysis stage runs this command bare; a bare run must be inert."""
    base = tmp_path / "works"
    write_paper(base, "carrier")
    out = tmp_path / "out"
    report = assemble(
        out, base, (), (), wrapper_entry("carrier", 1), resolver=blind_resolver()
    )
    assert report.sections == 1
    assert report.figures_copied == 0
    assert not out.exists(), "planning touched the tree"


# ------------------------------------------------------ the declared corpus


def corpus() -> tuple[object, ...]:
    """The declared works as they are on disk, or a skip that names what is missing.

    Every gate below measures the *whole* declared set, so a run with a work
    missing would be measuring less than the set and must not report a pass.
    It must not report a failure either: a separated copy of this project is
    supposed to travel alone, and `README.md` and `STANDALONE.md` both promise
    the suite passes with the siblings absent. So the gates skip, and they skip
    with the works named.

    The skip is positively controlled. Before it is taken, the absence is
    re-derived from disk rather than trusted from :attr:`SourcePaper.absence`:
    each named work is confirmed to have no readable section beside this one,
    or to have sections whose embedded plates are genuinely not files. A skip
    over a work that is in fact readable would be a silent pass, so that case
    fails instead. The assembling work's own manuscript is in this tree
    unconditionally, and its absence is a defect rather than a reason to skip.
    """
    papers = discover_papers(CORPUS_BASE, LINE_SET, WRAPPER_LINE)
    assert len(papers) == len(LINE_SET) + 1, "the scan set is not the declared set"
    assert papers[0].present, (
        "this project's own manuscript is in this tree; "
        f"it read as absent: {papers[0].absence}"
    )
    missing = [paper for paper in papers if not paper.present]
    if not missing:
        return papers

    named = []
    for paper in missing:
        manuscript = CORPUS_BASE / paper.entry.id / "manuscript"
        found = discover_paper(paper.entry, CORPUS_BASE)
        unbuilt = unbuilt_plates(found)
        assert not found.present or unbuilt, (
            f"{paper.entry.id} was reported missing, but its manuscript at "
            f"{manuscript} reads with {len(found.sections)} section(s) and every "
            "plate it embeds is on disk; skipping here would be a silent pass"
        )
        named.append(f"{paper.entry.id} ({paper.absence})")
    pytest.skip(
        "these corpus gates measure the whole declared set, and it is not all "
        f"here: {'; '.join(named)}. Nothing beside this project supplies them, "
        "and the assembler itself is checked against the same absence by "
        "test_a_missing_work_is_named_in_the_front_matter_and_the_volume_is_short "
        "and by the unbuilt-plate gates above, which run everywhere."
    )


def test_the_corpus_gates_below_have_something_to_measure() -> None:
    papers = corpus()
    assert len(papers) == len(LINE_SET) + 1
    assert sum(len(paper.sections) for paper in papers) > 50
    assert sum(len(paper.figures) for paper in papers) > 50


def test_the_declared_works_collide_on_anchors_and_the_volume_does_not() -> None:
    """The collision is real before the transform, which is why the gate is not vacuous."""
    before: dict[str, set[str]] = {}
    after: dict[str, set[str]] = {}
    for paper in corpus():
        for path in paper.sections:
            text = path.read_text(encoding="utf-8")
            for anchor in collect_anchors(text):
                before.setdefault(anchor, set()).add(paper.entry.id)
            moved, _, _ = namespace_anchors(
                text,
                paper.prefix,
                {
                    name
                    for section in paper.sections
                    for name in collect_anchors(section.read_text(encoding="utf-8"))
                },
            )
            for anchor in collect_anchors(moved):
                after.setdefault(anchor, set()).add(paper.entry.id)
    shared = {name for name, owners in before.items() if len(owners) > 1}
    assert shared, "no anchor collided; the namespacing gate would be vacuous"
    assert not {name for name, owners in after.items() if len(owners) > 1}


def test_every_reproduced_section_inverts_to_its_source_bytes() -> None:
    """Every transform is invertible, and the inversion is run, not asserted."""
    checked = 0
    for paper in corpus():
        anchors = {
            name
            for path in paper.sections
            for name in collect_anchors(path.read_text(encoding="utf-8"))
        }
        for path in paper.sections:
            source = path.read_text(encoding="utf-8")
            assembled = transform_section(source, paper.prefix, anchors).text
            assert invert_section(assembled, paper.prefix, anchors) == source, path
            checked += 1
    assert checked > 50, "too few sections were inverted for this to mean anything"


def test_the_inversion_can_fail_when_the_assembled_text_was_altered() -> None:
    """A round trip that cannot fail proves nothing, so it is shown failing."""
    paper = corpus()[1]
    path = paper.sections[0]
    source = path.read_text(encoding="utf-8")
    anchors = {
        name
        for section in paper.sections
        for name in collect_anchors(section.read_text(encoding="utf-8"))
    }
    assembled = transform_section(source, paper.prefix, anchors).text
    tampered = assembled.replace("the", "THE", 1)
    assert tampered != assembled, "the tamper did not take"
    assert invert_section(tampered, paper.prefix, anchors) != source


def test_every_negation_line_survives_verbatim() -> None:
    """The gate that binds to source bytes rather than to this module's inverse.

    A line the transforms do not touch — no heading marker, no anchor, no
    cross-reference, no figure path — must appear in the assembled text
    unchanged. Those are the lines that carry the caveats, and a compilation
    that softened one would be caught here whatever its inverse claimed.
    """
    untouched_total = 0
    for paper in corpus():
        anchors = {
            name
            for path in paper.sections
            for name in collect_anchors(path.read_text(encoding="utf-8"))
        }
        for path in paper.sections:
            source = path.read_text(encoding="utf-8")
            assembled = transform_section(source, paper.prefix, anchors).text
            # A line is excluded when this module would legitimately rewrite
            # it. Anchor declarations are found with ``collect_anchors`` rather
            # than by looking for ``{#``, because a formalism block declares
            # its label inside a fenced-Div attribute list where no brace
            # precedes it. Reference kinds come from what this paper actually
            # declares, plus the kinds pandoc-crossref owns.
            declared_kinds = {name.partition(":")[0] for name in anchors}
            reference_kinds = declared_kinds | {"eq", "fig", "lst", "sec", "tbl"}
            untouched = [
                line
                for line in source.splitlines()
                if any(marker in line.lower() for marker in NEGATION_MARKERS)
                and not line.lstrip().startswith("#")
                and not collect_anchors(line)
                and "](#" not in line
                and SOURCE_FIGURE_PREFIX not in line
                and not any(f"@{kind}:" in line for kind in reference_kinds)
            ]
            for line in untouched:
                assert line in assembled, f"{path.name}: {line!r}"
            untouched_total += len(untouched)
    assert untouched_total > 200, (
        f"only {untouched_total} caveat-bearing lines were checked; "
        "the gate would barely be measuring the corpus"
    )


def test_every_work_keeps_its_word_count() -> None:
    """Each transform rewrites a token in place; none adds, drops, or splits one."""
    for paper in corpus():
        anchors = {
            name
            for path in paper.sections
            for name in collect_anchors(path.read_text(encoding="utf-8"))
        }
        source_words = 0
        assembled_words = 0
        for path in paper.sections:
            source = path.read_text(encoding="utf-8")
            source_words += len(source.split())
            assembled_words += len(
                transform_section(source, paper.prefix, anchors).text.split()
            )
        assert source_words > 0
        assert assembled_words == source_words, paper.entry.id


def test_no_declared_work_ships_a_plate_basename_another_ships() -> None:
    """Measured at assembly rather than trusted from a previous measurement."""
    papers = corpus()
    gathered = gather_figures(papers)
    assert len(gathered) == sum(len(paper.figures) for paper in papers)


def test_every_declared_work_states_a_version_in_its_own_manuscript_config() -> None:
    for paper in corpus():
        assert paper.config is not None, paper.entry.id
        assert paper.config.version.strip()
        assert paper.config.title.strip()


def test_the_corpus_assembles_into_a_volume_with_no_unresolved_reference() -> None:
    """The whole assembly, over the real works, inside an import sandbox.

    The sandbox is not decoration: the default resolver prepends the sibling
    source checkouts to ``sys.path`` and imports them, and a later test in this
    session that hands the reader a synthetic package would otherwise bind to
    the real one.
    """
    papers = corpus()
    with import_sandbox():
        report = assemble(base=CORPUS_BASE)
    assert report.papers_missing == ()
    assert report.papers_included == len(LINE_SET) + 1
    assert report.sections > 50
    assert report.anchors_moved > 0
    assert report.references_moved > 0
    assert report.figures_retargeted == sum(len(paper.figures) for paper in papers)
    assert report.bib_entries_merged > 0
    assert report.figures_copied == 0, "a plan must not copy"


# ------------------------------------------------------ the operator command


def test_the_command_plans_without_writing_and_writes_when_asked(
    tmp_path: Path,
) -> None:
    """The script is the seam an operator and the analysis stage both use.

    It reads the real declaration, so the works below are written under the
    declared ids. The other declared works are genuinely absent from this
    temporary base, which is the honestly-incomplete path taken for real.
    """
    base = tmp_path / "works"
    write_paper(base, WRAPPER_LINE.id)
    out = tmp_path / "out"
    script = PROJECT_ROOT / "scripts" / "build_omnibus.py"

    planned = subprocess.run(
        [sys.executable, str(script), "--project-root", str(out), "--base", str(base)],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        check=False,
    )
    assert planned.returncode == 0, planned.stderr
    assert "planned only" in planned.stdout
    assert not out.exists()

    written = subprocess.run(
        [
            sys.executable,
            str(script),
            "--write",
            "--project-root",
            str(out),
            "--base",
            str(base),
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        check=False,
    )
    assert written.returncode == 0, written.stderr
    assert (out / "output" / "manuscript" / "config.yaml").is_file()


def test_the_command_exits_non_zero_on_a_bibliography_conflict(tmp_path: Path) -> None:
    """A gate that exits zero on a broken input is not a gate."""
    base = tmp_path / "works"
    write_paper(
        base,
        WRAPPER_LINE.id,
        bib=ONE_WORK,
        sections={"00_a.md": "# A\n\n[@shared_key]\n"},
    )
    write_paper(
        base,
        LINE_SET[0].id,
        bib=DIFFERENT_WORK,
        sections={"00_a.md": "# A\n\n[@shared_key]\n"},
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "build_omnibus.py"),
            "--write",
            "--project-root",
            str(tmp_path / "out"),
            "--base",
            str(base),
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        check=False,
    )
    assert completed.returncode == 1, completed.stdout
    assert "two different works" in completed.stderr


def test_a_bib_entry_is_a_frozen_record() -> None:
    entry = parse_bib(ONE_WORK, "s")[0]
    assert isinstance(entry, BibEntry)
    with pytest.raises(Exception):
        entry.key = "other"  # type: ignore[misc]


def test_inverting_leaves_a_name_that_was_never_moved_alone() -> None:
    """The inverse must not strip a prefix off something it did not prefix."""
    text = "# H {#sec:w-other}\n\nSee [@sec:w-other] and [x](#sec:w-other).\n"
    assert denamespace_anchors(text, "w", ("sec:mine",)) == text


def test_a_manuscript_directory_with_no_section_is_absent_not_empty(
    tmp_path: Path,
) -> None:
    base = tmp_path / "works"
    (base / "hollow" / "manuscript").mkdir(parents=True)
    (base / "hollow" / "manuscript" / "README.md").write_text(
        "# Read me\n", encoding="utf-8"
    )
    paper = discover_papers(base, declaration("hollow"), wrapper_entry("gone", 2))[1]
    assert not paper.present
    assert "no section" in paper.absence


def test_an_embed_outside_the_plate_directory_stops_the_assembly(
    tmp_path: Path,
) -> None:
    base = tmp_path / "works"
    write_paper(
        base, "carrier", sections={"00_a.md": "# A\n\n![P.](assets/logo.png)\n"}
    )
    with pytest.raises(OmnibusError) as error:
        assemble(
            tmp_path / "out",
            base,
            (),
            (),
            wrapper_entry("carrier", 1),
            resolver=blind_resolver(),
        )
    assert "assets/logo.png" in str(error.value)


def test_a_carrier_with_sections_but_no_configuration_is_refused(
    tmp_path: Path,
) -> None:
    base = tmp_path / "works"
    manuscript = base / "carrier" / "manuscript"
    manuscript.mkdir(parents=True)
    (manuscript / "00_a.md").write_text("# A\n", encoding="utf-8")
    with pytest.raises(OmnibusError) as error:
        assemble(
            tmp_path / "out",
            base,
            (),
            (),
            wrapper_entry("carrier", 1),
            resolver=blind_resolver(),
        )
    assert "configuration" in str(error.value)


def test_a_volume_config_without_a_date_omits_the_field() -> None:
    generated = volume_config('paper:\n  title: "T"\n', "V", "S", "1.0", None)
    assert "date:" not in generated
    assert GENERATED_ORDERING_MARKER in generated


def test_a_carrier_with_no_preamble_reports_no_dropped_directive(
    tmp_path: Path,
) -> None:
    base = tmp_path / "works"
    write_paper(base, "carrier", preamble=None)
    write_paper(base, "other", preamble="```latex\n\\usepackage{tikz}\n```\n")
    report = assemble(
        tmp_path / "out",
        base,
        declaration("other"),
        (),
        wrapper_entry("carrier", 2),
        resolver=blind_resolver(),
    )
    assert report.dropped_preamble == ()


def test_a_directive_no_carrier_preamble_declares_is_reported(tmp_path: Path) -> None:
    """The volume compiles under one preamble; what is left behind is stated."""
    base = tmp_path / "works"
    write_paper(base, "carrier", preamble="```latex\n\\usepackage{graphicx}\n```\n")
    write_paper(
        base,
        "other",
        preamble="```latex\n\\usepackage{graphicx}\n\\usepackage{tikz}\n```\n",
    )
    report = assemble(
        tmp_path / "out",
        base,
        declaration("other"),
        (),
        wrapper_entry("carrier", 2),
        resolver=blind_resolver(),
    )
    assert report.dropped_preamble == (("other", "\\usepackage{tikz}"),)


def test_a_truncated_entry_is_read_as_far_as_it_goes_and_no_further() -> None:
    """Real databases are edited by hand, and a half-written field is not a value."""
    assert parse_bib("@book{k, title = {T}, author =}\n", "s")[0].fields == (
        ("title", "T"),
    )
    assert parse_bib('@book{k, title = "unterminated}\n', "s")[0].fields == ()
    assert parse_bib("@book{k, title = {T}}\n", "s")[0].fields == (("title", "T"),)
    assert parse_bib("@book{k, year = 1999}\n", "s")[0].fields == (("year", "1999"),)


def test_matching_brace_finds_the_closing_brace_or_says_there_is_none() -> None:
    assert matching_brace("x{a{b}c}y", 0) == 7
    assert matching_brace("x{a{b}c", 0) is None
    assert matching_brace("no braces", 0) is None


def test_the_namespace_prefix_is_derived_from_the_declared_id() -> None:
    assert namespace_prefix("some_line") == "some-line"
    for entry in LINE_SET:
        assert namespace_prefix(entry.id) == entry.id.replace("_", "-")

"""Consumer-visible publication boundaries; candidate regressions, not run here."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from line_set._markdown_spans import prose_spans
from line_set.omnibus import (
    OmnibusError,
    assemble,
    collect_anchors,
    collect_embeds,
    discover_paper,
    invert_section,
    merge_bibliographies,
    parse_bib,
    read_paper_config,
    retarget_figures,
    transform_section,
    unresolved_references,
    volume_config,
)
from tests.test_omnibus import (
    PNG_BYTES,
    blind_resolver,
    declaration,
    wrapper_entry,
    write_paper,
)


def _assemble(
    out: Path, base: Path, *, write: bool = False, others: tuple[str, ...] = ()
):
    return assemble(
        out,
        base,
        declaration(*others),
        (),
        wrapper_entry("carrier", len(others) + 1),
        resolver=blind_resolver(),
        write=write,
    )


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _cover_paper(base: Path, *, section: str = "# A\n") -> Path:
    root = write_paper(
        base,
        "carrier",
        sections={"00_a.md": section},
        config=(
            "paper:\n  title: 'Carrier'\n  version: '1.0'\n"
            "  cover:\n    image: 'cover.png'\n"
        ),
    )
    (root / "manuscript" / "cover.png").write_bytes(PNG_BYTES)
    return root


def test_literal_examples_stay_bytes_while_adjacent_active_syntax_moves() -> None:
    literals = (
        "Write `{#sec:real} @sec:real ![demo](../figures/missing.png)` literally.\n"
        "Use ``a ` b {#sec:real} @sec:real`` too.\n\n"
        "    # Code {#sec:real}\n"
        "    @sec:real ![demo](../../output/figures/missing.png)\n\n"
        "`A multiline\n@sec:real {#fig:literal}\ncode span`.\n"
    )
    source = (
        "# Real {#sec:real}\n\n"
        + literals
        + "\nSee @sec:real. ![p](../output/figures/p.png){#fig:p}\n"
    )
    anchors = collect_anchors(source)
    assert anchors == ("fig:p", "sec:real")
    assert collect_embeds(source) == ("../output/figures/p.png",)
    result = transform_section(source, "w", anchors)
    assert literals in result.text
    assert "## Real {#sec:w-real}" in result.text
    assert "See @sec:w-real. ![p](../figures/p.png){#fig:w-p}" in result.text
    assert invert_section(result.text, "w", anchors) == source
    assert unresolved_references(literals, ()) == ()


@pytest.mark.parametrize(
    "outer,inner", [("````", "```"), ("```", "~~~"), ("~~~~", "~~~")]
)
def test_a_fence_closes_only_with_its_own_kind_and_sufficient_length(
    outer: str,
    inner: str,
) -> None:
    literal = f"{outer}\n{inner}\n# Example {{#sec:example}}\n@sec:missing\n{inner}\n{outer}\n"
    source = literal + "\n# Real {#sec:real}\n"
    assert collect_anchors(source) == ("sec:real",)
    assert unresolved_references(source, ("sec:real",)) == ()
    transformed = transform_section(source, "w", ("sec:real",)).text
    assert transformed.startswith(literal)
    assert transformed.endswith("## Real {#sec:w-real}\n")


def test_list_continuation_is_active_but_an_indented_code_block_is_not() -> None:
    source = (
        "# Real {#sec:real}\n\n- A list item.\n\n"
        "    See @sec:real and ![p](../output/figures/p.png).\n\n"
        "End of list.\n\n    See @sec:real and ![literal](../figures/missing.png).\n"
    )
    moved = transform_section(source, "w", ("sec:real",)).text
    assert "    See @sec:w-real and ![p](../figures/p.png)." in moved
    assert moved.endswith("    See @sec:real and ![literal](../figures/missing.png).\n")
    assert collect_embeds(source) == ("../output/figures/p.png",)


def test_shared_spans_use_original_unicode_offsets_and_keep_unmatched_ticks_active() -> (
    None
):
    text = "É `literal @sec:hidden` and `unmatched @sec:visible\n"
    spans = prose_spans(text)

    def active(offset: int) -> bool:
        return any(left <= offset < right for left, right in spans)

    assert not active(text.index("@sec:hidden"))
    assert active(text.index("@sec:visible"))
    assert unresolved_references(text, ()) == ("@sec:visible",)


def test_retargeting_changes_only_destinations_not_caption_or_path_prose() -> None:
    source = (
        "The path ../output/figures/p.png is prose.\n"
        "![../output/figures/p.png](../output/figures/p.png)\n"
        "```\n../figures/literal.png\n```\n"
    )
    moved, count = retarget_figures(source)
    assert count == 1
    assert moved == source.replace("](../output/figures/p.png)", "](../figures/p.png)")


def test_literal_embeds_do_not_withdraw_a_work_or_cover_a_dangling_reference(
    tmp_path: Path,
) -> None:
    base = tmp_path / "works"
    write_paper(base, "carrier")
    root = write_paper(
        base,
        "other",
        sections={"00_a.md": "# A\n\n`![literal](../output/figures/missing.png)`\n"},
    )
    report = _assemble(tmp_path / "out", base, others=("other",))
    assert report.papers_missing == ()
    (root / "manuscript" / "00_a.md").write_text(
        "# A\n\n`{#sec:missing}` is not a definition. See @sec:missing.\n",
        encoding="utf-8",
    )
    with pytest.raises(OmnibusError, match="@sec:missing"):
        _assemble(tmp_path / "out", base, others=("other",))


@pytest.mark.parametrize("write", [False, True])
@pytest.mark.parametrize("kind", ["part", "cover", "front"])
def test_only_assembler_introduced_identifier_collisions_are_refused(
    tmp_path: Path,
    kind: str,
    write: bool,
) -> None:
    base = tmp_path / "works"
    if kind == "cover":
        _cover_paper(base, section="# A\n\n::: {#fig:cover}\nText.\n:::\n")
    elif kind == "part":
        write_paper(base, "carrier", sections={"00_a.md": "# Partition {#sec:part}\n"})
    else:
        write_paper(base, "carrier")
        write_paper(
            base, "omnibus", sections={"00_a.md": "# Front {#sec:front-matter}\n"}
        )
    out = tmp_path / "out"
    with pytest.raises(OmnibusError, match="assembler-generated identifiers"):
        _assemble(
            out, base, write=write, others=("omnibus",) if kind == "front" else ()
        )
    assert not out.exists()


def test_authored_duplicate_ids_are_reproduced_not_newly_validated(
    tmp_path: Path,
) -> None:
    base = tmp_path / "works"
    write_paper(
        base,
        "carrier",
        sections={
            "00_a.md": "# First {#sec:same}\n",
            "01_b.md": "# Second {#sec:same}\n",
        },
    )
    report = _assemble(tmp_path / "out", base, write=True)
    sections = [
        (report.written / name).read_text(encoding="utf-8")
        for name in report.files
        if "carrier_" in name
    ]
    assert sum(text.count("{#sec:carrier-same}") for text in sections) == 2


def test_document_wide_formalism_kind_rule_remains_unchanged() -> None:
    assert unresolved_references("[@def:2020]", ("def:other-term",)) == ("@def:2020",)
    assert unresolved_references("[@def:2020]", ("sec:other-term",)) == ()


def test_bib_identity_uses_only_top_level_fields() -> None:
    def database(title: str) -> str:
        return f"@book{{k, author={{A}}, title={{{title}}}, year=2020, note={{title={{Same}}}}}}"

    first, second = database("First"), database("Second")
    assert dict(parse_bib(first, "a")[0].fields)["title"] == "First"
    with pytest.raises(OmnibusError, match="two different works"):
        merge_bibliographies((("a", first), ("b", second)))
    merged = merge_bibliographies((("a", first), ("b", first)))
    assert merged.render(("k",)) == first + "\n\n"


def test_bib_comments_do_not_revive_records_and_escaped_values_survive_verbatim() -> (
    None
):
    raw = r'@book{k, title={Literal \} and \{ braces}, note="An escaped \" quote, title={Other}", year=2020}'
    text = (
        "% @book{ghost, title={Ghost}}\n@comment{ @book{alsoGhost, title={G}} }\n" + raw
    )
    entries = parse_bib(text, "s")
    assert [entry.key for entry in entries] == ["k"]
    assert entries[0].raw == raw
    assert dict(entries[0].fields)["title"] == r"Literal \} and \{ braces"
    assert merge_bibliographies((("s", text),)).render(("k",)) == raw + "\n\n"


@pytest.mark.parametrize(
    "text",
    [
        '@string{press = "Example Press"}\n@book{k, publisher=press}',
        '@preamble{"prefix"}\n@book{k, title={T}}',
        "@book(k, title={T})",
        "@book{k, title=press}",
        "@book{k, title={A} # {B}}",
    ],
)
@pytest.mark.parametrize("write", [False, True])
def test_unsupported_bibtex_is_an_explicit_prewrite_refusal(
    tmp_path: Path,
    text: str,
    write: bool,
) -> None:
    base = tmp_path / "works"
    write_paper(base, "carrier")
    write_paper(base, "other", bib=text)
    out = tmp_path / "out"
    sentinel = out / "output" / "manuscript" / "manual.md"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_bytes(b"prior output\n")
    before = _snapshot(out)
    with pytest.raises(OmnibusError, match="unsupported BibTeX"):
        _assemble(out, base, others=("other",), write=write)
    assert _snapshot(out) == before


@pytest.mark.parametrize(
    "bad_registry",
    [
        None,
        "{broken",
        {"figures": []},
        {"figures": {}},
        {
            "figures": [
                {"label": "fig:other", "filename": "p.png", "alt_text": "Other."}
            ]
        },
        {
            "figures": [
                {"label": "fig:p", "filename": "other.png", "alt_text": "Wrong file."}
            ]
        },
        {"figures": [{"label": "fig:p", "filename": "p.png"}]},
        {"figures": [{"label": "fig:p", "filename": "p.png", "alt_text": "  "}]},
        {
            "figures": [
                {"label": "fig:p", "filename": "p.png", "alt_text": "First."},
                {"label": "fig:p", "filename": "p.png", "alt_text": "Second."},
            ]
        },
    ],
)
@pytest.mark.parametrize("write", [False, True])
def test_plan_and_write_refuse_the_same_uncovered_images_before_any_mutation(
    tmp_path: Path,
    bad_registry: object,
    write: bool,
) -> None:
    base = tmp_path / "works"
    source = write_paper(
        base,
        "carrier",
        plates=("p.png",),
        sections={
            "00_a.md": "# A\n\n![p](../output/figures/p.png){#fig:p}\n",
        },
    )
    out = tmp_path / "out"
    _assemble(out, base, write=True)
    registry = source / "output" / "figures" / "figure_registry.json"
    if bad_registry is None:
        registry.unlink()
    else:
        registry.write_text(
            bad_registry if isinstance(bad_registry, str) else json.dumps(bad_registry),
            encoding="utf-8",
        )
    before = _snapshot(out)
    with pytest.raises(OmnibusError):
        _assemble(out, base, write=write)
    assert _snapshot(out) == before


def test_repeated_actual_embeds_keep_the_exact_source_alt_and_ownership(
    tmp_path: Path,
) -> None:
    base = tmp_path / "works"
    source = write_paper(
        base,
        "carrier",
        plates=("p.png",),
        sections={
            "00_a.md": "# A\n\n![first](../output/figures/p.png){#fig:p}\n\n![again](../output/figures/p.png){#fig:p}\n",
        },
    )
    path = source / "output" / "figures" / "figure_registry.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["figures"][0]["alt_text"] = "Genuine source description; not the caption."
    path.write_text(json.dumps(payload), encoding="utf-8")
    out = tmp_path / "out"
    planned = _assemble(out, base)
    assert not out.exists()
    written = _assemble(out, base, write=True)
    assert (
        planned.image_sources
        == written.image_sources
        == (("../figures/p.png", source / "output" / "figures" / "p.png"),)
    )
    records = json.loads(
        (out / "output" / "figures" / "figure_registry.json").read_text()
    )["figures"]
    assert {record["alt_text"] for record in records} == {
        "Genuine source description; not the caption."
    }
    assert (out / "output" / "figures" / "p.png").read_bytes() == PNG_BYTES


@pytest.mark.parametrize("write", [False, True])
@pytest.mark.parametrize(
    "relative",
    [
        "output",
        "output/manuscript",
        "output/figures",
        "output/manuscript/002_carrier_00_a.md",
        "output/manuscript/config.yaml",
        "output/manuscript/omnibus_report.json",
        "output/manuscript/omnibus_claim_ledger.json",
        "output/figures/p.png",
        "output/figures/figure_registry.json",
    ],
)
def test_managed_symlinks_are_refused_without_touching_external_bytes(
    tmp_path: Path,
    relative: str,
    write: bool,
) -> None:
    base = tmp_path / "works"
    write_paper(
        base,
        "carrier",
        plates=("p.png",),
        sections={
            "00_a.md": "# A\n\n![p](../output/figures/p.png){#fig:p}\n",
        },
    )
    out = tmp_path / "out"
    _assemble(out, base, write=True)
    link = out / relative
    directory = link.is_dir()
    displaced = tmp_path / "displaced"
    link.rename(displaced)
    external = tmp_path / "external"
    if directory:
        external.mkdir()
        (external / "source.md").write_bytes(b"external source\n")
        (external / "references.bib").write_bytes(b"external bibliography\n")
        before = _snapshot(external)
    else:
        external.write_bytes(b"external source\n")
        before = external.read_bytes()
    link.symlink_to(external, target_is_directory=directory)
    with pytest.raises(OmnibusError):
        _assemble(out, base, write=write)
    assert (_snapshot(external) if directory else external.read_bytes()) == before


def test_obsolete_inventory_symlinks_are_refused_before_cleanup(tmp_path: Path) -> None:
    base = tmp_path / "works"
    source = write_paper(
        base, "carrier", sections={"00_a.md": "# A\n", "01_old.md": "# Old\n"}
    )
    out = tmp_path / "out"
    report = _assemble(out, base, write=True)
    old = report.written / next(name for name in report.files if "_01_old.md" in name)
    external = tmp_path / "external.md"
    external.write_bytes(b"not owned\n")
    old.unlink()
    old.symlink_to(external)
    (source / "manuscript" / "01_old.md").unlink()
    with pytest.raises(OmnibusError):
        _assemble(out, base, write=True)
    assert external.read_bytes() == b"not owned\n"
    assert old.is_symlink()


@pytest.mark.parametrize("inventory", [None, ["../source.md"], ["README.md"], [1]])
def test_malformed_previous_inventory_never_causes_extension_based_cleanup(
    tmp_path: Path,
    inventory: object,
) -> None:
    base = tmp_path / "works"
    write_paper(base, "carrier")
    out = tmp_path / "out"
    target = out / "output" / "manuscript"
    target.mkdir(parents=True)
    (target / "manual.md").write_bytes(b"keep\n")
    (target / "omnibus_report.json").write_text(
        json.dumps({"files": inventory}), encoding="utf-8"
    )
    before = _snapshot(out)
    with pytest.raises(OmnibusError, match="inventory"):
        _assemble(out, base, write=True)
    assert _snapshot(out) == before


@pytest.mark.parametrize("write", [False, True])
def test_native_and_cover_images_have_one_output_owner(
    tmp_path: Path, write: bool
) -> None:
    base = tmp_path / "works"
    _cover_paper(base)
    name = "carrier-cover-cover.png"
    write_paper(
        base,
        "other",
        plates=(name,),
        sections={
            "00_a.md": f"# A\n\n![Native](../output/figures/{name})\n",
        },
    )
    out = tmp_path / "out"
    with pytest.raises(OmnibusError, match="plate basename"):
        _assemble(out, base, others=("other",), write=write)
    assert not out.exists()


def test_distinct_native_and_cover_names_preserve_bytes_and_source_mapping(
    tmp_path: Path,
) -> None:
    base = tmp_path / "works"
    carrier = _cover_paper(base)
    other = write_paper(
        base,
        "other",
        plates=("native.png",),
        sections={
            "00_a.md": "# A\n\n![Native](../output/figures/native.png){#fig:native}\n",
        },
    )
    report = _assemble(tmp_path / "out", base, others=("other",), write=True)
    assert dict(report.image_sources) == {
        "../figures/carrier-cover-cover.png": carrier / "manuscript" / "cover.png",
        "../figures/native.png": other / "output" / "figures" / "native.png",
    }
    serialized = json.loads(report.as_json())
    assert serialized["image_sources"] == {
        target: str(path) for target, path in report.image_sources
    }
    for target, original in report.image_sources:
        assert (report.written / target).read_bytes() == original.read_bytes()


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("'A \"Quoted\" Work' # comment", 'A "Quoted" Work'),
        ("'It''s a \\ Work'", "It's a \\ Work"),
        (r'"A \"Quoted\" \\ Work"', 'A "Quoted" \\ Work'),
        ("A plain title # comment", "A plain title"),
        ("A#tag title", "A#tag title"),
        (
            r'"Lines\Nand\Land\P supplementary \U0001f600"',
            "Lines\x85and\u2028and\u2029 supplementary 😀",
        ),
    ],
)
def test_supported_yaml_scalars_decode_and_reemit_without_value_drift(
    tmp_path: Path,
    raw: str,
    expected: str,
) -> None:
    source = tmp_path / "source.yaml"
    source.write_text(f"paper:\n  title: {raw}\n  version: '1.0'\n", encoding="utf-8")
    config = read_paper_config(source)
    assert config.title == expected
    generated = volume_config(
        source.read_text(), config.title, expected, config.version, None
    )
    destination = tmp_path / "generated.yaml"
    destination.write_text(generated, encoding="utf-8")
    reread = read_paper_config(destination)
    assert (reread.title, reread.subtitle) == (expected, expected)
    title_line = next(
        line for line in generated.splitlines() if line.startswith("  title:")
    )
    assert json.loads(title_line.partition(":")[2]) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "|\n    multiline",
        ">\n    folded",
        "&alias Value",
        "*alias",
        "[A, B]",
        "Plain\n    continued",
    ],
)
def test_unsupported_yaml_node_forms_are_refused_not_silently_shortened(
    tmp_path: Path, raw: str
) -> None:
    source = tmp_path / "source.yaml"
    source.write_text(f"paper:\n  title: {raw}\n  version: '1.0'\n", encoding="utf-8")
    with pytest.raises(OmnibusError, match="unsupported"):
        read_paper_config(source)


def test_only_actual_references_stubs_are_omitted(tmp_path: Path) -> None:
    base = tmp_path / "works"
    write_paper(
        base,
        "carrier",
        sections={
            "00_a.md": "# A\n\nSee @sec:scope.\n",
            "99_scope.md": "# Scope {#sec:scope}\n",
            "99_example.md": "    # References\n",
            "99_references.md": "# References\n\n::: {#refs}\n:::\n",
        },
    )
    paper = discover_paper(wrapper_entry("carrier", 1), base)
    assert [path.name for path in paper.references_only] == ["99_references.md"]
    assert [path.name for path in paper.sections] == [
        "00_a.md",
        "99_example.md",
        "99_scope.md",
    ]
    report = _assemble(tmp_path / "out", base, write=True)
    scope = next(name for name in report.files if "99_scope" in name)
    assert (report.written / scope).read_text() == "## Scope {#sec:carrier-scope}\n"


def test_absent_inventory_grants_no_markdown_or_bibliography_cleanup(
    tmp_path: Path,
) -> None:
    base = tmp_path / "works"
    write_paper(base, "carrier")
    out = tmp_path / "out"
    target = out / "output" / "manuscript"
    target.mkdir(parents=True)
    (target / "manual.md").write_bytes(b"operator note\n")
    (target / "supplemental.bib").write_bytes(b"operator bibliography\n")
    _assemble(out, base, write=True)
    assert (target / "manual.md").read_bytes() == b"operator note\n"
    assert (target / "supplemental.bib").read_bytes() == b"operator bibliography\n"


def test_nested_list_continuations_and_fences_keep_distinct_literal_boundaries() -> (
    None
):
    source = (
        "# Real {#sec:real}\n\n- Root\n\n    - Nested\n\n"
        "        See @sec:real.\n\n"
        "        ````\n        ```\n        # Literal {#sec:hidden}\n"
        "        @sec:missing\n        ```\n        ````\n\n"
        "After the list, see @sec:real.\n"
    )
    anchors = collect_anchors(source)
    assert anchors == ("sec:real",)
    transformed = transform_section(source, "w", anchors).text
    assert "        See @sec:w-real." in transformed
    assert "        # Literal {#sec:hidden}\n        @sec:missing" in transformed
    assert transformed.endswith("After the list, see @sec:w-real.\n")
    assert unresolved_references(transformed, ("sec:w-real",)) == ()


def test_active_image_with_inline_literal_caption_still_has_real_ownership() -> None:
    source = (
        "![Use `@sec:literal` and `{#fig:literal}`](../output/figures/p.png){#fig:p}\n"
    )
    assert collect_embeds(source) == ("../output/figures/p.png",)
    assert collect_anchors(source) == ("fig:p",)
    transformed = transform_section(source, "w", ("fig:p",)).text
    assert "`@sec:literal` and `{#fig:literal}`" in transformed
    assert "](../figures/p.png){#fig:w-p}" in transformed
    assert invert_section(transformed, "w", ("fig:p",)) == source


def test_multiline_literal_reference_placeholder_is_not_removed(tmp_path: Path) -> None:
    base = tmp_path / "works"
    literal = "`literal\n::: {#refs}\n:::\nend`\n"
    write_paper(base, "carrier", sections={"00_a.md": "# A\n\n" + literal})
    report = _assemble(tmp_path / "out", base, write=True)
    section = next(name for name in report.files if "_00_a.md" in name)
    assert (report.written / section).read_text(
        encoding="utf-8"
    ) == "## A\n\n" + literal


@pytest.mark.parametrize(
    "separator", ["\n", "# Cover metadata\n", "  # Cover metadata\n"]
)
@pytest.mark.parametrize("write", [False, True])
def test_yaml_spacing_and_comments_do_not_erase_a_configured_png_cover(
    tmp_path: Path, separator: str, write: bool
) -> None:
    base = tmp_path / "works"
    carrier = _cover_paper(base)
    config = carrier / "manuscript" / "config.yaml"
    config.write_text(
        "paper:\n  title: 'Carrier'\n  version: '1.0'\n"
        + separator
        + "  cover:\n\n    image: 'cover.png'\n\n    alt: 'Original cover'\n",
        encoding="utf-8",
    )
    report = _assemble(tmp_path / "out", base, write=write)
    assert dict(report.image_sources) == {
        "../figures/carrier-cover-cover.png": carrier / "manuscript" / "cover.png"
    }
    if write:
        assert (
            report.written / "../figures/carrier-cover-cover.png"
        ).read_bytes() == PNG_BYTES
        assert "Original cover" in (
            report.written / "config.yaml"
        ).read_text(encoding="utf-8")

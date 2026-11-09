"""Retained native reference prose must not claim the volume bibliography."""

from pathlib import Path

import pytest

from line_set.omnibus import assemble, fence_mask
from tests.test_omnibus import (
    ONE_WORK,
    blind_resolver,
    declaration,
    wrapper_entry,
    write_paper,
)


@pytest.mark.parametrize(
    "delimiter", ("::: {#refs}\n:::\n", ":::: { #refs }\n\n:::::\n")
)
def test_only_empty_native_bibliography_placeholder_is_removed(delimiter: str) -> None:
    from line_set.omnibus import _remove_empty_reference_placeholders

    before = "# References\n\nProse [@shared_key] must not change.\n\n"
    after = "\nA second source-owned caveat.\n"
    assert (
        _remove_empty_reference_placeholders(before + delimiter + after)
        == before + after
    )


@pytest.mark.parametrize(
    "literal",
    (
        "```markdown\n::: {#refs}\n:::\n```\n",
        "~~~markdown\n::: {#refs}\n:::\n~~~\n",
        "    ::: {#refs}\n    :::\n",
        "The literal `::: {#refs}` is not a bibliography.\n",
        "::: {#refs}\nSource-owned caveat [@shared_key].\n:::\n",
        "::: {#refs}\nAn unclosed source-owned block.\n",
    ),
)
def test_reference_literals_and_nonempty_source_divs_are_preserved(
    literal: str,
) -> None:
    from line_set.omnibus import _remove_empty_reference_placeholders

    assert _remove_empty_reference_placeholders(literal) == literal


def test_multiple_native_reference_sections_leave_one_volume_bibliography(
    tmp_path: Path,
) -> None:
    base = tmp_path / "works"
    literal = "```markdown\n::: {#refs}\n:::\n```\n\n    ::: {#refs}\n    :::\n"
    contents = {
        "carrier": "# References\n\n::: {#refs}\n:::\n\nCarrier caveat [@shared_key].\n",
        "other": "# References\n\nOther caveat [@shared_key].\n\n:::: {#refs}\n\n::::\n\n"
        + literal,
    }
    for name, references in contents.items():
        write_paper(
            base,
            name,
            sections={
                "00_abstract.md": "# Abstract\n\nBody.\n",
                "99_references.md": references,
            },
            bib=ONE_WORK,
        )
    report = assemble(
        tmp_path / "out",
        base,
        declaration("other"),
        (),
        wrapper_entry("carrier", 2),
        resolver=blind_resolver(),
        write=True,
    )
    output = tmp_path / "out" / "output" / "manuscript"
    for name, original in contents.items():
        assert (base / name / "manuscript" / "99_references.md").read_text() == original
        target = next(output.glob(f"*_{name}_99_references.md"))
        assert f"{name.capitalize()} caveat [@shared_key]." in target.read_text()
    assert literal in next(output.glob("*_other_99_references.md")).read_text()
    live = []
    for path in output.glob("*.md"):
        text = path.read_text()
        for line, fenced in zip(text.splitlines(), fence_mask(text), strict=True):
            if not fenced and line == "::: {#refs}":
                live.append(path.name)
    assert live == [report.files[-1]]
    assert (base / "carrier" / "manuscript" / "references.bib").read_text() == ONE_WORK

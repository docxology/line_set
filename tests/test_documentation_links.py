"""Every relative link in this repository has to resolve inside this repository.

A link like ``../../docs/line-set.md`` resolves cheerfully inside a working tree
that happens to have the right thing two levels up, and resolves to nothing for
anyone holding only this repository. This project is its own repository, so a
link that walks above the repository root is a dead link for most readers, and
three of them shipped inside the rendered manuscript before this gate existed.

The gate is therefore about *containment* first: the resolved target of every
relative markdown link must sit at or below the project root. It checks
existence as a second, separate question, because those are two different
failures — one is a link that cannot resolve for anyone, the other is a link
that names a file this repository does not have.

External references are not forbidden. They are required to be addressed as
external: an absolute URL, which travels, rather than a relative path out of the
tree, which does not. So an ``https://`` target is passed over here on purpose,
and the list of them is reported by
:func:`test_the_external_urls_are_a_short_and_deliberate_list` rather than
silently ignored.

Nothing here reads the network. A URL is checked for its shape, never fetched.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from line_set.omnibus import fence_mask

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: Directories a documentation scan must not descend into.
#:
#: ``output/`` is disposable and holds a compiled copy of every work's prose,
#: which would be scanned twice and would make the corpus figure meaningless.
#: The rest are tool state, not documents.
SKIPPED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "output",
        "htmlcov",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
    }
)

#: An inline markdown link or image target, with any title string dropped.
LINK_RE = re.compile(r"!?\[[^\]]*\]\(\s*(<[^>]*>|[^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")

#: Targets that are not paths at all.
NON_PATH_PREFIXES: tuple[str, ...] = ("http://", "https://", "mailto:", "#")


def markdown_files() -> tuple[Path, ...]:
    """Every markdown document this repository ships."""
    found = []
    for path in sorted(PROJECT_ROOT.rglob("*.md")):
        relative = path.relative_to(PROJECT_ROOT)
        if any(part in SKIPPED_DIRS for part in relative.parts):
            continue
        found.append(path)
    return tuple(found)


def link_targets(text: str) -> tuple[str, ...]:
    """Every inline link target outside a fenced block, in order.

    Fenced blocks are excluded because a path inside one is being shown, not
    followed — the render recipes in ``docs/development.md`` name directories
    that deliberately do not exist here.
    """
    marks = fence_mask(text)
    targets = []
    for line, fenced in zip(text.splitlines(), marks, strict=True):
        if fenced:
            continue
        for match in LINK_RE.finditer(line):
            targets.append(match.group(1).strip("<>"))
    return tuple(targets)


def relative_links() -> tuple[tuple[Path, str], ...]:
    """Every link that is meant to resolve as a path, with the file it is in."""
    found = []
    for path in markdown_files():
        for target in link_targets(path.read_text(encoding="utf-8")):
            if target.startswith(NON_PATH_PREFIXES):
                continue
            found.append((path, target))
    return tuple(found)


def escaping(links: tuple[tuple[Path, str], ...]) -> tuple[str, ...]:
    """The links whose resolved target is not inside the project root."""
    escaped = []
    for path, target in links:
        resolved = (path.parent / target.partition("#")[0]).resolve()
        if resolved != PROJECT_ROOT and PROJECT_ROOT not in resolved.parents:
            escaped.append(f"{path.relative_to(PROJECT_ROOT)} -> {target}")
    return tuple(escaped)


# ------------------------------------------------------------- the scan set


def test_the_scan_found_documents_and_links_to_check() -> None:
    """An empty scan set would make every gate below vacuous."""
    files = markdown_files()
    assert len(files) > 20, [path.name for path in files]
    assert (PROJECT_ROOT / "README.md") in files
    assert (PROJECT_ROOT / "manuscript" / "06_conclusion.md") in files
    links = relative_links()
    assert len(links) > 20, links


# ------------------------------------------------------------- containment


def test_no_relative_link_resolves_outside_the_repository() -> None:
    """The gate this module exists for.

    A separated copy of this project is the ordinary case, not the exception.
    A relative target that climbs above the project root is dead for every
    reader who has only this repository, whatever it happens to find here.
    """
    assert escaping(relative_links()) == ()


def test_the_containment_check_catches_a_link_that_climbs_out(tmp_path: Path) -> None:
    """The positive control: a check that cannot fail is not a check.

    The escaping path is exercised against a real file with a real ``../../``
    target, so the gate above is known to be measuring something.
    """
    document = PROJECT_ROOT / "docs" / "planted.md"
    escaped = escaping(((document, "../../docs/line-set.md"),))
    assert escaped == ("docs/planted.md -> ../../docs/line-set.md",)
    assert escaping(((document, "../README.md"),)) == ()
    assert escaping(((document, "architecture.md#digests"),)) == ()


def test_the_link_scan_reads_targets_and_leaves_fenced_paths_alone() -> None:
    """The extraction the two gates stand on, shown working and shown bounded."""
    text = (
        "See [a doc](docs/a.md) and [an anchor](#sec:x).\n"
        "![Plate.](../output/figures/p.png){#fig:p width=100%}\n"
        "```bash\n"
        "cd /wherever/you/cloned/template\n"
        "see [shown, not followed](docs/inside_a_fence.md)\n"
        "```\n"
        '[titled](docs/b.md "A title")\n'
    )
    assert link_targets(text) == (
        "docs/a.md",
        "#sec:x",
        "../output/figures/p.png",
        "docs/b.md",
    )


# --------------------------------------------------------------- existence


def test_every_in_repository_link_names_a_file_that_is_here() -> None:
    """Containment is not enough; a contained link can still name nothing.

    ``output/`` is excluded because it is disposable by design and is rebuilt
    by the figure and volume builders. The manuscript's embeds are checked
    against the built plates by ``tests/test_figures.py``, which builds them
    first; duplicating that here would only make this module depend on a
    rasterizer it does not need.
    """
    dangling = []
    for path, target in relative_links():
        resolved = (path.parent / target.partition("#")[0]).resolve()
        if PROJECT_ROOT not in resolved.parents:
            continue  # an escaping link; the containment gate owns that failure
        if "output" in resolved.relative_to(PROJECT_ROOT).parts:
            continue
        if not resolved.exists():
            dangling.append(f"{path.relative_to(PROJECT_ROOT)} -> {target}")
    assert dangling == []


# ---------------------------------------------------------- external links


def test_the_external_urls_are_a_short_and_deliberate_list() -> None:
    """External references are allowed, and are held to being enumerable.

    They are the correct way to address something outside this repository, and
    the reason the links above can be required to stay inside it. This gate
    keeps that list visible and refuses a target that only looks like a URL.
    """
    urls = sorted(
        {
            target
            for path in markdown_files()
            for target in link_targets(path.read_text(encoding="utf-8"))
            if target.startswith(("http://", "https://"))
        }
    )
    assert urls, "the sibling works are cited by URL; an empty list means they are not"
    assert all(url.startswith("https://") for url in urls), urls
    for sibling in ("red_line", "black_line", "golden_line", "white_line"):
        assert f"https://github.com/docxology/{sibling}" in urls, sibling


def test_a_target_that_is_not_a_path_is_not_treated_as_one() -> None:
    """Anchors, URLs, and mail addresses are not files and are not resolved."""
    for target in ("#sec:x", "https://example.org/a", "mailto:someone@example.org"):
        assert target.startswith(NON_PATH_PREFIXES), target
    assert not "docs/a.md".startswith(NON_PATH_PREFIXES)


@pytest.mark.parametrize(
    "document",
    [PROJECT_ROOT / "README.md", PROJECT_ROOT / "STANDALONE.md"],
    ids=lambda path: path.name,
)
def test_the_ancestor_note_is_cited_rather_than_linked(document: Path) -> None:
    """The acknowledgement stays; the dead relative path does not.

    ``docs/line-set.md`` is an unpublished note in a private tree. Deleting the
    acknowledgement to fix the link would have been the dishonest repair, so
    the name is still here and the link is gone.
    """
    text = document.read_text(encoding="utf-8")
    assert "docs/line-set.md" in text, (
        "the acknowledgement was deleted, not re-addressed"
    )
    assert "](../../docs/line-set.md)" not in text
    assert "](../../../docs/line-set.md)" not in text

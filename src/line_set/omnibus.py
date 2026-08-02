"""Assemble the declared works into one compiled volume, as a build artifact.

The volume is written into ``output/manuscript/``, which the render toolchain
treats as an injected manuscript and prefers over the source one. Nothing here
writes to any source manuscript, and nothing here writes to a sibling checkout:
the compilation is disposable output, and the papers it reproduces stay exactly
where their authors put them.

What this module does is mechanical and it is the whole of what it does. It
concatenates, it moves anchors into per-paper namespaces so two papers that
both wrote ``{#sec:abstract}`` do not collide, it shifts headings down one
level so a part header can carry each paper's title, it retargets figure
embeds so they resolve from the injected location, and it merges the
bibliographies. It does not summarise, reconcile, rank, or reword. The
round-trip in :func:`invert_section` is the statement of that: every transform
below is invertible, and the suite inverts them back to the source bytes.

The compilation asserts nothing the individual papers do not assert. The one
claim it adds is the reading this package computed over the declared set, and
that reading says only that the declared vocabularies did not overlap.

Absence is reported, never smoothed. A declared work whose manuscript is not in
the tree is named in the front matter as missing, and the volume goes out
honestly short rather than silently short. Partial presence is reported the
same way: a work whose manuscript is here but whose plates have not been built
in that checkout is named as missing with that reason, because this project
reads sibling checkouts and never writes to one, so it cannot build their
figures and must not pretend the volume is complete without them. The
assembling work itself is held to the stricter rule — its own plates are its
own responsibility and an embed with no plate stops the build.
"""

from __future__ import annotations

import json
import re
import shutil
import unicodedata
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from .binding import PROJECT_ROOT, PackageResolver, sibling_base, sibling_path_resolver
from .models import LineEntry, ReadCode, SetReading, SharedToken
from .reader import read_set
from .registry import LINE_SET, SHARED_TOKENS, WRAPPER_LINE
from .serialization import reading_digest, registry_digest

#: Manuscript filenames the render toolchain never treats as a section.
NON_SECTION_NAMES: frozenset[str] = frozenset(
    {"AGENTS.md", "README.md", "SYNTAX.md", "preamble.md"}
)

#: Where a compiled volume is written, relative to the project root.
INJECTED_MANUSCRIPT_DIR: tuple[str, ...] = ("output", "manuscript")

#: Where the volume's plates are gathered, relative to the project root.
#:
#: This is not a free choice. The renderer rewrites every ``\includegraphics``
#: to ``../figures/<basename>`` relative to the directory LaTeX compiles in,
#: which is ``output/pdf``. A plate anywhere else is a plate the compiler will
#: not find, however correct the markdown path looks.
VOLUME_FIGURES_DIR: tuple[str, ...] = ("output", "figures")

#: The embed prefix every source paper uses, and what it becomes in the volume.
#:
#: ``../output/figures/`` is written relative to a source ``manuscript/``. From
#: the injected ``output/manuscript/`` the same text would resolve to
#: ``output/output/figures``, so it is retargeted rather than carried over.
SOURCE_FIGURE_PREFIX: str = "../output/figures/"
VOLUME_FIGURE_PREFIX: str = "../figures/"

#: The marker that makes the render toolchain keep a generated ordering.
#:
#: Without this literal in the injected ``config.yaml`` the toolchain refreshes
#: that file from the source manuscript's own config, and the volume would be
#: rendered under the wrapper paper's title.
GENERATED_ORDERING_MARKER: str = "# Generated manuscript ordering"

#: The metadata key that restarts formalism numbering at each reproduced work.
#:
#: The render toolchain's formalism filter numbers Definition, Proposition, and
#: the other declared block kinds per document, in document order. A volume
#: reproducing several works is still one pandoc document, so without a reset
#: the five papers would share one sequence and each paper's own
#: ``[@def:...]`` references would resolve to numbers that only make sense in
#: the volume — a work whose first definition is Definition 1 in its own PDF
#: would be Definition 9 here, silently.
FORMALISM_RESET_KEY: str = "formalism_reset_level"

#: The level at which the counters restart: this volume's part headings.
#:
#: Every reproduced work is introduced by a level-1 part heading and every
#: heading inside it has been demoted to level 2 or deeper, so level 1 is
#: exactly the boundary between one work and the next. A standalone paper must
#: not set this, because there a level-1 header is an ordinary section.
FORMALISM_RESET_LEVEL: int = 1

#: The metadata block the volume's front matter opens with.
#:
#: The generated ``config.yaml`` states the same value, but the toolchain reads
#: only ``paper``, ``authors``, and ``metadata`` out of that file when it builds
#: its pandoc command; a key it does not read is a key the filter never sees. A
#: YAML metadata block at the head of the first section is carried into the
#: combined markdown verbatim and *is* read, so the value is written in both
#: places and a test requires them to agree. Stating it only in the config
#: would be a setting that looks applied and is inert.
FORMALISM_METADATA_BLOCK: str = (
    f"---\n{FORMALISM_RESET_KEY}: {FORMALISM_RESET_LEVEL}\n---\n"
)

#: The filename the source bibliography is force-copied to by the renderer.
SOURCE_BIB_NAME: str = "references.bib"

#: The filename the rest of the merged bibliography is written to.
#:
#: The renderer copies the source manuscript's ``references.bib`` over anything
#: of that name in the injected directory, so the merge is partitioned: the
#: wrapper's own keys stay in the file that will be overwritten with an
#: identical one, and every other key goes here. BibTeX is handed both
#: databases and sees each key exactly once.
VOLUME_BIB_NAME: str = "omnibus_references.bib"

#: Where the machine-readable account of one assembly is written.
REPORT_NAME: str = "omnibus_report.json"

#: The deepest heading level LaTeX will still number and typeset as a heading.
MAX_HEADING_LEVEL: int = 5

#: Anchor kinds pandoc-crossref resolves, and therefore the kinds worth moving.
REFERENCE_KINDS: tuple[str, ...] = ("eq", "fig", "lst", "sec", "tbl")

_FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
_HEADING_RE = re.compile(r"^(#{1,6})(?=\s)")
_ANCHOR_DEF_RE = re.compile(r"\{#([A-Za-z][A-Za-z0-9]*):([A-Za-z0-9][A-Za-z0-9_.-]*)")

#: A fenced-Div line, which declares its label differently from a heading.
#:
#: A formalism block is written ``::: {.definition #def:x title="..."}``. The
#: identifier does not follow ``{`` there, so ``_ANCHOR_DEF_RE`` does not see
#: it, and without this the volume would carry two works' ``#def:x`` labels
#: unnamespaced into one document — where the render toolchain's formalism
#: filter reports a duplicate and lets the last one win, so one work's prose
#: would quietly resolve to another work's numbering.
_DIV_FENCE_RE = re.compile(r"^\s*:::")
_DIV_ANCHOR_DEF_RE = re.compile(r"#([A-Za-z][A-Za-z0-9]*):([A-Za-z0-9][A-Za-z0-9_.-]*)")
_CROSSREF_RE = re.compile(r"(?<![A-Za-z0-9_])@([A-Za-z]+):([A-Za-z0-9][A-Za-z0-9_.-]*)")
_LINK_RE = re.compile(r"\]\(#([A-Za-z]+:[A-Za-z0-9_.-]+)\)")
_EMBED_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
_BIB_FIELD_RE = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z][A-Za-z0-9_-]*)\s*=\s*")
_TOP_KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):")
_SCALAR_RE = re.compile(r"^\s{2}([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")

#: A LaTeX accent command, which spells a letter rather than naming a work.
#:
#: Matches the backslash-plus-symbol forms (``\\"o``, ``\\'e``, ``\\`a``,
#: ``\\^i``, ``\\~n``, ``\\=o``, ``\\.z``) and the word forms with a braced
#: argument (``\\c{c}``, ``\\v{s}``, ``\\u{a}``, ``\\H{o}``, ``\\r{a}``,
#: ``\\k{a}``, ``\\d{n}``, ``\\b{h}``, ``\\t{oo}``). The braces are already
#: gone by the time this runs, so only the command itself is removed and the
#: letter it decorates survives.
_ACCENT_COMMAND_RE = re.compile(r"\\(?:['`^~\"=.]|[cvuHrkdbt](?=[{\s]))")

#: The identity fields compared when one key is declared by two papers.
IDENTITY_FIELDS: tuple[str, ...] = ("author", "title", "year", "doi")


class OmnibusError(RuntimeError):
    """A compilation that would have been wrong if it had been allowed."""


# ------------------------------------------------------------- reading text


def fence_mask(text: str) -> tuple[bool, ...]:
    """Mark each line of ``text`` that is inside a fenced block.

    A fence delimiter is marked along with its contents, so no transform below
    can touch one. This matters even while no paper has a ``#`` or a ``{#`` in
    a code block: a transform that is only correct because of what the corpus
    happens to contain today is a transform that will be wrong later, quietly.
    """
    inside = False
    marks: list[bool] = []
    for line in text.splitlines():
        if _FENCE_RE.match(line):
            marks.append(True)
            inside = not inside
            continue
        marks.append(inside)
    return tuple(marks)


def map_prose_lines(text: str, transform: Callable[[str], str]) -> str:
    """Apply ``transform`` to every line outside a fenced block.

    The trailing newline of the input is preserved so a transformed file is
    byte-comparable with its source.
    """
    marks = fence_mask(text)
    lines = text.splitlines()
    rebuilt = [line if marks[i] else transform(line) for i, line in enumerate(lines)]
    joined = "\n".join(rebuilt)
    return joined + "\n" if text.endswith("\n") else joined


def anchor_pattern(line: str) -> re.Pattern[str]:
    """The label pattern that applies to one line.

    A fenced-Div line declares its identifier as a bare ``#kind:name`` among
    the Div's other attributes; everywhere else the identifier follows ``{``.
    Choosing one pattern per line rather than running both keeps a Div written
    ``::: {#def:x .definition}`` from being rewritten twice.
    """
    return _DIV_ANCHOR_DEF_RE if _DIV_FENCE_RE.match(line) else _ANCHOR_DEF_RE


def collect_anchors(text: str) -> tuple[str, ...]:
    """Return every ``kind:name`` anchor defined outside a fenced block."""
    found: set[str] = set()

    def record(line: str) -> str:
        for kind, name in anchor_pattern(line).findall(line):
            found.add(f"{kind}:{name}")
        return line

    map_prose_lines(text, record)
    return tuple(sorted(found))


def collect_embeds(text: str) -> tuple[str, ...]:
    """Return every image target embedded outside a fenced block."""
    found: list[str] = []

    def record(line: str) -> str:
        found.extend(_EMBED_RE.findall(line))
        return line

    map_prose_lines(text, record)
    return tuple(found)


# --------------------------------------------------------- the transforms


def namespace_prefix(line_id: str) -> str:
    """The anchor namespace one declared work gets, derived from its id."""
    return line_id.replace("_", "-")


def demote_headings(text: str, *, by: int = 1) -> str:
    """Shift every ATX heading down ``by`` levels.

    Raises when the result would be deeper than LaTeX will typeset, because a
    heading that silently stops being a heading is a structural loss that no
    later check would notice.
    """

    def shift(line: str) -> str:
        match = _HEADING_RE.match(line)
        if match is None:
            return line
        level = len(match.group(1)) + by
        if level > MAX_HEADING_LEVEL:
            raise OmnibusError(
                f"demoting by {by} would put a heading at level {level}, "
                f"deeper than the level {MAX_HEADING_LEVEL} LaTeX typesets: {line!r}"
            )
        return "#" * level + line[match.end(1) :]

    return map_prose_lines(text, shift)


def promote_headings(text: str, *, by: int = 1) -> str:
    """The inverse of :func:`demote_headings`."""

    def shift(line: str) -> str:
        match = _HEADING_RE.match(line)
        if match is None:
            return line
        level = len(match.group(1)) - by
        if level < 1:
            raise OmnibusError(f"promoting by {by} would leave no heading: {line!r}")
        return "#" * level + line[match.end(1) :]

    return map_prose_lines(text, shift)


def namespace_anchors(
    text: str, prefix: str, anchors: Iterable[str]
) -> tuple[str, int, int]:
    """Move anchor definitions and every reference to them into ``prefix``.

    Returns the rewritten text, the number of definitions moved, and the number
    of references moved. A reference is rewritten only when it names an anchor
    this paper actually defines, which is what keeps a bibliography key such as
    ``[@ostrom1990commons]`` — no colon, no anchor — out of reach, and what
    makes a reference that survives un-rewritten a detectable dangling one
    rather than a silently renamed citation.
    """
    known = frozenset(anchors)
    counts = [0, 0]

    def rewrite(line: str) -> str:
        def move_def(match: re.Match[str]) -> str:
            counts[0] += 1
            # Rebuilt from the matched text rather than from a literal ``{#``,
            # because a fenced-Div label has no brace in front of it.
            name = match.group(2)
            return f"{match.group(0)[: -len(name)]}{prefix}-{name}"

        def move_ref(match: re.Match[str]) -> str:
            target = f"{match.group(1)}:{match.group(2)}"
            if target not in known:
                return match.group(0)
            counts[1] += 1
            return f"@{match.group(1)}:{prefix}-{match.group(2)}"

        def move_link(match: re.Match[str]) -> str:
            if match.group(1) not in known:
                return match.group(0)
            counts[1] += 1
            kind, name = match.group(1).split(":", 1)
            return f"](#{kind}:{prefix}-{name})"

        line = anchor_pattern(line).sub(move_def, line)
        line = _CROSSREF_RE.sub(move_ref, line)
        return _LINK_RE.sub(move_link, line)

    return map_prose_lines(text, rewrite), counts[0], counts[1]


def denamespace_anchors(text: str, prefix: str, anchors: Iterable[str]) -> str:
    """The inverse of :func:`namespace_anchors`, over the moved names."""
    moved = {f"{kind}:{prefix}-{name}" for kind, _, name in _split_anchors(anchors)}

    def rewrite(line: str) -> str:
        def restore(match: re.Match[str]) -> str:
            kind, name = match.group(1), match.group(2)
            if f"{kind}:{name}" not in moved:
                return match.group(0)
            return f"{match.group(0)[: -len(name)]}{name[len(prefix) + 1 :]}"

        line = anchor_pattern(line).sub(restore, line)
        line = _CROSSREF_RE.sub(restore, line)

        def restore_link(match: re.Match[str]) -> str:
            if match.group(1) not in moved:
                return match.group(0)
            kind, name = match.group(1).split(":", 1)
            return f"](#{kind}:{name[len(prefix) + 1 :]})"

        return _LINK_RE.sub(restore_link, line)

    return map_prose_lines(text, rewrite)


def _split_anchors(anchors: Iterable[str]) -> tuple[tuple[str, str, str], ...]:
    """Split ``kind:name`` anchors into ``(kind, full, name)`` triples."""
    parts: list[tuple[str, str, str]] = []
    for anchor in anchors:
        kind, _, name = anchor.partition(":")
        parts.append((kind, anchor, name))
    return tuple(parts)


def retarget_figures(text: str) -> tuple[str, int]:
    """Point figure embeds at the volume's plate directory."""
    if VOLUME_FIGURE_PREFIX in text:
        raise OmnibusError(
            f"the source already writes {VOLUME_FIGURE_PREFIX!r}, so retargeting "
            "it would not be invertible"
        )
    count = [0]

    def rewrite(line: str) -> str:
        if SOURCE_FIGURE_PREFIX not in line:
            return line
        count[0] += line.count(SOURCE_FIGURE_PREFIX)
        return line.replace(SOURCE_FIGURE_PREFIX, VOLUME_FIGURE_PREFIX)

    return map_prose_lines(text, rewrite), count[0]


def restore_figures(text: str) -> str:
    """The inverse of :func:`retarget_figures`."""
    return map_prose_lines(
        text, lambda line: line.replace(VOLUME_FIGURE_PREFIX, SOURCE_FIGURE_PREFIX)
    )


@dataclass(frozen=True)
class SectionTransform:
    """One source section after the mechanical transforms, with its counts."""

    source: Path
    text: str
    anchors_moved: int
    references_moved: int
    figures_retargeted: int


def transform_section(
    text: str, prefix: str, anchors: Iterable[str]
) -> SectionTransform:
    """Apply every mechanical transform to one section's text."""
    named, moved_defs, moved_refs = namespace_anchors(text, prefix, anchors)
    demoted = demote_headings(named)
    retargeted, figures = retarget_figures(demoted)
    return SectionTransform(
        source=Path(),
        text=retargeted,
        anchors_moved=moved_defs,
        references_moved=moved_refs,
        figures_retargeted=figures,
    )


def invert_section(text: str, prefix: str, anchors: Iterable[str]) -> str:
    """Undo :func:`transform_section`, so the suite can compare against source."""
    return denamespace_anchors(promote_headings(restore_figures(text)), prefix, anchors)


def unresolved_references(text: str, anchors: Iterable[str]) -> tuple[str, ...]:
    """Return references in ``text`` that name no anchor in ``anchors``.

    Two families of kind are checked. The kinds pandoc-crossref resolves are
    checked always. Any other kind is checked only when some anchor in
    ``anchors`` declares it — the rule the render toolchain's formalism filter
    uses for the same decision, and the reason a bibliography key shaped like
    ``author:year`` is not mistaken for a broken cross-reference: no anchor
    declares that prefix, so nothing claims it.
    """
    known = frozenset(anchors)
    declared_kinds = frozenset(
        anchor.partition(":")[0] for anchor in known if ":" in anchor
    )
    checked = frozenset(REFERENCE_KINDS) | declared_kinds
    dangling: set[str] = set()

    def scan(line: str) -> str:
        for kind, name in _CROSSREF_RE.findall(line):
            if kind in checked and f"{kind}:{name}" not in known:
                dangling.add(f"@{kind}:{name}")
        for target in _LINK_RE.findall(line):
            if target.split(":", 1)[0] in REFERENCE_KINDS and target not in known:
                dangling.add(f"](#{target})")
        return line

    map_prose_lines(text, scan)
    return tuple(sorted(dangling))


# ------------------------------------------------------------- config files


def top_level_block(text: str, key: str) -> str | None:
    """Return one top-level YAML block verbatim, or ``None`` if absent.

    This is a text operation, not a parse. The volume's configuration reuses
    the wrapper paper's author, render, and geometry blocks unchanged, and
    copying the bytes is both simpler and more faithful than re-emitting a
    structure this package would have to model first.
    """
    lines = text.splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        match = _TOP_KEY_RE.match(line)
        if match is None:
            continue
        if match.group(1) == key:
            start = index
            continue
        if start is not None:
            return "\n".join(lines[start:index]).rstrip() + "\n"
    if start is None:
        return None
    return "\n".join(lines[start:]).rstrip() + "\n"


@dataclass(frozen=True)
class PaperConfig:
    """The manuscript configuration fields a compiled volume needs.

    The set contract treats ``manuscript/config.yaml`` as the authoritative
    statement of a work's version, so that is where the version is read from
    rather than from the package the reader happens to import.
    """

    title: str
    subtitle: str | None
    version: str
    date: str | None


def read_paper_config(path: Path) -> PaperConfig:
    """Read the ``paper:`` block of a manuscript configuration.

    Refuses a configuration with no title or no version rather than inventing
    either: a volume that stated a version it did not read would be making the
    one claim this compilation is supposed to be able to support.
    """
    text = path.read_text(encoding="utf-8")
    block = top_level_block(text, "paper")
    if block is None:
        raise OmnibusError(f"{path} declares no paper block")
    fields: dict[str, str] = {}
    for line in block.splitlines():
        match = _SCALAR_RE.match(line)
        if match is not None:
            fields[match.group(1)] = match.group(2).strip().strip('"').strip("'")
    missing = [name for name in ("title", "version") if not fields.get(name)]
    if missing:
        raise OmnibusError(f"{path} declares no paper {' or '.join(missing)}")
    return PaperConfig(
        title=fields["title"],
        subtitle=fields.get("subtitle") or None,
        version=fields["version"],
        date=fields.get("date") or None,
    )


# ------------------------------------------------------------ bibliography


@dataclass(frozen=True)
class BibEntry:
    """One bibliography entry, kept as the bytes its author wrote."""

    key: str
    entry_type: str
    fields: tuple[tuple[str, str], ...]
    raw: str
    source: str

    def identity(self) -> tuple[str, ...]:
        """The fields that decide whether two entries are the same work."""
        lookup = dict(self.fields)
        return tuple(normalise_field(lookup.get(name, "")) for name in IDENTITY_FIELDS)


def normalise_field(value: str) -> str:
    """Collapse formatting so a spelling of one name cannot look like a conflict.

    Whitespace, braces, LaTeX accent commands, and Unicode combining marks are
    all removed, because each of them is a way of *writing* a name rather than
    a way of naming a different work. Two works' bibliographies really did
    declare one key as ``Sch{\\"o}n`` and as ``Schön``; those are the same
    author, and a merge that refused them would be refusing a formatting
    difference while calling it a conflict.

    This is the one place in the project where a comparison is deliberately
    made looser, so the limit is worth stating: two genuinely different works
    that share a key and differ *only* in an accent would now merge silently.
    The identity is four fields — author, title, year, doi — and a difference
    in any of the rest still raises, which is what
    ``test_one_key_naming_two_different_works_fails_the_build_with_both_entries``
    and ``test_identity_ignores_formatting_and_a_per_work_note_but_not_a_title``
    hold it to.
    """
    stripped = _ACCENT_COMMAND_RE.sub("", value)
    decomposed = unicodedata.normalize(
        "NFKD", stripped.replace("{", "").replace("}", "")
    )
    without_marks = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(without_marks.split()).casefold()


def matching_brace(text: str, start: int) -> int | None:
    """Index of the brace closing the first one at or after ``start``.

    ``None`` when no brace closes it, which is the case a database edited by
    hand really does produce and the case a reader must not paper over.
    """
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def parse_bib(text: str, source: str) -> tuple[BibEntry, ...]:
    """Parse a BibTeX database by brace matching, keeping each entry verbatim."""
    entries: list[BibEntry] = []
    for match in re.finditer(r"@([A-Za-z]+)\s*\{\s*([^,\s]+)\s*,", text):
        end = matching_brace(text, match.start())
        if end is None:
            raise OmnibusError(f"{source}: unbalanced braces at entry {match.group(2)}")
        raw = text[match.start() : end + 1]
        entries.append(
            BibEntry(
                key=match.group(2),
                entry_type=match.group(1).lower(),
                # The body runs from after the key to just inside the closing
                # brace, which is what keeps that brace out of a trailing
                # field's value.
                fields=_parse_bib_fields(raw[match.end() - match.start() : -1]),
                raw=raw,
                source=source,
            )
        )
    return tuple(entries)


def _parse_bib_fields(body: str) -> tuple[tuple[str, str], ...]:
    """Read ``name = value`` pairs from an entry body, braces or quotes."""
    fields: list[tuple[str, str]] = []
    for match in _BIB_FIELD_RE.finditer(body):
        cursor = match.end()
        if cursor >= len(body):
            break
        opener = body[cursor]
        if opener == "{":
            end = matching_brace(body, cursor)
            if end is None:
                break
            fields.append((match.group(1).lower(), body[cursor + 1 : end]))
        elif opener == '"':
            end = body.find('"', cursor + 1)
            if end < 0:
                break
            fields.append((match.group(1).lower(), body[cursor + 1 : end]))
        else:
            end = body.find(",", cursor)
            stop = len(body) if end < 0 else end
            fields.append((match.group(1).lower(), body[cursor:stop].strip()))
    return tuple(fields)


@dataclass(frozen=True)
class BibDuplicate:
    """One key two papers both declared, with the same work behind it."""

    key: str
    kept_from: str
    dropped_from: str


@dataclass(frozen=True)
class MergedBibliography:
    """The union of the declared works' bibliographies."""

    entries: tuple[BibEntry, ...]
    duplicates: tuple[BibDuplicate, ...]

    @property
    def merged(self) -> int:
        """How many distinct keys survived the merge."""
        return len(self.entries)

    def render(self, keys: Iterable[str]) -> str:
        """Emit the selected entries, each as the bytes its author wrote."""
        wanted = frozenset(keys)
        chosen = [entry for entry in self.entries if entry.key in wanted]
        return "".join(f"{entry.raw}\n\n" for entry in chosen)


def merge_bibliographies(
    databases: Sequence[tuple[str, str]],
) -> MergedBibliography:
    """Union the databases, refusing any key that names two different works.

    ``databases`` is ``(source label, text)`` in volume order. When a key is
    declared twice with the same bibliographic identity — author, title, year,
    and doi, compared with whitespace and braces normalised — the first
    paper's entry is kept verbatim, which keeps that paper's own ``note``
    gloss and drops the later one's; the drop is recorded in ``duplicates``
    rather than being left to be noticed.

    When the identities differ the merge raises. A citation silently
    re-pointed at a different work is the worst thing this function could do,
    and it is the one outcome it is written to make impossible.
    """
    kept: dict[str, BibEntry] = {}
    order: list[str] = []
    duplicates: list[BibDuplicate] = []
    for source, text in databases:
        for entry in parse_bib(text, source):
            existing = kept.get(entry.key)
            if existing is None:
                kept[entry.key] = entry
                order.append(entry.key)
                continue
            if existing.identity() != entry.identity():
                raise OmnibusError(
                    f"bibliography key {entry.key!r} names two different works.\n"
                    f"--- from {existing.source} ---\n{existing.raw}\n"
                    f"--- from {entry.source} ---\n{entry.raw}"
                )
            duplicates.append(
                BibDuplicate(
                    key=entry.key,
                    kept_from=existing.source,
                    dropped_from=entry.source,
                )
            )
    return MergedBibliography(
        entries=tuple(kept[key] for key in order),
        duplicates=tuple(duplicates),
    )


# --------------------------------------------------------- source discovery


@dataclass(frozen=True)
class SourcePaper:
    """One declared work as it was found on disk, present or not.

    ``figures`` is read from what the manuscript embeds, resolved against the
    work's own output directory and deduplicated — never from a directory
    listing. ``output/`` is disposable, and in a project that assembles a
    volume into it, it is also where every other work's plates end up. A work
    that reported whatever was sitting in its output directory would claim to
    ship plates it never drew, and the collision check below would then fire on
    the assembler's own copies.
    """

    entry: LineEntry
    root: Path
    config: PaperConfig | None
    sections: tuple[Path, ...]
    references_only: tuple[Path, ...]
    bib: Path | None
    preamble: Path | None
    figures: tuple[Path, ...]
    cover_image: Path | None
    absence: str

    @property
    def present(self) -> bool:
        """Whether this work contributed any section to the volume."""
        return not self.absence

    @property
    def prefix(self) -> str:
        """The anchor namespace this work's anchors are moved into."""
        return namespace_prefix(self.entry.id)


def _is_bare_heading_file(path: Path) -> bool:
    """Whether a file holds one heading and nothing else."""
    lines = [
        line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    return len(lines) == 1 and lines[0].lstrip().startswith("#")


def discover_paper(entry: LineEntry, base: Path) -> SourcePaper:
    """Find one declared work's manuscript beside this project.

    A work whose manuscript directory holds no section is not an error and is
    not skipped quietly: it comes back with an ``absence`` string, which the
    front matter prints.

    Each work's bare ``References`` heading file is separated out rather than
    carried into the body. The volume has one merged bibliography, so five
    empty heading stubs would be five headings over nothing. The separation is
    conditional on the file really being nothing but a heading; a references
    file carrying prose stays in the body where its prose belongs.
    """
    root = base / entry.id
    manuscript = root / "manuscript"
    if not manuscript.is_dir() and entry.id == WRAPPER_LINE.id:
        # Standalone layout. This repository's own manuscript lives in the
        # repository root, not beside the sibling checkouts — which, in a
        # standalone copy, are absent. In the monorepo ``base/<id>`` IS this
        # repository, so this fallback only engages when a detached clone
        # cannot find itself beside the siblings; the value it lands on is the
        # same directory either way when the set is all present.
        if (PROJECT_ROOT / "manuscript").is_dir():
            root = PROJECT_ROOT
            manuscript = root / "manuscript"
    if not manuscript.is_dir():
        return SourcePaper(
            entry, root, None, (), (), None, None, (), None, "no manuscript directory"
        )
    named = tuple(
        path
        for path in sorted(manuscript.glob("*.md"))
        if path.name not in NON_SECTION_NAMES
    )
    if not named:
        return SourcePaper(
            entry,
            root,
            None,
            (),
            (),
            None,
            None,
            (),
            None,
            "manuscript directory holds no section",
        )
    references = tuple(
        path
        for path in named
        if path.stem.startswith("99_") and _is_bare_heading_file(path)
    )
    sections = tuple(path for path in named if path not in references)
    config_path = manuscript / "config.yaml"
    embedded: set[Path] = set()
    for path in sections:
        for target in collect_embeds(path.read_text(encoding="utf-8")):
            if target.startswith(SOURCE_FIGURE_PREFIX):
                embedded.add(
                    root / "output" / "figures" / target[len(SOURCE_FIGURE_PREFIX) :]
                )
    cover_image: Path | None = None
    if config_path.is_file():
        cover_text = paper_cover_block(config_path.read_text(encoding="utf-8"))
        if cover_text is not None:
            m = re.search(r'image:\s*"([^"]+)"', cover_text)
            if m:
                raw_img = m.group(1)
                for candidate in (
                    root / "manuscript" / raw_img,
                    root / raw_img,
                    root / "output" / raw_img,
                ):
                    if candidate.is_file():
                        cover_image = candidate
                        break
    return SourcePaper(
        entry=entry,
        root=root,
        config=read_paper_config(config_path) if config_path.is_file() else None,
        sections=sections,
        references_only=references,
        bib=(
            manuscript / SOURCE_BIB_NAME
            if (manuscript / SOURCE_BIB_NAME).is_file()
            else None
        ),
        preamble=(
            manuscript / "preamble.md"
            if (manuscript / "preamble.md").is_file()
            else None
        ),
        figures=tuple(sorted(embedded)),
        cover_image=cover_image,
        absence="",
    )


def volume_order(
    lines: tuple[LineEntry, ...] = LINE_SET,
    wrapper: LineEntry = WRAPPER_LINE,
) -> tuple[LineEntry, ...]:
    """The reading order of the volume: the wrapper, then the working order.

    The working order is read off the declaration's ``working_position`` rather
    than written down here, so appending a colour to the set changes this
    function's answer without changing this function.
    """
    return (wrapper, *sorted(lines, key=lambda item: item.working_position))


def unbuilt_plates(paper: SourcePaper) -> tuple[Path, ...]:
    """The plates this work embeds that are not on disk in its checkout.

    ``output/`` is disposable in every one of these projects, so a freshly
    cloned sibling has a manuscript and no figures at all. That is a state of
    the checkout, not a defect in the work.
    """
    return tuple(path for path in paper.figures if not path.is_file())


def _absent_if_unbuilt(paper: SourcePaper) -> SourcePaper:
    """Report a work whose plates were never built the way absence is reported.

    A read-only sibling cannot be repaired from here: this project reads other
    checkouts and writes to none of them, so it cannot build their figures. The
    two honest options are to stop the whole volume or to leave that work out
    and say so, and stopping would mean a freshly cloned set could not compile
    a volume at all while a set with no siblings could. So partial presence
    degrades exactly as absence does — the work is left out, its reason is
    named in the front matter, and the volume is honestly short.

    This is deliberately *not* applied to the assembling work. Its own plates
    are built by its own figure builder in its own tree, so an embed with no
    plate there is a defect in this project and still stops the assembly.
    """
    if not paper.present:
        return paper
    unbuilt = unbuilt_plates(paper)
    if not unbuilt:
        return paper
    shown = sorted(path.name for path in unbuilt)
    names = ", ".join(shown[:3])
    if len(shown) > 3:
        names += f", and {len(shown) - 3} more"
    return replace(
        paper,
        sections=(),
        references_only=(),
        bib=None,
        preamble=None,
        figures=(),
        absence=(
            f"manuscript found, but {len(unbuilt)} embedded plate(s) have not "
            f"been built in that checkout: {names}. Build that work's figures "
            "in its own tree and assemble again; this project does not write "
            "to another work's checkout"
        ),
    )


def discover_papers(
    base: Path | None = None,
    lines: tuple[LineEntry, ...] = LINE_SET,
    wrapper: LineEntry = WRAPPER_LINE,
) -> tuple[SourcePaper, ...]:
    """Find every declared work's manuscript, in volume order.

    ``base`` defaults to :func:`line_set.binding.sibling_base`, so a copy whose
    set is not in its parent directory names where it is with
    ``LINE_SET_SIBLINGS`` rather than being moved into a layout.

    The assembling work comes back exactly as it was found. Every other work
    is passed through :func:`_absent_if_unbuilt`, so a checkout that has the
    prose but not the plates is reported missing-with-a-reason rather than
    raising later out of :func:`gather_figures`.
    """
    root = sibling_base() if base is None else Path(base)
    found = [discover_paper(entry, root) for entry in volume_order(lines, wrapper)]
    return (found[0], *(_absent_if_unbuilt(paper) for paper in found[1:]))


# ------------------------------------------------------------- front matter


@dataclass(frozen=True)
class PaperPlacement:
    """Where one work sits in the volume, and what was read about it."""

    paper: SourcePaper
    part: int
    first_section: int
    last_section: int
    registry_size: int | None
    registry_digest: str | None
    read_code: str

    @property
    def span(self) -> str:
        """The volume section range this work occupies, or why it has none."""
        if not self.paper.present:
            return "none"
        return f"{self.first_section}-{self.last_section}"


def _cell(value: object) -> str:
    """A table cell that says nothing rather than saying a placeholder."""
    return "not read" if value is None else str(value)


def _short(digest: str | None) -> str:
    """A digest abbreviated for a table, or a statement that there is none."""
    return "not read" if digest is None else f"`{digest[:12]}...`"


def front_matter(
    placements: Sequence[PaperPlacement],
    reading: SetReading,
    merged: MergedBibliography,
    dropped_preamble: Sequence[tuple[str, str]],
) -> str:
    """Write the volume's front matter from what the assembly actually read.

    Every number in the table below is read: versions from each work's own
    manuscript configuration, registry sizes and digests from the reading this
    package computed, and section spans from where the sections were actually
    placed.
    """
    present = [item for item in placements if item.paper.present]
    missing = [item for item in placements if not item.paper.present]
    rows = [
        "| Work | Version | Registry size | Registry digest | Volume sections |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in placements:
        title = item.paper.config.title if item.paper.config else item.paper.entry.id
        version = item.paper.config.version if item.paper.config else None
        rows.append(
            f"| {title} | {_cell(version)} | {_cell(item.registry_size)} | "
            f"{_short(item.registry_digest)} | {item.span} |"
        )

    lines = [
        # Pandoc reads a YAML metadata block at the head of the combined
        # markdown, and the front matter is always the first file in the plan.
        # This is where the per-work numbering reset actually reaches the
        # formalism filter; see FORMALISM_METADATA_BLOCK.
        FORMALISM_METADATA_BLOCK.rstrip("\n"),
        "",
        "# About this compiled volume {#sec:omnibus-front-matter}",
        "",
        "This is a compiled volume. It adds no substantive instrument. The work "
        "that assembled it declares the set, reads whichever declared packages "
        "are installed, and checks that no two of them gave the same spelling to "
        "different things; it does not evaluate, rank, reconcile, or summarise "
        "the works it reproduces.",
        "",
        f"Each of the {len(present)} works below is reproduced from its own source "
        "at the version and registry digest stated in the table, unchanged in "
        "substance. The compilation asserts nothing the individual works do not "
        "assert. Its one added claim is the reading recorded immediately below, "
        "and that reading says only that the declared vocabularies of the works "
        "that could be read did not overlap.",
        "",
        f"The reading, computed at assembly: status `{reading.status.value}`, "
        f"read as of {reading.read_as_of}, set digest `{reading.set_digest[:12]}...`, "
        f"reading digest `{reading_digest(reading)[:12]}...`. It is not a finding "
        "that the instruments are correct, complete, good, or worth having, and "
        "it is not a finding about behaviour.",
        "",
        "## The works in this volume",
        "",
        *rows,
        "",
        "Versions are read from each work's own `manuscript/config.yaml`, which "
        "the set contract treats as authoritative. Registry sizes and digests are "
        "read from the installed packages by this volume's own reader; a work "
        "that could not be read reports no size and no digest rather than a "
        "placeholder. A volume section number counts the source sections in "
        "reading order, front matter and part headings excluded.",
        "",
        "## What the compilation changed, and what it did not",
        "",
        "Four mechanical transforms were applied and nothing else. Anchors were "
        "moved into a namespace per source work, so two works that both wrote "
        "`{#sec:abstract}` no longer collide, and every reference to a moved "
        "anchor was moved with it. Headings were shifted down one level so each "
        "work could be given a part heading carrying its own title. Figure "
        "embeds were retargeted at this volume's plate directory. The "
        "bibliographies were merged.",
        "",
        "No claim, caveat, limit, or abstract was altered, and none was omitted. "
        "The transforms are invertible and the assembling project's test suite "
        "inverts them back to the source bytes for every section reproduced here.",
        "",
        f"The merged bibliography holds {merged.merged} distinct keys. "
        f"{len(merged.duplicates)} key(s) were declared by more than one work; for "
        "each, both declarations named the same work, the earlier work's entry "
        "was kept verbatim, and the later work's `note` gloss was dropped.",
        "",
    ]

    if missing:
        lines.extend(
            [
                "## What is missing from this volume",
                "",
                "The following declared works are not reproduced here — some "
                "were not found, some were found without their built plates. "
                "This volume is therefore incomplete, and the gap is stated "
                "rather than closed:",
                "",
            ]
        )
        lines.extend(
            f"- **{item.paper.entry.id}** — {item.paper.absence}." for item in missing
        )
        lines.append("")
    else:
        lines.extend(
            [
                "## What is missing from this volume",
                "",
                "Every declared work was found and reproduced. Nothing declared is "
                "absent from this volume.",
                "",
            ]
        )

    if dropped_preamble:
        lines.extend(
            [
                "The volume compiles under the assembling work's own LaTeX "
                "preamble. These directives from other works' preambles are not "
                "carried into it:",
                "",
            ]
        )
        lines.extend(
            f"- `{directive}` (from {source})" for source, directive in dropped_preamble
        )
        lines.append("")

    return "\n".join(lines)


def part_heading(paper: SourcePaper, part: int) -> str:
    """The part heading that carries one work's own title into the volume.

    When a cover image is configured and present, it is embedded right after
    the title so each work's chapter opens with its own cover art.
    """
    config = paper.config
    title = config.title if config else paper.entry.id
    lines = [f"# {title} {{#sec:{paper.prefix}-part}}", ""]
    if config is not None and config.subtitle:
        lines.extend([f"*{config.subtitle}*", ""])
    if paper.cover_image is not None and paper.cover_image.is_file():
        lines.extend(
            [
                f"![Cover art for {title}]({VOLUME_FIGURE_PREFIX}{paper.cover_image.name})"
                f"{{#fig:{paper.prefix}-cover width=70%}}",
                "",
            ]
        )
    lines.extend(
        [
            f"Reproduced unchanged in substance from its own source at version "
            f"{config.version if config else 'not read'}. "
            f"It answers one question: {paper.entry.question}",
            "",
        ]
    )
    return "\n".join(lines)


def paper_cover_block(source_config: str) -> str | None:
    """Extract the cover block nested under ``paper:``, if present."""
    lines = source_config.splitlines()
    in_paper = False
    in_cover = False
    cover_lines: list[str] = []
    for line in lines:
        if not in_paper:
            if line.rstrip() == "paper:":
                in_paper = True
            continue
        if not line or line[0] not in (" ", "\t"):
            break
        if not in_cover:
            stripped = line.strip()
            if stripped == "cover:":
                in_cover = True
                cover_lines.append(line)
                continue
            if not line.startswith("  "):
                continue
        else:
            if not line.startswith("    "):
                break
            cover_lines.append(line)
    if cover_lines:
        return "\n".join(cover_lines) + "\n"
    return None


def volume_config(
    source_config: str,
    title: str,
    subtitle: str,
    version: str,
    date: str | None,
) -> str:
    """Generate the injected manuscript configuration for the volume.

    The generated-ordering marker is not decoration. Without it the render
    toolchain refreshes this file from the source manuscript's own config, and
    the volume would go out under the assembling paper's title.

    The author, keyword, render, geometry, and rendering blocks are copied
    verbatim from the source configuration, so the volume is typeset on exactly
    the settings the assembling work already uses.

    ``formalism_reset_level`` is added here and is *not* copied from the source:
    a standalone paper must not carry it, because there a level-1 header is a
    section and the counters would restart mid-paper. The volume is the one
    document where level 1 means "a new work", so it is the one document that
    sets it. The same value is written into the front matter as a pandoc
    metadata block, which is the copy the filter actually reads.
    """
    blocks = [
        GENERATED_ORDERING_MARKER,
        "# Written by line_set.omnibus. Every value below is derived; do not hand-edit.",
        "",
        f"{FORMALISM_RESET_KEY}: {FORMALISM_RESET_LEVEL}",
        "",
        "paper:",
        f'  title: "{title}"',
        f'  subtitle: "{subtitle}"',
        f'  version: "{version}"',
    ]
    if date:
        blocks.append(f'  date: "{date}"')
    blocks.append("")
    cover_block = paper_cover_block(source_config)
    if cover_block is not None:
        blocks.append(cover_block)
    for key in (
        "authors",
        "keywords",
        "publication",
        "render",
        "rendering",
        "metadata",
    ):
        block = top_level_block(source_config, key)
        if block is not None:
            blocks.append(block)
    return "\n".join(blocks).rstrip() + "\n"


# ----------------------------------------------------------------- assembly


@dataclass(frozen=True)
class AssemblyReport:
    """What one assembly did, in numbers that were counted rather than assumed."""

    written: Path
    papers_included: int
    papers_missing: tuple[str, ...]
    sections: int
    files: tuple[str, ...]
    anchors_moved: int
    references_moved: int
    figures_retargeted: int
    figures_gathered: int
    figures_copied: int
    bib_entries_merged: int
    bib_duplicates: tuple[BibDuplicate, ...]
    dropped_preamble: tuple[tuple[str, str], ...]

    def as_json(self) -> str:
        """A machine-readable account, sorted so two runs compare cleanly."""
        payload = {
            "written": str(self.written),
            "papers_included": self.papers_included,
            "papers_missing": list(self.papers_missing),
            "sections": self.sections,
            "files": list(self.files),
            "anchors_moved": self.anchors_moved,
            "references_moved": self.references_moved,
            "figures_retargeted": self.figures_retargeted,
            "figures_gathered": self.figures_gathered,
            "figures_copied": self.figures_copied,
            "bib_entries_merged": self.bib_entries_merged,
            "bib_duplicates": [
                {
                    "key": item.key,
                    "kept_from": item.kept_from,
                    "dropped_from": item.dropped_from,
                }
                for item in sorted(self.bib_duplicates, key=lambda item: item.key)
            ],
            "dropped_preamble": [list(item) for item in self.dropped_preamble],
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"

    def summary(self) -> str:
        """One operator-facing paragraph of what landed."""
        missing = ", ".join(self.papers_missing) if self.papers_missing else "none"
        return (
            f"{self.papers_included} work(s) assembled into {len(self.files)} file(s) "
            f"at {self.written}: {self.sections} section(s), {self.anchors_moved} anchor(s) "
            f"namespaced, {self.references_moved} reference(s) rewritten, "
            f"{self.figures_retargeted} embed(s) retargeted, {self.figures_gathered} plate(s) "
            f"gathered ({self.figures_copied} copied in), {self.bib_entries_merged} bibliography entries merged "
            f"({len(self.bib_duplicates)} deduplicated). Missing works: {missing}."
        )


def gather_figures(papers: Sequence[SourcePaper]) -> dict[str, Path]:
    """Map each plate's basename to its source, refusing any collision.

    A collision is refused rather than resolved. Two works shipping one
    basename cannot both be shown in one volume, and the copy that would
    silently win is the one nobody would look at again. The check is run over
    what the works embed at assembly time rather than over a measurement taken
    once; a plate added tomorrow that collides stops the build tomorrow.

    A plate a work embeds but does not have is refused too. A caption over a
    missing file renders as a caption over nothing. By the time a volume is
    assembled this can only be the assembling work's own defect:
    :func:`discover_papers` has already withdrawn every other work whose plates
    were not built, so what reaches here embedding a plate it does not have is
    a work whose figure builder was supposed to produce it.
    """
    gathered: dict[str, Path] = {}
    owners: dict[str, str] = {}
    for paper in papers:
        for path in paper.figures:
            previous = owners.get(path.name)
            if previous is not None:
                raise OmnibusError(
                    f"plate basename {path.name!r} is shipped by both {previous} "
                    f"and {paper.entry.id}; one would silently overwrite the other"
                )
            if not path.is_file():
                raise OmnibusError(
                    f"{paper.entry.id} embeds {path.name!r}, which is not at {path}"
                )
            gathered[path.name] = path
            owners[path.name] = paper.entry.id
    return gathered


def preamble_directives(text: str) -> tuple[str, ...]:
    """The LaTeX directives a fenced preamble block declares."""
    return tuple(
        line.strip() for line in text.splitlines() if line.strip().startswith("\\")
    )


def dropped_preamble_directives(
    papers: Sequence[SourcePaper], carrier: SourcePaper
) -> tuple[tuple[str, str], ...]:
    """Directives other works declare that the volume's preamble does not.

    The render toolchain copies the assembling work's preamble over the
    injected one, so the volume compiles under that preamble whatever this
    assembly writes. What can be done honestly is to say which directives were
    left behind.
    """
    if carrier.preamble is None:
        return ()
    carried = frozenset(
        preamble_directives(carrier.preamble.read_text(encoding="utf-8"))
    )
    dropped: list[tuple[str, str]] = []
    for paper in papers:
        if paper.preamble is None or paper is carrier:
            continue
        for directive in preamble_directives(
            paper.preamble.read_text(encoding="utf-8")
        ):
            if directive not in carried:
                dropped.append((paper.entry.id, directive))
    return tuple(dropped)


def _clear_previous(target: Path) -> None:
    """Remove what a previous assembly wrote, and nothing else."""
    for path in sorted(target.glob("*.md")):
        path.unlink()
    for path in sorted(target.glob("*.bib")):
        path.unlink()
    for name in ("config.yaml", REPORT_NAME):
        candidate = target / name
        if candidate.is_file():
            candidate.unlink()


def assemble(
    project_root: Path | None = None,
    base: Path | None = None,
    lines: tuple[LineEntry, ...] = LINE_SET,
    shared: tuple[SharedToken, ...] = SHARED_TOKENS,
    wrapper: LineEntry = WRAPPER_LINE,
    *,
    resolver: PackageResolver | None = None,
    write: bool = False,
) -> AssemblyReport:
    """Assemble the volume; write it only when asked.

    Writing is opt-in because writing replaces what the render toolchain
    renders for this project. A bare call plans the volume, runs every gate
    over it, and returns the same report without touching the tree, which is
    what makes it safe for the analysis stage to run this command by default.

    ``resolver`` is passed straight to :func:`line_set.reader.read_set`. It
    defaults to the sibling-path resolver, which is the one that finds the
    declared packages in a working tree; a caller that does not want its
    ``sys.path`` touched supplies its own.
    """
    root = PROJECT_ROOT if project_root is None else Path(project_root)
    works_base = sibling_base() if base is None else Path(base)
    papers = discover_papers(works_base, lines, wrapper)
    carrier = papers[0]
    if not carrier.present:
        raise OmnibusError(f"the assembling work has no manuscript: {carrier.absence}")
    if carrier.config is None:
        raise OmnibusError("the assembling work declares no manuscript configuration")

    reading = read_set(
        lines,
        shared,
        resolver=(
            sibling_path_resolver(
                (entry.package_name for entry in lines), base=works_base
            )
            if resolver is None
            else resolver
        ),
        as_of=carrier.config.date,
    )
    observations = {item.line_id: item for item in reading.observations}

    figures = gather_figures([paper for paper in papers if paper.present])
    databases = [
        (paper.entry.id, paper.bib.read_text(encoding="utf-8"))
        for paper in papers
        if paper.present and paper.bib is not None
    ]
    merged = merge_bibliographies(databases)

    plan: list[tuple[str, str]] = []
    placements: list[PaperPlacement] = []
    counts = {"anchors": 0, "references": 0, "figures": 0}
    section_number = 0
    sequence = 1

    for part, paper in enumerate(papers, start=1):
        if not paper.present:
            placements.append(
                PaperPlacement(paper, part, 0, 0, None, None, "not found on disk")
            )
            continue
        first = section_number + 1
        plan.append(
            (f"{sequence:03d}_part_{paper.entry.id}.md", part_heading(paper, part))
        )
        sequence += 1
        anchors: set[str] = set()
        for path in paper.sections:
            anchors.update(collect_anchors(path.read_text(encoding="utf-8")))
        for name in sorted(anchors):
            if name.partition(":")[2].startswith(f"{paper.prefix}-"):
                raise OmnibusError(
                    f"{paper.entry.id} already declares {name!r} in its own namespace, "
                    "so moving it there would not be invertible"
                )
        for path in paper.sections:
            source_text = path.read_text(encoding="utf-8")
            result = transform_section(source_text, paper.prefix, anchors)
            counts["anchors"] += result.anchors_moved
            counts["references"] += result.references_moved
            counts["figures"] += result.figures_retargeted
            section_number += 1
            plan.append(
                (f"{sequence:03d}_{paper.entry.id}_{path.stem}.md", result.text)
            )
            sequence += 1
        observation = observations.get(paper.entry.id)
        placements.append(
            PaperPlacement(
                paper=paper,
                part=part,
                first_section=first,
                last_section=section_number,
                registry_size=(
                    len(lines) if observation is None else observation.registry_size
                ),
                registry_digest=(
                    registry_digest(lines, shared)
                    if observation is None
                    else observation.registry_digest
                ),
                read_code=(
                    ReadCode.RESOLVED.value
                    if observation is None
                    else observation.code.value
                ),
            )
        )

    dropped = dropped_preamble_directives(papers, carrier)
    plan.insert(
        0,
        (
            "000_front_matter.md",
            front_matter(placements, reading, merged, dropped),
        ),
    )
    plan.append((f"{sequence:03d}_volume_references.md", "# References\n"))

    namespaced = {
        f"{kind}:{paper.prefix}-{name}"
        for paper in papers
        if paper.present
        for kind, _, name in _split_anchors(
            {
                anchor
                for path in paper.sections
                for anchor in collect_anchors(path.read_text(encoding="utf-8"))
            }
        )
    }
    namespaced.update(f"sec:{paper.prefix}-part" for paper in papers if paper.present)
    namespaced.add("sec:omnibus-front-matter")
    dangling = sorted(
        {ref for _, text in plan for ref in unresolved_references(text, namespaced)}
    )
    if dangling:
        raise OmnibusError(
            f"the assembled volume has unresolved references: {dangling}"
        )

    # Extend the figure map with cover images so the embed check passes.
    cover_map: dict[str, Path] = {}
    for paper in papers:
        if (
            paper.present
            and paper.cover_image is not None
            and paper.cover_image.is_file()
        ):
            cover_map[paper.cover_image.name] = paper.cover_image
    all_embeds = {**figures, **cover_map}
    for name, text in plan:
        for embed_target in collect_embeds(text):
            basename = embed_target[len(VOLUME_FIGURE_PREFIX) :]
            if (
                not embed_target.startswith(VOLUME_FIGURE_PREFIX)
                or basename not in all_embeds
            ):
                raise OmnibusError(
                    f"{name} embeds {embed_target!r}, which is not a plate this volume "
                    f"gathered; every embed must point at {VOLUME_FIGURE_PREFIX}"
                )

    target = root
    for part_name in INJECTED_MANUSCRIPT_DIR:
        target = target / part_name
    copied = 0
    if write:
        target.mkdir(parents=True, exist_ok=True)
        _clear_previous(target)
        for name, text in plan:
            (target / name).write_text(text, encoding="utf-8")
        (target / SOURCE_BIB_NAME).write_text(
            merged.render(_keys_of(carrier)), encoding="utf-8"
        )
        (target / VOLUME_BIB_NAME).write_text(
            merged.render(
                key
                for key in (entry.key for entry in merged.entries)
                if key not in _keys_of(carrier)
            ),
            encoding="utf-8",
        )
        plates = root
        for part_name in VOLUME_FIGURES_DIR:
            plates = plates / part_name
        plates.mkdir(parents=True, exist_ok=True)
        for name, source in sorted(figures.items()):
            destination = plates / name
            if destination.resolve() != source.resolve():
                shutil.copy2(source, destination)
                copied += 1
        # Copy cover images from sibling works so they render in the volume.
        for name, source in sorted(cover_map.items()):
            dest = plates / name
            if not dest.exists() or dest.resolve() != source.resolve():
                shutil.copy2(source, dest)

    report = AssemblyReport(
        written=target,
        papers_included=sum(1 for paper in papers if paper.present),
        papers_missing=tuple(paper.entry.id for paper in papers if not paper.present),
        sections=section_number,
        files=tuple(name for name, _ in plan),
        anchors_moved=counts["anchors"],
        references_moved=counts["references"],
        figures_retargeted=counts["figures"],
        figures_gathered=len(figures) if write else 0,
        figures_copied=copied,
        bib_entries_merged=merged.merged,
        bib_duplicates=merged.duplicates,
        dropped_preamble=dropped,
    )
    if write:
        (target / "config.yaml").write_text(
            volume_config(
                (carrier.root / "manuscript" / "config.yaml").read_text(
                    encoding="utf-8"
                ),
                title=volume_title(carrier),
                subtitle=volume_subtitle(placements),
                version=carrier.config.version,
                date=carrier.config.date,
            ),
            encoding="utf-8",
        )
        (target / REPORT_NAME).write_text(report.as_json(), encoding="utf-8")
    return report


def _keys_of(paper: SourcePaper) -> frozenset[str]:
    """The bibliography keys one work declares in its own database."""
    if paper.bib is None:
        return frozenset()
    return frozenset(
        entry.key
        for entry in parse_bib(paper.bib.read_text(encoding="utf-8"), paper.entry.id)
    )


def volume_title(carrier: SourcePaper) -> str:
    """The volume's title, derived from the assembling work's own title."""
    assert carrier.config is not None
    head = carrier.config.title.split(":", 1)[0].strip()
    return f"{head}: The Collected Volume"


def volume_subtitle(placements: Sequence[PaperPlacement]) -> str:
    """A subtitle that counts what is actually inside."""
    present = sum(1 for item in placements if item.paper.present)
    return (
        f"{present} works compiled unchanged in substance, with one merged "
        "bibliography and one reading of the set"
    )

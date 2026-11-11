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
bibliographies. It also omits actual reference stubs and removes empty live
bibliography placeholders, which belong to the volume's final reference page.
It does not summarize, reconcile, rank, or reword substantive prose. The
section round trip in :func:`invert_section` preserves source bytes except
that multi-hop image destinations restore to the canonical one-hop prefix;
literal examples and prose paths are not canonicalized.

The compilation asserts nothing the individual papers do not assert. The one
claim it adds is the lexical reading this package computed over the declared
set: observed published-name collisions and exact declared exemptions.

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

from ._markdown_spans import prose_spans
from .binding import PROJECT_ROOT, PackageResolver, sibling_base, sibling_path_resolver
from .models import LineEntry, ReadCode, SetReading, SharedToken
from .reader import read_set
from .registry import LINE_SET, SHARED_TOKENS, WRAPPER_LINE
from .serialization import reading_digest, registry_digest

#: Manuscript filenames the render toolchain never treats as a section.
NON_SECTION_NAMES: frozenset[str] = frozenset(
    {"AGENTS.md", "MANUSCRIPT_STATUS.md", "README.md", "SYNTAX.md", "preamble.md"}
)

#: A source manuscript embed points at the work's own plate directory with a
#: relative prefix; the number of ``../`` hops depends on the manuscript layout
#: (``docs/manuscript/`` needs two, a root ``manuscript/`` needs one).
_SOURCE_FIGURE_RE = re.compile(r"(?<![\w/])(?:\.\./)+output/figures/")


def _source_figure_basename(target: str) -> str | None:
    """The plate filename an embed target names, or None if it is not one."""

    if (basename := _SOURCE_FIGURE_RE.sub("", target, count=1)) != target:
        return basename
    return None


def _manuscript_dir(project_root: Path) -> Path:
    """A work's configured manuscript directory, docs-first when both exist.

    The line set's canonical manuscript tree lives under ``docs/manuscript/``;
    a sibling or synthetic fixture may keep ``manuscript/`` at the root.
    An unconfigured migration fragment must not shadow a configured source.
    Without either config, retain the directory-based absence behavior.
    """
    docs = project_root / "docs" / "manuscript"
    root_layout = project_root / "manuscript"
    if (docs / "config.yaml").is_file():
        return docs
    if (root_layout / "config.yaml").is_file():
        return root_layout
    if docs.is_dir():
        return docs
    return root_layout


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
#: ``../output/figures/`` is written relative to the manuscript sources. From
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
#: places. Citation links are enabled here too, so formats that consume source
#: metadata receive the setting rather than an inert root-config key.
FORMALISM_METADATA_BLOCK: str = (
    f"---\n{FORMALISM_RESET_KEY}: {FORMALISM_RESET_LEVEL}\nlink-citations: true\n---\n"
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


def map_prose_lines(text: str, transform: Callable[[str], str]) -> str:
    """Transform lines with literal spans hidden, then restore their bytes.

    Opaque tokens preserve line starts for heading/Div recognition. Callbacks
    must not treat a token-bearing image destination as an active embed.
    """
    marker = "\x00"
    while marker in text:
        marker += "\x00"
    spans: list[tuple[int, int]] = []
    previous = 0
    for left, right in prose_spans(text):
        if previous < left:
            spans.append((previous, left))
        previous = right
    if previous < len(text):
        spans.append((previous, len(text)))
    rebuilt: list[str] = []
    offset = 0
    span_index = 0
    for line in text.splitlines(keepends=True):
        ending = (
            "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
        )
        body = line[: -len(ending)] if ending else line
        stop = offset + len(body)
        replacements: list[tuple[str, str]] = []
        pieces: list[str] = []
        cursor = offset
        while span_index < len(spans) and spans[span_index][1] <= offset:
            span_index += 1
        index = span_index
        while index < len(spans) and spans[index][0] < stop:
            left, right = spans[index]
            left, right = max(left, offset), min(right, stop)
            token = f"{marker}literal-{len(replacements)}{marker}"
            pieces.extend((text[cursor:left], token))
            replacements.append((token, text[left:right]))
            cursor = right
            index += 1
        pieces.append(text[cursor:stop])
        masked = "".join(pieces)
        changed = transform(masked)
        for token, literal in replacements:
            changed = changed.replace(token, literal)
        rebuilt.append(changed + ending)
        offset += len(line)
    return "".join(rebuilt)


def anchor_pattern(line: str) -> re.Pattern[str]:
    """The label pattern that applies to one line.

    A fenced-Div line declares its identifier as a bare ``#kind:name`` among
    the Div's other attributes; everywhere else the identifier follows ``{``.
    Choosing one pattern per line rather than running both keeps a Div written
    ``::: {#def:x .definition}`` from being rewritten twice.
    """
    return _DIV_ANCHOR_DEF_RE if _DIV_FENCE_RE.match(line) else _ANCHOR_DEF_RE


def collect_anchors(text: str) -> tuple[str, ...]:
    """Return every supported ``kind:name`` definition outside literal spans."""
    found: set[str] = set()

    def record(line: str) -> str:
        for kind, name in anchor_pattern(line).findall(line):
            found.add(f"{kind}:{name}")
        return line

    map_prose_lines(text, record)
    return tuple(sorted(found))


def collect_embeds(text: str) -> tuple[str, ...]:
    """Return every active image target, excluding literal examples."""
    found: list[str] = []

    def record(line: str) -> str:
        found.extend(
            target for target in _EMBED_RE.findall(line) if "\x00" not in target
        )
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


def _crossref_parts(
    match: re.Match[str], anchors: frozenset[str]
) -> tuple[str, str, str]:
    """Separate a bare reference's kind, name, and sentence punctuation.

    Periods inside identifiers are exact. For terminal periods, prefer the
    longest declared target (including a declared trailing-dot name); any
    remaining periods stay in the source as punctuation. With no declared
    target, terminal periods are punctuation for unresolved-reference reports.
    Markdown link destinations do not use this contextual rule.
    """
    kind, raw_name = match.group(1), match.group(2)
    name = raw_name
    while name.endswith(".") and f"{kind}:{name}" not in anchors:
        name = name[:-1]
    return kind, name, raw_name[len(name) :]


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
            kind, name, punctuation = _crossref_parts(match, known)
            if f"{kind}:{name}" not in known:
                return match.group(0)
            counts[1] += 1
            return f"@{kind}:{prefix}-{name}{punctuation}"

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
    moved = frozenset(
        f"{kind}:{prefix}-{name}" for kind, _, name in _split_anchors(anchors)
    )

    def rewrite(line: str) -> str:
        def restore(match: re.Match[str]) -> str:
            kind, name = match.group(1), match.group(2)
            if f"{kind}:{name}" not in moved:
                return match.group(0)
            return f"{match.group(0)[: -len(name)]}{name[len(prefix) + 1 :]}"

        def restore_ref(match: re.Match[str]) -> str:
            kind, name, punctuation = _crossref_parts(match, moved)
            if f"{kind}:{name}" not in moved:
                return match.group(0)
            return f"@{kind}:{name[len(prefix) + 1 :]}{punctuation}"

        line = anchor_pattern(line).sub(restore, line)
        line = _CROSSREF_RE.sub(restore_ref, line)

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


def _embed_destination(match: re.Match[str], target: str) -> str:
    """Replace only the destination, even when its text repeats in the caption."""
    left = match.start(1) - match.start()
    right = match.end(1) - match.start()
    return match.group()[:left] + target + match.group()[right:]


def retarget_figures(text: str) -> tuple[str, int]:
    """Point figure embeds at the volume's plate directory.

    The source prefix may be written at any ``../`` depth (a root
    ``manuscript/`` writes one hop, a ``docs/manuscript/`` tree writes two);
    the volume's embeds are always the one-hop
    :data:`VOLUME_FIGURE_PREFIX`. The retargeting is depth-collapsing by
    design, so the inverse is :func:`restore_figures` with the same
    canonical one-hop restore documented there.
    """
    count = [0]

    def rewrite(line: str) -> str:
        def retarget(match: re.Match[str]) -> str:
            target = match.group(1)
            if "\x00" in target:
                return match.group()
            if target.startswith(VOLUME_FIGURE_PREFIX):
                raise OmnibusError(
                    f"the source already writes {VOLUME_FIGURE_PREFIX!r}, so "
                    "retargeting it would not be invertible"
                )
            basename = _source_figure_basename(target)
            if basename is None:
                return match.group()
            count[0] += 1
            return _embed_destination(match, VOLUME_FIGURE_PREFIX + basename)

        return _EMBED_RE.sub(retarget, line)

    return map_prose_lines(text, rewrite), count[0]


def restore_figures(text: str) -> str:
    """The inverse of :func:`retarget_figures` for a single-hop manuscript.

    :func:`retarget_figures` collapses any ``../`` depth to the volume's
    one-hop prefix, so the round trip restores one hop regardless of how many
    the source wrote. The volume itself is always written at the one-hop
    depth, so assembly round-trips exactly there; a multi-hop source section
    in some checkout is restored to the canonical one-hop spelling instead.
    """

    def restore(line: str) -> str:
        def destination(match: re.Match[str]) -> str:
            target = match.group(1)
            if "\x00" in target or not target.startswith(VOLUME_FIGURE_PREFIX):
                return match.group()
            return _embed_destination(
                match, SOURCE_FIGURE_PREFIX + target[len(VOLUME_FIGURE_PREFIX) :]
            )

        return _EMBED_RE.sub(destination, line)

    return map_prose_lines(text, restore)


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
        for match in _CROSSREF_RE.finditer(line):
            kind, name, _ = _crossref_parts(match, known)
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

    The set contract treats ``docs/manuscript/config.yaml`` as the authoritative
    statement of a work's version, so that is where the version is read from
    rather than from the package the reader happens to import.
    """

    title: str
    subtitle: str | None
    version: str
    date: str | None


def _yaml_scalar(raw: str) -> str:
    """Decode one single-line YAML string scalar; refuse other node forms."""
    value = raw.strip()
    if not value or value.startswith("#"):
        return ""
    if value[0] not in ("'", '"'):
        value = re.split(r"[ \t]+#", value, maxsplit=1)[0].rstrip()
        if value[0] in "|>!&*[{`,%@":
            raise OmnibusError("unsupported paper scalar; use a single-line string")
        return value
    quote = value[0]
    decoded: list[str] = []
    cursor = 1
    escapes = {
        "0": "\0",
        "a": "\a",
        "b": "\b",
        "t": "\t",
        "n": "\n",
        "v": "\v",
        "f": "\f",
        "r": "\r",
        "e": "\x1b",
        " ": " ",
        '"': '"',
        "/": "/",
        "\\": "\\",
        "N": "\x85",
        "_": "\xa0",
        "L": "\u2028",
        "P": "\u2029",
    }
    while cursor < len(value):
        char = value[cursor]
        if char == quote:
            if quote == "'" and value[cursor : cursor + 2] == "''":
                decoded.append("'")
                cursor += 2
                continue
            rest = value[cursor + 1 :]
            if rest and not re.fullmatch(r"[ \t]+(?:#.*)?", rest):
                raise OmnibusError("unsupported text after quoted paper scalar")
            return "".join(decoded)
        if char == "\\" and quote == '"':
            cursor += 1
            if cursor >= len(value):
                break
            escape = value[cursor]
            if escape in escapes:
                decoded.append(escapes[escape])
            elif escape in ("x", "u", "U"):
                length = {"x": 2, "u": 4, "U": 8}[escape]
                digits = value[cursor + 1 : cursor + 1 + length]
                if (
                    len(digits) != length
                    or re.fullmatch(r"[0-9a-fA-F]+", digits) is None
                ):
                    raise OmnibusError("invalid YAML scalar escape")
                number = int(digits, 16)
                if number > 0x10FFFF or 0xD800 <= number <= 0xDFFF:
                    raise OmnibusError("invalid YAML scalar code point")
                decoded.append(chr(number))
                cursor += length
            else:
                raise OmnibusError(f"unsupported YAML scalar escape: \\{escape}")
        else:
            decoded.append(char)
        cursor += 1
    raise OmnibusError("unsupported multiline or unterminated paper scalar")


def _yaml_quote(value: str) -> str:
    """Emit a double-quoted YAML scalar without raw YAML line/control breaks."""
    encoded = json.dumps(value, ensure_ascii=False)
    return "".join(
        f"\\u{ord(char):04x}"
        if 0x7F <= ord(char) <= 0x9F or char in "\u2028\u2029"
        else char
        for char in encoded
    )


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
    scalar_continuation = False
    for line in block.splitlines():
        match = _SCALAR_RE.match(line)
        if match is not None:
            scalar_continuation = match.group(1) in (
                "title",
                "subtitle",
                "version",
                "date",
            )
            if scalar_continuation:
                fields[match.group(1)] = _yaml_scalar(match.group(2))
        elif (
            scalar_continuation
            and len(line) - len(line.lstrip(" ")) > 2
            and line.strip()
            and not line.lstrip().startswith("#")
        ):
            raise OmnibusError(f"{path}: unsupported multiline paper scalar")
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
        return tuple(normalize_field(lookup.get(name, "")) for name in IDENTITY_FIELDS)


def normalize_field(value: str) -> str:
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
    """Find the first balanced brace group, ignoring escaped characters."""
    depth = 0
    cursor = start
    while cursor < len(text):
        char = text[cursor]
        if char == "\\":
            cursor += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}" and depth:
            depth -= 1
            if depth == 0:
                return cursor
        cursor += 1
    return None


def _bib_space(text: str, cursor: int) -> int:
    """Skip whitespace and percent comments outside values."""
    while cursor < len(text):
        if text[cursor].isspace():
            cursor += 1
        elif text[cursor] == "%":
            end = text.find("\n", cursor)
            cursor = len(text) if end < 0 else end + 1
        else:
            break
    return cursor


def _bib_quote_end(text: str, start: int) -> int | None:
    depth = 0
    cursor = start + 1
    while cursor < len(text):
        char = text[cursor]
        if char == "\\":
            cursor += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            if depth == 0:
                return None
            depth -= 1
        elif char == '"' and depth == 0:
            return cursor
        cursor += 1
    return None


def _bib_entry_end(text: str, start: int) -> int | None:
    """Find an entry closer without mistaking a field's contents for it."""
    cursor = start + 1
    while cursor < len(text):
        cursor = _bib_space(text, cursor)
        if cursor >= len(text):
            break
        char = text[cursor]
        if char in ('"', "{"):
            end = (
                _bib_quote_end(text, cursor)
                if char == '"'
                else matching_brace(text, cursor)
            )
            if end is None:
                return None
            cursor = end + 1
        elif char == "\\":
            cursor += 2
        elif char == "}":
            return cursor
        else:
            cursor += 1
    return None


def parse_bib(text: str, source: str) -> tuple[BibEntry, ...]:
    """Read literal braced records, or explicitly refuse unsupported BibTeX.

    Percent comments and balanced @comment blocks are not entries. Standard
    bare month names are retained. Macro declarations, other macro-valued fields,
    preambles, parenthesized records and concatenation are refused, never dropped.
    """
    entries: list[BibEntry] = []
    cursor = 0
    while cursor < len(text):
        cursor = _bib_space(text, cursor)
        if cursor >= len(text):
            break
        if text[cursor] != "@":
            cursor += 2 if text[cursor] == "\\" else 1
            continue
        match = re.match(r"@([A-Za-z]+)\s*([({])", text[cursor:])
        if match is None:
            raise OmnibusError(f"{source}: unsupported BibTeX directive at {cursor}")
        kind = match.group(1).lower()
        if kind in ("string", "preamble") or match.group(2) != "{":
            raise OmnibusError(f"{source}: unsupported BibTeX construct @{kind}")
        opening = cursor + match.end() - 1
        end = (
            matching_brace(text, opening)
            if kind == "comment"
            else _bib_entry_end(text, opening)
        )
        if end is None:
            raise OmnibusError(f"{source}: unbalanced BibTeX entry at {cursor}")
        if kind != "comment":
            key_match = re.match(r"\s*([^,\s{}()]+)\s*,", text[opening + 1 : end])
            if key_match is None:
                raise OmnibusError(f"{source}: unsupported or missing BibTeX key")
            body = text[opening + 1 + key_match.end() : end]
            try:
                fields = _parse_bib_fields(body)
            except OmnibusError as error:
                raise OmnibusError(
                    f"{source}: {key_match.group(1)}: {error}"
                ) from error
            entries.append(
                BibEntry(
                    key=key_match.group(1),
                    entry_type=kind,
                    fields=fields,
                    raw=text[cursor : end + 1],
                    source=source,
                )
            )
        cursor = end + 1
    return tuple(entries)


def _parse_bib_fields(body: str) -> tuple[tuple[str, str], ...]:
    """Read only top-level fields, advancing over each complete value."""
    fields: list[tuple[str, str]] = []
    cursor = _bib_space(body, 0)
    while cursor < len(body):
        match = _BIB_FIELD_RE.match(body, cursor)
        if match is None:
            raise OmnibusError("unsupported BibTeX field syntax")
        cursor = _bib_space(body, match.end())
        if cursor >= len(body):
            raise OmnibusError("missing BibTeX field value")
        opener = body[cursor]
        if opener in ("{", '"'):
            end = (
                matching_brace(body, cursor)
                if opener == "{"
                else _bib_quote_end(body, cursor)
            )
            if end is None:
                raise OmnibusError("unbalanced BibTeX field value")
            value = body[cursor + 1 : end]
            cursor = end + 1
        else:
            token = re.match(r"[0-9]+|[A-Za-z][A-Za-z0-9_-]*", body[cursor:])
            if token is None:
                raise OmnibusError("unsupported BibTeX field value")
            value = token.group()
            if not value.isdecimal() and value.lower() not in (
                "jan",
                "feb",
                "mar",
                "apr",
                "may",
                "jun",
                "jul",
                "aug",
                "sep",
                "oct",
                "nov",
                "dec",
            ):
                raise OmnibusError("unsupported BibTeX macro-valued field")
            cursor += token.end()
        fields.append((match.group(1).lower(), value))
        cursor = _bib_space(body, cursor)
        if cursor < len(body):
            if body[cursor] != ",":
                raise OmnibusError(
                    "unsupported BibTeX concatenation or field separator"
                )
            cursor = _bib_space(body, cursor + 1)
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
    and doi, compared with whitespace and braces normalized — the first
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


def _remove_empty_reference_placeholders(text: str) -> str:
    """Keep native reference prose and literals; the volume owns the bibliography."""
    if "#refs" not in text:
        return text
    lines = text.splitlines(keepends=True)
    active = prose_spans(text)
    marks: list[bool] = []
    offset = 0
    for line in lines:
        stop = offset + len(line.rstrip("\r\n"))
        marks.append(
            not any(left <= offset and stop <= right for left, right in active)
        )
        offset += len(line)
    kept: list[str] = []
    index = 0
    while index < len(lines):
        opening = (
            None
            if marks[index]
            else re.fullmatch(
                r" {0,3}(:{3,})[ \t]*\{[ \t]*#refs[ \t]*\}[ \t]*",
                lines[index].rstrip("\r\n"),
            )
        )
        if opening is not None:
            closing = index + 1
            while closing < len(lines) and not lines[closing].strip():
                closing += 1
            if closing < len(lines) and not marks[closing]:
                delimiter = re.fullmatch(
                    r" {0,3}(:{3,})[ \t]*", lines[closing].rstrip("\r\n")
                )
                if delimiter is not None and len(delimiter.group(1)) >= len(
                    opening.group(1)
                ):
                    index = closing + 1
                    continue
        kept.append(lines[index])
        index += 1
    return "".join(kept)


def _is_references_stub_file(path: Path) -> bool:
    """Recognize an actual References heading, never an indented code example."""
    lines = [
        line.rstrip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if (
        not lines
        or re.fullmatch(
            r" {0,3}#{1,6}\s+References(?:\s+\{[^{}\r\n]*\})?(?:\s+#+)?",
            lines[0],
            flags=re.IGNORECASE,
        )
        is None
    ):
        return False
    if len(lines) == 1:
        return True
    if len(lines) != 3:
        return False
    opening = re.fullmatch(r" {0,3}(:{3,})\s*\{\s*#refs\s*\}", lines[1])
    closing = re.fullmatch(r" {0,3}(:{3,})", lines[2])
    return (
        opening is not None
        and closing is not None
        and len(closing.group(1)) >= len(opening.group(1))
    )


def discover_paper(entry: LineEntry, base: Path) -> SourcePaper:
    """Find one declared work's manuscript beside this project.

    A work whose manuscript directory holds no section is not an error and is
    not skipped quietly: it comes back with an ``absence`` string, which the
    front matter prints.

    Each work's empty ``References`` page is separated out rather than carried
    into the body. A heading and an empty ``#refs`` Div are structural stubs:
    retaining that placeholder would put the entire merged bibliography inside
    one reproduced work. A references file carrying prose or examples stays in
    the body where its content belongs.
    """
    root = base / entry.id
    manuscript = _manuscript_dir(root)
    if not manuscript.is_dir() and entry.id == WRAPPER_LINE.id:
        # Standalone layout. This repository's own manuscript lives in the
        # repository root, not beside the sibling checkouts — which, in a
        # standalone copy, are absent. In the monorepo ``base/<id>`` IS this
        # repository, so this fallback only engages when a detached clone
        # cannot find itself beside the siblings; the value it lands on is the
        # same directory either way when the set is all present.
        if _manuscript_dir(PROJECT_ROOT).is_dir():
            root = PROJECT_ROOT
            manuscript = _manuscript_dir(root)
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
        if path.stem.startswith("99_") and _is_references_stub_file(path)
    )
    sections = tuple(path for path in named if path not in references)
    config_path = manuscript / "config.yaml"
    embedded: set[Path] = set()
    for path in sections:
        for target in collect_embeds(path.read_text(encoding="utf-8")):
            basename = _source_figure_basename(target)
            if basename is not None:
                embedded.add(root / "output" / "figures" / basename)
    cover_image: Path | None = None
    if config_path.is_file():
        cover_text = paper_cover_block(config_path.read_text(encoding="utf-8"))
        if cover_text is not None:
            m = re.search(r"^    image:\s*(.*)$", cover_text, flags=re.MULTILINE)
            if m:
                raw_img = _yaml_scalar(m.group(1))
                for candidate in (
                    manuscript / raw_img,
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
    than written down here, so appending a color to the set changes this
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
        "are installed, and checks published enum-member-name collisions under "
        "exact declared exemptions; it does not evaluate, rank, reconcile, or summarize "
        "the works it reproduces.",
        "",
        f"Each of the {len(present)} works below is reproduced from its own source "
        "at the version and registry digest stated in the table, unchanged in "
        "substance. The compilation asserts nothing the individual works do not "
        "assert. Its one added claim is the reading recorded immediately below, "
        "and that reading records published spellings and declared exemptions "
        "among the vocabularies that could be read. It does not establish "
        "conceptual separation.",
        "",
        f"The reading, computed at assembly: status `{reading.status.value}`, "
        f"read as of {reading.read_as_of}, set digest `{reading.set_digest[:12]}...`, "
        f"reading digest `{reading_digest(reading)[:12]}...`; "
        f"{len(reading.exempted_collisions)} exempted published-name collisions and "
        f"{len(reading.collisions)} unexempted published-name collisions; "
        f"{reading.counts()[ReadCode.RESOLVED.value]} of {len(reading.observations)} "
        "readable vocabularies. It is not a finding "
        "that the instruments are correct, complete, good, or worth having, and "
        "it is not a finding about behavior.",
        "",
        "## The works in this volume",
        "",
        *rows,
        "",
        "Versions are read from each work's own `docs/manuscript/config.yaml`, which "
        "the set contract treats as authoritative. Registry sizes and digests are "
        "read from the installed packages by this volume's own reader; a work "
        "that could not be read reports no size and no digest rather than a "
        "placeholder. A volume section number counts the source sections in "
        "reading order, front matter and part headings excluded.",
        "",
        "## What the compilation changed, and what it did not",
        "",
        "The mechanical section transforms moved anchors into "
        "a namespace per source work, so two works that both wrote "
        "`{#sec:abstract}` no longer collide, and every reference to a moved "
        "anchor was moved with it. Headings were shifted down one level so each "
        "work could be given a part heading carrying its own title. Figure "
        "embeds were retargeted at this volume's plate directory. The "
        "bibliographies were merged. Actual reference stubs were omitted and "
        "empty live reference placeholders were removed so the volume owns one "
        "final bibliography; meaningful reference sections remain in place.",
        "",
        "Substantive prose, caveats, limits, and literal examples are not reworded. "
        "The section round-trip contract preserves source bytes except that "
        "source image-prefix depth is normalized to the canonical one-hop "
        "spelling. Stub omission and placeholder removal are separate assembly "
        "operations, not claims of whole-volume byte inversion.",
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


def cover_embed_name(paper: SourcePaper) -> str:
    """The unique volume basename one work's cover copy gets.

    Two works can ship covers under one basename (``cover_art.png``), and the
    render toolchain maps one filename to exactly one registry record. Each
    part's cover is therefore copied under a prefix-unique name, which gives
    every part heading's ``fig:{prefix}-cover`` label its own file and record.

    Raises ``ValueError`` when the paper declares no cover image; callers gate
    on ``paper.cover_image is not None`` before reaching here.
    """

    if paper.cover_image is None:
        raise ValueError(f"{paper.prefix} declares no cover image to name")
    return f"{paper.prefix}-cover-{paper.cover_image.name}"


def part_heading(paper: SourcePaper, part: int) -> str:
    """The part heading that carries one work's own title into the volume.

    When a cover image is configured and present, it is embedded right after
    the title at full text width so compilation does not unnecessarily reduce
    the native labels. The configured figure-height cap still applies.
    """
    config = paper.config
    title = config.title if config else paper.entry.id
    lines = [f"# {title} {{#sec:{paper.prefix}-part}}", ""]
    if config is not None and config.subtitle:
        lines.extend([f"*{config.subtitle}*", ""])
    if paper.cover_image is not None and paper.cover_image.is_file():
        lines.extend(
            [
                f"![Cover art for {title}]({VOLUME_FIGURE_PREFIX}{cover_embed_name(paper)})"
                f"{{#fig:{paper.prefix}-cover width=100%}}",
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
        if not line.strip() or line.lstrip().startswith("#"):
            if in_cover:
                cover_lines.append(line)
            continue
        if line[0] not in (" ", "\t"):
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
        f"  title: {_yaml_quote(title)}",
        f"  subtitle: {_yaml_quote(subtitle)}",
        f"  version: {_yaml_quote(version)}",
    ]
    if date:
        blocks.append(f"  date: {_yaml_quote(date)}")
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
    """One assembly's counts, Markdown inventory, and original image sources.

    ``files`` inventories section Markdown only, not every generated artifact.
    ``image_sources`` binds exact compiled targets to native files, not to a
    renderer or a presumed SVG sibling. Neither is a complete custody manifest.
    """

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
    image_sources: tuple[tuple[str, Path], ...]

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
            "image_sources": {
                target: str(source) for target, source in self.image_sources
            },
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


def _managed_path(root: Path, path: Path, *, directory: bool = False) -> None:
    """Refuse symlinks, escapes, and wrong node kinds before output mutation."""
    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise OmnibusError(f"managed output escapes project root: {path}") from error
    current = root
    for part in ("", *relative.parts):
        if part:
            current = current / part
        if current.is_symlink():
            raise OmnibusError(f"managed output must not be a symlink: {current}")
        is_directory = current != path or directory
        if current.exists() and not (
            current.is_dir() if is_directory else current.is_file()
        ):
            raise OmnibusError(f"managed output has the wrong node kind: {current}")
    try:
        path.resolve().relative_to(root.resolve())
    except (ValueError, OSError, RuntimeError) as error:
        raise OmnibusError(f"managed output escapes project root: {path}") from error


def _previous_files(target: Path) -> tuple[str, ...]:
    """Read the existing section inventory; never infer ownership by extension."""
    path = target / REPORT_NAME
    if not path.exists():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as error:
        raise OmnibusError(
            f"cannot read previous assembly inventory: {path}"
        ) from error
    files = payload.get("files") if isinstance(payload, dict) else None
    if not isinstance(files, list) or any(
        not isinstance(name, str)
        or Path(name).name != name
        or not name.endswith(".md")
        or name in NON_SECTION_NAMES
        for name in files
    ):
        raise OmnibusError(f"invalid previous assembly section inventory: {path}")
    return tuple(files)


def _clear_previous(target: Path, obsolete: Iterable[str]) -> None:
    """Remove only obsolete sections named in the previous assembly inventory."""
    for name in sorted(obsolete):
        path = target / name
        if path.exists():
            path.unlink()


def _figure_placements(text: str) -> tuple[tuple[str | None, str], ...]:
    """Read active image targets and their adjacent supported figure labels."""
    placements: list[tuple[str | None, str]] = []

    def record(line: str) -> str:
        for match in _EMBED_RE.finditer(line):
            if "\x00" in match.group(1):
                continue
            label = _ANCHOR_DEF_RE.match(line[match.end() :].lstrip(" \t"))
            placements.append(
                (
                    f"fig:{label.group(2)}"
                    if label is not None and label.group(1) == "fig"
                    else None,
                    match.group(1),
                )
            )
        return line

    map_prose_lines(text, record)
    return tuple(placements)


def _check_figure_coverage(
    plan: Sequence[tuple[str, str]], records: Sequence[dict[str, object]]
) -> None:
    """Bind every actual compiled image to one genuine accessible record."""
    for name, text in plan:
        for label, target in _figure_placements(text):
            filename = target[len(VOLUME_FIGURE_PREFIX) :]
            matching = [
                record
                for record in records
                if (
                    record.get("label") == label
                    if label is not None
                    else record.get("filename") == filename
                )
            ]
            if len(matching) != 1 or matching[0].get("filename") != filename:
                raise OmnibusError(
                    f"{name}: figure {label or target!r} needs exactly one registry "
                    f"record for {filename!r}"
                )
            alt = matching[0].get("alt_text")
            if not isinstance(alt, str) or not alt.strip():
                raise OmnibusError(
                    f"{name}: figure {label or target!r} has no alt text"
                )


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
        lines if lines else (wrapper,),
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
            source_text = _remove_empty_reference_placeholders(
                path.read_text(encoding="utf-8")
            )
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
    plan.append(
        (f"{sequence:03d}_volume_references.md", "# References\n\n::: {#refs}\n:::\n")
    )

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
    generated = ["sec:omnibus-front-matter"]
    for paper in papers:
        if paper.present:
            generated.append(f"sec:{paper.prefix}-part")
            if paper.cover_image is not None and paper.cover_image.is_file():
                generated.append(f"fig:{paper.prefix}-cover")
    collision = namespaced.intersection(generated)
    if collision or len(set(generated)) != len(generated):
        raise OmnibusError(
            f"assembler-generated identifiers collide with authored/generated IDs: "
            f"{sorted(collision) or generated}"
        )
    namespaced.update(generated)
    dangling = sorted(
        {ref for _, text in plan for ref in unresolved_references(text, namespaced)}
    )
    if dangling:
        raise OmnibusError(
            f"the assembled volume has unresolved references: {dangling}"
        )

    # Extend the figure map with cover images so the embed check passes.
    cover_map: dict[str, Path] = {}
    cover_registry_records: list[dict[str, object]] = []
    for paper in papers:
        if (
            paper.present
            and paper.cover_image is not None
            and paper.cover_image.is_file()
        ):
            name = cover_embed_name(paper)
            if name in figures or name in cover_map:
                raise OmnibusError(
                    f"plate basename {name!r} is claimed by both a generated cover "
                    "and another volume image"
                )
            cover_map[name] = paper.cover_image
    # Cover copies share the same ownership check as all native plates.
    for paper in papers:
        if (
            paper.present
            and paper.cover_image is not None
            and paper.cover_image.is_file()
        ):
            cover_registry_records.append(
                {
                    "label": f"fig:{paper.prefix}-cover",
                    "filename": cover_embed_name(paper),
                    "alt_text": f"Cover art for {paper.entry.id.replace('_', ' ')}.",
                }
            )
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

    # Complete every deterministic input/config/registry gate before writes.
    registry_text = namespaced_figure_registry(root, papers, cover_registry_records)
    registry_records = json.loads(registry_text)["figures"]
    _check_figure_coverage(
        plan,
        [record for record in registry_records if record["origin"] != "standalone"],
    )
    config_text = volume_config(
        (_manuscript_dir(carrier.root) / "config.yaml").read_text(encoding="utf-8"),
        title=volume_title(carrier),
        subtitle=volume_subtitle(placements),
        version=carrier.config.version,
        date=carrier.config.date,
    )
    reference_rows = [
        {
            "claim_id": label.replace(":", "_"),
            "kind": "citation",
            "value": label,
            "source": f"output/manuscript/{name}: declared formalism label",
            "source_path": f"output/manuscript/{name}",
            "source_tier": "manuscript_formalism_block",
            "freshness": "active",
        }
        for name, text in plan
        for label in collect_anchors(text)
        if label.partition(":")[0]
        in {"def", "prop", "thm", "lem", "cor", "rem", "ax", "clm", "ex"}
    ]
    carrier_keys = _keys_of(carrier)
    prepared = dict(plan)
    prepared.update(
        {
            "omnibus_claim_ledger.json": json.dumps(
                {
                    "schema": "line-set-volume-reference-ledger/1",
                    "boundary": "Label declarations only; no proposition is verified and no sibling metric is computed.",
                    "claims": reference_rows,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            SOURCE_BIB_NAME: merged.render(carrier_keys),
            VOLUME_BIB_NAME: merged.render(
                entry.key for entry in merged.entries if entry.key not in carrier_keys
            ),
            "config.yaml": config_text,
        }
    )
    target = root.joinpath(*INJECTED_MANUSCRIPT_DIR)
    plates = root.joinpath(*VOLUME_FIGURES_DIR)
    for directory in (target, plates):
        _managed_path(root, directory, directory=True)
    _managed_path(root, target / REPORT_NAME)
    previous = _previous_files(target)
    obsolete = set(previous) - prepared.keys()
    for name in (*prepared, REPORT_NAME, *previous):
        if Path(name).name != name or name in ("", ".", ".."):
            raise OmnibusError(
                f"managed manuscript filename is not a basename: {name!r}"
            )
        _managed_path(root, target / name)
    for name in (*all_embeds, "figure_registry.json"):
        if Path(name).name != name or name in ("", ".", ".."):
            raise OmnibusError(f"managed image filename is not a basename: {name!r}")
        _managed_path(root, plates / name)
    to_copy = [
        (name, source)
        for name, source in sorted(all_embeds.items())
        if (plates / name).resolve() != source.resolve()
    ]
    copied = sum(name in figures for name, _ in to_copy) if write else 0

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
        image_sources=tuple(
            (VOLUME_FIGURE_PREFIX + name, source)
            for name, source in sorted(all_embeds.items())
        ),
    )
    prepared[REPORT_NAME] = report.as_json()
    prepared_bytes = {name: text.encode("utf-8") for name, text in prepared.items()}
    registry_bytes = registry_text.encode("utf-8")
    if write:
        # No deterministic preparation occurs after the first mutation.
        target.mkdir(parents=True, exist_ok=True)
        plates.mkdir(parents=True, exist_ok=True)
        _clear_previous(target, obsolete)
        for name, content in prepared_bytes.items():
            (target / name).write_bytes(content)
        for name, source in to_copy:
            shutil.copy2(source, plates / name)
        (plates / "figure_registry.json").write_bytes(registry_bytes)
    return report


def _registry_label(record: dict[str, object]) -> str:
    """Read a label in the same validated domain as source registry records."""
    label = record.get("label")
    if not isinstance(label, str) or not label.strip():
        raise OmnibusError("figure registry contains a missing or invalid label")
    return label


def _source_records(records: object) -> list[dict[str, object]]:
    """The raw build records in one work's registry payload.

    A record the assembly itself wrote carries an ``origin`` stamp
    (``standalone``, ``omnibus-mirror``, or ``cover``) and is regenerated on
    the next assembly, never re-read. Everything else came from the work's
    own figure build and feeds both registry classes below. Reading back only
    what the build produced is what makes the written registry idempotent:
    assembling twice in a row lands on the same bytes.
    """
    if not isinstance(records, list):
        raise OmnibusError("figure registry figures must be a list")
    source: list[dict[str, object]] = []
    for record in records:
        if not isinstance(record, dict):
            raise OmnibusError("figure registry contains a non-record")
        if record.get("origin") in ("omnibus-mirror", "cover"):
            continue
        _registry_label(record)
        source.append(record)
    return source


def _namespaced_record(
    record: dict[str, object], prefix: str, origin: str
) -> dict[str, object]:
    """One registry record restamped under a work's anchor namespace."""
    renamed = dict(record)
    label = _registry_label(record)
    kind, _, name = label.partition(":")
    renamed["label"] = f"{kind}:{prefix}-{name}"
    renamed["origin"] = origin
    return renamed


def namespaced_figure_registry(
    root: Path,
    papers: Sequence[SourcePaper],
    cover_registry_records: Sequence[dict[str, object]] = (),
) -> str:
    """The volume's merged figure registry, written over the carrier's own.

    The file this assembly writes sits where the carrier's figure build wrote
    its registry, so the write is a merge of two record classes, not a
    replacement:

    * **standalone** — the carrier's own build records, labels unchanged,
      because the carrier's source manuscript references those exact labels
      and the validation stage checks that manuscript against this registry.
    * **omnibus-mirror** — every present work's build records renamed the way
      ``namespace_anchors`` renames the volume's manuscript anchors, so the
      rendered volume's labels agree with the registry the render toolchain
      reads. Collisions between generated record classes are refused rather
      than letting a later record silently replace another.

    Cover records the assembly generates are stamped ``cover``. Every record
    written here carries an ``origin`` stamp; on the next assembly only native
    or retained standalone records are read back (see :func:`_source_records`), so
    the merge never compounds. A missing registry for a present work is
    refused rather than silently dropped, because a figure the volume shows
    must stay accessibility-covered.
    """
    carrier = papers[0]
    standalone: list[dict[str, object]] = []
    mirror: list[dict[str, object]] = []
    for paper in papers:
        if not paper.present:
            continue
        registry_path = (
            paper.root
            / VOLUME_FIGURES_DIR[0]
            / VOLUME_FIGURES_DIR[1]
            / "figure_registry.json"
        )
        if not registry_path.is_file():
            if paper.figures:
                raise OmnibusError(
                    f"{paper.entry.id} ships plates but no figure registry at "
                    f"{registry_path}; the volume cannot carry its figures "
                    "accessibility-covered"
                )
            continue
        try:
            payload = json.loads(registry_path.read_text(encoding="utf-8"))
        except ValueError as error:
            raise OmnibusError(f"invalid figure registry at {registry_path}") from error
        records = (
            payload["figures"]
            if isinstance(payload, dict) and "figures" in payload
            else payload
        )
        source = _source_records(records)
        if paper is carrier:
            standalone.extend(dict(record, origin="standalone") for record in source)
        mirror.extend(
            _namespaced_record(record, paper.prefix, "omnibus-mirror")
            for record in source
        )
    covers = [dict(record, origin="cover") for record in cover_registry_records]
    classes = [standalone, mirror, covers]
    for index, records in enumerate(classes):
        labels = {_registry_label(record) for record in records}
        for other in classes[index + 1 :]:
            collision = labels.intersection(_registry_label(record) for record in other)
            if collision:
                raise OmnibusError(
                    f"assembly introduces figure registry label collisions: {sorted(collision)}"
                )
    return (
        json.dumps(
            {
                "schema_version": "1.3-omnibus",
                "note": (
                    "Merged figure registry written by the omnibus assembly: "
                    "the standalone records are the assembling work's own, "
                    "under the labels its source manuscript references, and "
                    "the omnibus-mirror records carry every work's figures "
                    "under the prefix-namespaced labels the volume renders. "
                    "Each record's origin states its class; source registries "
                    "are unchanged."
                ),
                "figures": [*standalone, *mirror, *covers],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )


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

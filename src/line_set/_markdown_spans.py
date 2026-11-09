"""Source-offset Markdown literal boundaries for publication consumers.

This is not a Markdown renderer. It protects exact-run backtick code spans,
backtick/tilde fences, and indented code without treating ordinary list
continuations as code. Consumers parse their own supported syntax only inside
``prose_spans``; offsets always refer to the original, unmodified string.
"""

from __future__ import annotations

import re

_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


def _block_masks(text: str) -> tuple[tuple[bool, bool], ...]:
    """Track fence and indentation state in ordinary and nested list blocks."""
    opened: tuple[str, int, int] | None = None
    list_indents: list[int] = []
    boundary = True
    indented = False
    marks: list[tuple[bool, bool]] = []
    for line in text.splitlines():
        expanded = line.expandtabs(4)
        indent = len(expanded) - len(expanded.lstrip(" "))
        empty = not line.strip()
        if opened is not None and opened[2] and not empty and indent < opened[2]:
            # A list container ended before its unclosed fence.
            opened = None
        if opened is not None:
            match = _FENCE_RE.match(expanded[opened[2] :])
            marks.append((True, False))
            if (
                match is not None
                and match.group(1)[0] == opened[0]
                and len(match.group(1)) >= opened[1]
                and not match.group(2).strip()
            ):
                opened = None
            boundary = True
            indented = False
            continue
        if not empty:
            while list_indents and indent < list_indents[-1]:
                list_indents.pop()
        base = list_indents[-1] if list_indents else 0
        item = re.match(r" *(?:[-+*]|\d+[.)])[ \t]+", expanded)
        if item is not None and indent <= base + 3:
            base = item.end()
            list_indents.append(base)
        else:
            item = None
        match = (
            _FENCE_RE.match(expanded[base:])
            if empty or indent >= base or item is not None
            else None
        )
        if match is not None and not (
            match.group(1)[0] == "`" and "`" in match.group(2)
        ):
            opened = (match.group(1)[0], len(match.group(1)), base)
            marks.append((True, False))
            boundary = True
            indented = False
            continue
        code = (
            item is None
            and (indented or boundary)
            and ((empty and indented) or (not empty and indent >= base + 4))
        )
        marks.append((False, code))
        indented = code
        boundary = (
            empty or re.match(r" {0,3}#{1,6}(?:\s|$)", expanded[base:]) is not None
        )
    return tuple(marks)


def fence_mask(text: str) -> tuple[bool, ...]:
    """Mark fenced lines, closing only with the opening kind and length."""
    return tuple(fenced for fenced, _ in _block_masks(text))


def prose_spans(markdown: str) -> tuple[tuple[int, int], ...]:
    """Return half-open active nonliteral spans in original source offsets.

    Four-space/tab code starts at a block boundary, not in paragraph or list
    continuation indentation. List code needs four additional spaces. Inline
    spans can cross lines within one paragraph, never a literal block or blank
    paragraph boundary. An unmatched backtick run remains active prose.
    """
    lines = markdown.splitlines(keepends=True)
    blocks = _block_masks(markdown)
    literals: list[tuple[int, int]] = []
    barriers: list[tuple[int, int]] = []
    offset = 0
    for line, (fenced, code) in zip(lines, blocks, strict=True):
        end = offset + len(line)
        if fenced or code:
            literals.append((offset, end))
        if fenced or code or not line.strip():
            barriers.append((offset, end))
        offset = end

    start = 0
    for left, right in [*barriers, (len(markdown), len(markdown))]:
        cursor = start
        while cursor < left:
            opening = re.search(r"`+", markdown[cursor:left])
            if opening is None:
                break
            begin = cursor + opening.start()
            end = cursor + opening.end()
            escape_start = begin
            while escape_start and markdown[escape_start - 1] == "\\":
                escape_start -= 1
            if (begin - escape_start) % 2:
                cursor = end
                continue
            closing = end
            while closing < left:
                match = re.search(r"`+", markdown[closing:left])
                if match is None:
                    break
                stop = closing + match.end()
                if len(match.group()) == end - begin:
                    literals.append((begin, stop))
                    end = stop
                    break
                closing = stop
            cursor = end
        start = right

    active: list[tuple[int, int]] = []
    cursor = 0
    for left, right in sorted(literals):
        if cursor < left:
            active.append((cursor, left))
        cursor = max(cursor, right)
    if cursor < len(markdown):
        active.append((cursor, len(markdown)))
    return tuple(active)

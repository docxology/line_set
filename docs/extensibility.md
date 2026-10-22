# Adding a colour

The set is meant to grow. This page is the exact recipe, the list of files an
addition touches, and the list of files it must not touch. The second list is
the interesting one: if adding a colour ever requires editing the reader or the
checks, the design has failed and the fix is the design, not the edit.

## The recipe

Before adding a colour, a person records its distinct question, explicit
must-not-become boundary, package identity, published vocabulary and dated
binding evidence, and reviews any proposed exemption meanings. These are
substantive admission decisions; a namespace reading cannot make them.

**1. Append one `LineEntry` to `LINE_SET` in `src/line_set/registry.py`.**

For an executable hypothetical entry, use the suite's fixture:

```python
from tests.test_extensibility import APPENDED

# The unused teal identity is the same fixture exercised by the suite.
APPENDED
```

Five constraints, each enforced by a check that fails closed rather than by
convention:

| Field | Constraint | Check that catches a violation |
| --- | --- | --- |
| `id` | Unique across the declaration. | `check_distinct_line_ids` |
| `color` | Unique across the declaration. | `check_distinct_colours` |
| `opus_stage` | Either `None`, or an unused member of `OPUS_STAGE_ORDER`. | `check_distinct_opus_stages` |
| `working_position` | Extends the sequence to a contiguous `1..N`. | `check_contiguous_working_positions` |
| `must_not_become` | Non-blank. | `check_must_not_become_declared` |

The `opus_stage` constraint bites immediately in practice. `OPUS_STAGE_ORDER`
has one member per classical stage and the existing lines already use each of
them, so **another colour added today must carry `opus_stage=None`.** That is
the correct outcome rather than an obstacle: the opus supplies four stage names
and the set never claimed the naming resonance would extend to arbitrary
growth. Inventing a ninth stage name is rejected — `opus_stage="viriditas"`
fails `distinct_opus_stages` with `stages that are not opus stages:
['viriditas']` — and reusing an existing one fails the same check with
`duplicate opus stages: ['rubedo']`. A colourless, stageless ninth line is what
the declaration is shaped to accept.

**2. Declare an exemption only if the new line genuinely shares a token.** Add a
`SharedToken` to `SHARED_TOKENS` in the same file, naming *exactly* the lines
that carry it and supplying a non-blank meaning for each. An exemption that
names two lines when three carry the token does not exempt anything; neither
does one that omits a meaning. This is `exemption_for` failing closed, and it is
deliberate — see [claim_boundaries.md](claim_boundaries.md) for what an
exemption does and does not establish.

**3. Update the prose that names the set.** This is the part no check can do for
you; see *Files this touches* below.

## Executable isolated example

This example uses the same hypothetical teal entry as the suite. It constructs
real temporary packages with distinct names, independent of installed siblings.
The package source under `src/` is unchanged.

The fixture uses a fixed hypothetical identifier and colour currently distinct
from the declaration; only its working position is derived. A real extension
must choose unused values. Conceptual admission is separate human work in the
[dossier](admission/dossier.md).

```python
from tempfile import TemporaryDirectory
from pathlib import Path
from line_set import LINE_SET, SHARED_TOKENS, all_invariants, read_set, registry_digest
from tests.test_extensibility import APPENDED
from tests.support import import_sandbox, load_line_package, resolved, write_line_package

extended = LINE_SET + (APPENDED,)
assert APPENDED.id not in {entry.id for entry in LINE_SET}
assert all(result.passed for result in all_invariants(extended, SHARED_TOKENS))
with TemporaryDirectory() as directory, import_sandbox():
    root = Path(directory)
    answers = {}
    for index, entry in enumerate(LINE_SET):
        write_line_package(root, entry.package_name, (f"TOKEN_{index}",))
        answers[entry.package_name] = resolved(
            entry.package_name, load_line_package(root, entry.package_name))
    from tests.support import canned_resolver
    reading = read_set(extended, SHARED_TOKENS,
                       resolver=canned_resolver(answers), as_of="2026-10-21")
print("membership:", tuple(entry.id for entry in LINE_SET))
print("lines:", len(LINE_SET), "->", len(extended))
print("status:", reading.status.value)
print("counts:", reading.counts())
print("digest before:", registry_digest(LINE_SET, SHARED_TOKENS))
print("digest after:", registry_digest(extended, SHARED_TOKENS))
```

The executable example is bound by
`tests/test_review_regressions.py::test_documented_extension_executes_without_siblings`.
Its date is explicit, its resolver is an injected callable over temporary package
sources, and its coverage is every declared identity plus the absent hypothetical
entry. The review base was `3be000b`; the release packet records the implementing
commit and the separate pinned sibling reading. This fixture is namespace evidence,
not a measurement of any sibling.

The old 2026-07-29 transcript described an earlier membership. It is superseded by
the executable fixture above; its historical bytes remain in Git history at
`3be000b:docs/extensibility.md`. Green is already declared and cannot be used as
an unused identity.

## Files this touches

- **`src/line_set/registry.py`** — the append itself, and any new `SharedToken`.
  This is the only source file an addition edits.
- **`docs/manuscript/reading_record.json`** — regenerated, never hand-edited. Rerun
  `scripts/record_reading.py`. The record carries the declaration digest, so an
  append invalidates it immediately and `tests/test_manuscript_bindings.py`
  fails on any machine until it is refreshed — including one with no sibling
  installed.
- **The manuscript** — `docs/manuscript/01b_the_set.md` describes the lines and
  `docs/manuscript/03_extensibility.md` describes this recipe; both name the set's
  membership in prose. `docs/manuscript/02b_scholarship.md` and
  `docs/manuscript/05_limits.md` should be re-read for sentences that assume the
  current membership.
- **A figure caption, if and only if that caption names a count.** The builders
  derive their content from the declaration, so a figure re-renders correctly
  with an appended entry without being edited. A caption that says *four* does not.
  Grep the caption text before assuming it is clean.
- **Project-root and `docs/` prose, wherever it names a count or lists the
  lines.** Same rule as captions: the prose is not derived, so the prose is what
  drifts. Today that means `README.md` (which names the lines and counts the
  stages, figures, and commands), `AGENTS.md`, `STANDALONE.md`, `CHANGELOG.md`,
  and this file. Grep for the line names and for spelled-out numbers before
  concluding the pass is done; a count in prose has no test behind it.

## Files this does not touch

- **`src/line_set/reader.py`.** `read_set` takes `lines` and `shared` as
  arguments and names no line. Nothing in the resolve, bind, collide, declare,
  or status stage is per-line logic.
- **`src/line_set/invariants.py`.** Every check takes the declaration as an
  argument. Adding a colour adds no check and changes no check.
- **`src/line_set/binding.py`.** Resolution is by `package_name` from the entry.
  A new line is resolved by the same code path as an old one.
- **`src/line_set/models.py` and `src/line_set/serialization.py`.** The types
  and the canonical form are per-entry, not per-set.
- **The figure builders** in `src/line_set/figures/`. They read the declaration
  and lay out however many entries they find. A builder that would need editing
  to accept an appended entry is a bug in the builder.

If a change to the set requires touching anything in the second list, stop and
ask whether the thing being added is a line at all, or a second concern wearing
a line's shape.

## Removing a colour

The same edit in reverse, with one extra step: `working_position` must be
renumbered so the remaining entries are still contiguous from `1`, and any
`SharedToken` naming the removed line must be removed or rewritten. An exemption
left naming a line that no longer exists stops matching — `exemption_for`
requires the declared line set to equal the set actually carrying the token — so
a stale exemption surfaces as `SET_COLLIDING` rather than as silence. That is
the fail-closed direction, and it is the reason not to relax the equality rule.

## What the extensibility claim is

That adding a colour is a `registry.py` edit is a claim about *this* package's
coupling, and it is bound by a test. It is not a claim that adding a line to the
set is cheap: the new line needs its own project, its own question, its own
registry, its own tests, and its own manuscript. This package makes the
bookkeeping cheap. It does not make the instrument cheap, and it has no opinion
on whether the instrument should exist.

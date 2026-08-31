# Adding a colour

The set is meant to grow. This page is the exact recipe, the list of files an
addition touches, and the list of files it must not touch. The second list is
the interesting one: if adding a colour ever requires editing the reader or the
checks, the design has failed and the fix is the design, not the edit.

## The recipe

**1. Append one `LineEntry` to `LINE_SET` in `src/line_set/registry.py`.**

```python
LineEntry(
    id="green_line",                       # unique across the set
    color="green",                         # unique across the set
    question="What is still growing?",     # the one question the line answers
    job="...",                             # what it does
    must_not_become="...",                 # non-blank; the drift it refuses
    opus_stage=None,                       # see the constraint below
    working_position=len(LINE_SET) + 1,    # must extend 1..N contiguously
    package_name="green_line",             # what the reader imports
    registry_noun="growth records",        # prose label, for figures and text
    verdict_noun="growth status",          # prose label, for figures and text
)
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
them, so **a fifth colour added today must carry `opus_stage=None`.** That is
the correct outcome rather than an obstacle: the opus supplies four stage names
and the set never claimed the naming resonance would extend to arbitrary
growth. Inventing a fifth stage name is rejected — `opus_stage="viriditas"`
fails `distinct_opus_stages` with `stages that are not opus stages:
['viriditas']` — and reusing an existing one fails the same check with
`duplicate opus stages: ['rubedo']`. A colourless, stageless fifth line is what
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

## Executed example

The following runs against the declaration as it stands today. It appends a
fifth entry at runtime, runs the whole offline battery over the extended
declaration, takes a live reading, and compares the declaration digest before
and after. Nothing in `src/line_set/` is modified by it.

```python
import sys
sys.path.insert(0, "src")
from line_set import (
    LINE_SET, SHARED_TOKENS, LineEntry,
    all_invariants, read_set, registry_digest, sibling_path_resolver,
)

green = LineEntry(
    id="green_line",
    color="green",
    question="What is still growing?",
    job="Placeholder used only to demonstrate extension",
    must_not_become="A real instrument without its own project",
    opus_stage=None,
    working_position=len(LINE_SET) + 1,
    package_name="green_line",
    registry_noun="growth records",
    verdict_noun="growth status",
)
extended = LINE_SET + (green,)

for result in all_invariants(extended, SHARED_TOKENS):
    print(f"{'PASS' if result.passed else 'FAIL'}  {result.name}")

reading = read_set(extended, SHARED_TOKENS,
                   resolver=sibling_path_resolver(), as_of="2026-07-29")
print("status:", reading.status.value)
print("counts:", reading.counts())
print("digest before:", registry_digest(LINE_SET, SHARED_TOKENS)[:16])
print("digest after: ", registry_digest(extended, SHARED_TOKENS)[:16])
```

Measured output, run from the project root on 2026-07-29 with the sibling
checkouts present:

```text
PASS  distinct_line_ids
PASS  distinct_colours
PASS  distinct_opus_stages
PASS  contiguous_working_positions
PASS  orders_diverge
PASS  must_not_become_declared
PASS  shared_tokens_disambiguated
status: set_partial
counts: {'resolved': 4, 'not_installed': 1, 'import_failed': 0, 'no_vocabulary': 0}
digest before: 40db5e0e3e038707
digest after:  aef45330a26f53ce
```

Three things in that output are worth naming.

The whole offline battery passes on the extended declaration with no code
change, because every check takes `lines` as an argument and none of them names
an individual line.

The reading is `SET_PARTIAL`, not an error, because `green_line` is a name with
no package behind it. Declaring a line before writing it is a normal state and
the reader reports it as one: the entry resolves to `not_installed`, its
version, registry size, and digest stay `None`, and the four real lines are
still read and still checked for collisions. A declaration is allowed to run
ahead of an installation.

The declaration digest changes, which is the intended behaviour and the whole
use of the digest: a set whose declaration grew is a different declaration. It
is not evidence that the growth was legitimate — see the tamper-evidence
paragraph in [claim_boundaries.md](claim_boundaries.md).

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
  with a fifth entry without being edited. A caption that says *four* does not.
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
  to accept a fifth entry is a bug in the builder.

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

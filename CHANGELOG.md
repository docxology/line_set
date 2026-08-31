# Changelog

## 2026-08-01 — standalone-clone discovery fix (publication readiness)

`discover_paper()` in `src/line_set/omnibus.py` found every work's manuscript
at `base/<id>/manuscript`, which is the monorepo layout. On a detached
single-project clone the assembling work's own manuscript sits at the
repository root, so `discover_papers()` reported this project's own entry
absent — and every corpus gate in `tests/test_omnibus.py` failed instead of
skipping, breaking the README/AGENTS promise that the suite passes with the
siblings absent. Discovery now falls back to the repository root for the
wrapper's own entry (a no-op wherever `base/<id>` is this repository), and
`test_a_detached_repo_finds_its_own_manuscript_at_the_repository_root` locks the
standalone layout. Measured: 409 passed, 1 skipped in the monorepo; 393 passed,
17 skipped on a detached clone; `ruff check` + `ruff format --check` and
`mypy src` clean. This removes a blocker to publishing each work as its own
standalone repository.

## Unreleased — 2026-07-29 — the envelope convention recorded, and correspondence answered

"The Space Between the Lines" (an external review, 2026-07-29) reviewed
the collected set and proposed that each line export a common report envelope
and that a separate shared witness register co-register them without ranking,
averaging, merging, or overriding any line. The set-level piece of the answer
lands here as documentation, because this is the work that declares what the
set is — and only as documentation, because a set reading is not a line report
and the wrapper has no envelope to export.

- **`docs/envelope.md` records the set-wide report envelope convention.** The
  schema string `line.report-envelope/1.0`, the ten fields as the exporting
  works publish them, the rule that each work declares its own literal in its
  own `envelope.py` — alignment by published convention, never by import — and
  the rule that `native_status` is one instrument's word in that instrument's
  vocabulary and must not be compared, ranked, averaged, or merged across
  lines. The roster is dated and verified by import, not file existence — an
  earlier check on 2026-07-29 found a file at golden_line's path that did not
  yet import: as of the final check that day, all four lines export the
  envelope, each with its own declared literal and the same ten field names;
  golden_line's module landed latest, mid-window.
- **The shared schema string needs no exemption and gets none.** The collision
  scan compares member names of enums exported at each package root, a
  module-level string constant is invisible to it, and the string is not a
  Python identifier so it can never be a member name. It is deliberately not
  a `SHARED_TOKENS` entry: that table exempts tokens the matcher can actually
  see, and a declaration the matcher could never match would be a declaration
  about nothing. The scan, the matcher, and the declaration are all unchanged
  — `check_registry.py` and `check_set.py` pass byte-for-byte on the same
  digest, `40db5e0e3e03…`.
- **Co-registration stays outside the set, in writing.** The register the
  review proposes is a separate work; a companion named witness_register is
  being scaffolded beside the set this window and is referenced as a
  companion, not a member — not in `LINE_SET`, not a colour, contents not
  asserted. The reader will not collect, store, or compute anything across
  envelopes.
- **`docs/correspondence.md` opens the decision record.** Same form as the
  sibling repositories': what the review said about this work — already the
  set's modular witness, already admitting that a missing colour leaves no
  trace — then adopted, deferred, and declined, each with its reason. The
  manuscript statement of the convention is the deferral: the manuscript
  contract confines sibling facts to the dated reading block, and which
  repositories export an envelope module is a sibling fact.
- **The dated reading record went stale under this window's sibling work, and
  the suite says so.** Measured 2026-07-29: white_line moved 0.5.0 → 0.6.0
  and its exported vocabulary grew from 19 to 24 distinct names. A live
  reading is still `SET_LEGIBLE` — the one exempted collision, no unexempted
  token, the wrapper's 8 tokens disjoint from all four vocabularies — but
  `docs/manuscript/reading_record.json` no longer matches it, so 3 of the suite's
  402 tests fail and `record_reading.py --check` exits 1, which is exactly
  what both exist to do. Re-recording mid-window would go stale again before
  the siblings stop moving and drags the paper date and a re-render with it;
  mid-window the run stood at 398 passed, 3 failed (all three the stale
  record), 1 skipped.
- **The settled recording pass was then taken, once, at the window's close.**
  With the four siblings settled (white_line at 0.7.0, 24 distinct exported
  names), the paper date in `docs/manuscript/config.yaml` moved 2026-07-27 →
  2026-07-29, `scripts/record_reading.py` re-recorded against that date
  (`recorded_on=2026-07-29`; first taken as `b4e836174eac809d…`, then
  re-taken the same day as `b99eb55c29579a62…` (and once more as `e783001a0baa1c16…` when black_line released 0.4.0) after golden_line's version
  bump 0.3.0 → 0.4.0 moved the live reading — the census was unchanged and
  two binding tests caught the staleness within the hour), and every
  prose site that quotes the date or the reading digest moved with it: the
  abstract's dated sentence, the reading block in `04_examples.md` (whose
  quoted `reading_digest` changed because the digest covers `read_as_of`),
  the `as_of` literals in `03_extensibility.md` and `docs/extensibility.md`.
  The census the record now holds is 19 enum classes, 89 declared members,
  81 line-and-name pairs, 80 distinct names — the same numbers the prose
  already carried. The compiled volume was re-assembled (`build_omnibus.py
  --write`, front matter now reads "read as of 2026-07-29") and re-rendered;
  the rendered text carries the new date and digest with zero undefined
  references. Measured at close: 401 passed, 1 skipped, coverage 99.81%
  statement and branch; `check_registry.py`, `check_set.py`, and
  `record_reading.py --check` all pass; set digest unchanged at
  `40db5e0e3e03…` because the declaration itself never moved.

## Unreleased — 2026-07-28 — the instrument stated formally, and a volume that numbers per work

`docs/manuscript/02a_formalism.md` states the records, the exemption matcher, the
staged reading, the precedence rule, and the self-application as definitions and
propositions, each written from the module it describes and each bound by a
named test that re-derives it. Every block is written in the render toolchain's
fenced-Div form, so the numbers come from document order and no number is typed
into the source; `tests/test_formalism.py` requires a label on every block, a
declared target for every `[@label]` reference, a label prefix that matches its
kind, and no hand-written `Definition N` outside a code block. Each of those
four rules was measured rejecting a violation planted in the real manuscript
before it was trusted.

- **The compiled volume restarts formalism numbering at each reproduced work.**
  Without it, five papers share one sequence and every paper's own references
  resolve to numbers that mean nothing outside the volume — a work whose first
  definition is Definition 1 in its own PDF becomes Definition 5 here. The
  assembler writes `formalism_reset_level: 1` into the generated `config.yaml`
  *and* emits it as a pandoc metadata block at the head of the front matter,
  because the toolchain builds its pandoc command from a fixed set of config
  keys and this is not one of them; a value only in the config would be a
  setting that looks applied and is inert. Both copies come from one constant
  and a test requires them to agree, a second test pins the heading level that
  makes level 1 the boundary between works, and a third runs the real filter and
  checks a negative control in the same run.
- **Formalism labels are namespaced per work in the volume.** A block declares
  its label inside a Div attribute list, where no brace precedes it, so the
  anchor mover did not see it: two works reproducing `#def:x` put one label on
  two blocks, which the filter resolves last-wins. `anchor_pattern()` now
  chooses the pattern per line and the move round-trips to the source bytes.
  Measured over the five-work corpus, the volume now numbers each work
  independently and the filter reports no duplicate label and no undeclared
  reference.
- **`src/line_set/probes.py` demonstrates the fail-closed matcher instead of
  asserting it.** It weakens a declared exemption six ways — truncated token,
  case-folded token, a query naming one line more, a declaration naming one line
  more, a missing per-line meaning, two declarations of one token — and reports
  what `exemption_for()` returned for each, with the positive control first.
  The manuscript's fail-closed proposition is bound to that probe set, so a
  matcher that started accepting a looser input fails the prose as well as the
  code.
- **Two new plates, both computed at build time.** `exemption_gate` draws the
  probe set with the matcher's own return values in the outcome column.
  `self_application` draws this package's exported enum member names against
  each line's and prints the self-check's own verdict, taken from
  `self_disjointness_from_reading()` rather than recomputed — the check was
  split so the plate and the check cannot disagree. Both refuse to be vacuous:
  no declared exemption, no wrapper vocabulary, or no line to compare against
  each draws a stated absence. All seven plates are byte-identical across two
  builds and land at 6.23pt against the 6.0pt floor.
- **Scholarship deepened where it was already load-bearing.** Parnas,
  Clements, and Weiss on the module guide, and Parnas on designing for
  extension and contraction, are the two Parnas papers behind the claims this
  project actually makes; Star's companion 1989 paper supplies the typology
  that makes the exemption table a standardised form rather than a defect
  awaiting a rename; and the XML namespaces recommendation is where the `SET_`
  prefix comes from and where the transfer stops, since there is no authority
  behind it. Each is cited once, situated, and given a sentence saying what it
  does not carry here.
- **The bibliography merge no longer refuses an accent.** Two works declared one
  key with the author written `Sch{\"o}n` and `Schön`. Those are one author, and
  `normalise_field()` now strips LaTeX accent commands and Unicode combining
  marks so a spelling cannot look like a conflict. The loosening is narrow and
  stated in the docstring; a key naming two genuinely different works still
  stops the merge.
- **The manuscript was rendered end to end for the first time.** 26 pages, zero
  undefined references, zero `??`, and the seven formalism blocks numbered
  Definition 1-4 and Proposition 1-3 in document order with every `[@label]`
  reference resolved.

## Unreleased — 2026-07-28 — standing alone as its own repository

This project now has its own repository, `docxology/line_set`, as well as a
place in the private tree it is developed in. A fresh-clone audit of that
repository found four ways it was still leaning on the tree around it. All four
are closed here, and each is bound by a test that fails when the defect is
reintroduced.

- **The omnibus corpus gates no longer fail with the siblings absent.** Nine
  gates in `tests/test_omnibus.py` reached the declared works through a helper
  that hard-asserted every one of them was on disk, so a clone with no siblings
  reported nine failures — directly contradicting `README.md` and
  `STANDALONE.md`, which both say the suite passes without them. The helper now
  skips with the missing works and their reasons named, and the skip is
  positively controlled: the absence is re-derived from disk first, so a work
  that is in fact readable fails rather than skipping. The production module was
  not at fault and is unchanged in that respect — `assemble()` already reported
  `papers_missing` honestly and exited zero.
- **A sibling that is present but unbuilt now degrades instead of raising.**
  `gather_figures` refused a work embedding a plate that was not on disk, so a
  freshly cloned sibling — manuscript present, `output/` never built, which is
  the normal state of a clone — stopped the whole volume. Absence was handled
  and partial presence was not. `discover_papers` now withdraws such a work the
  way it withdraws an absent one, naming the unbuilt plates and their count in
  the front matter. The assembling work is deliberately still held to the strict
  rule: its own plates are its own responsibility.
- **Every relative link now resolves inside the repository.** Five links walked
  above the repository root to `docs/line-set.md`, three of them inside the
  rendered manuscript. That note is unpublished and lives in a private tree, so
  it is now cited by name, with the four instruments' own repositories as the
  durable references. The acknowledgement was kept; only its address changed.
  `tests/test_documentation_links.py` resolves every inline link in every
  markdown file and fails on one that escapes the root or names nothing.
- **The render path no longer assumes a monorepo layout.** `docs/development.md`
  said `cd ../../../template`. It now states plainly that rendering is an
  external dependency on the separate `docxology/template` engine, that the
  engine may be cloned anywhere, and that it is pointed at an external projects
  root rather than found by walking up — and it says what this project can do
  without it, which is everything except typeset itself.
- **Where the siblings are is now addressable rather than positional.**
  `sibling_base()` still defaults to this project's parent directory, which is
  where they sit in the development tree, but `LINE_SET_SIBLINGS` names the
  directory explicitly for a copy whose set is elsewhere. It is honoured by the
  resolver, the live check, the reading record, and the omnibus assembler. An
  empty value reads as unset rather than as the working directory.
- Self-description corrected in `AGENTS.md`, `STANDALONE.md`, `TODO.md`, and
  `docs/development.md`: this is a repository, not a subdirectory of one.

## 0.1.0 — 2026-07-27 (initial)

First release of the fifth work in the line set: a declaration, a reader, and a
non-overlap check. It adds no substantive instrument. The four questions —
refusal, method, aspiration, absence — stay where they were, and this work
answers none of them.

### The declaration

- `src/line_set/registry.py` holds `LINE_SET`, one `LineEntry` per line in
  working order, each carrying the question it answers, the job it does, the
  thing it must not become, its working position, its package name, and the
  opus stage its colour echoes. Content follows the sidecar line-set map in
  substance; the manuscript is new writing rather than a copy of it.
- `SHARED_TOKENS` is the exemption table: the tokens two lines are allowed to
  share, each with a distinct meaning recorded per line and a rationale.
- `WRAPPER_LINE` is this package's own entry, kept deliberately out of
  `LINE_SET`. It is colourless and carries no opus stage, because it names no
  refusal, method, aspiration, or absence and is not a stage of anything. It
  exists so this package can be put through this package's own check.

### The reader

- `read_set(lines, shared, *, resolver=None, as_of=None)` runs five stages —
  resolve, bind, collide, declare, status — and records each into the returned
  `SetReading.derivation`, so a reading can be re-read rather than trusted.
- Four statuses: `SET_LEGIBLE`, `SET_PARTIAL`, `SET_COLLIDING`,
  `SET_UNDECLARED`, applied in the precedence pinned by `STATUS_PRECEDENCE`.
  `SET_LEGIBLE` is reachable only when every declared line was read, so a
  partial install cannot launder itself into a clean reading.
- Absence is an ordinary outcome. A line that will not import yields
  `NOT_INSTALLED` or `IMPORT_FAILED` and leaves its version, registry size, and
  digest `None`; nothing is invented for a package that could not be read.
- `exemption_for` fails closed: exact token equality, set equality between the
  declared lines and the lines actually carrying the token, a non-blank meaning
  for every named line and none for a line it does not name, and exactly one
  matching declaration. Every failure leaves the collision unexempted.
- `resolver` is the injection point. It is a plain callable, which is how absent,
  failing, vocabulary-less, and undeclared packages are exercised with no
  mocking framework anywhere in the tree.

### Reading the siblings

- `binding.py` is the only module that imports a sibling package. It reads a
  version string, finds the primary registry tuple and takes its length, asks the
  package for its own digest, and collects the member names of the enums exported
  at the package root. It never calls a sibling's evaluator and never computes a
  digest on a sibling's behalf.
- Importing this package touches `sys.path` not at all. `default_resolver` adds
  nothing; `sibling_path_resolver()` is the explicit opt-in and records exactly
  what it inserted in `added_paths`.
- Registry-size discovery is a stated generic convention rather than a per-package
  special case, and a tie yields `None` instead of a guess.

### Checks

- `all_invariants()` is the offline battery over the declaration: distinct ids,
  distinct colours, distinct and real opus stages, contiguous working positions,
  working order diverging from opus order, a stated must-not-become for every
  entry, and every exemption being one the live matcher would honour. It imports
  no sibling and returns identical results with none installed.
- `check_self_disjointness()` is the live self-application: this package's own
  status tokens are checked against the line vocabularies using the production
  reader over `LINE_SET + (WRAPPER_LINE,)`. It is kept out of `all_invariants()`
  because it cannot be answered without importing the siblings, and it reports
  `passed=False` rather than passing vacuously when there is nothing to compare
  against. An exempted collision involving the wrapper counts against it exactly
  like an unexempted one.
- Every check fails on an empty scan set, with a detail saying so.

### Serialization

- `canonical_registry` and `canonical_reading` sort every collection before
  writing, so no `dict` or `set` iteration order can reach a digest. The
  exemption table is serialized with the lines: a set whose shared tokens changed
  is a different set.
- `registry_digest` and `reading_digest` are review and drift-detection handles.
  They are not tamper evidence and carry no attestation.

### Documentation

- `README.md`, `AGENTS.md`, `STANDALONE.md`, `TODO.md`, and the `docs/` set.
  `docs/claim_boundaries.md` is the non-claim register and the document a hostile
  reader should find first; `docs/extensibility.md` carries the executed example
  showing that appending a colour is a `registry.py` edit, with the explicit list
  of files an addition does not touch.

### The dated reading is recorded, not only quoted

The manuscript reports numbers measured against the installed siblings. They
cannot be re-derived where those packages are absent, which is most places the
manuscript will be read, so on those machines the paper's one empirical claim
would have travelled entirely unchecked.

- `scripts/record_reading.py` writes `docs/manuscript/reading_record.json` — the
  reading, its digest, and a per-line vocabulary census — and refuses to record
  anything but a `SET_LEGIBLE` reading of every declared line. `--check`
  compares against the record without rewriting it.
- `binding.vocabulary_census()` counts a package's exported enums and the
  members they declare, keeping the pre-deduplication total apart from the
  distinct names the collision scan actually compares. Conflating the two
  inflates the arithmetic, and the abstract had done so.
- `tests/test_manuscript_bindings.py` binds the prose to the record on every
  machine and binds the record to a live reading wherever one can be taken. The
  record carries the declaration digest, so a declaration change invalidates it
  with no sibling installed and no network.
- `binding.exported_enums()` is now the one place the exported set is decided,
  so the token reader and the census cannot come to describe different classes.
  It excludes the standard library's own `enum` classes: a package writing
  `from enum import Enum` at its root had been counted as declaring one.

### Fixes found by integration

- **The reader no longer believes a resolver that contradicts itself.** A
  resolution reporting `RESOLVED` while supplying no module was accepted as
  resolved, which put a line with no vocabulary into the read set — where it
  counted as read, contributed nothing to the collision scan, and could not make
  the reading partial. A set of them would have reported `SET_LEGIBLE` on the
  strength of having compared nothing. It is now downgraded to `IMPORT_FAILED`
  with the resolver's own explanation kept.
- **`check_registry.py` parses its command line.** It previously ignored
  arguments entirely and exited zero on anything, so a mistyped flag produced a
  run that looked like it had checked something it never looked at.
- **The rasterizer override resolves the path it found.** A bare relative name
  naming a real executable in the working directory was located and then handed
  to `subprocess` unresolved, so the build refused a rasterizer it had just
  found.
- **`canvas.arrow_defs` removed.** It was exported and drawn by no plate.

### Fixes found by adversarial verification

- **The figure legibility floor was measuring the wrong unit.**
  `canvas.MIN_TEXT_UNITS` stopped a label being authored below 13 canvas units,
  and nothing converted that into the size the label reaches on the page. Every
  plate was landing at **4.27pt**, against the 6.0pt floor the sibling line
  projects hold their figures to. `TODO.md` recorded the gap but gave a reason
  that was wrong — that the embed width "is a property of the render that has
  not happened" — when the width is declared on the embed and the geometry in
  `docs/manuscript/config.yaml`, so the number is derivable from the checkout.
  `src/line_set/figures/legibility.py` now derives it, `MIN_TEXT_UNITS` is 18,
  every plate's labels were raised to clear it, the five embeds take the full
  text width, and the measured minimum is **6.2279pt**.
- **The matrix and the installation surface needed real layout work to hold the
  new floor**, not just larger numbers. The vocabulary matrix sized its label
  gutter from a magic constant and a bigger label ran into its own column's
  cells; the gutter and the column count are now derived from the longest token
  in the reading at the worst-case advance any token character can have, which
  keeps the plate byte-reproducible because it still opens no font. On the
  installation surface the read-code gloss ran under the version value and
  `REGISTRY ENTRIES` collided with `TOKENS`; the gloss wrap is now sized to the
  room before the stat blocks and the label is the manuscript's own wording,
  `REGISTRY SIZE`.
- **`canvas.plural` was wrong for two of the nouns the plates count.** It
  appended a bare `s`, so a shipped caption read "the exit ladder of 4 statuss"
  and another "4 entrys of the declaration carries an opus stage" — the second
  also disagreeing with its own verb. The alt text carried a hand-written
  `row(s)` escape hatch beside a `plural()` call in the same sentence. The
  helper now inflects the regular English classes, the verbs agree with their
  live counts, and the escape hatch is gone. The old test only ever passed it
  `line`, which is why the whole irregular class went unchecked; it now
  exercises the sibilant, consonant-y, and compound cases, and a second test
  scans the generated captions and alt text themselves.

### Tests

- `tests/test_figure_legibility.py` derives each plate's rendered point size
  from the page geometry, the embed widths, and the built SVGs, and gates on
  `MIN_LEGIBLE_PT`. Its load-bearing test is the planted one: an SVG whose
  smallest label is under the floor must be reported illegible, and the
  height-cap case — where a tall plate shrinks and takes every label with it —
  is exercised separately, because nothing in an SVG shows it. A project with
  no embed, an embed whose plate is missing, a plate with no text, and a config
  with no geometry are each refused rather than skipped or defaulted.
- `tests/test_figures.py` covers the figure machinery: plate rendering across
  every reading status, byte-identical rebuilds across two dates, the refusal to
  draw a matrix with fewer than two vocabularies, shape-and-label encoding of
  exempted against undeclared collisions, and the fail-closed rasterizer paths.
  The rasterizer seam is exercised with a real executable script rather than a
  substitute for one.
- `tests/test_scripts.py` runs every command in `scripts/` as a subprocess and
  requires a non-zero exit on an unrecognised argument and on the failure each
  gate exists to catch.
- `src/line_set/` is at 100% statement and branch coverage, measured with the
  siblings importable and again with none of them importable.

# Deferred work

This file tracks only open work. Completed windows are logged at the bottom.
[`docs/claim_boundaries.md`](docs/claim_boundaries.md) defines what this project
may claim regardless of anything listed here.

## Open — inside the current instrument boundary

- **The render has now happened once, and once is not a standing gate.** On
  2026-07-28 the manuscript rendered through the external template engine to a
  26-page PDF with zero undefined references and no `??`, and the seven
  formalism blocks numbered correctly from document order. What is still open is
  that nothing re-runs that render: the suite checks the sources, and a
  regression that only shows up in LaTeX would not be caught until someone
  renders again by hand.
- **The volume's numbering reset is verified through pandoc, and now once
  through a rendered volume.** `formalism_reset_level` was measured restarting
  the counters at each work over the real five-work corpus, using the render
  toolchain's own filter, and the negative control fired. On 2026-07-29 the
  compiled volume was rendered to a PDF and its text read back: zero undefined
  references, and "Definition 1" recurs across works while within-work
  sequences run past 13. That is one dated reading, not a standing gate; the
  behavioural test still skips wherever `LINE_SET_FORMALISM_FILTER` names no
  filter, which is every machine that does not also hold the template
  checkout.
- **No plate has been read by a person in greyscale print.** The tests establish
  that no encoding is colour-only — every collision cell carries a shape and a
  word as well as an ink — and that every text run clears both the canvas floor
  and the rendered-point floor. What is still unestablished is that a person has
  looked at a greyscale print and found the distinctions readable. Recheck after
  the first render.

  This entry used to say that readability at the embedded width could not be
  checked "because that width is a property of the render that has not
  happened". That reason was wrong, and it was load-bearing: the width is
  declared on the embed and the page geometry is declared in
  `manuscript/config.yaml`, so the rendered point size is derivable from the
  checkout with nothing built but the figures. While the claim stood, every
  plate was landing at 4.27pt against the 6.0pt floor the sibling line projects
  hold their figures to — the canvas floor was passing and measuring a unit the
  page never sees. `src/line_set/figures/legibility.py` now derives the real
  number and `tests/test_figure_legibility.py` gates on it.
- **The measured numbers are checked against a record, not re-measured
  everywhere.** `manuscript/reading_record.json` lets a machine without the
  sibling packages catch prose that drifted from the reading; only a machine that
  can read the siblings catches a record that drifted from them. Both halves run
  in the suite, and the second reports as skipped where it cannot run. That is
  the honest arrangement, not a complete one: a stale record on a machine that
  never had the siblings is undetectable except through the declaration digest.
- **`--as-of` is an operator input.** `record_reading.py` takes the review date
  rather than deriving it, so a record can be written under a date that is not
  the day it was taken. The suite checks the record's date against
  `manuscript/config.yaml`, which catches disagreement with the paper but not a
  date that was wrong in both places.

## Open — intentionally outside the current instrument boundary

These are not represented anywhere as hidden features:

- **No tamper evidence.** `registry_digest` detects disagreement with a digest
  someone already holds. Signing, an external anchor, or an attested envelope
  would each need their own key-management and provenance contract, and none is
  claimed today.
- **No independent verification of any sibling.** Every version, registry size,
  and digest reported is read from that sibling, using the sibling's own
  function. Verifying a sibling would require running its evaluator against
  independently authored inputs — a different project with a different claim.
- **Conceptual overlap stays human work.** The reader compares spellings of
  exported enum member names. Detecting that two lines are about the same thing
  in different words is not something this package attempts, and a heuristic
  that guessed at it would produce exactly the kind of confident meta-judgement
  the project refuses.
- **Undeclared-line discovery stays convention-based.** A package is found by a
  naming convention and by what is already imported. An empty
  `undeclared_lines` is a report of what that convention turned up, never proof
  that nothing else exists. Making it exhaustive would need a packaging
  contract the set does not have.
- **The declaration is source-configured in Python.** Moving `LINE_SET` and
  `SHARED_TOKENS` to an editable data file would need its own validation and
  provenance contract — the same ladder the sibling instruments record.
- **Public release.** This project has its own repository, `docxology/line_set`,
  and that repository is private. Making it public needs a citation/release
  workflow, a release packet with the exact command outputs attached, and a
  re-render at the release tree.

## Standing discipline

- After any change to the declaration, the reader, or the checks: update tests,
  docs, manuscript, and figures in the same patch, and rebuild `output/`.
- Never modify a sibling line project from this tree. Read them freely; write
  nothing. A reading that implies a sibling should change is a finding for a
  person, not an edit.
- Any change to `exemption_for` needs a planted-bad test proving the looser
  input is still refused.
- Keep the citation of the line-set map and of the sibling repositories current
  when sibling projects change, and never link out of this repository's root;
  never copy their prose, registries, figure designs, or evaluator logic.

## Log

- 2026-08-01 — floor re-derivation and type/lint pass. The canvas legibility
  floor `MIN_TEXT_UNITS` (18) and its justification were calibrated to a
  0.42in-margin text block (553.6pt), but `manuscript/config.yaml` declares
  0.33in margins, a 566.6pt block, so `tests/test_figure_legibility.py`'s
  tight-floor check failed: at the real width one unit below the floor (17)
  would still clear 6pt, meaning 18 was no longer the minimal floor. The gate
  caught real drift. Re-derived the floor to 17 (`17 * 566.597 / 1600 =
  6.02pt`, and 16 clears nothing) and corrected the stale arithmetic in
  `src/line_set/figures/canvas.py`; no plate output changed because the
  smallest shipped label is 18 units. mypy went from 27 errors to 0 with
  behavior-preserving changes: `palette._require_exact` is now generic over
  `Mapping`/`Iterable`, `pipeline._rung_*` are typed to `SetStatus`,
  shadowed loop variables were renamed in `plates/reading.py` (int/str `row`)
  and `omnibus.py` (str/`Path` `target`), `two_orders` narrows `opus_stage`,
  and the reader's resolver injection is now a documented `PackageResolver`
  protocol re-exported from the package root. `ruff format` was applied to the
  source/tests the pinned tool disagreed with, and a dead
  `shared = SHARED_TOKENS` assignment plus stale comments were removed from
  `tests/test_formalism.py`. Measured: 408 passed, 1 skipped (the
  formalism-filter behavioural test, which skips where the template's filter
  is not named), 99.30% statement and branch; `ruff check` and
  `ruff format --check` pass; `mypy src` clean; the figure build is
  byte-identical across two runs; `check_registry.py`, `check_set.py`, and
  `record_reading.py --check` all pass; declaration digest unchanged
  (`40db5e0e3e03…`) because the declaration never moved.

- 2026-07-29 — the settled recording pass. The stale-record entry that stood
  here is closed: with the siblings settled at the window's end (white_line
  0.7.0, 24 distinct exported names), the paper date moved to 2026-07-29,
  `record_reading.py` re-recorded (`recorded_on=2026-07-29`, reading digest
  `b4e836174eac809d…`, re-taken the same day as `b99eb55c29579a62…` (and once more as `e783001a0baa1c16…` when black_line released 0.4.0) after
  golden_line's 0.3.0 → 0.4.0 bump moved the live reading), and the dated
  prose, the reading block's quoted
  digest, and both extensibility examples' `as_of` literals moved with it.
  The compiled volume was re-assembled and re-rendered, and the rendered text
  was read back: it carries the new date and digest, has zero undefined
  references, and "Definition 1" recurs across works while within-work
  sequences run past 13 — consistent with the per-work numbering restart the
  filter test verifies at the source level. Measured: 401 passed, 1 skipped,
  99.81% statement and branch; `check_registry.py`, `check_set.py`, and
  `record_reading.py --check` all pass; set digest unchanged
  (`40db5e0e3e03…`) because the declaration never moved.

- 2026-07-27 — adversarial verification. Every number in `README.md`,
  `AGENTS.md`, `TODO.md`, `CHANGELOG.md`, `docs/`, and `manuscript/` was
  re-derived from the code rather than read back from a report: the census
  (16 enum classes, 80 declared members, 76 line-and-name pairs, 75 distinct
  names, one shared name) was reproduced by an independent counter that imports
  the four package roots without going through this package at all, and the
  seven offline checks, the eighth live check, the two executed extension
  examples with their digests, the per-line repeat counts, and the
  "four and four and two and two" occurrence claim all reproduced exactly. The
  figure and citation sets have no orphan in either direction. Three defects
  were found and fixed, all in the figures: the legibility floor was measuring
  canvas units rather than page points and every plate was below the rendered
  floor the rest of the set holds; two plates needed layout work rather than
  larger numbers to hold the corrected floor; and `plural()` was putting
  malformed words into shipped caption and alt text while its test exercised
  only the one noun the bug did not affect. The suite is 293 tests at 100%
  statement and branch coverage, measured with the siblings importable and
  again with none of them importable.

- 2026-07-27 — integration and claim audit. All four commands run from a clean
  checkout and each was measured refusing a deliberately broken input, so the
  note about a contracted-but-unbuilt surface is closed. `tests/test_figures.py`
  and `tests/test_manuscript_bindings.py` were written, `tests/test_scripts.py`
  added, and `src/line_set/` reached 100% statement and branch coverage measured
  twice — with the siblings importable and with none of them importable, the
  same figure both times. The figure build is byte-identical across two runs and
  across two review dates. Four defects found and fixed: a reader that believed
  a resolver reporting `RESOLVED` with no module, a gate that exited zero on any
  argument, a rasterizer path that was located and then not resolved, and an
  exported drawing primitive no plate used. The claim audit re-derived every
  number in `README.md`, `docs/`, and `manuscript/`; the abstract's status
  precedence was stated backwards and the token arithmetic conflated members
  declared with distinct names carried, both corrected and both now bound by a
  test. `manuscript/reading_record.json` and `scripts/record_reading.py` were
  added so the measured numbers are checkable where the sibling packages are not
  installed.

- 2026-07-27 — documentation and project-root prose. Added `README.md`,
  `AGENTS.md`, `STANDALONE.md`, `CHANGELOG.md`, this file, the `docs/` set
  (`README`, `AGENTS`, `architecture`, `invariants`, `extensibility`,
  `claim_boundaries`, `development`), and the folder contracts under `tests/`
  and `scripts/`. Numbers in the documentation were derived by running the
  package rather than transcribed: the offline battery passes on the real
  declaration and each check was measured rejecting its planted-bad input and
  failing on an empty scan set; `check_self_disjointness()` was measured both
  passing against the four installed siblings and failing — not passing
  vacuously — with none importable; and the executed extension example in
  `docs/extensibility.md` was run as printed, including the `SET_PARTIAL`
  reading for a declared-but-uninstalled fifth line and the declaration digest
  changing across the append.

- 2026-07-27 — package spine. `pyproject.toml`, `.gitignore`, and
  `src/line_set/` (`__init__`, `version`, `models`, `registry`, `binding`,
  `reader`, `invariants`, `serialization`) with the package contract in
  `src/line_set/AGENTS.md` and `src/line_set/README.md`.

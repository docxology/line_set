# Line Set project guidance

Line Set is its own repository — `docxology/line_set`, currently private — and
it is developed inside a larger private projects tree that also holds the four
sibling works. It is not a subdirectory of anything it depends on: a clone of
this repository alone installs, tests, checks its declaration, builds its
figures, and explains itself. Every rule below is written for that clone as much
as for the working tree.

What it is: a declaration of the line set, a staged reader for it, and a
non-overlap check. Its source of truth is
`src/line_set/`, its executable contract is tested under `tests/`, and its
manuscript and generated figures must stay synchronized with the declaration.

It is a wrapper and a reader. It is not a fifth instrument, a meta-evaluator, a
merge of the four lines, or a ranking of them. Every rule below exists to keep it
from becoming one.

## Working contract

- **Keep the declaration in `src/line_set/registry.py` and the logic around it.**
  `scripts/` are thin CLIs that import the package and delegate. No business
  logic in `scripts/`, no declaration content anywhere else.
- **`binding.py` is the only module that imports a sibling package.** If a second
  module ever needs to reach one, route it through `binding` rather than
  importing directly. Keep that seam narrow: read a version, count a registry,
  call the package's own digest function, collect exported enum member names.
  Never call a sibling's evaluator, never pass it data, never form an opinion
  about what it concluded, and never compute a digest on its behalf.
- **Never modify a sibling line project.** Red, Black, Golden, and White Line are
  read-only from here — no edits, no fixes, no "small" corrections. If a reading
  implies a sibling should change, that is a finding to report to a person, not
  an edit to make from this tree. Do not copy their prose, registries, figure
  designs, or evaluator logic either.
- **The siblings are optional and coverage may not depend on them.** The package
  installs, tests, checks its declaration, builds what it can, and renders its
  manuscript with zero siblings present. A suite that only passes inside this
  working tree cannot travel with a standalone export.
- **Absence is an outcome, never an exception and never a fabricated value.** A
  line that will not import yields `NOT_INSTALLED` or `IMPORT_FAILED` with
  `version`, `registry_size`, and `registry_digest` left `None`. Nothing in this
  package invents a value for something it could not read.
- **`exemption_for` fails closed and must stay that way.** Exact token equality,
  set equality between declared lines and the lines actually carrying the token,
  a non-blank meaning for every named line and none for a line it does not name,
  exactly one matching declaration. Any change here needs a planted-bad test
  proving the looser input — substring, case-folded, subset, superset, duplicate
  declaration — is still refused. A generous match converts the non-overlap
  guarantee into a rubber stamp, silently.
- **Every gate fails on an empty scan set.** A check that passes because it had
  nothing to look at is a defect. This applies to checks added later as much as
  to the ones already there.
- **`all_invariants()` stays offline; `check_self_disjointness()` stays live.**
  Do not move the self-check into the offline battery to make a sibling-free run
  go green. It would delete the only check that had anything to say.
- **Adding a colour is a `registry.py` edit.** If a change to the set requires
  touching `reader.py`, `invariants.py`, `binding.py`, or a figure builder, the
  design has failed and the fix is the design. See `docs/extensibility.md`.
- **Nothing sorted by accident.** Token collection, collision partitioning,
  candidate discovery, and every canonical form sort before they emit, so no
  `dict` or `set` iteration order can reach a reading or a digest.
- **Pure standard library.** No third-party runtime dependency, ever.
  `from __future__ import annotations`, frozen dataclasses, module docstrings
  that bound what the code does and does not establish.
- **No mocking framework.** `unittest.mock`, `MagicMock`, and `mocker.patch` are
  prohibited across `src/`, `tests/`, and `scripts/`. The resolver injection
  point exists precisely so absent, failing, vocabulary-less, and undeclared
  packages are exercised with plain callables and real temporary directories.
- **A registry, status, reader, or check change updates tests, docs, manuscript,
  figures, and `output/figures/` together.** A generated-but-unembedded figure is
  inert; a manuscript number with no test binding is unverified.

## Claim discipline

This is the rule agents break most often here, because the package *looks* like
an auditor.

- A reading is about spellings of enum member names exported at a package root.
  It is never validation, certification, audit, approval, or a safety property.
- `SET_LEGIBLE` is not a statement that the lines are correct, complete, well
  chosen, or worth having, and disjoint vocabularies are not disjoint concepts.
- A digest detects disagreement with a digest someone already holds. It is not
  tamper evidence; anyone who edits the declaration recomputes it for free.
- Every version, registry size, and digest reported is what a sibling says about
  itself. Reporting it faithfully is not verifying it.
- `undeclared_lines` being empty is not proof that no undeclared line exists;
  discovery is convention-based.
- Underclaim. First person, narrow, non-universalizing, no compliance or
  marketing register. `docs/claim_boundaries.md` is the register of record, and
  adding a capability means adding its limits there in the same patch.

## Deriving, not restating

Never hardcode a number, digest, version, count, or status that code can produce.
Derive it and say where it came from, or point at the command instead of
restating its output. Measured transcripts in the documentation carry the date
and the conditions they were run under; re-run them rather than editing a stale
number in place.

## Commands

The local validation surface, what each command needs, and the render path live
in [`docs/development.md`](docs/development.md). Everything except rendering runs
from this repository alone. Rendering is a stated external dependency: the PDF
and HTML come from the separate `docxology/template` engine, cloned wherever you
like and pointed at an external projects root, with the qualified project name
`working/line_set`. There is no assumed path from here to it. A rendered PDF is
evidence that rendering succeeded; it is not independent validation of anything
the manuscript says.

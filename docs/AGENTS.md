# Documentation folder contract

This folder owns the project-facing explanation of the declaration, the reader,
and their limits. It does not own the declaration itself
([`../src/line_set/registry.py`](../src/line_set/registry.py)), the reading
semantics ([`../src/line_set/reader.py`](../src/line_set/reader.py)), the
figures, or the manuscript. The project-level [`../AGENTS.md`](../AGENTS.md)
remains authoritative; the rules below add documentation-specific constraints.

## Ownership

- `claim_boundaries.md` is the non-claim register and the first document a
  hostile reader should find. Its boundary — that a reading is about declared
  vocabulary and never about correctness, completeness, coverage, tamper
  evidence, independent verification, or rank — is preserved, never softened.
  Adding a capability to the package means adding its limits here in the same
  patch.
- `architecture.md` owns the module map, the stage sequence, and digest
  semantics. It explains the source; it does not restate the source's logic in
  a second form that could drift.
- `invariants.md` owns the check table and the proof-of-detection discipline.
  A new check is added to that table in the same patch that adds the check.
- `extensibility.md` owns the recipe and, critically, the two lists of files an
  addition does and does not touch. If a change makes the second list wrong,
  fix the design, not the list.
- `development.md` owns the command surface and the render order.
- `envelope.md` owns the record of the set-wide report envelope convention.
  It documents a contract the sibling instruments publish; this package
  implements none of it, and the page must keep saying so. Its roster of
  exporting works is dated and is re-checked against the sibling
  repositories, never extended on trust.
- `correspondence.md` owns the record of external design reviews: what was
  adopted, deferred, and declined, each with its reason. It is a decision
  record, not an endorsement chain.
- `publication.md` owns the citation metadata, the DOI discipline, and the
  reserve-first workflow.
- `releases/` owns the per-version release packets — gate results, artifact
  hashes, and tag names — one subdirectory per release.

## Rules

- **Derive numbers or point at the command.** Do not type a count, digest,
  version, coverage figure, or status into prose when a command produces it. The
  measured transcripts in `extensibility.md` and `invariants.md` are labelled
  with the date and conditions under which they were run; keep that labelling
  and re-run rather than editing a stale number in place.
- **Never claim more than the code establishes.** A reading is about spellings
  of exported enum member names. It is not a verdict on the packages read, and
  no document here may describe it as validation, certification, audit,
  approval, or a safety property.
- **Underclaim in the register the set uses.** First person, narrow, no
  compliance or marketing voice, no universalizing. Say what was measured and
  under what conditions.
- **Keep module paths, command names, and check names aligned with the source.**
  A renamed function is a documentation change in the same patch.
- **Relative links only for documents inside this repository.** A relative link
  that walks above the repository root resolves to nothing for anyone holding
  only this repository, so it is a defect even where it happens to resolve in a
  working tree; cite an out-of-tree document by name, or by the URL of the
  repository that publishes it. The line-set map and the sibling instruments are
  orientation references, not dependencies; do not copy sibling prose,
  registries, figure designs, or evaluator logic into this folder.
- **Do not document a surface that does not exist yet.** Where this folder
  describes a contract that is not yet built, say so in
  [`../TODO.md`](../TODO.md) rather than letting the description read as a
  report of something on disk.

## Verification

Documentation claims are checked against the source they describe:

```bash
uv run python scripts/check_registry.py
uv run python scripts/check_set.py
uv run pytest tests/ --cov=src --cov-branch --cov-report=term-missing
```

Read [README.md](README.md) for the document index,
[`../src/line_set/AGENTS.md`](../src/line_set/AGENTS.md) before documenting a
package surface, and [`../AGENTS.md`](../AGENTS.md) for the repository
invariants.

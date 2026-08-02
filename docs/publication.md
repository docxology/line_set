# Publication and citation

## How to cite

No DOI has been minted for this work yet. Until one exists, cite the
repository:

> Friedman, D. A. (2026). *The Line Set: Holding Instruments Apart* (version
> 0.1.0) \[Software and manuscript\].
> <https://github.com/docxology/line_set>

BibTeX:

```bibtex
@software{friedman_line_set_2026,
  author  = {Friedman, Daniel Ari},
  title   = {The Line Set: Holding Instruments Apart},
  version = {0.1.0},
  year    = {2026},
  doi     = {10.5281/zenodo.21754244}
}
```

`CITATION.cff` carries the same metadata in machine-readable form, and
`.zenodo.json` carries the deposit metadata. All three are generated from
`manuscript/config.yaml`; `tests/test_publication_metadata.py` fails if they
disagree.

## The DOI is deliberately absent

There is no DOI field anywhere in this repository, and that is enforced rather
than merely intended. `tests/test_publication_metadata.py` refuses any
DOI-shaped string in the citation metadata unless that exact DOI is listed as
verified inside the test itself. A placeholder DOI that renders like a real one
is worse than no DOI: it survives copy-and-paste into someone else's
bibliography and points nowhere.

## Reserving a DOI (reserve-first, the only supported order)

1. Create the Zenodo deposition **without publishing it**, and reserve its DOI.
2. Record the reserved DOI in this repository: add it under `identifiers:` in
   `CITATION.cff`, add it to `related_identifiers` in `.zenodo.json` if
   relevant, add `publication.doi` to `manuscript/config.yaml`, and add the
   exact string to the verified list in `tests/test_publication_metadata.py`.
   The gate turns green only when a person has asserted the DOI is real.
3. Re-render the manuscript so the printed artifact carries its own DOI. A PDF
   deposited without its DOI on the cover cannot be cited from the paper alone.
4. Upload the re-rendered artifacts and publish the deposition.

Doing this in the other order — publish, then get the DOI, then edit — produces
a deposited artifact that does not contain its own identifier, and a second
deposit to fix it produces a second DOI.

## The other works

This work is one of six. They reference each other by name and repository URL
only: no work imports another, and the shared report-envelope schema string is
aligned by published convention rather than by dependency.

| Work | Role | Repository | DOI |
| --- | --- | --- | --- |
| `red_line` | line — what I refuse (personal security boundary) | <https://github.com/docxology/red_line> | not yet minted |
| `black_line` | line — how I try to do strong work (declaration coverage) | <https://github.com/docxology/black_line> | not yet minted |
| `golden_line` | line — what is worth reaching toward (directional readings) | <https://github.com/docxology/golden_line> | not yet minted |
| `white_line` | line — what is absent, withheld, or unknowable (absence ledger) | <https://github.com/docxology/white_line> | not yet minted |
| `witness_register` | companion beside the set — co-registration without aggregation | <https://github.com/docxology/witness_register> | not yet minted |

When sibling DOIs are minted, add them to this table, to `CITATION.cff`
`references`, and to `.zenodo.json` `related_identifiers` — and to the verified
list in the gate, in the same change.

## Before the repository goes public

- [ ] Every gate in `AGENTS.md` green on a clean checkout.
- [ ] `LICENSE` present and accurate.
- [ ] No absolute local paths, secrets, or private-project names in any tracked
      file (`tests/test_publication_metadata.py` checks the first of these).
- [ ] Git history contains nothing that should not be public — the published
      history is a fresh initial-release commit, not a monorepo extract.
- [ ] The rendered PDF regenerated at the release tree.

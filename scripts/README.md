# Scripts

`scripts/` holds the command-line entry points. These files parse nothing and
decide nothing: they import the installed `line_set` package and delegate to it.

```bash
uv run python scripts/check_registry.py   # offline structural battery over the declaration
uv run python scripts/check_set.py        # live reading of the installed lines
uv run python scripts/build_figures.py    # deterministic SVG/PNG pairs into output/figures/
uv run python scripts/record_reading.py   # write docs/manuscript/reading_record.json
uv run python scripts/build_omnibus.py    # compile the declared works under output/manuscript/
uv run python scripts/gen_formalism_ledger.py   # regenerate data/formalism_claim_ledger.json
```

`check_registry.py` needs no sibling line package and exits non-zero if any
offline check fails. `check_set.py` takes a live reading, so with no sibling
importable it reports `SET_PARTIAL` and an unestablished self-disjointness and
exits non-zero — the contract was not checked, and an unchecked contract is not
a held one. `build_figures.py` needs `rsvg-convert` on `PATH`, not the siblings,
and fails closed with install guidance if the rasterizer is absent.
`record_reading.py` needs every declared line readable and refuses to write a
record of a reading it could not take; `--check` compares the record on disk
against a live reading without rewriting it.

Every one of them refuses an argument it does not understand rather than
ignoring it, and `tests/test_scripts.py` runs each as a subprocess and requires
a non-zero exit on the failure it exists to catch.

What each command establishes, and what it does not, is in
[`../docs/development.md`](../docs/development.md) and
[`../docs/claim_boundaries.md`](../docs/claim_boundaries.md). The folder contract
is [AGENTS.md](AGENTS.md).

# Test folder contract

`tests/` exercises the public API, registry, invariants, reader, serialization,
deterministic figures, omnibus assembly, manuscript bindings, and cross-cutting
contracts.

## Test modules

- `test_public_api.py` — imports, version markers, public surface
- `test_models.py` — LineEntry, SharedToken, SetReading, ReadCode
- `test_registry.py` — LINE_SET, SHARED_TOKENS, WRAPPER_LINE, lookups
- `test_invariants.py` — structural checks and planted-bad cases
- `test_reader.py` — read_set staging, resolution, observation
- `test_serialization.py` — canonical JSON and registry digest
- `test_figures.py` — figure determinism and registry metadata
- `test_figure_legibility.py` — printed text size constraints
- `test_omnibus.py` — omnibus assembly, gate enforcement, round-trip invertibility
- `test_manuscript_bindings.py` — prose, reading record, figure, and bibliography bindings
- `test_formalism.py` — formalism block parsing, prefixes, citation split
- `test_binding.py` — sibling_path_resolver and package resolution
- `test_extensibility.py` — adding a fifth line entry and re-deriving results
- `test_self_disjointness.py` — the wrapper line's vocabulary is disjoint from the set
- `test_documentation_links.py` — all documentation cross-references resolve
- `test_publication_metadata.py` — publication metadata across config and package
- `test_scripts.py` — every read-only script passes on good input
- `test_no_mocks.py` — lexical ban on mocks, stand-in names, path hardcodes

## Invariants

- No mocks. Use real records, temporary output roots, and constructed declarations.
- Keep project coverage at or above the `90` floor in `pyproject.toml`.
- Import figure builders from `line_set.figures`, not from `scripts/`.

## Validation

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90 --cov-report=term-missing
```

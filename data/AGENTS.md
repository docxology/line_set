
## Formalism claim ledger (2026-08-29)

`formalism_claim_ledger.json` declares the manuscript's formalism-block labels
(`def:`/`prop:`) and the vocabulary-census numbers stated in the prose, so the
render engine's evidence registry resolves those `[@...]` cross-references
instead of reporting them as unsupported bibliography citations. Every row is
derived from the manuscript or `docs/manuscript/reading_record.json`;
`tests/test_formalism_claim_ledger.py` checks formalism reference closure,
evidence paths, and unique claim identities. Canonical replay and an independent
live-package census are checked in `tests/test_manuscript_bindings.py`.
The numeric binding covers every scalar census field, each per-line field and
the within-line and cross-line repeat totals. Generate these rows from the
record; never add an unrelated number merely to satisfy the renderer.

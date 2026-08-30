
## Formalism claim ledger (2026-08-29)

`formalism_claim_ledger.json` declares the manuscript's formalism-block labels
(`def:`/`prop:`) and the vocabulary-census numbers stated in the prose, so the
render engine's evidence registry resolves those `[@...]` cross-references
instead of reporting them as unsupported bibliography citations. Every row is
derived from the manuscript or `manuscript/reading_record.json`;
`tests/test_formalism_claim_ledger.py` re-derives the whole set and fails if a
block is added, renamed, or removed without this file following.

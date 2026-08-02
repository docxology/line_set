# Line Set figures

Seven deterministic plates, hand-written as SVG and rasterized with
`rsvg-convert`. Importing this package reads nothing: plates are assembled by
`figure_plates()` when a build asks for them, so nothing here imports a sibling
line package or touches `sys.path` at import time.

| Plate | Drawn from |
| --- | --- |
| `set_compass` | the declaration — one card per line, plus the wrapper below a rule |
| `two_orders` | the declaration and `OPUS_STAGE_ORDER`, with the live divergence check |
| `vocabulary_matrix` | a live reading — every token against the lines that export it |
| `set_reading_pipeline` | `READER_STAGES` and `STATUS_PRECEDENCE` |
| `installation_surface` | a live reading — what this machine could actually read |
| `exemption_gate` | `line_set.probes` — the production matcher over a declared exemption and six weakenings |
| `self_application` | the reading that includes the wrapper, with the verdict from `invariants.self_disjointness_from_reading()` |

Build them with `uv run python scripts/build_figures.py`. Artifacts land in
`output/figures/`: seven SVGs, seven PNGs, `set_registry.json` (the canonical
declaration and its digest), and `figure_registry.json` (the manifest the
manuscript embeds read).

`rsvg-convert` must be on `PATH`, or `LINE_SET_RSVG_CONVERT` must name the
executable to use. Without one the build raises with install guidance and
writes nothing — it never skips a figure and reports success.

The three plates drawn from the declaration take `lines` as an argument and
compute every position from it, so appending a colour to `registry.py` changes
them with no edit here. Nothing in a plate is a score, and no plate says a
line works — only what the declaration says a line is for, and what the reader
could read.

See [AGENTS.md](AGENTS.md) for the working contract.

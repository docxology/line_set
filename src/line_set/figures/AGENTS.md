# Line Set figures contract

`src/line_set/figures/` owns the drawing, the artifact protocol, and the
display maps. It owns no semantics: it never decides anything the reader did
not already decide.

## Modules

- `__init__.py` re-exports `build_figures()`, `figure_summary()`, `figure_plates()`, `FigurePlate`, the rasterizer constants, and the legibility surface (`EmbedOccurrence`, `measure_project()`, `measure_surface()`, `illegible()`, `FigureLegibility`, `MIN_LEGIBLE_PT`).
- `build.py` defines `build_figures()`, `figure_summary()`, `RSVG_CONVERT`, `RSVG_ENV_VAR`, `BUILD_PROVENANCE`, and `PROJECT_ROOT`.
- `canvas.py` defines the SVG primitives — `text()`, `rect()`, `line()`, `path()`, `glyph()`, `hatch_defs()`, `open_canvas()`, `header()`, `close_canvas()`, `wrap()`, `plural()` — plus `WIDTH`, `MARGIN`, `CONTENT_RIGHT`, and `MIN_TEXT_UNITS`.
- `legibility.py` derives printed-point sizes from explicit placements, page margins, a height cap and source SVGs. `parse_embed_text()` and `parse_embeds()` retain every active occurrence, including unlabeled images (empty label), with original source/line diagnostics; shared `prose_spans()` excludes literal examples. `measure_project()` measures standalone source only. `measure_surface()` optionally measures a compiled plan without writing or rendering it.
- `palette.py` defines the inks, `line_fill()`/`line_ink()`/`shape_for()`/`dash_for()`, the enumeration-keyed display maps, and `verify_coverage()`.
- `plates/__init__.py` defines `FigurePlate` and `figure_plates(lines, shared, reading, wrapper, self_reading)`. Two readings are passed: `reading` covers the declared lines, `self_reading` covers them plus the wrapper and is the one the self-check itself runs.
- `plates/declaration.py` draws `set_compass` and `two_orders`.
- `plates/pipeline.py` draws `set_reading_pipeline`.
- `plates/reading.py` draws `vocabulary_matrix` and `installation_surface`.
- `plates/exemption.py` draws `exemption_gate` from `line_set.probes.exemption_probes()`.
- `plates/application.py` draws `self_application` from `self_reading` and `line_set.invariants.self_disjointness_from_reading()`.

## Invariants

`canvas.wrap_to_width()` uses conservative per-character width estimates and
breaks long unspaced words. `exact_lines()` and `text_block()` retain full
dynamic identities at a fixed font size, with exact full text on the SVG group.
Cards and cover rows grow from their wrapped text; token columns have a usable
width floor. No identity is shortened or font reduced to fit. Native glyph,
vertical layout and physical-page checks remain separate required proof.

- **Prerequisites and owned paths fail closed before writes.** Display-map and
  rasterizer lookup failures precede the first SVG. The builder preflights every
  owned destination and refuses symlinked `output`, `output/figures`, SVG, PNG,
  and manifest paths, including dangling links. Unrelated files are not removed.
  This is a local preflight, not race resistance or transactional rendering:
  the caller must exclude concurrent output mutation, and a runtime rasterizer
  failure can leave a partial set.
- **No clock reading reaches a plate.** A reading's `read_as_of` is
  deliberately not drawn. It is a property of the reading, available from
  `read_set()`, and drawing it would make two builds of an unchanged
  declaration differ. Do not add a build date, a generation timestamp, or a
  `reading_digest` (which is dated) to a plate or to a manifest.
- **Everything sorts before it draws.** Entries sort by `working_position`,
  tokens sort, collisions sort. No `dict` or `set` iteration order reaches an
  artifact. Coordinates are formatted to one decimal place so a trigonometric
  polygon cannot carry a floating-point difference into the file.
- **No distinction is carried by color alone.** Every line, read code, and
  status has a marker shape *and* a written label. The sparse vocabulary matrix
  writes each carrier's working position beside the token and keys those
  positions to named lines; fill alone never identifies a carrier. The exempted collision and
  the undeclared one differ by shape, by fill, and by the words on the row.
  Check any new encoding against a grayscale conversion before shipping it.
- **The written label has to survive the page, not just the canvas.** The
  grayscale mitigation is worthless if the word repeating the color is too
  small to read once the plate has been scaled into the text block, and a floor
  in canvas units cannot tell you whether it is. `MIN_TEXT_UNITS` stops a label
  being authored too small; `legibility.py` derives where it lands in points and
  is the binding gate. Lowering `MIN_TEXT_UNITS`, widening a canvas, or
  narrowing an embed's `width=` attribute all move that number, so re-derive it
  in the same patch rather than assuming the floor still holds.
- **A plate with nothing to show says so.** `vocabulary_matrix` over fewer
  than two legible vocabularies draws the honest panel, not an empty grid. An
  empty grid reads like a clean result and would be a vacuous claim. Do not
  replace that panel with a grid to make a build look better. `self_application`
  and `exemption_gate` follow the same rule: no wrapper vocabulary, no line to
  compare against, or no declared exemption each draws a stated absence.
- **A verdict on a plate is the check's own verdict.** `self_application`
  calls `self_disjointness_from_reading()` and prints what it returned; the
  `exemption_gate` outcome column is what `exemption_for()` returned. Neither
  plate re-implements the decision it displays, because a second copy of a
  rule is free to disagree with the first while both stay green.
- **No number is typed in.** Counts, token totals, versions, registry sizes,
  and digests all come from the declaration or the reading, including the ones
  in captions. A caption that states a number the plate does not derive will
  drift away from the plate.
- **A new color needs no edit here.** `line_fill()`/`line_ink()` fall back to
  a deterministic accent and `shape_for()` cycles, so an unknown color draws.
  The maps that must stay exhaustive are keyed by `ReadCode`, `SetStatus`, and
  `READER_STAGES`, and `verify_coverage()` fails the build when one falls
  behind.

## Claim boundaries

A plate draws a declaration or a reading. `set_legible` on the installation
surface means every declared vocabulary was readable and no unexempted
published-name collision was found. Exemptions stay visible. These facts do not
establish sibling correctness or conceptual separation. A row
marked not read is a fact about one machine's installation. A digest prefix
detects disagreement with a digest someone already holds and is not tamper
evidence.

### Physical measurement API and limits

`EmbedOccurrence(source, line, image_path, label, width_fraction)` identifies one
placement; repeated paths and labels remain distinct. `parse_embeds(directory)`
returns a tuple in sorted-source and original-offset order, not a basename map.
`parse_embed_text(markdown, source=...)` accepts planned text before it is written.
`FigureLegibility` includes `source`, `source_line`, and `surface` diagnostics.

`measure_project(root)` selects `docs/manuscript` (or `manuscript`) and derives
each SVG counterpart beside the exact source-relative image destination,
normally `output/figures`. Distinct paths with one basename stay distinct.
It never selects an injected compiled manuscript and must not be cited as
compiled-volume qualification.

For optional compiled measurement call
`measure_surface(occurrences, config_text=generated_config,
svg_sources={exact_image_path: original_svg_path}, surface="compiled")`.
Supply every actual planned placement, including covers, and the compiled
carrier's generated config. Missing exact SVG mappings or files refuse the
measurement; PNG-only assembly remains independently supported. The caller owns
SVG-to-image correspondence; this function does not authenticate it.

The geometry model is US Letter in TeX points, four explicit inch margins in a
double-quoted `geometry:` scalar, percentage embed widths (absent means full
text width), and a numeric `figure_height_fraction` (absent means the documented
template default). Image parsing uses inline Markdown image destinations and
optional brace attributes, not arbitrary Markdown/HTML or renderer layout.
This is an authored-font-size derivation under those assumptions, not a PDF,
HTML, EPUB, font-substitution, accessibility or human-readability verdict.
Tall exact-text extensions may fail the physical floor despite fitting the SVG;
do not hide that failure with smaller fonts, truncation or omitted placements.


## Validation

- `uv run python scripts/build_figures.py`
- Build twice and diff the SVGs; they must be byte-identical.
- `uv run pytest tests/test_figure_legibility.py` — derives the rendered point
  size of every plate's smallest label and fails below `MIN_LEGIBLE_PT`.
- `uv run pytest tests/test_figure_layout.py` — measures native glyph widths
  and refuses horizontal overflow or text overlap near the same baseline,
  with a planted bad SVG control.
- Convert a plate to grayscale and confirm every distinction survives.
- Build once with a resolver that finds no sibling; `installation_surface`
  must hatch every card and `vocabulary_matrix` must draw its honest panel.

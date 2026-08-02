# Line Set figures contract

`src/line_set/figures/` owns the drawing, the artifact protocol, and the
display maps. It owns no semantics: it never decides anything the reader did
not already decide.

## Modules

- `__init__.py` re-exports `build_figures()`, `figure_summary()`, `figure_plates()`, `FigurePlate`, the rasterizer constants, and the legibility surface (`measure_project()`, `illegible()`, `FigureLegibility`, `MIN_LEGIBLE_PT`).
- `build.py` defines `build_figures()`, `figure_summary()`, `RSVG_CONVERT`, `RSVG_ENV_VAR`, `BUILD_PROVENANCE`, and `PROJECT_ROOT`.
- `canvas.py` defines the SVG primitives — `text()`, `rect()`, `line()`, `path()`, `glyph()`, `hatch_defs()`, `open_canvas()`, `header()`, `close_canvas()`, `wrap()`, `plural()` — plus `WIDTH`, `MARGIN`, `CONTENT_RIGHT`, and `MIN_TEXT_UNITS`.
- `legibility.py` derives what a canvas unit becomes in printed points — `measure_project()`, `measure_plate()`, `illegible()`, `parse_page_geometry()`, `parse_embeds()`, `parse_height_fraction()`, `MIN_LEGIBLE_PT` — from `manuscript/config.yaml`, the embed widths, and the built SVGs. It draws nothing.
- `palette.py` defines the inks, `line_fill()`/`line_ink()`/`shape_for()`/`dash_for()`, the enumeration-keyed display maps, and `verify_coverage()`.
- `plates/__init__.py` defines `FigurePlate` and `figure_plates(lines, shared, reading, wrapper, self_reading)`. Two readings are passed: `reading` covers the declared lines, `self_reading` covers them plus the wrapper and is the one the self-check itself runs.
- `plates/declaration.py` draws `set_compass` and `two_orders`.
- `plates/pipeline.py` draws `set_reading_pipeline`.
- `plates/reading.py` draws `vocabulary_matrix` and `installation_surface`.
- `plates/exemption.py` draws `exemption_gate` from `line_set.probes.exemption_probes()`.
- `plates/application.py` draws `self_application` from `self_reading` and `line_set.invariants.self_disjointness_from_reading()`.

## Invariants

- **The build fails closed before it writes.** `verify_coverage()` and the
  rasterizer lookup both run before the first SVG is written. A missing
  `rsvg-convert` raises with install guidance; it is never skipped, never
  warned about, and never leaves a partial artifact set behind.
- **No clock reading reaches a plate.** A reading's `read_as_of` is
  deliberately not drawn. It is a property of the reading, available from
  `read_set()`, and drawing it would make two builds of an unchanged
  declaration differ. Do not add a build date, a generation timestamp, or a
  `reading_digest` (which is dated) to a plate or to a manifest.
- **Everything sorts before it draws.** Entries sort by `working_position`,
  tokens sort, collisions sort. No `dict` or `set` iteration order reaches an
  artifact. Coordinates are formatted to one decimal place so a trigonometric
  polygon cannot carry a floating-point difference into the file.
- **No distinction is carried by colour alone.** Every line, read code, and
  status has a marker shape *and* a written label. A carried grid cell also
  gets a dark pip: the white line's fill is nearly the paper colour, and fill
  alone makes its column unreadable in greyscale. The exempted collision and
  the undeclared one differ by shape, by fill, and by the words on the row.
  Check any new encoding against a greyscale conversion before shipping it.
- **The written label has to survive the page, not just the canvas.** The
  greyscale mitigation is worthless if the word repeating the colour is too
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
- **A new colour needs no edit here.** `line_fill()`/`line_ink()` fall back to
  a deterministic accent and `shape_for()` cycles, so an unknown colour draws.
  The maps that must stay exhaustive are keyed by `ReadCode`, `SetStatus`, and
  `READER_STAGES`, and `verify_coverage()` fails the build when one falls
  behind.

## Claim boundaries

A plate draws a declaration or a reading. `set_legible` on the installation
surface means the declared vocabularies of the lines that were read did not
overlap — not that the lines are correct, complete, or worth having. A row
marked not read is a fact about one machine's installation. A digest prefix
detects disagreement with a digest someone already holds and is not tamper
evidence.

## Validation

- `uv run python scripts/build_figures.py`
- Build twice and diff the SVGs; they must be byte-identical.
- `uv run pytest tests/test_figure_legibility.py` — derives the rendered point
  size of every plate's smallest label and fails below `MIN_LEGIBLE_PT`.
- Convert a plate to greyscale and confirm every distinction survives.
- Build once with a resolver that finds no sibling; `installation_surface`
  must hatch every row and `vocabulary_matrix` must draw its honest panel.

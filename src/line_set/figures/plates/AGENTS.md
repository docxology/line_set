# Line Set plates contract

Each plate is a pure function from a declaration, a reading, or a reader tuple
to an SVG string. A plate reads; it never decides.

## Rules

- **A plate takes its data as an argument.** No plate imports `LINE_SET` or
  calls `read_set()`. The build passes `lines`, `shared`, `reading`, and
  `wrapper` in. That is what makes the extensibility claim testable: append a
  fifth entry at runtime, pass it, and the plate must change.
- **No module here names an individual line.** Layout comes from
  `len(entries)` and from each entry's `working_position`; colours and shapes
  come from `palette`. A branch on `entry.id == "red_line"` would break the
  moment the set grows.
- **Box heights derive from their text.** `_row_height`, `_stage_height`, and
  `_rung_height` measure wrapped line counts, so a verbose new entry renders
  rather than overflowing its card.
- **A plate that cannot show its subject says so.** `vocabulary_matrix` falls
  through to `_empty_matrix` when fewer than two lines yielded a vocabulary,
  and that panel states in words that nothing was compared. Never let a plate
  render an empty version of itself as though it were a result.
- **Unread is drawn, not omitted.** `installation_surface` hatches an
  unresolved row, marks each metric with an em dash and the words "not read",
  and prints the code that explains it. Do not substitute a zero, a previous
  value, or a blank.
- **Shape and label carry every distinction.** Colour is redundant. A new
  encoding must survive a greyscale conversion.
- **Marker shapes must stay distinct on one plate.** `set_compass` passes
  `marker_position=len(entries) + 1` for the wrapper, because the wrapper's
  declared `working_position` was fixed when `registry.py` was written and
  would collide with a real line's shape once the set grows.

## Validation

- `uv run python scripts/build_figures.py`, then read the PNGs.
- Append a fifth `LineEntry` at runtime, rebuild into a scratch root, and
  confirm `set_compass`, `two_orders`, `vocabulary_matrix`, and
  `installation_surface` all change while no module here was edited.
  `set_reading_pipeline` must *not* change: it is drawn from the reader's
  stages, not from the set.

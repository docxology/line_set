# Line Set plates contract

Each plate is a pure function from a declaration, a reading, or a reader tuple
to an SVG string. A plate reads; it never decides.

## Rules

- **A plate takes its data as an argument.** No plate imports `LINE_SET` or
  calls `read_set()`. The build passes `lines`, `shared`, `reading`, and
  `wrapper` in. That is what makes the extensibility claim testable: append a
  new entry at runtime, pass it, and the plate must change.
- **No module here names an individual line.** Layout comes from
  `len(entries)` and from each entry's `working_position`; colors and shapes
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
- **Shape and label carry every distinction.** Color is redundant. A new
  encoding must survive a grayscale conversion.
- **Markers are redundant; written identities are authoritative.** The current
  declaration and a single-entry extension have distinct shapes. `set_compass`
  assigns the wrapper `marker_position=len(entries) + 1`. Larger declarations
  may exhaust the finite cycle; never hide a full line ID or working position.
- **Compactness must come from layout, not smaller labels.** The compass keeps
  its full-width cards but removes excess vertical padding. Two orders sizes
  each working card from its own wrapped question and packs the staged and
  unstaged panels independently in the right column; the footer starts below
  both columns. The vocabulary matrix reserves carrier width per name, then
  balances contiguous alphabetic panels by their actual wrapped row heights.
  Keep artifact identities, all written data, and both legibility floors.

## Validation

- `uv run python scripts/build_figures.py`, then read the PNGs.
- Append a new `LineEntry` at runtime, rebuild into a scratch root, and
  confirm `set_compass`, `two_orders`, `vocabulary_matrix`, and
  `installation_surface` all change while no module here was edited.
  `set_reading_pipeline` must *not* change: it is drawn from the reader's
  stages, not from the set.

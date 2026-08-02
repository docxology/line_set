# Line Set plates

One module per family of plate, plus `__init__.py`, which assembles the plate
list and its declared provenance.

- `declaration.py` — `set_compass`, `two_orders`. Drawn from the declared
  lines alone; neither imports a sibling package.
- `pipeline.py` — `set_reading_pipeline`. Drawn from `READER_STAGES` and
  `STATUS_PRECEDENCE`, so it describes the contract rather than any reading.
- `reading.py` — `vocabulary_matrix`, `installation_surface`. Drawn from one
  `SetReading` handed in by the build.
- `exemption.py` — `exemption_gate`. Drawn from `line_set.probes`, which runs
  the production matcher over a declared exemption and six weakenings of it.
- `application.py` — `self_application`. Drawn from the reading that includes
  the wrapper, with the verdict taken from
  `invariants.self_disjointness_from_reading()` rather than recomputed.

`figure_plates()` is a function, not a module-level tuple, so importing this
package does not trigger a reading. The build computes two readings — one over
the declaration, one over the declaration plus the wrapper — and passes each to
the plates that need it, so every plate describes the same moment.

Captions and alt text live beside the plates in `__init__.py`. Every number in
them is read from the declaration or the reading, so a caption cannot drift
away from the plate it sits under.

See [AGENTS.md](AGENTS.md) for the working contract.

# Line Set package contract

`src/line_set/` is the source of truth for the set declaration, the staged
reader, the structural checks, the canonical serialization, and the version
markers.

## Modules

- `__init__.py` re-exports the supported public API; `__all__` is sorted and duplicate-free.
- `binding.py` defines `Resolution`, `Vocabulary`, `VocabularyCensus`, `ImportResolver`, `default_resolver`, `sibling_path_resolver()`, `sibling_source_roots()`, `candidate_packages()`, `exported_enums()`, `enum_tokens()`, `vocabulary_census()`, and `read_vocabulary()`. `exported_enums()` is the single place the exported set is decided, so the token reader and the census cannot come to describe different classes; anything that needs the package's enums goes through it.
- `invariants.py` defines `SoundnessResult`, the seven offline structural checks, `self_disjointness_from_reading()`, `check_self_disjointness()`, `all_invariants()`, `live_invariants()`, and `registry_sound()`. The self-check is split so the judgement is pure: `check_self_disjointness()` takes the reading and delegates, and a figure drawing the property calls the same judgement instead of a second copy of it.
- `probes.py` defines `ExemptionProbe`, `exemption_probes()`, `probes_hold()`, `spare_line_id()`, and `DERIVED_LINE_SUFFIX`. It weakens a *declared* exemption six ways and reports what `exemption_for()` did with each. It checks nothing and demonstrates detection over the inputs it names; a probe built from a literal instead of from the declaration would stop tracking the declaration.
- `models.py` defines `SetStatus`, `ReadCode`, `OPUS_STAGE_ORDER`, `LineEntry`, `SharedToken`, `LineObservation`, `TokenCollision`, `DerivationStage`, and `SetReading`.
- `reader.py` defines `read_set(lines=LINE_SET, shared=SHARED_TOKENS, *, resolver=None, as_of=None)`, `exemption_for()`, `READER_STAGES`, and `STATUS_PRECEDENCE`.
- `registry.py` defines `LINE_SET`, `SHARED_TOKENS`, `WRAPPER_LINE`, `line_ids()`, and `find_line()`.
- `serialization.py` defines `canonical_registry()`, `registry_digest()`, `canonical_reading()`, and `reading_digest()`.
- `version.py` defines `__version__` and `SET_VERSION`.

## Invariants

- **`binding.py` is the only module that imports a sibling package.** Every
  other module takes the declaration as an argument and computes over it. If
  a second module ever needs to reach a sibling, route it through `binding`
  rather than importing directly.
- **Absence is never an exception and never a fabricated value.** A line that
  is not installed yields `ReadCode.NOT_INSTALLED` with `version`,
  `registry_size`, and `registry_digest` left `None`.
- **The default resolver touches nothing.** Sibling source directories go on
  `sys.path` only when a caller constructs an `ImportResolver` with
  `search_paths` or calls `sibling_path_resolver()`, and what was inserted is
  recorded in `added_paths`.
- **`exemption_for()` fails closed and must stay that way.** Token equality,
  line-set equality, a non-blank meaning for every named line, and exactly one
  matching declaration. A looser match — substring, case-folded, subset —
  silently converts the non-overlap guarantee into a rubber stamp. Any change
  here needs a planted-bad test that proves the looser input is still refused.
- **Nothing sorted by accident.** Token collection, collision partitioning,
  candidate discovery, and every canonical form sort before they emit, so no
  `dict` or `set` iteration order can reach a reading or a digest.
- **Adding a colour is a `registry.py` edit.** No module names an individual
  line; the reader and the checks take `lines` and `shared` as arguments.
- **Every check fails on an empty scan set.** A check that had nothing to look
  at reports that, rather than passing.
- **`all_invariants()` is offline; `check_self_disjointness()` is live.** The
  offline battery passes with zero siblings installed. Self-disjointness
  cannot: with no sibling vocabulary the comparison set is empty, and it
  reports `passed=False` rather than passing vacuously. Do not move it into
  `all_invariants()` to make a run go green.

## Claim boundaries

A reading reports which declared vocabularies were legible and whether any two
of them overlapped. `SET_LEGIBLE` is not a statement that the lines are
correct, complete, consistent, or worth having. The reader reads declarations,
not behaviour: two lines can have wholly disjoint vocabularies and still
overlap conceptually. A digest detects disagreement with a digest someone
already holds; it is not tamper evidence.

## Validation

- `uv run pytest tests/ --cov=src --cov-branch --cov-report=term-missing`
- `uv run python scripts/check_registry.py`
- `uv run python scripts/check_set.py`
- `uv run python scripts/build_figures.py`

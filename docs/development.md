# Development

The package is pure standard library with no runtime dependencies. The local
validation surface is four commands:

```bash
uv run pytest tests/ --cov=src --cov-branch --cov-report=term-missing
uv run python scripts/check_registry.py
uv run python scripts/check_set.py
uv run python scripts/build_figures.py
uv run python scripts/record_reading.py --check
```

The coverage floor is configured in `pyproject.toml`; read it there rather than
from a number restated in prose.

## What each command needs

| Command | Needs the siblings? | What it establishes |
| --- | --- | --- |
| `pytest` | No | The package's own behaviour, including all four reading statuses driven through injected resolvers. |
| `check_registry.py` | No | The offline structural battery over the declaration. |
| `check_set.py` | Yes, for a full reading | A live reading plus `live_invariants()`. Without them it reports `SET_PARTIAL` and an unestablished self-disjointness — an honest result, not a pass. |
| `build_figures.py` | No — it needs `rsvg-convert` instead | Deterministic SVG/PNG pairs and the figure registry under `output/figures/`. Two plates are drawn from a live reading; with the siblings absent they render that absence visibly and the run still succeeds. |
| `record_reading.py` | Yes | Writes `docs/manuscript/reading_record.json`, the dated reading the manuscript's measured numbers are bound to. Refuses to write anything but a `SET_LEGIBLE` reading of every declared line — an incomplete measurement in the place a complete one is expected is worse than no record. `--check` compares without rewriting. |

## Why the manuscript's measured numbers have a record

The manuscript quotes sibling versions, registry sizes, per-line token counts,
digests, and the token arithmetic that carries its one empirical claim. None of
those can be re-derived where the sibling packages are absent, which is most
places the manuscript will be read.

So the check is split. `scripts/record_reading.py` writes what the reading said
into `docs/manuscript/reading_record.json`; `tests/test_manuscript_bindings.py` binds
the prose to that record on every machine, and binds the record to a live
reading only where one can be taken. Prose drift therefore fails in a bare
checkout, and a stale record fails on a machine that can re-measure. The
record's own `set_digest` is checked everywhere, so a declaration change
invalidates it with no sibling installed and no network.

After changing the declaration, or after a sibling release, rerun
`record_reading.py` and update any prose whose numbers moved. The suite will
name which ones.

**The test suite must not depend on the siblings being importable.** Coverage of
`src/` is measured with them absent as well as present; a suite that only passes
inside this working tree would be a suite that cannot travel with a standalone
export.

## Reading the siblings

Nothing is added to `sys.path` by importing this package. The default resolver
finds exactly what an ordinary `import` finds, which in a bare checkout is
nothing:

```python
import line_set
line_set.read_set().status.value        # 'set_partial' with no siblings installed
```

`sibling_path_resolver()` is the explicit opt-in. It locates
`<siblings>/<package>/src` for each declared `package_name`, prepends what
exists to `sys.path` on first use, and records exactly what it inserted:

```python
resolver = line_set.sibling_path_resolver()
reading = line_set.read_set(resolver=resolver)
resolver.added_paths                    # what this call actually inserted
```

A line with no checkout is simply absent from the search paths and reads as
`NOT_INSTALLED`. That is an ordinary outcome and never an exception.

**Where it looks, and how to say somewhere else.** `sibling_base()` returns this
project's parent directory by default, because that is where the checkouts sit
in the tree this project is developed in. That default is positional, and this
project is its own repository: a clone will usually have something unrelated in
its parent directory. `LINE_SET_SIBLINGS` names the directory explicitly, is
read at call time, and is honoured by the resolver, by `check_set.py`, by
`record_reading.py`, and by the omnibus assembler:

```bash
LINE_SET_SIBLINGS=/wherever/the/set/lives uv run python scripts/check_set.py
```

An empty or whitespace-only value is read as unset rather than as the working
directory. An explicit `base=` argument still wins over both.

## Figures

Rasterization requires `rsvg-convert` from librsvg on `PATH`. It is a system
rendering prerequisite, not a runtime package dependency; the builder fails
closed with install guidance rather than skipping silently, and
`LINE_SET_RSVG_CONVERT` overrides the binary location.

Two floors govern figure text, and only one of them is about the page.
`canvas.MIN_TEXT_UNITS` refuses a label authored below the floor in canvas
units. `figures/legibility.py` derives what a canvas unit becomes in printed
points — from the page geometry in `docs/manuscript/config.yaml`, the `width=NN%`
attribute on each embed, and the plate's own aspect ratio against the template's
figure height cap — and `tests/test_figure_legibility.py` fails any plate whose
smallest label lands below `MIN_LEGIBLE_PT`. The rendered floor is the binding
one: a canvas floor alone measures a unit the page never sees, and while that
was the only check the plates were rendering at 4.27pt. Nothing here reads a
PDF, so the check runs on a fresh checkout with only the figures built.

Three of the figures — the vocabulary matrix, the installation surface, and the
self-application plate — are drawn from a live reading, so they need the
siblings importable. A figure built with a sibling absent must render that
absence visibly rather than omitting the row; an omitted row is a figure that
lies by being tidy. The exemption gate needs no sibling: it runs the production
matcher over the declaration alone.

Never hand-edit anything under `output/`. Rebuild it.

## Rendering the manuscript

**Rendering is an external dependency, and it is stated as one rather than
hidden.** This repository ships no renderer. The manuscript is markdown plus a
`docs/manuscript/config.yaml`, and the PDF and HTML are produced by the separate
`docxology/template` engine, which lives in its own repository and is
deliberately not vendored here.

Everything else works without it. The test suite, `check_registry.py`,
`check_set.py`, `build_figures.py`, `record_reading.py`, and `build_omnibus.py`
all run from this repository alone; what needs the template is the typeset
artifact and the template's own output validation. A copy of this project with
no template anywhere on the machine is still a complete, checkable project — it
simply has no PDF.

Clone the engine wherever you like. Nothing below assumes it sits at a
particular place relative to this project:

```bash
git clone https://github.com/docxology/template.git /wherever/you/want/template
```

The template discovers projects by mirroring an external projects root into its
own `projects/` tree, and the root is given to it explicitly rather than
guessed. It expects that root to hold lifecycle folders, so this project should
sit at `<root>/working/line_set` — a symlink is enough if the clone lives
elsewhere:

```bash
# From anywhere; substitute your own two paths.
TEMPLATE=/wherever/you/want/template
PROJECTS_ROOT=/wherever/you/keep/projects      # must contain working/line_set

cd "$TEMPLATE"
uv sync
export TEMPLATE_PRIVATE_PROJECTS_ROOT="$PROJECTS_ROOT"
uv run python -m infrastructure.orchestration link-projects --dry-run
uv run python scripts/maintenance/rerender_working_pdfs.py --project line_set
uv run python scripts/pipeline/stage_04_validate.py --project working/line_set
```

`working/line_set` is the qualified project name for a project mirrored from
`<root>/working/`; link it under a different lifecycle folder and the qualified
name changes with it. The command surface belongs to the template, not to this
project — read the template's own documentation when it moves, and do not treat
a stale recipe here as authoritative.

A rendered PDF is evidence that rendering succeeded. It is not independent
validation of anything the manuscript says.

The template's strict public publication audit is a public-release check that
asks whether a project sits inside its own public repository. Run against a copy
mirrored in from an external projects root, it reports the project path as
outside the public repository; that finding is about where the copy was linked
from and is not a source or manuscript defect, and it is not a reason to weaken
the public validator.

## House rules that bite during development

- **No mocking framework.** `unittest.mock`, `MagicMock`, and `mocker.patch` are
  prohibited across `src/`, `tests/`, and `scripts/`. Use injected plain
  callables for resolution and real temporary directories for packages.
- **Do not modify a sibling project.** Read them freely; write nothing. If a
  reading needs a sibling to change, that is a finding to report, not an edit to
  make from here.
- **Derive, do not restate.** A count, digest, version, or status that code can
  produce belongs in a command's output or a test binding, not typed into prose.
- **Fail closed.** Any change to `exemption_for` needs a planted-bad test
  proving the looser input is still refused.

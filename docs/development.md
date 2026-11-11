# Development

The package is pure standard library with no runtime dependencies. The local
validation surface is:

```bash
uv run pytest tests/ --cov=src --cov-branch --cov-report=term-missing
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run mypy src/line_set
uv run python scripts/check_registry.py
uv run python scripts/check_set.py
uv run python scripts/gen_formalism_ledger.py
uv run python scripts/build_figures.py
uv run python scripts/record_reading.py --as-of <recorded-review-date> --withhold-source violet_line --withhold-source copper_line --withhold-source iron_line --check
```

The coverage floor is configured in `pyproject.toml`; read it there rather than
from a number restated in prose.

Ruff is configured locally at the package's Python floor, using its standalone
default syntax/logic checks. A surrounding collection's lint policy is not an
implicit dependency of this repository. Formatting remains a separate check.

For a release preserving an earlier reading, take the date from
`docs/manuscript/reading_record.json` (`reading.read_as_of`), not the new
publication date. `--check` compares every recorded measurement field and
reports the retained producer version separately from the current checker.
It does not relabel the historical record as produced by the current release.
Malformed producer metadata, empty measurement sets, missing fields and any
measurement drift still fail.
Comparison reads raw bytes and requires canonical UTF-8 with LF line endings;
CRLF, lone CR, a byte-order mark or another encoding fails even if JSON values
match. New writes use those same canonical bytes on every platform.
For an offline lane, point `LINE_SET_SIBLINGS` at an empty directory before the
suite and registry check. `check_set.py` must fail there with `SET_PARTIAL`;
absence is an outcome, not a successful integration result.

For the integration lane, collect each source in a read-only Git snapshot with
a `.line-set-source.json` receipt recording its actual full `revision`, and set
`LINE_SET_SIBLINGS` to their common parent. This also supports source checkouts
whose original locations or access classes differ. Never point canonical
recording at actively edited worktrees or label changed bytes with an earlier
commit. Development snapshots must be identified as such, not as released tags.
When snapshots supply compiled artifacts, retain their source custody and Git
repository boundaries for the external renderer.

```bash
uv run python scripts/check_set.py --require-pinned --as-of YYYY-MM-DD
uv run python scripts/record_reading.py --as-of YYYY-MM-DD --withhold-source violet_line --withhold-source copper_line --withhold-source iron_line --check
```

Use the retained record's `reading.read_as_of` for both date arguments when
checking that record; the publication date may differ.

The pinned gate fails on an empty scan, missing package metadata, unpinned
sources or incomplete discovery. It is a reproducible namespace lane, not an
evaluation or certification of sibling behavior. The release packet records the
exact tags, commits and gate results. See [binding_contract.md](binding_contract.md).

The maintained record is an explicit `2.0-public` namespace view. The repeatable
`--withhold-source LINE_ID` option removes that line's revision and module path
only after the complete underlying reading passes the unchanged admission gates.
Its `withheld_sources` list names the omissions, and its digest is recomputed
from the projected reading. The public view does not pass `check_pinned_sources`;
it is not a fully publicly reproducible source-pin proof or general deidentification.
Review other metadata and diagnostic text separately before publication.
The current public cutover must request all three PRIVATE producers explicitly:
`violet_line`, `copper_line`, and `iron_line`. This is operator disclosure policy,
not a reader whitelist or a relaxation of admission. A historical eight-line view
uses its own retained withheld-source list and date when checked against its
matching historical captures.

Omitting the option retains the full `2.0` canonical format. Store that record
in an authorized private location when any producer's source identity is private:

```bash
uv run python scripts/record_reading.py --as-of YYYY-MM-DD --out "$PRIVATE_READING_RECORD"
uv run python scripts/record_reading.py --as-of YYYY-MM-DD --out "$PRIVATE_READING_RECORD" --check
```

Set `PRIVATE_READING_RECORD` to the operator's private evidence path. Public
`--check` re-admits every source and compares the disclosed measurement with
the same explicitly requested view. It cannot detect revision-only changes in
withheld source identities; exact continuity belongs to the privately retained
full record. Forgetting the option does not silently infer a public view.

## What each command needs

| Command | Needs the siblings? | What it establishes |
| --- | --- | --- |
| `pytest` | No | The package's own behavior, including all four reading statuses driven through injected resolvers. |
| `check_registry.py` | No | The offline structural battery over the declaration. |
| `check_set.py` | Yes, for a full reading | A live reading plus `live_invariants()`. Without them it reports `SET_PARTIAL` and an unestablished self-disjointness — an honest result, not a pass. |
| `build_figures.py` | No — it needs `rsvg-convert` instead | Deterministic SVG/PNG pairs and the figure registry under `output/figures/`. Live plates are drawn from a reading; with the siblings absent they render that absence visibly and the run still succeeds. |
| `record_reading.py` | Yes | Requires a complete `SET_LEGIBLE` pinned reading before writing. By default writes a full `2.0` record; explicit `--withhold-source` writes a distinct `2.0-public` view with selected source identities omitted. `--check` compares the requested view without rewriting; withholding never permits incomplete source admission. |

## Why the manuscript's measured numbers have a record

The manuscript quotes sibling versions, registry sizes, per-line token counts,
digests, and the token arithmetic that carries its one empirical claim. None of
those can be re-derived where the sibling packages are absent, which is most
places the manuscript will be read.

`scripts/record_reading.py` refuses incomplete, colliding, unpinned or
metadata-incomplete readings, including incomplete discovery. The maintained
public view is tested through reading replay, projected reading/declaration
hashes, disclosed source correspondence and census arithmetic. Where the full
underlying pinned sources are accessible, the same view is compared with a
fresh admitted reading without changing its original producer metadata.

After a declaration or vocabulary change, preserve the previous record as
historical evidence, take a new pinned reading with an explicit date, and
review all measured manuscript passages against that record. Tests do not
certify authored wording. Regenerate `data/formalism_claim_ledger.json` with
`scripts/gen_formalism_ledger.py` after the record refresh; its scalar census
fields and repeat totals remain references to recorded measurements, not
independent findings.

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
read at call time, and is honored by the resolver, by `check_set.py`, by
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

The vocabulary matrix, installation surface and self-application plate are
drawn from a live reading, so they need the
siblings importable. A figure built with a sibling absent must render that
absence visibly rather than omitting the row; an omitted row is a figure that
lies by being tidy. The exemption gate needs no sibling: it runs the production
matcher over the declaration alone.

Never hand-edit anything under `output/`. Rebuild it.

`uv run pytest tests/test_figure_layout.py` measures glyph widths through the
existing `rsvg-convert` backend, checking each standalone plate against its
horizontal viewport and card boundaries and checking text overlap near the same
baseline. A planted overflowing,
overlapping SVG must fail. These measurements accompany the printed-point
floor and visual inspection of the generated PNGs and final PDF.

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
uv sync --frozen --group rendering
export TEMPLATE_PRIVATE_PROJECTS_ROOT="$PROJECTS_ROOT"
uv run python -m infrastructure.orchestration link-projects --dry-run
uv run python -m infrastructure.orchestration link-projects
uv run python scripts/pipeline/stage_03_render.py --project working/line_set --skip-manuscript-hydration
uv run python scripts/pipeline/stage_04_validate.py --project working/line_set
```

Use a Git-indexed engine checkout: its rendered provenance gate fingerprints
tracked engine implementation files. A source archive can render, but cannot
supply that index. The `--skip-manuscript-hydration` option retains this
repository's authored `docs/manuscript` layout.

The current complete volume contains Main plus ten instruments, eleven works;
Witness remains outside it. Violet, Copper, and Iron require authorized PRIVATE
source access. Assemble and render that complete volume only in independent
private custody, never in a public repository/worktree sharing its object store.
Public Main figures and ledgers must contain only reviewed public namespace
metadata, not private module paths, source revisions, native receipts, or content.

First run this repository's omnibus builder in a separate render clone.
Preserve its authored `docs/manuscript` outside that
clone, then copy the assembled `output/manuscript` to `docs/manuscript` in the
render clone. Record the release revision and hashes of both manuscript trees,
and commit this generated source projection locally in that clone. Render and
validate this derivative with the commands above. Keep its projection receipt,
assembly report, sibling-source custody and native provenance with the artifacts.
Retain the wrapper's unchanged preamble and recorded reading alongside the
projected sources, relocate the
wrapper's evidence-metadata source paths to its generated section filenames,
and mirror the gathered figures at `docs/figures` for source-relative inspection.
Record those metadata relocations and mirrored-file hashes in the projection
receipt. The assembler writes `omnibus_claim_ledger.json` from the formalism
anchors actually declared in the assembled sections, so the engine can resolve
their namespaced cross-references. Its rows record label presence only.

The volume owns one final merged bibliography. A `99_` reference page is a
structural stub only when its heading actually says **References**, optionally
followed by an empty Pandoc `#refs` Div. A heading-only `99_scope.md` is still
a source section. Reference pages containing prose or examples remain source
sections; their empty live `#refs` Divs are removed before the normal section
transforms. Prose, citations, nonempty Divs and fenced, inline or indented literal
examples remain intact. Fences close only with the opening delimiter character
and at least its run length. Inline code uses matching backtick runs, including
multiline spans within a paragraph; ordinary list continuation indentation is
not an indented code block. The shared `line_set._markdown_spans.prose_spans`
reader exposes active half-open ranges in original string offsets for publication
consumers. Literal syntax is neither collected nor rewritten nor validated as an
active anchor, reference, or image. Figure retargeting changes image destinations
only, not prose paths or captions. The final volume reference page owns the single
citeproc placeholder, and the generated front matter sets `link-citations: true`
in leading Markdown YAML.

Assembly refuses collisions it introduces between authored namespaced IDs and
generated front-matter, part, or cover IDs. It does not add validation of duplicate
IDs already authored within a work or broaden the supported anchor-attribute
syntax. The document-wide formalism-kind versus citation rule is unchanged.

The bibliography reader preserves raw supported entries and compares only their
top-level identity fields. It accepts braced records with balanced nested braced
or quoted literal values, escaped characters, numeric values, standard bare
month names (`jan` through `dec`), percent comments outside values, and balanced
`@comment{...}` blocks. Comments do not become live entries. Unsupported
constructs raise `OmnibusError` before any write: in particular parenthesized
records, `@string`, `@preamble`, other macro-valued fields, concatenation, and
incomplete fields are not silently dropped or shortened.
This is a bounded reader, not a BibTeX evaluator.

Both planning and writing prepare the complete config, reference ledger,
bibliography, registry, destination checks, and UTF-8 output bytes before
mutation. Every actual compiled embed must have exactly one matching accessible
registry record: label and filename must agree when a label is present; an
unlabeled embed needs an unambiguous filename match. Required alt text must be
nonblank and is retained from the source record. Repeated placements remain
covered; literal examples do not demand records. Native plates and generated
covers share one output-basename ownership map, so neither silently replaces the
other. PNG-only works remain supported; assembly does not require source SVGs
or claim to measure compiled physical legibility.

`AssemblyReport.image_sources` contains sorted `(compiled image target, source
Path)` pairs, including generated cover copies. Its JSON representation is an
`image_sources` object. Targets use the exact `../figures/<basename>` spelling
in the compiled embeds. This is source-file ownership, not renderer provenance
or a claim that a source SVG sibling exists. A physical compiled-surface check
must independently bind those exact targets to genuine SVG sources and the
compiled config.
Blank lines and standalone comments inside supported `paper` metadata do not
erase a configured cover; its image and alternative text remain in the copied
cover block and source inventory.

Generated part covers use the full text width, subject to the existing figure
height cap; their native text must satisfy the same physical floor as other
placements. The set cover derives its column budget from complete declared
names, while longer labels still wrap without losing characters.

When an external SDK consumes a compiled canonical manuscript tree, retain
required non-Markdown evidence resources at their declared paths. For example,
copy the genuine current `reading_record.json` from the preserved authored tree
to `docs/manuscript/reading_record.json` and record byte correspondence. Do not
replace compiled sections with authored sections or substitute an older reading
to satisfy a source-path check. This resource retention is the rendering
caller's responsibility, not additional namespace or evaluator authority.

The physical-layout API is in `line_set.figures.legibility`:

- `parse_embeds(manuscript_dir)` returns a tuple of `EmbedOccurrence` records,
  not a dictionary keyed by basename. Every repeated active placement retains
  its exact destination, label, width, source file, and original line number.
  `parse_embed_text(markdown, source=...)` accepts an explicit text surface.
  Inline code in a caption, including bracket text, does not hide an actual
  placement or change its original destination or line.
- `measure_project(project_root)` measures only standalone authored placements;
  it never treats an `output/manuscript` tree as a qualified compiled volume.
- `measure_surface(occurrences, config_text=..., svg_sources=..., surface=...)`
  requires the explicit `standalone` or `compiled` scope and a complete exact
  image-destination-to-source-SVG map. A compiled caller includes every generated
  placement, including covers, and the actual compiled configuration. Missing
  source SVGs or an empty measurement surface are refused.

The font inventory accepts explicit numeric `font-size` attributes in single or
double quotes, with optional `px`, and numeric pixel declarations in CSS. It
takes the smallest declaration conservatively; it does not evaluate the CSS
cascade, inherited or relative sizes, font substitution, glyph bounds, or
computed browser styles. A missing supported declaration remains a refusal.
Only real XML attributes and CSS-bearing style attributes/elements contribute
declarations. XML/CSS comments, quoted CSS strings, ordinary text and similarly
named data attributes do not. Supported geometry and height scalars honor
ordinary YAML trailing comments; commented-out keys are not declarations.

Bind each SVG to its actual native raster generation before measuring it;
filename resemblance alone does not establish correspondence. The result is
per-occurrence geometry under the declared US Letter page model, not PDF text
extraction, accessibility certification, or human visual acceptance. A generic
PNG-only assembly remains valid without this optional SVG measurement.

Managed manuscript/figure directories and all files assembly will write or
remove must be nonsymlink nodes contained under the project root. Wrong node
kinds and unsafe filenames are refused in both modes. Cleanup reads the prior
`omnibus_report.json` section inventory and removes only obsolete listed
sections; unrelated Markdown/BibTeX files survive. A missing inventory grants
no inferred section-deletion authority; a malformed inventory is refused.
Known generated config, bibliography, ledger, report, and current section
filenames are replaced explicitly. Deterministic input failure leaves the
previous output unchanged; this is not a transaction against runtime I/O
failures or concurrent filesystem changes.

The paper metadata subset is single-line plain, single-quoted, or double-quoted
string scalars for title, subtitle, version, and date. Quoting, escapes, and
inline comments are decoded before use; generated string scalars are safely
quoted, including quotes, backslashes, and escaped YAML line separators.
Multiline scalars, aliases, tags, and collection nodes are explicitly refused
rather than partially read. Reused author/render/geometry blocks remain verbatim.

Native authored sources can contain producer-owned variables. Preserve the raw
assembled tree, then consume a genuine native-resolved manuscript projection
before rendering the derivative. Blue's existing `gen_formalism_ledger.py` and
`render_manuscript.py` produce its variables and resolved manuscript; do not
substitute a value by hand or execute an evaluator from this wrapper. Retain the
actual producer command, source revision, variable-file hash, authored and
resolved section hashes, and any effective date policy. Blue's default-window
variable derives from its native configuration, not a new review date.

Apply the existing `collect_anchors`, `transform_section`, and `invert_section`
operations to those native-produced section bytes. Keep the same declared
anchors and documented figure-prefix normalization, record every changed
projected filename, and commit that source projection only in the private
render clone. This is an explicitly recorded native-resolved derivative, not
a claim that rendered prose is byte-identical to the authored template.

Run the renderer's existing
`infrastructure.validation.publication.audit.check_placeholder_tokens` against
the real rendered-project audit context, and inspect the actual PDF, HTML, and
EPUB. Stage04 and current provenance alone do not establish resolved variables
or working section-page fragments. Intentional code examples remain distinct
from unresolved variables in manuscript prose.

Carry each included work's published numeric claim ledgers as byte-exact
producer artifacts outside the engine's automatic ledger scan roots. A generated
ledger under `data/` may quote their numeric rows, retaining producer identity,
revision, original row and raw-ledger hash, with a distinct
`quoted_sibling_ledger` source tier and source path to the copied artifact.
Preserve producer freshness flags. This carries existing numerical evidence
without executing a sibling or presenting its original test tier as a test run
by the wrapper. Never manufacture support by harvesting numbers from prose.
Any remaining unsupported required value blocks validation and is an owner
finding. Retain these quoted artifacts and their custody with the volume.
The dated release evidence retains the projection and native-ledger custody
helpers used for these operator steps. They run in the external renderer's
environment, including its YAML reader; they are not package runtime dependencies.
Never apply this projection to the canonical source checkout or publish its
scratch commit as the software release.

The engine requires each rendered manuscript filename to have a canonical
source counterpart. Rendering assembled filenames against the wrapper's authored
source tree produces `UNCONSUMED_MANUSCRIPT`; the generated projection gives the
complete volume its own explicit canonical render inputs. Native provenance
then binds that derivative, while the assembler's source-preservation gates and
the separate custody receipt bind it back to the released works. It does not
turn the generated volume into independently authored or verified sibling work.
Keep the actual project clone's basename `line_set` as well as its qualified
link name: the engine's output-structure check derives the expected combined
PDF filename from the resolved clone basename.
The builder selects a configured source tree before considering an unconfigured
directory. If both `docs/manuscript/` and `manuscript/` have `config.yaml`, the
former wins. A partial migration without a config cannot shadow the configured
source. Corpus tests use the same explicit `LINE_SET_SIBLINGS` location as the
reader and assembler.
Paper sections exclude the engine's operational control files, including
`MANUSCRIPT_STATUS.md`; the compiled volume reproduces authored body sections
and handles preambles separately.

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

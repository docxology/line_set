# Line Set

Line Set is the fifth work in the line set, and it is not a fifth instrument. It
has no opinion about refusal, method, aspiration, or absence — those questions
belong to Red, Black, Golden, and White Line, and this work does not answer, merge,
rank, or second-guess any of them. Its job is bookkeeping: hold the declaration
of what the set is, read the sibling packages that are actually installed, and
check that the set's non-overlap contract still holds.

The declaration is a tuple of `LineEntry` records in
[`src/line_set/registry.py`](src/line_set/registry.py), one per line, each
carrying the question that line answers, the job it does, the thing it must not
become, its position in the working order, and the opus stage its colour echoes.
`read_set()` resolves each declared package, reads a version, counts a registry,
asks the package for its own digest, collects the enum member names it exports,
and reports `SET_LEGIBLE`, `SET_PARTIAL`, `SET_COLLIDING`, or `SET_UNDECLARED`
through five recorded stages. `all_invariants()` checks the declaration's shape
offline; `check_self_disjointness()` applies the collision check to a set that
includes this package.

That last check is the point. A package that checks other packages for shared
status tokens has to survive that check itself, or it is applying a rule it is
exempt from. The reading statuses are prefixed so their disjointness from every
sibling vocabulary is *checkable* rather than merely intended, and the check
runs the production reader over the real declaration plus this package's own
entry. A declared exemption does not rescue the wrapper: it is not a line and
has no standing to share a token with one.

## The honest boundary

A `SET_LEGIBLE` reading says that the declared lines the reader could import each
exported a set of enum member names, and that no name appeared in more than one
of them except where an exemption was declared in advance with a distinct meaning
per line. It does not say the instruments are correct, complete, well chosen, or
worth having; it does not say the set covers what it should cover; it is not
tamper evidence; it is not independent verification of any sibling, since every
version, size, and digest reported is read from that sibling using the sibling's
own function; it is not a ranking; and it is emphatically not a claim about
substance — two lines can have entirely disjoint vocabularies and still overlap
conceptually, which is human work this package does not do and does not shorten.
The full non-claim register is [`docs/claim_boundaries.md`](docs/claim_boundaries.md),
and it is the first thing to read if you suspect this project of overreach.

## Install

Pure standard library, no runtime dependencies. The sibling line packages are
**optional**: this project installs, tests itself, checks its declaration, and
renders its manuscript with none of them present.

```bash
uv sync
```

With no sibling importable, a reading is `SET_PARTIAL` and self-disjointness
reports itself unestablished. Both are honest outcomes rather than failures, and
neither is a pass. To read the real set, hand `read_set()` a
`sibling_path_resolver()` — the explicit opt-in that puts the sibling source
trees on `sys.path` and records exactly what it inserted. Nothing is added to
`sys.path` by importing this package.

It looks for those trees in this project's parent directory by default, which is
where they sit in the tree this project is developed in. That default is
positional and this project is its own repository, so a clone whose set lives
elsewhere names the directory with `LINE_SET_SIBLINGS` rather than being moved
into a layout.

## The four commands

```bash
uv run python scripts/check_registry.py   # offline structural battery over the declaration
uv run python scripts/check_set.py        # live reading of the installed lines
uv run python scripts/build_figures.py    # deterministic SVG/PNG pairs into output/figures/
uv run python scripts/record_reading.py   # write the dated reading the manuscript quotes
```

The first needs no sibling and reaches nothing outside this tree. The second
needs them: without a full reading the non-overlap contract was not checked, so
it exits non-zero rather than reporting a pass. The third runs either way — it
needs `rsvg-convert`, not the siblings — and the two plates drawn from a live
reading render an absent sibling visibly rather than omitting its row. The
fourth needs them too, and refuses to record a reading it could not take;
`--check` compares the record on disk against a live reading instead of
rewriting it. The test suite is
`uv run pytest tests/ --cov=src --cov-branch --cov-report=term-missing`, and it
must pass with the siblings absent as well as present.

The manuscript quotes numbers it measured against the installed siblings, and
those numbers cannot be re-derived on a machine without them. So they are
written to `manuscript/reading_record.json` and the suite binds the prose to
that record on every machine, while binding the record itself to a live reading
wherever one can be taken. A prose number that drifts fails anywhere; a stale
record fails on the machine that can tell. Full command surface and
render path: [`docs/development.md`](docs/development.md).

## Figures

Seven, all deterministic, all hand-written SVG rasterized through
`rsvg-convert`, none using colour as the only encoding, and all measured through
to the point size their smallest label reaches on the page rather than only to a
floor in canvas units:

| Figure | What it shows |
| --- | --- |
| `set_compass` | Each declared line with its question, its job, and what it must not become. Derived from the declaration, so it re-renders correctly when a colour is appended. |
| `two_orders` | Working order against opus order as two columns with crossing connectors — the divergence is deliberate, and citrinitas is deliberately not collapsed into rubedo. |
| `vocabulary_matrix` | Tokens against lines, from a live reading. Collisions marked, with the exempted cell distinguished from an unexempted one by shape *and* label, never by colour alone. |
| `set_reading_pipeline` | The five reader stages, with the status precedence rule drawn as the exit ladder. |
| `installation_surface` | Per line: resolved or not, version, registry size, digest prefix. Genuinely live, and it must render an absent sibling visibly rather than tidily omitting the row. |
| `exemption_gate` | The declared exemption and six weakenings of it, each put through `exemption_for()` at build time; the outcome column is a return value. The first row is the positive control, without which six refusals would prove nothing. |
| `self_application` | This package's own exported enum member names against each line's, with the live verdict of the self-check printed from the check itself. |

## Adding a colour

Append one `LineEntry` to `LINE_SET`. That is the whole edit to the source: no
module outside `registry.py` names an individual line, so the reader, the checks,
the serialization, and the figure builders all take the new entry without being
touched. The prose that names the set is what actually drifts. The recipe, an
executed example, and the exact lists of files an addition does and does not
touch are in [`docs/extensibility.md`](docs/extensibility.md).

## Standalone rule

Line Set is standalone. It has its own package, tests, documentation, manuscript,
references, and figures, and a separated copy must still explain its own purpose
and limits without the siblings present — see [`STANDALONE.md`](STANDALONE.md).
Its relationship to Red, Black, Golden, and White Line is declared as data in
[`src/line_set/registry.py`](src/line_set/registry.py) and described at length in
the manuscript. Each of the four is its own repository —
[Red Line](https://github.com/docxology/red_line),
[Black Line](https://github.com/docxology/black_line),
[Golden Line](https://github.com/docxology/golden_line), and
[White Line](https://github.com/docxology/white_line) — and those are the durable
references. This project's ancestor, the short internal note `docs/line-set.md`,
is unpublished, lives in the author's private projects tree, and does not travel
with this repository; it is cited by name rather than linked, because a relative
path out of this repository's root resolves to nothing for anyone holding only
this copy. This work links to those boundaries; it does not copy their prose,
registries, figure designs, or evaluator logic, and it never modifies them.

## Documentation

- [`docs/claim_boundaries.md`](docs/claim_boundaries.md) — the non-claim register.
- [`docs/architecture.md`](docs/architecture.md) — modules, stages, precedence, digests.
- [`docs/invariants.md`](docs/invariants.md) — the checks and their proof of detection.
- [`docs/extensibility.md`](docs/extensibility.md) — adding a colour.
- [`docs/development.md`](docs/development.md) — commands and render path.
- [`docs/envelope.md`](docs/envelope.md) — the set-wide report envelope convention.
- [`docs/correspondence.md`](docs/correspondence.md) — design reviews received and answered.
- [`AGENTS.md`](AGENTS.md) — working rules for this tree. [`TODO.md`](TODO.md) — what is not yet built.

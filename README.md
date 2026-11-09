# Line Set

The [2026-11-08 admission decision](docs/admission/decision-20261108.md)
adds Copper's dimensioned resource arithmetic and Iron's scenario-bound recovery
target comparisons. Separate packaging is an explicit architectural choice,
not an empirically established defeat of the strongest native extensions.
The older [admission materials](docs/admission/README.md) and
[family refinement note](docs/refinement-20261106.md) retain their dated
no-addition decisions and eight-line evidence. The optional
[evidence/replay profile](docs/evidence/README.md) remains a companion convention;
this package executes no native replay.

The completed [0.7.0 release packet](docs/releases/v0.7.0.md) retains its source,
measurement, verification, and publication evidence. New qualification is
separate; earlier packets and public readings keep their original identities.

Line Set is the bookkeeping work in the line set, and it is not an instrument. It
does not answer, merge, rank, or second-guess any substantive line's question.
Its job is bookkeeping: hold the declaration, read the sibling packages that
are actually accessible, and report the published-name separation contract.

The declaration is a tuple of `LineEntry` records in
[`src/line_set/registry.py`](src/line_set/registry.py), one per line, each
carrying the question that line answers, the job it does, the thing it must not
become, its position in the working order, and the opus stage its color echoes.
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
Admission rejects empty or ambiguous declarations before imports. Published enum
names include aliases; binding and discovery retain structured provenance and
coverage. The exact contracts are in [`docs/binding_contract.md`](docs/binding_contract.md).

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
uv run python scripts/record_reading.py --withhold-source violet_line --withhold-source copper_line --withhold-source iron_line  # public view after complete pinned admission
```

The first needs no sibling and reaches nothing outside this tree. The second
needs them: without a full reading the non-overlap contract was not checked, so
it exits non-zero rather than reporting a pass. The third runs either way — it
needs `rsvg-convert`, not the siblings — and live plates render an unread
sibling visibly rather than omitting its row. The fourth additionally requires
pinned source snapshots, complete metadata and completed discovery; a readable
but unpinned development installation is not canonical evidence. `--check`
compares the held record without rewriting it. The test suite is
`uv run pytest tests/ --cov=src --cov-branch --cov-report=term-missing`, and it
must pass with the siblings absent as well as present.

The manuscript's measured numbers come from `docs/manuscript/reading_record.json`.
A new current `2.0-public` view must withhold all three private producers'
revisions and module paths: Violet, Copper, and Iron. The full pinned measurement
stays in private custody. Preserved eight-line evidence is not a ten-line census.
The suite replays the public reading, checks its identity and census, and compares
the same view with a newly admitted complete pinned reading where those sources are
accessible. Public replay is not complete public source-pin proof, and revision-only
changes in a withheld source are not detectable from this view. Authored prose is
reviewed against that dated measurement, not certified by matching sentences.
Previously public historical records remain under `docs/releases/evidence/`.
Full commands and render path:
[`docs/development.md`](docs/development.md).

## Figures

Figures are deterministic hand-written SVG rasterized through `rsvg-convert`.
Names and outlines accompany color; legibility is measured at the declared
manuscript embed size, not only in canvas units.

| Figure | What it shows |
| --- | --- |
| `line_set_cover` | Named color bands in a presentation layout, not a second working order or an additional instrument. |
| `set_compass` | Each declared line with its question, its job, and what it must not become. Derived from the declaration, so it re-renders correctly when a color is appended. |
| `two_orders` | Working order against opus order as two columns with crossing connectors — the divergence is deliberate, and citrinitas is deliberately not collapsed into rubedo. |
| `vocabulary_matrix` | Tokens against lines, from a live reading. Collisions marked, with the exempted cell distinguished from an unexempted one by shape *and* label, never by color alone. |
| `set_reading_pipeline` | The five reader stages, with the status precedence rule drawn as the exit ladder. |
| `installation_surface` | Per line: resolved or not, version, registry size, digest prefix. Genuinely live, and it must render an absent sibling visibly rather than tidily omitting the row. |
| `exemption_gate` | The declared exemption and six weakenings of it, each put through `exemption_for()` at build time; the outcome column is a return value. The first row is the positive control, without which six refusals would prove nothing. |
| `self_application` | This package's own exported enum member names against each line's, with the live verdict of the self-check printed from the check itself. |

## Adding a color

Appending a distinct `LineEntry` is technical registration, not conceptual
admission. Behavioral extension fixtures exercise the existing reader, checks,
serialization and figure builders without adding instrument-specific branches;
they do not prove a useful new question or unbounded figure capacity. The recipe
and admission boundary are in [`docs/extensibility.md`](docs/extensibility.md).

## Standalone rule

Line Set is standalone. It has its own package, tests, documentation, manuscript,
references, and figures, and a separated copy must still explain its own purpose
and limits without the siblings present — see [`STANDALONE.md`](STANDALONE.md).
Current membership is declared in
[`src/line_set/registry.py`](src/line_set/registry.py); the family roster below
links each independent repository. A declared member need not be installed or
publicly accessible in a particular environment. This project's ancestor,
the short internal note `docs/line-set.md`,
is unpublished, lives in the author's private projects tree, and does not travel
with this repository; it is cited by name rather than linked, because a relative
path out of this repository's root resolves to nothing for anyone holding only
this copy. This work links to those boundaries; it does not copy their prose,
registries, figure designs, or evaluator logic, and it never modifies them.

## Documentation

- [`docs/claim_boundaries.md`](docs/claim_boundaries.md) — the non-claim register.
- [`docs/architecture.md`](docs/architecture.md) — modules, stages, precedence, digests.
- [`docs/invariants.md`](docs/invariants.md) — the checks and their proof of detection.
- [`docs/extensibility.md`](docs/extensibility.md) — adding a color.
- [`docs/development.md`](docs/development.md) — commands and render path.
- [`docs/envelope.md`](docs/envelope.md) — the set-wide report envelope convention.
- [`docs/correspondence.md`](docs/correspondence.md) — design reviews received and answered.
- [`AGENTS.md`](AGENTS.md) — working rules for this tree. [`TODO.md`](TODO.md) — what is not yet built.

## The Line Set

The current family has ten substantive instruments, their colorless cross-line
reader, and the separate Witness Register: twelve projects. The authorized
private omnibus includes eleven works and excludes Witness:

- [Black Line](https://github.com/docxology/black_line) — declared practice and evidence-label coverage
- [Golden Line](https://github.com/docxology/golden_line) — the aspiration and horizon registry
- [Red Line](https://github.com/docxology/red_line) — the cognitive-security registry of self-assessments
- [White Line](https://github.com/docxology/white_line) — the absence and omission ledger
- [Silver Line](https://github.com/docxology/silver_line) — the memory-and-succession instrument
- [Violet Line](https://github.com/docxology/violet_line) — PRIVATE consent ledger; authorized source access only
- [Blue Line](https://github.com/docxology/blue_line) — the stewardship instrument for maintained commitments
- [Green Line](https://github.com/docxology/green_line) — the capacity-under-development instrument
- [Copper Line](https://github.com/docxology/copper_line) — PRIVATE finite-resource exposure arithmetic and burden attribution
- [Iron Line](https://github.com/docxology/iron_line) — PRIVATE scenario-bound recorded recovery-target comparisons
- [The Witness Register](https://github.com/docxology/witness_register) — co-registration without aggregation

# Line Set standalone guide

Line Set is its own repository — `docxology/line_set` — as well as a project
inside the private tree it is developed in, and it runs in both. The package is
pure standard library, the sibling line packages are optional, and the tests,
the offline check battery, and the manuscript all work with none of them
present. What a separated copy cannot do on its own is typeset itself: PDF and
HTML rendering uses the separate `docxology/template` engine, which is a stated
external dependency and is never vendored here. Everything else — the suite,
`check_registry.py`, `check_set.py`, `build_figures.py`, `record_reading.py`,
and `build_omnibus.py` — runs from the clone alone.

Separation is not the hard part. Staying legible after separation is, because
this project's whole subject is a set it is no longer sitting inside. What
follows is what a separated copy must still be able to explain about itself.

## What a separated copy must still explain

**What it is.** A declaration of a set of small instruments, a reader that
reports which of them are installed and what vocabulary each publishes, and a
check that no two of them share a status token. Not a fifth instrument, not a
meta-evaluator, not a merge of the set, not a ranking of it.

**What the set is, without the siblings there to point at.** The declaration in
`src/line_set/registry.py` is self-describing: each entry carries the question
its line answers, the job it does, and the thing it must not become. A reader who
has never seen Red, Black, Golden, or White Line can learn what the set claims to
be from that file alone. Keep it that way — an entry that only makes sense by
following a link out of the tree is an entry that will not survive the move.

**Why its own status names are prefixed.** This is the property most likely to
look arbitrary after separation. A package that checks other packages for shared
status tokens has to survive that check itself; the prefixes make its
disjointness checkable, and `check_self_disjointness()` is what checks it. Detach
that explanation from the siblings' presence and it still stands on its own.

**What a reading does not establish.** `docs/claim_boundaries.md` travels with
the copy and is the first document to read. Nothing in a separated copy may
describe a reading as validation, certification, audit, or a safety property; a
digest is not tamper evidence; the versions and sizes reported are what each
sibling says about itself.

**That a sibling-free reading is honest, not broken.** With nothing importable,
`read_set()` returns `SET_PARTIAL` and `check_self_disjointness()` reports itself
unestablished. A separated copy will hit this state on the first run, and its
documentation must already say that this is the designed outcome — not a failed
install, and not a pass either.

**Where the siblings are.** `sibling_path_resolver()` looks in
`sibling_base()`, which is this project's parent directory unless
`LINE_SET_SIBLINGS` names another. In a separated copy the parent directory
usually holds nothing to do with the set, and the resolver correctly finds
nothing. A copy that does have the set somewhere says where with
`LINE_SET_SIBLINGS` rather than being relocated into a layout; a copy that does
not should say plainly that the lines are not available here. The layout is a
default, never a requirement, and the eight instruments are their own
repositories — `docxology/red_line`, `docxology/black_line`,
`docxology/golden_line`, `docxology/white_line` — which is where a copy that
wants them gets them.

**Its ancestor.** The short internal note `docs/line-set.md`, in the author's
private projects tree, is what this project grew from. It is unpublished and
does not travel with this repository, so — this copy being the separated one —
it is cited here by name rather than linked: a relative path out of the
repository root resolves to nothing for anyone holding only this repository. The
acknowledgement stays and the ancestor's prose is never pasted into the
manuscript in its place. The durable references for the set are the four
instruments' own repositories: `docxology/red_line`, `docxology/black_line`,
`docxology/golden_line`, and `docxology/white_line`.

## Clean copy

Copy the project tree, `uv.lock`, and the manuscript together. Do not copy the
template engine into the project. After copying: update `docs/manuscript/config.yaml`,
the publication metadata, and every cross-project link, then run the local
validation surface in [`docs/development.md`](docs/development.md) before
claiming the copy is sound.

## Validation after separation

The offline gates — the test suite and `scripts/check_registry.py` — are the ones
that must still pass unchanged. `scripts/check_set.py` and the two live figures
will report absence, which is the correct result and not a gate failure.

The `build_omnibus.py` volume is a further gate on separation, and it degrades
rather than raising. With no sibling beside the clone it assembles this work
alone and names those it could not find; with a sibling whose manuscript is
present but whose figures were never built it names that too, with the reason,
because this project reads other checkouts and writes to none of them. Both
outcomes exit zero and both are honest, and the omnibus corpus gates in the
suite skip with the missing works named rather than failing.

The local gates are necessary and not sufficient. Rendered PDF/HTML output must
also pass the template's validation, which needs the external engine described
in [`docs/development.md`](docs/development.md). The template's strict public
publication audit asks whether a project sits inside its own public repository,
so it reports a repository-boundary finding against a copy mirrored in from an
external projects root; that finding is about where the copy was linked from and
is not a source or manuscript defect.

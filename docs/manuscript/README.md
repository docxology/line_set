# Manuscript source

The numbered Markdown files are the source sections for *The Line Set: Holding
Instruments Apart*. Start with [`config.yaml`](config.yaml) for publication
metadata, then [`02_method.md`](02_method.md) for the declaration and the staged
reader, [`02a_formalism.md`](02a_formalism.md) for the same machinery stated as
definitions and propositions, and [`05_limits.md`](05_limits.md) for what a
reading does not establish.

Section order:

| File | Contents |
| --- | --- |
| [`00_abstract.md`](00_abstract.md) | The claim and its boundary; the measured collision result |
| [`01_introduction.md`](01_introduction.md) | Why a set of small instruments needs a checkable separation |
| [`01b_the_set.md`](01b_the_set.md) | The four lines, the shared token, and the alchemical naming with its three caveats |
| [`02_method.md`](02_method.md) | Declaration, five reader stages, fail-closed exemption matcher, eight checks, digests |
| [`02a_formalism.md`](02a_formalism.md) | The records, the matcher, the reading, the precedence rule, and the self-application, stated as definitions and propositions |
| [`02b_scholarship.md`](02b_scholarship.md) | Modularity, boundary objects, and the hazard of the index |
| [`03_extensibility.md`](03_extensibility.md) | Executed example: appending a fifth colour |
| [`04_examples.md`](04_examples.md) | Executed readings, including every status and every read code |
| [`05_limits.md`](05_limits.md) | What the reader cannot see |
| [`06_conclusion.md`](06_conclusion.md) | What the project earns |
| [`99_references.md`](99_references.md) | Bibliography anchor |

Every number in the prose is derived from the package rather than transcribed,
and `tests/test_manuscript_bindings.py` re-derives them. Sibling versions,
registry sizes, and digests appear only inside the dated reading in
[`04_examples.md`](04_examples.md); they are what the installed siblings
reported on the review date, not constants of the set.

Figures are embedded as `../output/figures/<name>.png` and are rebuilt with
`uv run python scripts/build_figures.py`. Do not hand-edit anything under
`output/`.

Read [AGENTS.md](AGENTS.md), [../README.md](../README.md), and
[../README.md](../README.md) next.

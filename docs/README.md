# Line Set documentation

Line Set declares the line set, reads whichever line packages are installed, and
checks that no two of them share a status token. It is a wrapper and a reader,
not an instrument of its own.

Start with [claim_boundaries.md](claim_boundaries.md) if you are evaluating what
this project asserts, and with [architecture.md](architecture.md) if you are
about to change it.

- [admission/decision-20261108.md](admission/decision-20261108.md) — current
  architectural admission of Copper and Iron, including the extension alternative.
- [admission/README.md](admission/README.md) — historical no-addition decision,
  dossier, hypothetical contrast cases, unexecuted protocol and owner requirements.
- [evidence/README.md](evidence/README.md) — optional versioned evidence/replay
  companion convention; no native exporter or evaluator in this package.

- [claim_boundaries.md](claim_boundaries.md) — what a reading does and, at
  length, does not establish; the meaning of each status; the evidence classes.
- [architecture.md](architecture.md) — module map, the five reader stages,
  status precedence, the resolver seam, the self-application property, and
  digest semantics.
- [invariants.md](invariants.md) — the offline structural battery, the live
  self-disjointness check, the proof-of-detection discipline, and the rule that
  an empty scan set fails.
- [extensibility.md](extensibility.md) — the exact recipe for adding a color,
  with an executed example, and the list of files it does and does not touch.
- [development.md](development.md) — the local command surface, what each
  command needs, figures, and the render path.
- [envelope.md](envelope.md) — the set-wide report envelope convention
  (`line.report-envelope/1.0`): the shape the instruments publish, alignment
  by convention rather than import, and why the shared string is invisible to
  the collision scan.
- [correspondence.md](correspondence.md) — external design reviews received
  and what this repository did about each.
- [publication.md](publication.md) — how to cite, the DOI discipline, and the
  reserve-first workflow.
- [releases/v0.7.0.md](releases/v0.7.0.md) — completed Copper/Iron integration packet; current 0.8.0 source changes are in [the changelog](../CHANGELOG.md).
- [releases/README.md](releases/README.md) — current and historical release packets.

The declaration lives in [`../src/line_set/registry.py`](../src/line_set/registry.py),
the staged reader in [`../src/line_set/reader.py`](../src/line_set/reader.py),
the checks in [`../src/line_set/invariants.py`](../src/line_set/invariants.py),
and the single sibling-import seam in
[`../src/line_set/binding.py`](../src/line_set/binding.py). The package contract
is [`../src/line_set/AGENTS.md`](../src/line_set/AGENTS.md); repository working
rules are [`../AGENTS.md`](../AGENTS.md).

This project's ancestor is `docs/line-set.md`, a short internal note in the
author's private projects tree that first recorded the set, its colors, and its
non-overlap contract. It is unpublished and does not travel with this
repository, so it is named rather than linked. It stays as the short map; this
project is the paper. The durable references for the declared instruments are their
own repositories: [red_line](https://github.com/docxology/red_line),
[black_line](https://github.com/docxology/black_line),
[golden_line](https://github.com/docxology/golden_line),
[white_line](https://github.com/docxology/white_line),
[silver_line](https://github.com/docxology/silver_line),
[violet_line](https://github.com/docxology/violet_line) (PRIVATE),
[blue_line](https://github.com/docxology/blue_line),
[green_line](https://github.com/docxology/green_line),
[copper_line](https://github.com/docxology/copper_line) (PRIVATE), and
[iron_line](https://github.com/docxology/iron_line) (PRIVATE). Private repository
references require authorized source access. Current questions and nonclaims are
declared in the registry, not inferred from repository accessibility.

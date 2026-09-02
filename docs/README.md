# Line Set documentation

Line Set declares the line set, reads whichever line packages are installed, and
checks that no two of them share a status token. It is a wrapper and a reader,
not an instrument of its own.

Start with [claim_boundaries.md](claim_boundaries.md) if you are evaluating what
this project asserts, and with [architecture.md](architecture.md) if you are
about to change it.

- [claim_boundaries.md](claim_boundaries.md) — what a reading does and, at
  length, does not establish; the meaning of each status; the evidence classes.
- [architecture.md](architecture.md) — module map, the five reader stages,
  status precedence, the resolver seam, the self-application property, and
  digest semantics.
- [invariants.md](invariants.md) — the offline structural battery, the live
  self-disjointness check, the proof-of-detection discipline, and the rule that
  an empty scan set fails.
- [extensibility.md](extensibility.md) — the exact recipe for adding a colour,
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
- [releases/v0.1.0.md](releases/v0.1.0.md) — the release packet with gate
  results, artifacts, and tag name.

The declaration lives in [`../src/line_set/registry.py`](../src/line_set/registry.py),
the staged reader in [`../src/line_set/reader.py`](../src/line_set/reader.py),
the checks in [`../src/line_set/invariants.py`](../src/line_set/invariants.py),
and the single sibling-import seam in
[`../src/line_set/binding.py`](../src/line_set/binding.py). The package contract
is [`../src/line_set/AGENTS.md`](../src/line_set/AGENTS.md); repository working
rules are [`../AGENTS.md`](../AGENTS.md).

This project's ancestor is `docs/line-set.md`, a short internal note in the
author's private projects tree that first recorded the set, its colours, and its
non-overlap contract. It is unpublished and does not travel with this
repository, so it is named rather than linked. It stays as the short map; this
project is the paper. The durable references for the eight instruments are their
own repositories: [red_line](https://github.com/docxology/red_line),
[black_line](https://github.com/docxology/black_line),
[golden_line](https://github.com/docxology/golden_line),
[white_line](https://github.com/docxology/white_line),
[silver_line](https://github.com/docxology/silver_line),
[violet_line](https://github.com/docxology/violet_line),
[blue_line](https://github.com/docxology/blue_line), and
[green_line](https://github.com/docxology/green_line).

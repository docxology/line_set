# Worked readings {#sec:examples}

## The pinned source reading

This reading was taken on 2026-10-21 using `sibling_path_resolver` against read-only Git clones. Released lines were read at their tags; Red was read at its current `origin/main` after the dispatcher stopped its release wait following an engine infrastructure timeout. The source revisions below identify the bytes read; the release packet identifies each source policy and the artifact checksums. All declared vocabularies were readable. This is a namespace reading, not verification of sibling conclusions. The previous environment's record remains unchanged in `docs/releases/evidence/reading-record-20260901-v1.json`.

```python
from line_set import read_set, sibling_path_resolver

reading = read_set(resolver=sibling_path_resolver(), as_of="2026-10-21")
```

```text
status        : set_legible
set_digest    : de4bd085666ef66ff73aaa934cc94946530df33ad8d35d69669d514e9dcf6140
reading_digest: d6c2743319f69cae
counts        : {'resolved': 8, 'not_installed': 0, 'import_failed': 0, 'no_vocabulary': 0}
  black_line   resolved v0.5.0 registry=11 digest=a02bff47a767 tokens=10
  blue_line    resolved v0.2.0 registry=12 digest=9ae7cae1f0f7 tokens=8
  golden_line  resolved v0.5.0 registry=9 digest=3e0a7e38ecec tokens=7
  green_line   resolved v0.2.0 registry=11 digest=2d40bfefb9a5 tokens=10
  red_line     resolved v0.3.0 registry=7 digest=72835fd81d1f tokens=40
  silver_line  resolved v0.2.0 registry=11 digest=30711e134eec tokens=12
  violet_line  resolved v0.2.0 registry=8 digest=6494a6bcafbd tokens=16
  white_line   resolved v0.8.0 registry=11 digest=11047a641a8e tokens=24
  [resolve] asked the resolver for 8 declared packages
  [bind] read version, registry size, digest, and enum member names from each package that resolved
  [collide] 0 unexempted and 8 exempted cross-line token collisions
  [declare] scanned 8 candidate packages and found 0 that resolved but were not declared
  [status] set_legible: no unexempted published-name collisions among all 8 declared readable vocabularies; 8 declared exemption(s)
```

| Package | Reported version | Source revision | Binding policy |
| --- | --- | --- | --- |
| black_line | 0.5.0 | `79056aacf0f86b4287322dd5dced9d301882cb03` | convention-heuristic |
| blue_line | 0.2.0 | `15ef8043833fd790e0d52a8fa47289905e4d867f` | convention-heuristic |
| golden_line | 0.5.0 | `23095f7f9759a3027e5ceb8380310d54c87cd977` | convention-heuristic |
| green_line | 0.2.0 | `e05007f9858bb55194b0d867aed7bed7d51777e2` | convention-heuristic |
| red_line | 0.3.0 | `375e8ae9b7a111bcdb66f0ba33872c078083983c` | convention-heuristic |
| silver_line | 0.2.0 | `3ff05b23a6a59c0f68b7a11e4cd70696f321fe0d` | convention-heuristic |
| violet_line | 0.2.0 | `4bb20dbdc1c2df6cd505faee0b9729979d3892bd` | convention-heuristic |
| white_line | 0.8.0 | `869aaab63c37aa118f469497cb513cf29697acda` | convention-heuristic |

The eight packages export 34 enum classes between them — 7 in red_line, 3 in black_line, 2 in golden_line, 7 in white_line, 4 in silver_line, 5 in violet_line, 3 in blue_line, 3 in green_line — and those classes declare 148 members in total, including aliases. Ordinary enum iteration reaches 148 canonical members; root re-exports of one class are counted once. 21 of the 148 are a line repeating a word it already uses in another enum: red_line repeats one name across its seven enum classes; black_line repeats three names across its three enum classes; white_line repeats four names across its seven enum classes; silver_line repeats four names across its four enum classes; violet_line repeats three names across its five enum classes; blue_line repeats three names across its three enum classes; green_line repeats three names across its three enum classes. After that within-line collapse, the reading holds 127 line-and-name pairs — 40 for red_line, 10 for black_line, 7 for golden_line, 24 for white_line, 12 for silver_line, 16 for violet_line, 8 for blue_line, 10 for green_line — spanning 115 distinct names.

The arithmetic is the whole finding: 127 minus 115 is twelve. The shared spellings are `COMMUNICATION`, `KEPT`, `METHOD`, `NEEDS_REWORK`, `OUTSIDE_SCOPE`, `STALE`, `STEWARDSHIP`, `VERIFICATION`. There are 8 exempted collisions and 0 unexempted collisions; the record retains each exemption's exact carrier set and per-line meanings. Disjoint spellings do not establish distinct concepts.

![Vocabulary matrix: every published name, including aliases, with observed carrier positions keyed to declared lines. Rows distinguish declared exemptions from unexempted collisions using shape and label. Unread lines remain unknown.](../../output/figures/vocabulary_matrix.png){#fig:vocabulary-matrix width=100%}

## Additional carriers and discovery

The isolated real-package regressions in `tests/test_reader.py` and `tests/test_review_regressions.py` exercise `set_colliding` when an additional carrier makes an exemption's exact set cease to match. No exemption stretches to cover a new party. A missing declared carrier is also retained as uncertainty; collision precedence remains conservative rather than shrinking the exemption.

The tests also produce `set_undeclared` for an importable candidate outside the declaration. Discovery follows the resolver's convention, not an exhaustive search. Capability, attempt, completion and candidate failures travel as structured data. A failed generator after its first yield retains that yield without claiming a completed scan. No enumerator and a completed zero-hit enumeration are different records even when their namespace status agrees.

## Lines that will not read

Real temporary packages and plain resolver callables produce `set_partial` for absence, failed import and unavailable vocabulary. `NO_VOCABULARY` preserves whatever version or registry metadata was actually read. `NOT_INSTALLED` and `IMPORT_FAILED` leave version, size and digest unset. No missing value becomes zero. Process-control exceptions propagate; in-process imports execute package code and have no sandbox or hanging-import guarantee.

The eight offline checks pass with no sibling installed because they inspect the declaration. The live self-disjointness check fails when no vocabulary is available to compare. An empty scan cannot establish separation. The release's absent-sibling test lane exercises this outcome separately from its pinned integration lane.

![Installation surface: one row per declared line, reporting the observed version, registry size and digest. Missing metadata remains visibly absent.](../../output/figures/installation_surface.png){#fig:installation-surface width=100%}

## A weakened exemption

The production matcher refuses missing meanings, blank rationale, mismatched carrier sets and duplicate declarations. The full-table mutation suite executes the named controls for every shipped exemption, including later table entries; its matrix is a finite demonstration, not proof against every possible malformed declaration. A declaration cannot establish its own conceptual distinction merely by spelling out two meanings. That remains a human review boundary.

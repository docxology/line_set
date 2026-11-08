# Worked readings {#sec:examples}

## Historical eight-line 0.6.1 measurement and public view

The following retained transcript and census describe the eight-line 0.6.1 source refresh, not the expanded declaration. They are preserved rather than relabeled as a ten-line run. A new current reading requires final actual native snapshots and parent-generated records. For that cutover, use all three withholding options (`violet_line`, `copper_line`, `iron_line`) after complete pinned admission; keep the full record private. New binding policies, counts, and identities must come from the actual new record, never from these historical values.

This measurement uses an explicit review date of 2026-11-08 against eight immutable current producer commits, including Golden 0.6.1. Each captured source's regular-file bytes match its actual Git revision and tree, not merely a caller-supplied SHA label. All eight used convention-heuristic binding with `pinned-source-snapshot` provenance. The public `2.0-public` view withholds Violet's private producer revision and module path after complete pinned admission; the full current and initial working-source records remain in private custody. This is a namespace reading, not verification of sibling conclusions or native report correspondence. Previously public historical records remain under `docs/releases/evidence/`.

The patch source refresh remeasures all eight actual immutable captures instead of swapping source labels in an old record. The preceding final 0.6.0 public record remains byte-identical at `docs/releases/evidence/reading-record-v0.6.0-final-public.json`. Earlier source-closure and preparation records remain unchanged at `docs/releases/evidence/reading-record-20261106-pre-final-source-closure-public.json` and `docs/releases/evidence/reading-record-20261106-pre-source-refresh-public.json`. A matching vocabulary census does not make different source snapshots interchangeable.

The following display summarizes the public JSON view. Select the authorized snapshot parent through `LINE_SET_SIBLINGS`; an ordinary, unpinned checkout cannot produce the underlying canonical record. Replaying this public view verifies its disclosed measurement and digest, not a complete public source-pin proof or continuity of a withheld revision.

```python
from line_set.recording import build_record

record, refusals = build_record("2026-11-08", withheld_sources=("violet_line",))
```

```text
status        : set_legible
set_digest    : 018f930a14597e85403beb1397987b2b07865f3327e37a37ab7135817136dd1e
reading_digest: ad3c65376f807815
counts        : {'resolved': 8, 'not_installed': 0, 'import_failed': 0, 'no_vocabulary': 0}
  black_line   resolved v0.6.0 registry=11 digest=a02bff47a767 tokens=10
  blue_line    resolved v0.3.0 registry=12 digest=9ae7cae1f0f7 tokens=8
  golden_line  resolved v0.6.1 registry=9 digest=3e0a7e38ecec tokens=7
  green_line   resolved v0.3.0 registry=11 digest=7be6d699bb36 tokens=10
  red_line     resolved v0.5.0 registry=7 digest=72835fd81d1f tokens=41
  silver_line  resolved v0.3.0 registry=11 digest=ce808709c7db tokens=12
  violet_line  resolved v0.3.0 registry=8 digest=d049774c40e6 tokens=16
  white_line   resolved v0.9.0 registry=11 digest=11047a641a8e tokens=24
  [resolve] asked the resolver for 8 declared packages
  [bind] read version, registry size, digest, and enum member names from each package that
    resolved
  [collide] 0 unexempted and 8 exempted cross-line token collisions
  [declare] scanned 8 candidate packages and found 0 that resolved but were not declared
  [status] set_legible: no unexempted published-name collisions among all 8 declared
    readable vocabularies; 8 declared exemption(s)
```

| Package | Reported version | Source revision | Binding policy |
| --- | --- | --- | --- |
| black_line | 0.6.0 | `97961f6621e86359bf3bb6436ce6049f2644642d` | convention-heuristic |
| blue_line | 0.3.0 | `03b71534f9024f098fbf0afe05dbd80e1d75587a` | convention-heuristic |
| golden_line | 0.6.1 | `5a10c8799c1097b7b7e2876932307bcce676df66` | convention-heuristic |
| green_line | 0.3.0 | `3edf49f5426a2c9dfa8c925846d318476206988d` | convention-heuristic |
| red_line | 0.5.0 | `3fa8d9a68a435384f53abc4afeb7ad462b133adb` | convention-heuristic |
| silver_line | 0.3.0 | `51f54d8cc5f44938f3b537ebbcb42536fe36f5c1` | convention-heuristic |
| violet_line | 0.3.0 | Withheld; private producer custody | convention-heuristic |
| white_line | 0.9.0 | `5ab6c8e0c3c5f8d7fc3dd57a4cd3f519afd36dce` | convention-heuristic |

The eight packages export 34 enum classes between them — 7 in red_line, 3 in black_line, 2 in golden_line, 7 in white_line, 4 in silver_line, 5 in violet_line, 3 in blue_line, 3 in green_line — and those classes declare 149 members in total, including aliases. Ordinary enum iteration reaches 149 canonical members; root re-exports of one class are counted once. Twenty-one of the 149 are a line repeating a word it already uses in another enum: red_line repeats one name; black_line repeats three; white_line repeats four; silver_line repeats four; violet_line repeats three; blue_line repeats three; green_line repeats three. After that within-line collapse, the reading holds 128 line-and-name pairs — 41 for red_line, 10 for black_line, 7 for golden_line, 24 for white_line, 12 for silver_line, 16 for violet_line, 8 for blue_line, 10 for green_line — spanning 116 distinct names.

The arithmetic is the whole finding: 128 minus 116 is twelve. The shared spellings are `COMMUNICATION`, `KEPT`, `METHOD`, `NEEDS_REWORK`, `OUTSIDE_SCOPE`, `STALE`, `STEWARDSHIP`, `VERIFICATION`. There are 8 exempted collisions and 0 unexempted collisions; the record retains each exemption's exact carrier set and per-line meanings. Disjoint spellings do not establish distinct concepts.

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

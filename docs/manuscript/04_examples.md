# Worked readings {#sec:examples}

## Ten-line 0.8.0 pinned measurement and public view

The 2026-11-10 measurement reads all ten actual native-qualified producer commits from immutable Git-archive captures whose regular-file bytes match their recorded commits and trees. These are real reviewed source commits, not predicted release tags. Eight producers use `convention-heuristic` binding; Copper and Iron use their explicit `line-set-binding/1` descriptors. All ten use `pinned-source-snapshot` provenance. This measures the exported namespace, not native report correctness, practical usefulness, or conceptual independence.

The public `2.0-public` record withholds Violet, Copper, and Iron producer revisions and module paths only after complete pinned admission. The complete `2.0` record remains private. The current public reading digest is `c5b88c6b8aff271bff4f6b4d9c57f6eb1e0a8a97ab7a9e0e68817c8c52cc05f9`; the declaration digest is `73b407e1fe8a84c03412453cd1bab6e89f78530e55011728f628dca4d90446f9`. The seven disclosed source revisions, full vocabulary, exact exemption carrier sets, and per-line meanings are retained in `reading_record.json`.

Select the authorized source-capture parent through `LINE_SET_SIBLINGS` before reproducing the reading. Missing sources refuse canonical recording; they never become empty vocabularies or zero metadata. The executed full/private and public checks match their own artifacts, and both wrong-view substitutions are refused. A successful public-view check is not complete public source-pin proof or continuity proof for a withheld source.

The current captures use publishable producer commits with privacy-safe attribution. Changing a disclosed source revision changes the reading identity even when the vocabulary census is unchanged. The native recorder refused the earlier candidate record against these new revisions before producing and checking the new record; earlier candidate and historical records were not relabeled.

```python
from line_set.recording import build_record

record, refusals = build_record(
    "2026-11-10",
    withheld_sources=("violet_line", "copper_line", "iron_line"),
)
```

| Package | Reported version | Root enum classes | Declared members | Distinct per-line names |
| --- | --- | ---: | ---: | ---: |
| red_line | 0.5.2 | 7 | 42 | 41 |
| black_line | 0.6.2 | 3 | 13 | 10 |
| golden_line | 0.7.0 | 2 | 7 | 7 |
| white_line | 0.9.2 | 7 | 28 | 24 |
| silver_line | 0.5.0 | 4 | 16 | 12 |
| violet_line | 0.4.0 | 5 | 19 | 16 |
| blue_line | 0.3.2 | 3 | 11 | 8 |
| green_line | 0.5.0 | 3 | 13 | 10 |
| copper_line | 0.2.0 | 6 | 21 | 21 |
| iron_line | 0.2.0 | 3 | 15 | 15 |
| Total | — | 43 | 185 | 164 line-and-name pairs |

Ordinary enum iteration reaches all 185 canonical members; root re-exports of one class are counted once. Removing 21 within-line repetitions leaves the 164 line-and-name pairs shown above. Collapsing twelve additional cross-line repetitions leaves 152 globally distinct spellings. Copper and Iron introduce no within-line repeats and no new shared-name carrier. The shared spellings remain `COMMUNICATION`, `KEPT`, `METHOD`, `NEEDS_REWORK`, `OUTSIDE_SCOPE`, `STALE`, `STEWARDSHIP`, and `VERIFICATION`: eight exact exemptions, all fully observed, and zero unexempted collisions. These are name facts, not proof that the underlying concepts do not overlap.

The preceding ten-line 0.7.0 record remains byte-identical in [its historical public artifact](https://github.com/docxology/line_set/blob/main/docs/releases/evidence/reading-record-v0.7.0-ten-line-public.json), with [its original manuscript section](https://github.com/docxology/line_set/blob/main/docs/releases/evidence/manuscript-v0.7.0-ten-line/04_examples.md). Equal census values do not make its producer identities interchangeable with this new capture.

The preceding eight-line 0.6.1 record remains byte-identical in [its historical public artifact](https://github.com/docxology/line_set/blob/main/docs/releases/evidence/reading-record-v0.6.1-eight-line-public.json); its original worked reading and transcript are preserved in [the original manuscript section](https://github.com/docxology/line_set/blob/main/docs/releases/evidence/manuscript-v0.6.1-eight-line/04_examples.md). Earlier four/eight-line records and source-closure artifacts remain under `docs/releases/evidence/`. None has been relabeled as this ten-line measurement, and equal census values never make different source captures interchangeable.

![Vocabulary matrix: every published name, including aliases, with observed carrier positions keyed to declared lines. Rows distinguish declared exemptions from unexempted collisions using shape and label. Unread lines remain unknown.](../../output/figures/vocabulary_matrix.png){#fig:vocabulary-matrix width=100%}

## Additional carriers and discovery

The isolated real-package regressions in `tests/test_reader.py` and `tests/test_review_regressions.py` exercise `set_colliding` when an additional carrier makes an exemption's exact set cease to match. No exemption stretches to cover a new party. A missing declared carrier is also retained as uncertainty; collision precedence remains conservative rather than shrinking the exemption.

The tests also produce `set_undeclared` for an importable candidate outside the declaration. Discovery follows the resolver's convention, not an exhaustive search. Capability, attempt, completion and candidate failures travel as structured data. A failed generator after its first yield retains that yield without claiming a completed scan. No enumerator and a completed zero-hit enumeration are different records even when their namespace status agrees.

## Lines that will not read

Real temporary packages and plain resolver callables produce `set_partial` for absence, failed import and unavailable vocabulary. `NO_VOCABULARY` preserves whatever version or registry metadata was actually read. `NOT_INSTALLED` and `IMPORT_FAILED` leave version, size and digest unset. No missing value becomes zero. Process-control exceptions propagate; in-process imports execute package code and have no sandbox or hanging-import guarantee.

The eight offline checks pass with no sibling installed because they inspect the declaration. The live self-disjointness check fails when no vocabulary is available to compare. An empty scan cannot establish separation. The release's absent-sibling test lane exercises this outcome separately from its pinned integration lane.

![Installation surface: one card per declared line in two columns. Each card pairs its line and read code with version, registry size, token count, and digest-prefix fields. Missing metadata remains visibly absent.](../../output/figures/installation_surface.png){#fig:installation-surface width=100%}

## A weakened exemption

The production matcher refuses missing meanings, blank rationale, mismatched carrier sets and duplicate declarations. The full-table mutation suite executes the named controls for every shipped exemption, including later table entries; its matrix is a finite demonstration, not proof against every possible malformed declaration. A declaration cannot establish its own conceptual distinction merely by spelling out two meanings. That remains a human review boundary.

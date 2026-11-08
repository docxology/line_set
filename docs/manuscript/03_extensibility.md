# Extensibility: adding a color is an edit to one file {#sec:extensibility}

The set has grown before and may grow again, so the cost of adding a line is a design property rather than a convenience. The target is that a new color costs one appended record in `registry.py` ([@def:line-entry]) and nothing else: no branch in the reader, no case in a check, no new figure code.

Cheap registration is not conceptual admission. The 2026-11-08 decision adds
Copper and Iron by explicit architectural choice; typed existing-native
extensions remain credible alternatives, and no empirical admission study is
claimed. Contestation/repair and Titanium remain unadmitted. A renamed instrument
can avoid every token collision and still duplicate another instrument's question.

Parnas treats extension and contraction as one problem and locates their cost in the *uses* relation [@parnas1979extension]. His program families and documented uses relations set a stronger standard than this small wrapper. Here I exercise a bounded observable property: the existing reader, checks and figures accept a distinct appended declaration without an instrument-specific implementation branch. This does not measure every possible caller or establish a useful new question.

The evidence is behavioral rather than a word-count scan of source files. Temporary packages expose distinct vocabularies; the extended reading retains all known entries and reports the missing appended package explicitly. Display maps may choose an ink or outline, but they do not interpret an instrument's result.

## The executable isolated example

The following recorded output and nine-entry discussion retain the executed
2026-11-06 eight-to-nine teal example. The code uses the current declaration when
run again, so its new output must be measured rather than hand-repinned. The old
transcript is not a ten-to-eleven run or current collision proof.

The hypothetical teal entry is bookkeeping test material, not an admission
proposal or a new member of the set. Its identifier and color are fixed
examples, currently unused; its working position is derived from the
declaration. The fixture reading below is separate from the preserved
historical sibling record and from the current pinned release reading.

```python
from tempfile import TemporaryDirectory
from pathlib import Path
from line_set import LINE_SET, SHARED_TOKENS, all_invariants, read_set, registry_digest
from tests.test_extensibility import APPENDED
from tests.support import (
    canned_resolver, import_sandbox, load_line_package, resolved, write_line_package,
)

extended = LINE_SET + (APPENDED,)
print("lines:", len(LINE_SET), "->", len(extended))
print("digest:", registry_digest(LINE_SET, SHARED_TOKENS)[:12],
      "->", registry_digest(extended, SHARED_TOKENS)[:12])
for result in all_invariants(extended, SHARED_TOKENS):
    print(f"  {'PASS' if result.passed else 'FAIL'}  {result.name}")
with TemporaryDirectory() as directory, import_sandbox():
    root = Path(directory)
    answers = {}
    for index, entry in enumerate(LINE_SET):
        write_line_package(root, entry.package_name, (f"TOKEN_{index}",))
        answers[entry.package_name] = resolved(
            entry.package_name, load_line_package(root, entry.package_name))
    reading = read_set(extended, SHARED_TOKENS,
                       resolver=canned_resolver(answers), as_of="2026-11-06")
print("status:", reading.status.value)
print("counts:", reading.counts())
print("reason:", reading.derivation[-1].detail)
assert all(result.passed for result in all_invariants(extended, SHARED_TOKENS))
assert reading.counts()["resolved"] == len(LINE_SET)
assert reading.counts()["not_installed"] == 1
```

This output was reproduced for the 2026-11-06 review using the exact code above.
Its injected resolver reads real temporary packages and explicitly leaves the
hypothetical entry absent; installed siblings cannot change that fixture.
It is namespace evidence, not a native sibling measurement or a pinned record.
The shorter recipe in `docs/extensibility.md` exercises the same contract.

The measured fixture output:

```text
lines: 8 -> 9
digest: 018f930a1459 -> e60aafda008d
  PASS  declaration_admission
  PASS  distinct_line_ids
  PASS  distinct_colors
  PASS  distinct_opus_stages
  PASS  contiguous_working_positions
  PASS  orders_diverge
  PASS  must_not_become_declared
  PASS  shared_tokens_disambiguated
status: set_partial
counts: {'resolved': 8, 'not_installed': 1, 'import_failed': 0, 'no_vocabulary': 0}
reason: set_partial: 1 declared line(s) could not be read: ['teal_line']
```

All eight structural checks pass on the nine-entry declaration. Position contiguity now expects `1..9` and gets it. Color distinctness has a ninth color to consider. The orders still diverge, because the appended entry declares no opus stage and is therefore ignored by that comparison — a line may join the set without being assigned a stage, and the set has in fact grown past four while the four borrowed stage names stayed exactly four.

The wrapper's own collision check ([@prop:self-disjointness]) applies to any extended declaration.

The reading is `SET_PARTIAL`, and that is the correct answer rather than a shortfall. I declared a line whose package does not exist on this machine, and the reader said so, named it, and left its version, registry size, and digest unset. It did not invent a version, and it did not quietly drop an entry it could not resolve. A declaration that runs ahead of an installation is an ordinary state — it is what the first commit of a new line looks like — and the reader is built to report it rather than to fail.

## What the digest change means

The fixture's digest changes from `018f930a1459` to `e60aafda008d`: the declaration and exemption table together identify a different set. Rewording an entry's question also changes the digest; membership alone is not the identity being compared.

The value is a comparison handle and nothing more. It tells you that a declaration you hold differs from a declaration someone else holds. It does not tell you which one is right, it does not record who changed what, and it is not tamper evidence.

## What this does not establish

What the run above shows is that the declaration is extensible without touching the reader or the checks: the battery passed on the nine-entry declaration, the reading was taken, and no module outside `registry.py` was edited to make either happen. Two nearby claims are not shown and should not be read in.

Adding a color is cheap in code. It is not cheap in judgment: the hard part of another line is deciding whether the set actually has another question, and nothing in this package can help with that. A line whose question overlaps an existing line's would pass every check here, because the checks read names.

Figure builders also accept the appended fixture. Labels remain authoritative, and the current outlines distinguish the declared members and wrapper; the extension regression additionally compares actual glyph geometry. The outline cycle is finite, so larger declarations can repeat a shape. A produced plate is not proof of unbounded capacity, legibility at an arbitrary embed size, or readability in physical grayscale print.

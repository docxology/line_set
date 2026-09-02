# Extensibility: adding a colour is an edit to one file {#sec:extensibility}

The set has grown before and will grow again, so the cost of adding a line is a design property rather than a convenience. The target is that a new colour costs one appended record in `registry.py` ([@def:line-entry]) and nothing else: no branch in the reader, no case in a check, no new figure code.

Parnas treats extension and contraction as one problem and puts the cost of both in the *uses* relation rather than in the size of the edit: what makes a subset removable, or an addition cheap, is that nothing outside it names it [@parnas1979extension]. That is the property claimed here, and it is claimed narrowly. He is designing families of programs whose minimal subsets are chosen in advance and whose uses relation is documented and enforced; I have one package, and the only uses relation I have measured is which modules mention a line id as a whole word. Those are different standards of evidence for the same-shaped claim, and the second is the one this section supports.

The claim holds because no module outside `registry.py` names an individual line. Every function that does work takes `lines` and `shared` as arguments and computes over whatever it was handed. Searching the package for the eight line ids as whole words finds them only in `registry.py`, four and fourteen and two and four and eight and four and six and fourteen times; `reader.py`, `invariants.py`, `binding.py`, `serialization.py`, `models.py`, and `__init__.py` contain none of them. One mention of `OUTSIDE_SCOPE` survives in `reader.py`, inside the exemption matcher's docstring, where it is the worked example of a substring the matcher must refuse. It is prose, not a branch.

## The executed example

Here is a further colour, appended at runtime and put through the whole battery. Nothing in the package was edited to run it.

```python
from line_set import (LINE_SET, SHARED_TOKENS, LineEntry, all_invariants,
                      read_set, registry_digest, sibling_path_resolver)

fifth = LineEntry(
    id="teal_line",
    color="teal",
    question="What does keeping this alive cost?",
    job="Standing upkeep, dependencies, and the bill for continued existence",
    must_not_become="A reason to drop work that is merely expensive",
    opus_stage=None,
    working_position=9,
    package_name="teal_line",
    registry_noun="upkeep records",
    verdict_noun="upkeep status",
)
extended = LINE_SET + (fifth,)

print("lines:", len(LINE_SET), "->", len(extended))
print("digest:", registry_digest(LINE_SET, SHARED_TOKENS)[:12],
      "->", registry_digest(extended, SHARED_TOKENS)[:12])
for r in all_invariants(extended, SHARED_TOKENS):
    print(f"  {'PASS' if r.passed else 'FAIL'}  {r.name}")
reading = read_set(extended, SHARED_TOKENS,
                   resolver=sibling_path_resolver(), as_of="2026-09-01")
print("status:", reading.status.value)
print("counts:", reading.counts())
print("reason:", reading.derivation[-1].detail)
```

The measured output:

```text
lines: 8 -> 9
digest: 7b7e70b70c5c -> 81d9e7d415d0
  PASS  distinct_line_ids
  PASS  distinct_colours
  PASS  distinct_opus_stages
  PASS  contiguous_working_positions
  PASS  orders_diverge
  PASS  must_not_become_declared
  PASS  shared_tokens_disambiguated
status: set_partial
counts: {'resolved': 8, 'not_installed': 1, 'import_failed': 0, 'no_vocabulary': 0}
reason: set_partial: 1 declared line(s) could not be read: ['teal_line']
```

All seven structural checks pass on the nine-entry declaration. Position contiguity now expects `1..9` and gets it. Colour distinctness has a ninth colour to consider. The orders still diverge, because the appended entry declares no opus stage and is therefore ignored by that comparison — a line may join the set without being assigned a stage, and the set has in fact grown past four while the four borrowed stage names stayed exactly four.

The wrapper's own collision check ([@prop:self-disjointness]) applies to any extended declaration.

The reading is `SET_PARTIAL`, and that is the correct answer rather than a shortfall. I declared a line whose package does not exist on this machine, and the reader said so, named it, and left its version, registry size, and digest unset. It did not invent a version, and it did not quietly drop an entry it could not resolve. A declaration that runs ahead of an installation is an ordinary state — it is what the first commit of a new line looks like — and the reader is built to report it rather than to fail.

## What the digest change means

The set digest moved from `7b7e70b70c5c` to `81d9e7d415d0`. That is the intended behaviour: the digest covers the lines and the exemption table together, so a set with a fifth line is a different set. It is also worth noticing that the digest binds to the *content* of the entry and not merely to its presence. Rewording the fifth line's question produces a different digest, which is what makes the value useful for spotting that two people are reading different declarations.

The value is a comparison handle and nothing more. It tells you that a declaration you hold differs from a declaration someone else holds. It does not tell you which one is right, it does not record who changed what, and it is not tamper evidence.

## What this does not establish

What the run above shows is that the declaration is extensible without touching the reader or the checks: the battery passed on five entries, the reading was taken, and no module outside `registry.py` was edited to make either happen. Two nearby claims are not shown and should not be read in.

Adding a colour is cheap in code. It is not cheap in judgement: the hard part of a fifth line is deciding whether the set actually has a fifth question, and nothing in this package can help with that. A line whose question overlaps an existing line's would pass every check here, because the checks read names.

The same requirement is placed on the figure builders — they draw from the declaration rather than from a fixed list of four, and a test appends a colour and re-renders to hold them to it. A passing render is a weaker result than it sounds. It says the plate was produced, not that it is still readable at five entries, or at nine.

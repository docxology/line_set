# Invariants and proof of detection

`src/line_set/invariants.py` holds the structural checks over the declaration
plus one live self-check. Each returns a frozen
`SoundnessResult(name, passed, detail)`. `all_invariants()` runs the offline
battery, `live_invariants()` adds the self-check, and `registry_sound()`
collapses the offline battery to a boolean.

These checks establish that the declaration is **well formed**. They establish
nothing about whether it is well chosen. A declaration with distinct ids,
contiguous positions, and a stated must-not-become for every entry can still
describe a set of instruments nobody needed; see
[claim_boundaries.md](claim_boundaries.md).

## The offline battery

Pure computation over `lines` and `shared`. It imports no sibling and returns
identical results whether or not any line package is installed.

| Check | What breakage it detects | Planted-bad input |
| --- | --- | --- |
| `distinct_line_ids` | A duplicate id, which makes every observation about that id ambiguous. | Two entries sharing one `id`. |
| `distinct_colours` | A duplicate colour, which is how a line is named in prose and figures. | Two entries sharing one `color`. |
| `distinct_opus_stages` | A stage claimed twice, or a name that is not an opus stage at all. `None` is allowed and ignored, but a declaration where *no* entry carries a stage reports that distinctness is unestablished rather than passing. | An entry re-using `rubedo`; an entry claiming an invented stage. |
| `contiguous_working_positions` | Positions that are not exactly `1..N` — a gap, a duplicate, or a stale number left behind by a removal. | An entry renumbered off the end of the sequence. |
| `orders_diverge` | Working order and opus order having become the same order, which would make the set read as a re-enactment of the opus. | Every entry renumbered into opus order. |
| `must_not_become_declared` | An entry with no stated drift, which means it has no stated boundary — and the set's separation is exactly those boundaries. | An entry whose `must_not_become` is blank. |
| `shared_tokens_disambiguated` | An exemption the live matcher would not honour, one naming a line that is not declared, or one with no recorded rationale. | An exemption missing a per-line meaning; an exemption naming a third line; an empty exemption table. |

Two of these deserve a note.

**`orders_diverge` pins a claim rather than catching a typo.** The set says the
working order is chosen for how the instruments support the work and that it
deliberately does not line up with the opus order. That is a claim in the prose,
and this check is what keeps it true by construction instead of true by
assertion. Measured today, working order is
`['red_line', 'black_line', 'golden_line', 'white_line']` and opus order is
`['black_line', 'white_line', 'golden_line', 'red_line']`.

**`shared_tokens_disambiguated` calls the production matcher.** It asserts that
`exemption_for(shared, token.token, token.lines)` returns the very object it was
given, rather than re-deriving the matching rules. A check that re-implemented
the rules would be a second copy free to drift away from the one the reader
actually uses, and the drift would be invisible because both would be green.

An empty exemption table **fails** this check. That is the uncomfortable
direction and it is chosen deliberately: a table empty because no exemption is
needed and a table empty because it was accidentally cleared look identical from
inside the check, and only one of them is fine. A set with genuinely no shared
tokens should say so where a person reads it, not by leaving the table blank.

## The live check

`check_self_disjointness(lines, shared, *, wrapper=WRAPPER_LINE, resolver=None,
as_of=None)` is different in kind. It appends this package's own entry to the
declaration, runs the ordinary reader over the result, and asks whether any of
this package's tokens turned up in a collision.

This is the property the project exists to hold. A package that checks other
packages for shared status tokens must survive that check itself, which is why
`SetStatus` and `ReadCode` are prefixed the way they are. The check reuses the
production reader rather than a private comparison, so it cannot pass by
checking something easier.

An exempted collision involving the wrapper counts against it exactly like an
unexempted one. The wrapper is not a line and has no standing to share a token
with one, so an exemption cannot launder its overlap.

It is **not** in `all_invariants()`. It cannot be answered without importing the
siblings, and a check that cannot be answered must not report success. With no
sibling importable it returns:

```text
self_disjointness  passed=False  no line vocabulary was available to compare
against, so the comparison set was empty; unread lines: ['black_line',
'golden_line', 'red_line', 'white_line']
```

Moving it into the offline battery would make a sibling-free run go green by
deleting the only check that had anything to say. That is called out as
prohibited in [`../src/line_set/AGENTS.md`](../src/line_set/AGENTS.md).

The check also refuses a partial pass. If some lines were read and others were
not, and no collision was found, it reports `passed=False` with a detail naming
which lines it compared against and which it could not read — disjointness
against a subset is not disjointness across the set.

## Demonstrating the matcher rather than asserting it

`src/line_set/probes.py` builds a declared exemption's six weakenings — a
truncated token, a case-folded token, a query naming one line more than the
record does, a record naming one line more than carries the token, a record
missing a meaning for a line it names, and two records for one token — and hands
each to `exemption_for()`. Every probe carries the specification (`should this
match?`) and the answer (`did it?`) separately, and `probes_hold()` is true only
when they agree on every probe *and* there was at least one probe.

The first probe is the positive control: the declaration as written, asked for
exactly the lines it names, must match. Without it, six refusals would be
equally consistent with a matcher that refuses everything.

What this establishes is detection over the six inputs named there. It is not
evidence that a seventh, looser input would be refused, and a probe that matched
as intended is not a finding about the set. The probes are what
`output/figures/exemption_gate.svg` draws and what the manuscript's fail-closed
proposition is bound to.

## Proof of detection

A green check that never saw a bad input is not evidence of anything. For every
check, `tests/test_invariants.py` asserts both directions:

- the check **passes** on the real `LINE_SET` and `SHARED_TOKENS`, and
- the check **fails** on the planted-bad input in the table above, built with
  `dataclasses.replace` on the real entries — no mocking framework, no
  hand-written fake registry that could diverge from the real record type.

The failure assertion is the load-bearing half. A test that only shows the good
input passing is compatible with a check that returns `True` unconditionally.

## The empty-input rule

**Every check fails on an empty scan set**, and the failure detail says why:

```text
distinct_line_ids             passed=False  the declaration is empty; there is nothing to check
distinct_colours              passed=False  the declaration is empty; there is nothing to check
distinct_opus_stages          passed=False  the declaration is empty; there is nothing to check
contiguous_working_positions  passed=False  the declaration is empty; there is nothing to check
orders_diverge                passed=False  the declaration is empty; there is nothing to check
must_not_become_declared      passed=False  the declaration is empty; there is nothing to check
shared_tokens_disambiguated   passed=False  the declaration is empty; there is nothing to check
```

A check that passes because it had nothing to look at is a defect, not a
success, and it is the most common way a gate stops being a gate: the input set
silently empties, everything goes green, and the green is mistaken for evidence.
Two checks extend the rule past literal emptiness — `distinct_opus_stages` fails
when no entry declares a stage, and `orders_diverge` fails when fewer than two
entries carry both a stage and a position — because in each case the scan set
for that particular question was empty even though the declaration was not.

## Running them

```bash
uv run python scripts/check_registry.py   # offline battery, non-zero on failure
uv run python scripts/check_set.py        # live reading and the full battery
uv run pytest tests/test_invariants.py -v
```

`check_registry.py` is the offline gate and passes with no sibling installed.
`check_set.py` takes a live reading, so it needs the siblings; what it reports
when they are absent is itself part of the contract.

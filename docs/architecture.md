# Architecture

Line Set is a small package with one seam. Everything except `binding.py` is
pure computation over a declaration that is passed in as an argument;
`binding.py` is the single place where this package reaches for another one.
That split is the whole design, and most of what follows is a consequence of it.

## Module map

| Module | Question it answers |
| --- | --- |
| `src/line_set/version.py` | Which package version and which reviewed revision of the declaration is this? |
| `src/line_set/models.py` | What are the record types — entry, exemption, observation, collision, stage, reading? |
| `src/line_set/registry.py` | What is the set? `LINE_SET`, `SHARED_TOKENS`, and the wrapper's own entry. |
| `src/line_set/binding.py` | How is one sibling package resolved and read? The only module that imports one. |
| `src/line_set/reader.py` | How does a reading follow, in recorded stages, from what resolved? |
| `src/line_set/invariants.py` | Is the declaration well formed, and does this package survive its own check? |
| `src/line_set/serialization.py` | What is the canonical form and digest of a declaration or a reading? |
| `src/line_set/probes.py` | What does the exemption matcher do with a deliberately weakened exemption? |
| `src/line_set/omnibus.py` | How are the declared works compiled into one volume without altering any of them? |
| `src/line_set/figures/` | How is each figure drawn deterministically from the declaration and a live reading? |
| `src/line_set/figures/legibility.py` | What point size does each plate's smallest label reach on the rendered page? |

No module outside `registry.py` names an individual line. That is what makes
adding a colour a one-file edit; see [extensibility.md](extensibility.md).

## The staged reading

`read_set(lines, shared, *, resolver=None, as_of=None)` runs five stages and
records each one into the returned `SetReading.derivation`, so a reading can be
re-read instead of trusted.

1. **resolve** — ask the resolver for each declared `package_name`. The outcome
   is a `ReadCode`: `RESOLVED`, `NOT_INSTALLED`, `IMPORT_FAILED`, or
   `NO_VOCABULARY`. Absence is an ordinary outcome, never an exception. A line
   that did not resolve gets no version, no registry size, and no digest — those
   fields stay `None` rather than being filled with a placeholder.
2. **bind** — for each resolved package, read a version string, find the primary
   registry tuple and take its length, ask the package for its own digest, and
   collect the member names of every enum exported at the package root. A
   package that imported but exported no enum is downgraded to `NO_VOCABULARY`.
3. **collide** — invert to `token → {line ids}`, keep the tokens carried by more
   than one line, and partition them with `exemption_for` into
   `exempted_collisions` and `collisions`.
4. **declare** — ask the resolver to enumerate line-shaped packages, and report
   any that resolved but are not in the declaration. A resolver that offers no
   enumeration produces `None`, and the stage records that it did not scan
   rather than that it found nothing.
5. **status** — apply the precedence below and record the reason.

### Status precedence

`STATUS_PRECEDENCE` is the order, strongest finding first, and a test pins it:

```text
SET_COLLIDING  >  SET_UNDECLARED  >  SET_PARTIAL  >  SET_LEGIBLE
```

An unexempted collision outranks everything, because it is the one finding that
says the set's non-overlap contract stopped holding. An undeclared line outranks
a partial read, because a line nobody declared is a gap in the declaration,
while a line that would not import is a gap in the installation — the first is a
worse thing to be silent about. `SET_LEGIBLE` is only reachable when every
declared line was read, which is why a partial install can never launder itself
into a clean reading.

## The resolver seam

`resolver` is any callable taking a package name and returning a `Resolution`.
Three consequences:

- **Tests need no mocking framework.** A plain function that returns a
  `Resolution` is a real object. Every reader test drives absent, failing,
  vocabulary-less, and undeclared packages through injected callables and real
  temporary-directory packages. `unittest.mock` and friends are prohibited in
  this tree.
- **Nothing touches `sys.path` by default.** `default_resolver` is constructed
  with no search paths and inserts nothing at import time. `sibling_path_resolver()`
  is the explicit opt-in; it prepends the sibling `src` directories on first use
  and records exactly what it inserted in `added_paths`.
- **Enumeration is optional.** A resolver may offer `candidates()`.
  `candidate_packages()` returns `None` when it does not, which the declare
  stage reports as "did not scan" rather than as an empty finding.

### What `binding.py` will and will not do

It reads a version string, counts a registry, calls the package's own digest
function, and collects exported enum member names. It never calls a sibling's
evaluator, never passes a sibling any data, and never computes a digest on a
sibling's behalf — a value this package derived would say nothing about whether
the sibling agrees with it.

Registry-size discovery is a convention read, stated generically rather than
per-package: the primary registry is the public, non-empty tuple in the
package's `registry` submodule whose members are all instances of one dataclass
type. When several qualify, the strictly largest wins; a tie yields `None`
rather than a guess. A package that keeps its registry elsewhere or under a
private name simply reports no size, and a reported `None` means *not found*,
never *not present*.

Undeclared-line discovery is likewise conventional — a top-level package whose
name ends in `LINE_PACKAGE_SUFFIX`, plus what is already in `sys.modules`. It is
best-effort and is documented as such in [claim_boundaries.md](claim_boundaries.md).

## Structural checks, offline and live

`invariants.py` splits deliberately in two.

`all_invariants()` is the **offline** battery. It imports no sibling and returns
the same results whether or not any line package is installed, which is what
lets this project be tested and rendered standing alone.

`check_self_disjointness()` is **live**. It appends the wrapper's own entry to
the declaration, runs the ordinary reader over the result, and hands that
reading to `self_disjointness_from_reading()`, which is the pure half: it
imports nothing and reads only what the reading holds. The split exists so the
`self_application` plate can print the same verdict rather than re-deriving it
— a second implementation of four conditions is free to disagree with the first
while both stay green. The check asks whether any of this package's own tokens
turned up in a collision. It cannot be answered
without importing the siblings, so it is not in the offline battery, and it
reports `passed=False` — never a vacuous pass — when there is nothing to compare
against. `live_invariants()` is the offline battery plus this check.

Moving self-disjointness into `all_invariants()` would make a sibling-free run
go green by removing the only check that had anything to say. Do not.

## The self-application property

This package checks other packages for shared status tokens. It therefore has to
survive that check itself, or it would be applying a rule it is exempt from.

The mechanism is plain: `SetStatus` members are `SET_`-prefixed so that their
disjointness from the sibling vocabularies is structural rather than lucky,
`ReadCode` members carry ordinary names and are subject to the same check with
no such help, `WRAPPER_LINE` in `registry.py` carries this package's own entry
(colourless, no opus stage, since it names no refusal, method, aspiration, or
absence and is not a stage of anything), and `check_self_disjointness` runs the
production reader over `LINE_SET + (WRAPPER_LINE,)`.

A declared exemption does not help here. The wrapper is not a line and has no
standing to share a token with one, so an *exempted* collision involving the
wrapper counts against it exactly like an unexempted one.

`WRAPPER_LINE` stays out of `LINE_SET` because the wrapper is not a fifth
instrument. Its `working_position` continues the sequence so that appending it
still yields a contiguous `1..N`, which is how the check can reuse the ordinary
reader with no special case.

## Digest semantics

`canonical_registry` and `canonical_reading` produce order-independent JSON:
every collection is sorted before it is written, so no `dict` or `set` iteration
order can reach a digest. `registry_digest` and `reading_digest` are SHA-256
over those forms.

The exemption table is serialized *with* the lines, because a set whose shared
tokens changed is a different set even if its lines did not. `shared` defaults
to empty only so a caller can digest the lines alone when that is what it means
to compare.

A digest is a review and drift-detection handle. It detects that your copy
disagrees with a digest someone already holds. It is not tamper evidence, it
carries no attestation, and it is trivially recomputed by anyone who edits the
declaration. This is restated at greater length in
[claim_boundaries.md](claim_boundaries.md) because it is the single most
frequently overread property in the set.

## Failing closed

Two places in the package decide whether a guarantee holds, and both are written
so that the cheap direction is refusal.

`exemption_for` requires exact token equality, set equality between the declared
lines and the lines actually carrying the token, a non-blank meaning for each
named line and no meaning for a line it does not name, and exactly one matching
declaration. Every failure returns `None`, which leaves the collision
unexempted. A missed exemption costs a visible `SET_COLLIDING` that a person
fixes by writing the declaration properly; a generous match costs a guarantee
that stopped holding without anyone being told.

Every structural check fails on an empty scan set. A check that had nothing to
look at reports that it had nothing to look at. A battery that goes green
because the input was empty is worse than no battery, because it is mistaken for
one.

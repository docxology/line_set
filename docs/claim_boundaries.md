# Claim boundaries

This is the document to read first if you suspect this project of overclaiming.
It exists because a package that checks other packages is the easiest thing in
the set to misread: it looks like an auditor, it is shaped like an auditor, and
it is not one. It reads declarations.

The whole positive claim fits in one sentence. **A `SET_LEGIBLE` reading says
that the declared lines the reader could import each exported a set of enum
member names, and that no name appeared in more than one of them except where
an exemption was declared in advance with a distinct meaning per line.** Every
sentence below is a restatement of what that does *not* reach.

## The non-claims, flatly

**It does not establish that the instruments are correct.** The reader never
calls a sibling's evaluator, never passes it an input, and never looks at what
it concluded. `binding.py` reads a version string, counts a tuple, calls the
package's own digest function, and collects enum member names. A line whose
evaluator returns the wrong answer for every input reads exactly the same as
one that returns the right answer.

**It does not establish that the instruments are complete.** `registry_size` is
the length of a tuple. It is not coverage of a domain, a proportion of anything,
or evidence that the rows in that tuple are the rows that should be there. A
line with one row and a line with a hundred are both simply read and reported.

**It does not establish that the set covers what it should cover.** The
declaration in `registry.py` is a list of the lines that exist. Nothing in this
package can tell you that a question worth its own instrument has no line, that
two of the declared lines should have been one, or that one of them should not
exist. The set is not derived from a survey of the space of governance
questions; it is a record of decisions a person made, and this package checks
the record's shape, not the decisions.

**It is not tamper evidence.** `registry_digest` is SHA-256 over a canonical
JSON form of the declaration. It detects that your copy disagrees with a digest
someone already holds. It does not detect editing, because anyone who edits
`registry.py` recomputes the digest for free by running the same function. There
is no signature, no key, no external anchor, and no attestation. A changed
digest means *changed*; an unchanged digest means *the bytes match the ones you
already had*, and nothing at all if you had none.

**It is not independent verification of any sibling.** Every fact reported per
line comes from that line: the version string is the package's `__version__`,
the digest is computed by the package's own digest function over the package's
own registry, and the tokens are the enum members the package chose to export
at its root. This package deliberately does not compute a digest on a sibling's
behalf, because a value the wrapper derived would tell you nothing about whether
the sibling agrees with it. What you get is a faithful report of what each
package says about itself.

**It is not a ranking, and no output of it is an ordering by merit.**
`working_position` is the sequence in which the instruments are used, not a
league table. The opus stage is a borrowed label with, by the set's own
statement, none of the opus's direction: no line completes, supersedes, or ranks
above another. The reader emits no score, no total, and no aggregate, and the
absence of one is deliberate — an aggregate over instruments that answer
different questions would be a number with no referent.

**Disjoint vocabularies are not disjoint concepts.** This is the sharpest limit
in the project. The check is over spellings of enum member names. Two lines can
be about substantially the same thing in different words and read `SET_LEGIBLE`;
two lines can be entirely distinct in substance and collide because they both
liked a word. Non-overlap of vocabulary is a necessary condition for the set's
separation contract and nowhere near a sufficient one. Conceptual overlap is
found by reading the instruments, which is human work this package does not do
and does not shorten.

**It does not read behaviour, and it does not read all the names.**
`enum_tokens` collects members of enums exported at the *package root*. A token
defined in a submodule and not re-exported is invisible to the reader by design:
the contract is about the vocabulary a line publishes. A line could therefore
carry a colliding token privately and read clean. That is a bounded reading, not
a loophole being hidden — it is written here because a hostile reader would find
it in `binding.py` in a minute.

**An empty `undeclared_lines` is not proof that no undeclared line exists.**
Discovery is convention-based: an installed top-level package whose name ends in
`_line`, plus anything already in `sys.modules`. A line package named otherwise
is not found. The reader says it scanned candidates; it never says it enumerated
the world. When the resolver cannot enumerate at all, the derivation says the
scan did not happen rather than reporting nothing found.

**A declared exemption is not evidence that the exemption is right.**
`exemption_for` checks that an exemption is *well formed*: exact token, exactly
the lines that carry it, a non-blank meaning for each, exactly one declaration.
It cannot check that the two meanings are genuinely different meanings. A person
who writes two plausible sentences for a token that really is one concept used
twice gets an exempted collision and a `SET_LEGIBLE` reading. The matcher
guarantees the disambiguation was *written down*, not that it is true.

**It cannot tell you whether a line is worth having.** There is no path from any
output of this package to that question.

**Self-disjointness is a claim about tokens, not about restraint.**
`check_self_disjointness` establishes that this package's own status names do
not collide with any line's vocabulary. It is the property the project exists to
hold and it is genuinely checked. It does not establish that the wrapper has
stayed out of the siblings' business, that it has not drifted into being a
meta-evaluator, or that its prose is modest. Those are read by a person; the
check only ensures the wrapper is subject to the same rule it applies.

**Nothing here is a claim about a person.** No status describes an author,
their diligence, or their judgement. `SET_COLLIDING` is a fact about two
spellings.

## What each status actually means

| Status | Means | Does not mean |
| --- | --- | --- |
| `SET_LEGIBLE` | Every declared line was read; no unexempted token appeared in more than one. | That the lines are correct, complete, well chosen, or non-overlapping in substance. |
| `SET_PARTIAL` | At least one declared line could not be imported. What was read still holds. | That the set is broken, or that the missing line is missing from the world rather than from this environment. |
| `SET_COLLIDING` | A token is carried by more than one line with no well-formed exemption. | That either line is wrong. It means the separation contract needs a decision — split the token, or declare the overlap with a meaning per line. |
| `SET_UNDECLARED` | A package that resolved looks like a line and is not in the declaration. | That the package is illegitimate. It means the declaration is behind the installation. |

## Evidence classes

| Claim class | What this project supports | Evidence | What it does not support |
| --- | --- | --- | --- |
| Structural | The declaration is well formed: ids, colours, and opus stages distinct; positions contiguous; working order and opus order distinct; every entry states what it must not become; every exemption is one the live matcher honours. | `all_invariants()` and its planted-bad detection tests. | That a well-formed declaration is a well-chosen one. |
| Reading | Which declared packages resolved, what version and registry size each reports, and which tokens are carried by more than one line. | `read_set()`, its recorded five-stage derivation, and the resolver-injection tests. | Anything about the behaviour, quality, or completeness of the packages read. |
| Self-application | This package's own status tokens are disjoint from every line vocabulary the reader could read. | `check_self_disjointness()`, run against the live siblings. | That the wrapper has honoured its other boundaries, which are prose commitments a person checks. |
| Empirical | None. | There is no dataset, no observation of use, and no measurement of whether the set helps anyone. | Any claim that separating instruments this way works, is better than not doing so, or generalizes past one person's practice. |

The Reading row is where the manuscript's counted numbers live — how many enum
classes the packages export, how many members those classes declare, how
many distinct names survive, and which name two lines carry. Those are
measurements of four packages on one machine on one date, recorded in
`docs/manuscript/reading_record.json` and bound to the prose by
`tests/test_manuscript_bindings.py`. They are not the Empirical row, which
stays at none: counting spellings is not evidence that keeping instruments
apart this way does any good.

## The reading protocol

1. Find the claim.
2. Decide which of the four classes above it belongs to.
3. Check the corresponding function, test, or recorded derivation stage.
4. If it belongs to none of them, it is not a claim this project supports —
   including when this project's own prose is what said it.

Step four applies to this document too. If you find a sentence anywhere in this
tree that reaches past what `src/line_set/` executes, the sentence is the defect.

# Method: a declaration, a staged reader, and one seam {#sec:method}

## The declaration

A `LineEntry` has ten fields. Four are identity and prose — the line's id, its colour, the question it answers, the job it does. One is the boundary: `must_not_become`, which every line fills in and which a structural check refuses to let go blank. Two are ordering: `opus_stage`, which may be absent, and `working_position`, a one-based integer that must land in a contiguous `1..N` across the whole declaration. The last three are addresses. `package_name` is what the reader asks the import system for, and it is kept separate from `id` so that a line's identity in the declaration does not depend on how its code happens to be distributed. `registry_noun` and `verdict_noun` are prose labels for what a line keeps and what it emits; figures and manuscript text use them, and the reader never uses them to find anything.

A `SharedToken` has four: the token, the tuple of line ids allowed to carry it, a tuple of per-line meanings, and a rationale. The meanings tuple is the load-bearing one. A shared token with no meaning recorded for each line it names is a label, and a label cannot show that two uses of one spelling are two different things.

The two record types are stated as [@def:line-entry] and [@def:shared-token]. The declaration ships eight line entries and eight shared token. The wrapper's own entry lives beside `LINE_SET` rather than inside it, because it is not a fifth instrument; its `working_position` continues the sequence so that appending it still yields a contiguous run.

## The reader

`read_set` takes the lines, the exemption table, an optional resolver, and an optional review date, and runs five stages, formalized as [@def:reading]. Each stage records what it did into the returned derivation, so a reading can be re-read rather than trusted.

**Resolve** asks the resolver for each declared line's package and records one of four codes. `RESOLVED` means the package imported. `NOT_INSTALLED` means the import system found nothing. `IMPORT_FAILED` means it found something that raised, and the exception text is kept. `NO_VOCABULARY` means the package imported and exported no enum at its root. None of these is an exception. A line that cannot be read produces no version, no registry size, and no digest, and those fields stay `None`; nothing in the package invents a value for a package it could not read.

**Bind** reads what a resolved package publishes about itself: a version string from `__version__` or `PROJECT_VERSION`, a registry size, a digest, and the member names of every `enum.Enum` exported at the package root. Only the root is read. A token defined in a submodule and never re-exported is invisible here, which is intentional — the contract is about the vocabulary a line publishes, not about every name that exists somewhere inside it.

**Collide** inverts the observations into a token-to-lines map and keeps every token carried by more than one line. Each such token is partitioned by asking the exemption matcher whether the set already declared it.

**Declare** looks for line packages that resolved but appear nowhere in the declaration. This stage depends on the resolver being willing to enumerate; when it is not, the derivation says the scan did not happen rather than reporting that nothing was found. That distinction matters more than it looks: an empty finding and an unasked question read identically in a summary, and only one of them is evidence.

**Status** applies the fixed precedence of [@prop:precedence]. An unexempted collision yields `SET_COLLIDING` and outranks everything, because it is the single finding that says the set's contract stopped holding. An undeclared line yields `SET_UNDECLARED`, ranking above a partial read because a line nobody declared is a gap in the declaration rather than a gap in the installation. A line that could not be read yields `SET_PARTIAL`. Only when none of those applies is the reading `SET_LEGIBLE`.

![The reader's five stages, with the status precedence drawn as the exit ladder: a collision leaves at the first rung, an undeclared line at the second, an unread line at the third, and only a reading that reaches the bottom is legible.](../output/figures/set_reading_pipeline.png){#fig:set-reading-pipeline width=100%}

## The seam

One module imports siblings. `binding.py` resolves a package by name, reads a version, counts a registry, asks the package for its own digest, and collects enum member names. It never calls a sibling's evaluator, never passes it data, and never forms an opinion about what a sibling concluded. Every other module in the package is pure computation over a declaration handed to it as an argument.

Two details in that module are deliberate. The digest is always the package's own, computed by the package's own function over the package's own registry; a digest this wrapper derived on a sibling's behalf would say nothing about whether the sibling agrees with it. And the registry-size rule is a convention read rather than a contract: the size is the length of the unique public, non-empty tuple in the package's `registry` submodule whose members are all one dataclass type, with the strictly largest winning when several qualify and a tie reporting no size at all rather than a guess. A package that keeps its registry somewhere else simply reports nothing, which is the correct answer to a question the wrapper is not entitled to force.

The default resolver adds nothing to `sys.path` and finds exactly what an ordinary import would find. Looking in the sibling checkouts is an explicit opt-in, and a resolver that was asked to do so records precisely which directories it inserted.

## Failing closed

The exemption matcher is the only thing standing between a declared exemption and the non-overlap guarantee, so it is written so that a too-generous match is impossible rather than unlikely. Its conditions are stated as [@def:exemption-match] and its behaviour as [@prop:fail-closed]; the design decision behind them is that every condition is an equality and every failure returns no match. A matcher that accepted `OUTSIDE` for `OUTSIDE_SCOPE`, or that let a two-line exemption cover a third line which later adopted the word, would exempt collisions nobody ever declared, and it would do so silently.

## The checks

Seven checks run offline over the declaration and import nothing: distinct ids, distinct colours, distinct opus stages drawn from the known stage names, contiguous working positions, working order differing from opus order, a non-blank `must_not_become` on every entry, and an exemption table the live matcher would honour. That last one calls the matcher the reader actually uses instead of re-deriving its rules, so the check cannot drift away from the thing it is checking.

Every one of the seven fails on an empty declaration, and each says why in its detail. A check that passed because it had nothing to look at is not evidence of anything, and the same principle applies to the exemption table: an empty table fails, because a table that is empty because none is needed and a table that was accidentally cleared look identical from inside the check.

The eighth check appends the wrapper's own entry to the declaration, runs the ordinary reader over the result, and asks whether any of the wrapper's own tokens turned up in any collision; it is stated as [@prop:self-disjointness]. A declared exemption does not help here — the wrapper is not a line and has no standing to share a token with one, so an exempted collision involving it counts against it exactly like an unexempted one. The check needs the siblings importable, so it lives outside the offline battery, and when there is no sibling vocabulary to compare against it reports failure with the reason. Moving it into the offline battery would make an unattended run go green and would establish nothing.

## Digests

Two canonical forms exist, both sorted before serialization so that no dictionary or set iteration order can reach them. The set digest covers the lines and the exemption table together. The reading digest covers a whole reading, including its date and derivation. Both are review handles for detecting that two people are looking at different things. Neither carries safety, warranty, or attestation semantics, and neither is tamper evidence.

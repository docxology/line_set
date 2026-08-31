# The instrument stated formally {#sec:formalism}

The method section says what the reader does, in the order it does it. This one restates the same machinery as objects and rules, so that a claim about the instrument can be checked against a statement rather than against a paragraph. Every statement below is written from the module it describes and is bound by a named test that re-derives it; where the code turned out narrower than a formal statement might be expected to be, the narrower thing is what is written down.

## The declared objects

::: {.definition #def:line-entry title="Declared line"}
A declared line is a `LineEntry` record with ten fields: `id`, `color`, `question`, `job`, `must_not_become`, `opus_stage`, `working_position`, `package_name`, `registry_noun`, and `verdict_noun`. `opus_stage` may be absent, `working_position` is an integer, and every other field is text. A *declaration* is a tuple of such records paired with an exemption table. The reader, the structural checks, the serialization, and the figure builders each take that pair as an argument, and no module outside `registry.py` names an individual record.
:::

::: {.definition #def:shared-token title="Declared exemption"}
A declared exemption is a `SharedToken` record with four fields: `token`, the spelling more than one line is allowed to carry; `lines`, the ids of the lines allowed to carry it; `meanings`, a sequence of line-and-meaning pairs; and `rationale`. The exemption table is a tuple of these records, and it is serialized together with the lines, so a set whose exemptions changed is a different set even when its lines did not.
:::

The meanings field is the load-bearing one. A shared token with no meaning recorded per line is a label, and a label cannot show that two uses of one spelling are two different things — which is what [@def:exemption-match] refuses to accept.

## The exemption matcher

::: {.definition #def:exemption-match title="Exemption match"}
Given an exemption table, a token, and the set of lines carrying that token, `exemption_for` returns a record when all of the following hold, and no match otherwise. The token is non-empty text. At least two lines carry it. Exactly one record in the table carries a `token` equal to it, character for character. That record's `lines` are text, non-blank, distinct, at least two, and equal *as a set* to the lines carrying the token. Its `meanings` supply a non-blank meaning for each line it names and name no line outside them. A multi-line token with a match is an **exempted** collision; one without a match is an **unexempted** collision.
:::

::: {.proposition #prop:fail-closed title="Failing closed"}
Every condition in [@def:exemption-match] is an equality, and every failure returns no match, which leaves the collision unexempted. Six weakenings are therefore refused: a query for a proper prefix of a declared token, a query for the token in another case, a query naming one line more than the record does, a record naming one line more than carries the token, a record omitting the meaning for a line it names, and two records declaring one token. What the refusals cost is asymmetric, and that asymmetry is the reason for the design: a missed exemption costs a visible `SET_COLLIDING` reading that a person then fixes by writing the declaration properly, while a generous match costs a guarantee that stopped holding without anyone being told.
:::

[@prop:fail-closed] names six weakenings, and the plate below is those six run through the matcher the reader actually calls, together with the declaration as written. The seventh row is the positive control: without it, six refusals would be equally consistent with a matcher that refuses everything.

![The exemption gate. Each row weakens the declaration or the query in one way and reports what `exemption_for` returned for it; the outcome column is a return value, not a claim written into the plate. The first row is the declaration as shipped, asked for exactly the lines it names, and it must be honoured. A refused row leaves its collision standing.](../output/figures/exemption_gate.png){#fig:exemption-gate width=100%}

## The reading

::: {.definition #def:reading title="A reading"}
`read_set` takes a declaration of [@def:line-entry] records, an optional resolver, and a review date, and returns a reading that records five stages in order. **Resolve** asks the resolver for each line's `package_name` and records one of `RESOLVED`, `NOT_INSTALLED`, `IMPORT_FAILED`, or `NO_VOCABULARY`. **Bind** reads, from each package that resolved, a version string, a registry size, a digest that package computed itself, and the member names of every enum exported at its root; a line that did not resolve carries no version, no registry size, and no digest. **Collide** inverts the observations into a token-to-lines map, keeps every token carried by more than one line, and partitions those by [@def:exemption-match] over the [@def:shared-token] table. **Declare** names packages that resolved and appear in no entry, or records that the resolver could not be asked. **Status** applies [@prop:precedence]. The self-application check ([@prop:self-disjointness]) appends the wrapper's own entry and takes an ordinary reading through the same five stages.
:::

::: {.proposition #prop:precedence title="Status precedence"}
A reading's status is the first of `SET_COLLIDING`, `SET_UNDECLARED`, `SET_PARTIAL`, `SET_LEGIBLE` whose condition holds: an unexempted collision, then a resolved package that is not declared, then a declared line whose read code is not `RESOLVED`, then nothing else. `SET_LEGIBLE` is reachable only when no condition above it matched, so a live collision cannot be hidden behind a missing install and a partial installation cannot present itself as a clean reading.
:::

## The self-application

::: {.proposition #prop:self-disjointness title="Self-disjointness"}
`check_self_disjointness` appends the wrapper's own entry to the declaration, takes an ordinary reading of the result by [@def:reading], and holds only when four things are true together: the wrapper's own vocabulary was read; at least one other line supplied a vocabulary; no collision in that reading names the wrapper; and no other declared line went unread. An exempted collision naming the wrapper counts against it exactly as an unexempted one does, because the wrapper is not a line and has no standing to share a token with one.
:::

The middle two conditions are what keep the property from being established by an empty comparison. They are also why the check cannot live in the offline battery: it needs the sibling packages importable, so on a machine without them it reports failure with the reason rather than a pass.

::: {.proposition #prop:vocabulary-disjointness title="Vocabulary disjointness"}
The reading (see [@def:reading]) partitions every token into the lines that carry it. Each vocabulary term maps to exactly one registry entry: no term is ambiguous across the line set. After exempted collisions are removed by [@def:exemption-match], any token appearing in more than one vocabulary is an unexempted collision, and the reading's status is `SET_COLLIDING`. The set's contract is that every terminal spelling names exactly one registry entry; non-overlap of vocabulary is a necessary condition for separation and nowhere near a sufficient one — two lines can be about substantially the same thing in different words and read `SET_LEGIBLE`, and two lines can be entirely distinct in substance and collide because they both liked a word.
:::

![The wrapper under its own rule. Above, the enum member names this package publishes at its own root; below, one row per declared line with the vocabulary it published and whether any spelling is shared. The verdict panel prints the check's own result and detail over this reading, so the plate and the check cannot disagree.](../output/figures/self_application.png){#fig:self-application width=100%}

## What the statements do not carry

They are statements about this package, and each is exactly as strong as the function it describes. [@prop:precedence] says which status a reading takes, not that the status is deserved. [@prop:fail-closed] says the matcher refuses six named weakenings, not that no seventh would be accepted; the probes demonstrate detection over the inputs written down, which is the most a demonstration can do. [@prop:self-disjointness] is about spellings in namespaces and says nothing about whether this package has stayed out of the siblings' business — that boundary is prose, and a person checks it.

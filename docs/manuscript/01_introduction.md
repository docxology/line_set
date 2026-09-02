# Introduction: what keeps four instruments from becoming one {#sec:introduction}

For most of the time the four lines have existed, their separation was a sentence in a markdown file. Each project's documentation said it did not duplicate the others' registries, evaluators, figures, or conclusions. I believed it, and I had written it, and nothing anywhere checked it.

Two things go wrong when a set of small instruments grows, and they go wrong
quietly. The first is that two instruments give the same name to different
things — `OUTSIDE_SCOPE` is the set's only such collision, defined in
[@def:shared-token]. Someone reading a stored finding sees that word and has
to already know which line produced it before it means anything; if they
guess wrong, they read a refusal as a competence judgement. The second is
that one instrument slowly takes on another's job — an aspiration registry
acquires a prohibition, a method checklist starts issuing permissions — until the set is one instrument wearing four names. The second failure is the more serious of the two. It is also the one I cannot check by machine.

So this work addresses the first, and it addresses it narrowly. It declares the set as data, reads whichever line packages are installed, collects the enum member names each of them publishes at its package root, and reports whether any name is carried by more than one line. A name carried by two lines is a collision. A collision the set has already written down, with a separate meaning recorded for each line, is exempted. Any other collision makes the reading `SET_COLLIDING`, and that is the whole of the contract.

I want to be exact about the size of that claim, because a wrapper is the easiest place in a project to overstate one. Disjoint vocabularies are a necessary condition for the separation I want, not a sufficient one. Two lines can share no spelling whatsoever and be duplicating each other's judgement in every particular; the reader would call that set legible and be technically right and substantively useless. The check catches the failure that produces silent misreads downstream. It does not catch conceptual overlap, and nothing in this package should be cited as though it did.

There is a hazard specific to being the bookkeeping work, and I have tried to design against it rather than promise around it. An instrument that sits above the others is well positioned to become a scoreboard for them — to start reporting which line is healthiest, which is best maintained, which one earns its place. The eight lines are peers. Nothing here ranks them, aggregates them, merges them, or evaluates them, and the package's own entry in `registry.py` records that as the thing it must not become, in the same field every line uses for the same purpose. The entry is deliberately colourless and carries no stage, because the wrapper answers no question about refusal, method, aspiration, or absence.

The design constraint that follows is the part I find most worth reporting. A package that checks other packages for shared tokens has to survive that check itself. If this one had named its reading statuses `LEGIBLE`, `PARTIAL`, `COLLIDING`, and `UNDECLARED`, it would have been one plausible sibling release away from colliding with the very set it reads. The statuses are `SET_`-prefixed instead, and a check appends the wrapper's own entry to the declaration and runs the ordinary reader over the result. That check is the only one in the battery that needs the siblings importable, so it sits outside the offline battery and reports failure — not silence, and not a pass — when it has nothing to compare against.

The rest of the paper describes the declaration and the reader, states both as definitions and propositions that a test re-derives from the code, situates the separation question in work on modularity and on artifacts that coordinate without merging, shows an executed example of appending a further colour, walks through readings I actually took, and states what the instrument cannot see.

The paper proceeds as follows. [Section @sec:the-set](#sec:the-set) names the eight instruments and the shared words. [Section @sec:method](#sec:method) defines the declaration, the staged reader, and the seam. [Section @sec:formalism](#sec:formalism) states the instrument formally. [Section @sec:extensibility](#sec:extensibility) demonstrates that adding a colour is an edit to one file, and [Section @sec:limits](#sec:limits) closes with epistemic boundaries.

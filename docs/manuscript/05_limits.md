# Limits and Epistemic Boundaries {#sec:limits}

## The reader reads declarations

Everything this package reports is derived from what the sibling packages say about themselves at their package roots: a version string, a registry tuple, a digest function, and the member names of the enums they export. Nothing is executed. No evaluator is called, no data is passed to a line, and no finding a line has ever produced is examined. A line could return the same verdict for every input it is given and read as perfectly healthy here, because the reader never asks it a question.

The consequence is that `SET_LEGIBLE`, in [@prop:precedence], is a statement about names in four namespaces on one machine on one date. It is not a statement that the instruments work, that they are internally consistent, that their tests pass, or that their registries are current.

## Disjoint vocabularies are not disjoint concepts

This is the limit I most want a reader to carry away, because it is the one the instrument's own name invites people to forget. The check finds tokens two lines spell identically. It cannot find two lines that answer the same question in different words.

Nothing would stop me from writing a fifth line whose registry duplicates Golden Line's aspirations under new names, whose evaluator reimplements Golden Line's decision rule, and whose statuses are spelled so as to collide with nothing. The reading would be `SET_LEGIBLE`. It would be correct and it would be worthless, because the separation I actually care about is conceptual and the property I can check is lexical. The lexical check is worth having — it catches the failure that makes stored findings ambiguous downstream — and it is a necessary condition for the separation, not evidence of it. Whether two lines are thinking about the same thing remains a judgement someone has to make by reading them.

## A digest is not tamper evidence

The set digest and the reading digest exist so that two people, or one person at two times, can tell whether they are looking at the same declaration or the same reading. A mismatch is a prompt to go and find out what changed. That is the entire semantics.

A digest carries no safety, warranty, attestation, or authorship claim. It detects disagreement with a digest someone already holds; it does not detect tampering, because anyone who can change the declaration can recompute the digest, and there is no signature, no key, and no independent witness anywhere in this package. Each sibling's digest is likewise the sibling's own value, computed by its own function over its own registry, and this package never derives one on a sibling's behalf — a number the wrapper computed would say nothing about whether the sibling agrees with it.

## The reader cannot say whether a line is worth having

There is no score here, no aggregate, no ranking, and nothing that could be turned into one without an obvious edit. A reading says whether the declared vocabularies overlapped and which lines could be read. It has no view on whether Red Line's question is well posed, whether White Line earns its place, whether four is the right number, or whether any of these instruments has ever improved a piece of work.

That silence is deliberate rather than an omission awaiting a future release. The lines are peers, the colours are labels rather than a ladder, and an instrument sitting above four others is exactly the wrong place to start assigning merit. The wrapper's own declaration records that as the thing it must not become.

## The reader cannot see a missing colour

Nothing in this package can tell whether the set is incomplete. It reads what was declared and looks for installed packages whose names follow a convention; a question nobody has asked yet leaves no trace in either. The set could be missing an instrument for what work costs to maintain, or for who else is affected, or for something I have not thought of, and every check here would keep passing.

Discovery is also weaker than it may appear from a passing run. It finds importable top-level packages whose names end in `_line`, plus what is already imported in the process. A line package named otherwise is invisible to it. An empty `undeclared_lines` is a report of what that convention turned up on that machine, and never a proof that nothing else exists.

## Smaller boundaries worth naming

Only the package root is read for enums. A token defined in a submodule and never re-exported does not participate in the collision scan. That is a deliberate scoping of the contract to the vocabulary a line publishes, and it does mean two lines could collide privately without this reader noticing.

Registry size comes from a convention: the unique public, non-empty tuple in the package's `registry` submodule whose members are all one dataclass type, largest winning, ties reporting nothing. A package that organizes itself differently reports no size, which is an absence of information rather than a finding about the package.

Self-disjointness needs the siblings importable and fails when they are not — the second and third conditions of [@prop:self-disjointness] are what make it fail rather than pass. That failure is honest and it is also a real coverage limit: on a machine with no siblings, the property this project exists to hold is unestablished, not established.

Each structural check is backed by a test that plants its defined bad input and proves the check rejects it. What that establishes is detection of the planted defect. It is not evidence that no other defect exists in the declaration, and it says nothing at all about the four packages the declaration describes.

Finally, the colours. The alchemical resonance is a naming resonance held in Jung's symbolic register and nothing further [@jung1953alchemy]. No line is a stage of anyone's transformation, the working order does not re-enact the opus, and the borrowed names carry none of the opus's direction. A structural check pins the divergence of the two orders; nothing pins how a reader will hear the names, and the honest safeguard there is to keep saying what the echo is not.

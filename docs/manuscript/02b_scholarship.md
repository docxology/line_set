# Scholarship: what is old about this problem, and what my check is not {#sec:scholarship}

Keeping parts of a system from becoming each other is not a new problem, and I did not solve it. The literature below gave me the shape of the failure and a list of things to be afraid of. None of it validates the declaration, the reader, or the collision check, and none of the cited work studies this package or anything like it. I am reporting where the design came from, not borrowing authority for it.

## Modules defined by what they hide

Parnas argued that a system should be decomposed by design decisions rather
than by processing steps, and that a module's value lies in what it keeps from
the rest of the system — the decision it hides, so that changing it does not
propagate [@parnas1972modules]. That is the argument the line set is organized
around. Red Line's classification logic, Black Line's practice registry,
Golden Line's horizon rules, and White Line's staleness contract are all
decisions each line owns and none of the others should have to know. The
published vocabulary is the interface; the evaluator is not. The distance
between that argument and what this package checks is worth stating precisely,
because it is large. Parnas is concerned with which decisions are hidden and
whether a change stays local. My reader collects the enum member names a
package exports at its root and asks whether any two lines spell something the
same. Those names are a proxy for the published interface, and a coarse one: a
line could hide nothing, expose its entire internal state through functions
rather than enums, and still read as perfectly disjoint here. Information
hiding is a property of what a module keeps back. A name collision is a
property of what two modules happen to say out loud. The second is checkable
in a hundred lines and the first is not, which is why I checked the second and
am saying so rather than letting the citation imply otherwise.

Thirteen years later Parnas, Clements, and Weiss reported what it took to keep a real decomposition legible, and their answer was a second artifact: a *module guide*, a document naming each module and the secret it holds, maintained deliberately because the decomposition is not recoverable from the code that implements it [@parnas1985modular]. `LINE_SET` is a module guide of the smallest possible kind, one record per line ([@def:line-entry]). Their paper is also the warning I took most seriously, because a guide is a second statement of the structure and a second statement can disagree with the first. Their remedy is review by people who know the system. Mine is narrower and mechanical: the entry that names a package is the entry the reader imports, so a guide describing a package that is not there produces `SET_PARTIAL` rather than a sentence nobody reread. The interesting half still has no mechanism. Nothing checks that a line's declared job is its actual job, and nothing checks that the secret each line holds is still hidden.

Dijkstra's essay names the discipline the set is trying to practise: study one aspect at a time, in the knowledge that the other aspects remain true and will have to be faced [@dijkstra1982role]. He is careful that separating concerns is not the same as neglecting the ones set aside. The set inherits that caution structurally — Red Line's refusal keeps applying while I am working inside Black Line, and a `TOWARD` reading in Golden Line cannot authorize anything Red Line refuses. What this package adds is small: it checks that the vocabularies stayed apart. It does not check that the concerns did.

Conway observed that a system's structure tends to reproduce the communication structure of the organization that built it [@conway1968committees]. The line set inverts the premise rather than illustrating it. There is no organization here; there is one person and four repositories, which means no team boundary, no handoff, and no separate maintainer doing the separating for me. Whatever separation exists has to be written into a declaration and checked mechanically, precisely because the social structure that would ordinarily produce it is absent. I take Conway as a diagnosis of why a single-author set needs an explicit contract, not as evidence that this one works.

## Prefixes, and what they are worth without an authority

The oldest mechanical answer to a name collision is to qualify the name. XML namespaces bind a short prefix to a URI so that names minted by different authorities cannot collide even when they spell the same word, and the URI is what does the work: it is owned, so two authors cannot mint the same one by accident [@bray1999namespaces]. The `SET_` prefix on this package's reading statuses is that move performed by hand, at the smallest scale I could get away with, and [@prop:self-disjointness] is what it buys.

Where the transfer stops is exactly where the authority would have been. There is no URI, no registry, and nothing preventing a sibling from adopting the same prefix tomorrow. A namespace makes collisions impossible by construction; a convention makes them *visible*, one review at a time, and only on a machine where every line is installed. That is the weaker guarantee, and it is the one available to a set of packages nobody governs.

## Coordinating without merging

Star and Griesemer described boundary objects: artifacts "plastic enough to
adapt to local needs" in several communities while remaining "robust enough
to maintain a common identity across sites," which lets groups cooperate
without agreeing [@star1989boundary]. The shared token ([@def:shared-token])
has that shape. `OUTSIDE_SCOPE` carries one spelling and two local meanings,
and the exemption table records both rather than forcing either line to give
the word up.

Star's companion paper of the same year is the more useful one here, because it is the one with a typology: repositories, ideal types, coincident boundaries, and standardised forms [@star1989illstructured]. The exemption table is a standardised form — a fixed shape, filled in the same way each time, whose function is to carry a local meaning across a boundary without negotiating it away. Reading it that way is what stopped me treating the shared token as a defect awaiting a rename.

Star later objected to how the concept had been taken up, in particular to its application to any object that happens to sit between two groups, detached from the infrastructural and standardizing work the original study was about [@star2010notboundary]. Her objection applies to me, so I will not make the claim. Two Python packages in one person's working tree are not two communities of practice; there is no negotiation between amateur collectors and professional zoologists here, no institutional ecology, and no cooperation across divergent viewpoints, because the divergent viewpoints are mine. What I took from the 1989 papers is a design move: a shared term can be kept, with its local meanings written down, instead of being resolved by renaming. That is a resemblance I found useful. It is not a case study, and the concept is not doing evidentiary work in this package.

## The hazard of the index

The specific danger of building the fifth work is that an instrument which reads the other four becomes the place people look, and then the other four start being written to read well in it.

Bowker and Star show how classification systems become infrastructure: once embedded, they stop being visible as choices, and the categories begin to organize the work rather than describe it, with the things that fit badly quietly pushed into residual bins [@bowker_star1999]. A declaration listing lines with a colour, a stage, and a position is a classification system, however small. Strathern's account of audit makes the same point about instruments of assessment specifically — a mechanism introduced to describe a practice can end up reorganizing that practice around the mechanism's own categories [@strathern1997audit]. Neither argument is about a hundred-line Python package, and I am not claiming a package this size carries that weight. The mechanism is what I am watching for, at the scale I actually have.

The design responses are modest and I would rather name them than promise around them. There is no score, no aggregate, and no ordering by merit; the reader emits a status about the set and never a judgement about a line. The wrapper's own entry is colourless and carries no stage, so it cannot be read as a fifth position in the sequence. The entry declares what the wrapper must not become in the same field every line uses for the same purpose, which puts the wrapper under the same discipline it applies to the others. And the wrapper's own vocabulary is run through the wrapper's own collision check, so the package cannot exempt itself from the one rule it enforces.

None of that prevents the drift. Bowker and Star's point is that infrastructure becomes invisible, and a package that has become invisible is exactly the one nobody re-reads. What these design choices buy is that the drift, if it happens, has to happen in the open: someone would have to add a ranking field, or an aggregate, or an exemption for the wrapper, and each of those is a visible edit to a small file. Visibility is a weaker guarantee than prevention. It is the one I can actually implement.

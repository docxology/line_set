# The set: four questions, four jobs, and one shared word {#sec:the-set}

The declaration is small enough to print. Each line answers one question, does one job, and names the thing it must not become; the last field is the one that does the work, because a boundary is easier to hold when the drift it guards against has been written down in advance.

| Line | Question | Job | Must not become |
| --- | --- | --- | --- |
| Red Line | What must I refuse? | Security boundary and explicit No document | A complete ethics system or an enforcement mechanism |
| Black Line | How do I do strong work? | Positive wire for concise, rigorous research and engineering | Permission to cross Red Line |
| Golden Line | What is worth reaching toward? | Aspirational thread and long-horizon direction | A compliance score or proof of virtue |
| White Line | What is absent or unknowable? | Epistemic gaps, ethical restraint, omission, silence, and negative space | Evidence that an absent thing is safe or true |

The order is the order I use them in. Red stops a prohibited direction before any work begins. Black gives the work that survives that stop a method. Golden keeps the method pointed at something worth serving. White keeps every claim honest about what was never observed. Each line has its own package, registry, evaluator, figures, tests, and manuscript, and a cross-reference between them is an orientation link rather than a dependency. A separated copy of any one of them still has to explain itself.

## The one shared word

Red Line and Black Line both spell a status `OUTSIDE_SCOPE`, and they mean different things by it. In Red Line it marks a complete, evidenced intake that implicates no red line — the instrument looked and found no prohibition. In Black Line it marks an attempt outside the discipline's evaluation scope — the instrument did not look, because the attempt is not the kind of thing its practices assess. One is a finding of absence after inspection. The other is a declination to inspect.

Both lines needed a name for work their own question does not reach, and the two senses did not turn out to be the same sense. Rather than rename one of them, the set records the overlap: `SHARED_TOKENS` holds a single entry naming the token, the exactly two lines allowed to carry it, a distinct meaning for each, and a rationale. The exemption table is part of the declaration and travels inside the set digest, so a set whose exemptions changed is a different set even when its lines did not.

## The colours, said plainly

The four colour names openly echo the classical stages of the alchemical *magnum opus*: nigredo the blackening, albedo the whitening, citrinitas the yellowing, rubedo the reddening. Anyone who knows the opus will hear it, and it is meant to be heard. I read it in exactly one register — the symbolic-psychological one, following Jung's treatment of the stages as figures for individuation rather than as laboratory chemistry [@jung1953alchemy]. The echo is a naming resonance. It is not an empirical, mystical, or causal claim; the colour of a line has no operative power. It is also not a doctrinal endorsement of alchemy or of Jung's psychology, which would be a much larger commitment than borrowing four words.

Three caveats keep the resonance from being read as more than it is, and the first two of them are checked in code rather than merely promised here.

**The working order is not the opus order.** The set runs refuse, method, aspire, account-for-absence: Red, Black, Golden, White. The opus runs nigredo, albedo, citrinitas, rubedo: Black, White, Golden, Red. The working order was chosen for how the instruments actually support the work, not for any dependency between them — each line stands alone and a cross-reference is an orientation link — and the two sequences deliberately do not line up. `check_orders_diverge` sorts the declaration both ways and fails if they ever coincide, which keeps the claim true by construction instead of by assertion.

**Citrinitas is kept distinct on purpose.** After the fifteenth century the yellowing stage was frequently folded into the reddening, leaving a three-stage nigredo–albedo–rubedo reading. The set does not perform that collapse. Golden Line stays its own instrument with its own question, and `OPUS_STAGE_ORDER` carries four stages rather than three, so a future edit that dropped citrinitas would have to do so visibly.

**No borrowed telos and no ranking.** The opus is a teleological arc toward gold and a completed stone. The set borrows the stage names as symbols and claims none of the direction. Calling Red Line rubedo does not make it final, perfected, or the culmination of the other three; calling Black Line nigredo implies no deficiency in it. The colours are peers. No line completes, supersedes, or outranks another, and this package has no aggregate, no score, and no ordering by merit to offer.

![Two orders: the working sequence (refuse, method, aspire, absence) drawn against the opus sequence (nigredo, albedo, citrinitas, rubedo), with connectors showing where they cross. The divergence is deliberate, and citrinitas is deliberately not collapsed into rubedo. Position in either column encodes sequence only, never rank.](../output/figures/two_orders.png){#fig:two-orders width=100%}

The set's short internal orientation note, `docs/line-set.md`, lives in the author's private projects tree; it is unpublished and does not travel with this repository, so it is cited here by name rather than linked. Each instrument it maps is its own repository — [Red Line](https://github.com/docxology/red_line), [Black Line](https://github.com/docxology/black_line), [Golden Line](https://github.com/docxology/golden_line), and [White Line](https://github.com/docxology/white_line) — and those are the durable references. This paper is the version with a package under it.

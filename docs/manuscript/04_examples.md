# Worked readings {#sec:examples}

Every reading below was executed against the package as it stands. Where a reading needed a package that does not exist, I built one in a temporary directory and pointed a resolver at it; there is no mocking framework anywhere in this project, and a resolver is a plain callable passed as an argument.

## The live set

```python
from line_set import read_set, reading_digest, sibling_path_resolver

reading = read_set(resolver=sibling_path_resolver(), as_of="2026-09-01")
```

```text
status        : set_legible
set_digest    : 7b7e70b70c5c22eaf5daeac59dd54d3c8b771fee3b1193d7446f66c0a1b156b4
reading_digest: afae36b01400bf91
counts        : {'resolved': 8, 'not_installed': 0, 'import_failed': 0, 'no_vocabulary': 0}
  black_line   resolved   v0.4.0  registry=11  digest=a02bff47a767  tokens=10
  blue_line    resolved   v0.1.0  registry=12  digest=9ae7cae1f0f7  tokens= 8
  golden_line  resolved   v0.4.0  registry= 9  digest=3e0a7e38ecec  tokens= 7
  green_line   resolved   v0.1.0  registry=11  digest=2d40bfefb9a5  tokens=10
  red_line     resolved   v0.3.0  registry= 7  digest=72835fd81d1f  tokens=40
  silver_line  resolved   v0.1.0  registry=11  digest=3d4f90f50de3  tokens=11
  violet_line  resolved   v0.1.0  registry= 8  digest=cc2df72dfdba  tokens=16
  white_line   resolved   v0.7.0  registry=11  digest=11047a641a8e  tokens=24
  exempted: COMMUNICATION over ['black_line', 'green_line']; KEPT over ['silver_line', 'violet_line']; METHOD over ['black_line', 'green_line']; NEEDS_REWORK over ['black_line', 'green_line', 'silver_line']; OUTSIDE_SCOPE over ['black_line', 'blue_line', 'green_line', 'red_line', 'silver_line']; STALE over ['blue_line', 'white_line']; STEWARDSHIP over ['black_line', 'green_line']; VERIFICATION over ['black_line', 'green_line']
  unexempted: []
  [resolve] asked the resolver for 8 declared packages
  [bind] read version, registry size, digest, and enum member names from each package that resolved
  [collide] 0 unexempted and 8 exempted cross-line token collisions
  [declare] scanned 8 candidate packages and found 0 that resolved but were not declared
  [status] set_legible: all 8 declared line(s) were read and their vocabularies do not overlap
```

The eight packages export 34 enum classes between them — 7 in red_line, 3 in black_line, 2 in golden_line, 7 in white_line, 4 in silver_line, 5 in violet_line, 3 in blue_line, 3 in green_line — and those classes declare 146 members in total. Twenty of the 146 are a line repeating a word it already uses in another of its own enums, which is not a cross-line event and which the reader collapses: red_line spells `OUTSIDE_SCOPE` in two of its enums, black_line repeats three names across its three, silver_line repeats three names across its four, violet_line repeats three names across its five, blue_line repeats three names across its three, green_line repeats three names across its three, and white_line repeats four names across its seven — its witness-facet alphabets reuse states its ledger already declares. After that collapse the reading holds 126 line-and-name pairs — 40 for red_line, 10 for black_line, 7 for golden_line, 24 for white_line, 11 for silver_line, 16 for violet_line, 8 for blue_line, 10 for green_line — spanning 114 distinct names.

The arithmetic is the whole finding: 126 minus 114 is twelve, and the twelve are the eight shared spellings — `OUTSIDE_SCOPE` contributing four pairings beyond its first carrier, `NEEDS_REWORK` two, `KEPT`, `STALE`, `METHOD`, `VERIFICATION`, `COMMUNICATION`, and `STEWARDSHIP` one each — every one of them declared and disambiguated in the exemption table (governed by [@prop:precedence]).

![Vocabulary matrix: exported enum member names down the side, declared lines across the top. A cell is marked where a line carries that token. The one token carried by two lines is marked as a collision, and the exempted cell is distinguished from an unexempted one by both its shape and its label, so the plate reads in greyscale.](../output/figures/vocabulary_matrix.png){#fig:vocabulary-matrix width=100%}

## A second line adopts the word

Suppose a fifth line joins the set and reuses `OUTSIDE_SCOPE`. Written as a real package in a temporary directory and declared as a fifth entry:

```text
status: set_colliding
  unexempted: OUTSIDE_SCOPE over ('black_line', 'red_line', 'teal_line')
  [status] set_colliding: 1 cross-line token collision(s) are not covered by a declared exemption
```

The existing exemption did not stretch to cover it. It names exactly two lines, three lines now carry the token, and [@def:exemption-match] requires set equality rather than a subset test, so the exemption stops applying to a collision it no longer describes. This is the behaviour I most wanted to see and least wanted to assume: an exemption written for two parties does not silently license a third. Making the reading legible again means writing a new declaration that says what the word means in the third line, or renaming.

## A package nobody declared

The same temporary package, present and importable but absent from the declaration:

```text
status: set_undeclared
  undeclared_lines: ('teal_line',)
  [declare] scanned 5 candidate packages and found 1 that resolved but were not declared
```

Discovery here is convention-based: the resolver looks for importable top-level packages whose names end in `_line`, plus anything already in `sys.modules`. That finds a package following the naming convention and cannot find one that does not. An empty `undeclared_lines` is a report of what the convention turned up, never a proof that nothing else exists. When a resolver offers no enumeration at all, the derivation says the scan did not happen instead of reporting zero.

## Lines that will not read

Two more temporary packages, one that raises on import and one that imports cleanly while exporting no enum:

```text
status: set_partial
  red_line     import_failed  version=None  :: import raised RuntimeError: this line does not import
  black_line   no_vocabulary  version=9.9.9 :: the package root exports no enum
  golden_line  not_installed  version=None  :: the import system found no such package
  white_line   not_installed  version=None  :: the import system found no such package
```

All four read codes appear at once. The one worth pointing at is `black_line`: it imported, so its real version string was read and kept, but it published no vocabulary, so there was nothing to compare and no registry to size. The reader neither discarded the version it did have nor filled in the two it did not.

## No siblings at all

Run from a directory where none of the sibling packages is importable:

```text
registry_sound()              : True
offline checks passing        : 7 / 7
read_set()                    : set_partial  {'resolved': 0, 'not_installed': 4, ...}
every version/size/digest None: True
check_self_disjointness()     : FAIL — no line vocabulary was available to compare
                                against, so the comparison set was empty;
                                unread lines: ['black_line', 'golden_line',
                                'red_line', 'white_line']
```

The seven offline checks pass, because they are computation over the declaration and need nothing installed. The reading is honestly partial. And self-disjointness fails rather than passing, which is the point of keeping it out of the offline battery: an overlap check that found no overlap because it had nothing to look at is not a result, and reporting it as a pass would be the most convenient lie this package could tell.

![Installation surface: one row per declared line, showing whether it resolved, the version it reported, its registry size, and the first characters of its digest. Unresolved lines render as visibly empty rather than as zero, because a line that could not be read has no size, not a size of none.](../output/figures/installation_surface.png){#fig:installation-surface width=100%}

## A weakened exemption

The last reading is the one that checks the check. Replacing the shipped exemption with one that names both lines but records a meaning for only the first:

```text
exemption_for(...)  -> None
status              : set_colliding
  unexempted: OUTSIDE_SCOPE over ('black_line', 'red_line')
```

The declaration still names the token and still names both lines. It is refused anyway, because an exemption without a meaning for each line it names is a label, and a label does not show that two uses of one spelling are two different things. The same refusal covers every other weakening in [@prop:fail-closed], and no match leaves the collision standing.

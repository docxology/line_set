<!-- Note (2026-07-29): reviewer attribution has been anonymized pending explicit
consent for inclusion in permanently archived DOI records. Attribution will be
restored on confirmation. -->

# Correspondence: design reviews received

This page records external design reviews of Line Set and what this
repository did about them. It is a decision record, not an endorsement chain:
each item names what was adopted, what was deferred with a reason, and what
was declined with a reason.

## 2026-07-29 — "The Space Between the Lines" (an external reviewer, with an analytic reader)

A two-voiced review of the collected line set (dated source: *The Line Set:
The Collected Volume*, 2026-07-27). Its reading of this work: the wrapper is
already the set's modular witness — it declares without evaluating, reads
without reinterpreting, and admits in its own limits section that a missing
colour leaves no trace ("a question nobody has asked yet leaves no trace" —
`manuscript/05_limits.md`). The review's pressure lands elsewhere: each
line's selected status is a safe projection that must not become the whole
state, and the missing layer is a *shared witness register* that co-registers
each line's complete report without ranking, averaging, merging, or
overriding any of them — "precedence without information destruction."

**Adopted here, set-wide:**

- *The common report envelope, documented as the set's convention.* The
  review's smallest implementable piece is a data contract: one envelope per
  line report, under the shared schema string `line.report-envelope/1.0`,
  pointing at — never reinterpreting — the complete native report.
  [envelope.md](envelope.md) now records the shape as the exporting works
  publish it, the rule that each work declares its own literal (alignment by
  convention, never by import), the rule that `native_status` is per-line
  vocabulary and must not be compared, ranked, averaged, or merged across
  lines, and the dated roster of which works export it. Line Set is the right
  home for the convention's *record* precisely because it is the work that
  declares what the set is; it is the wrong home for the convention's
  *implementation*, because a set reading is not a line report.

**Deferred, with a reason:**

- *A manuscript statement of the convention.* The natural neighbour is
  `01b_the_set.md` §"The one shared word", but the manuscript's own contract
  confines sibling facts to the dated reading block in `04_examples.md`, and
  which repositories export an envelope module is a sibling fact. Folding a
  dated sibling roster into the section that states the set's timeless shape
  would blur exactly the line that contract holds. If the envelope becomes
  part of the declaration itself rather than a convention beside it, it earns
  a manuscript section and the re-render that comes with one.

**Declined, by design:**

- The shared witness register itself. The review is explicit that it should
  not be smuggled into any existing line, and it must not be smuggled into
  the wrapper either — a register that stores envelopes, cross-line
  relations, and append-only history inside Line Set would turn the reader
  into exactly the meta-instrument its declaration forbids
  (`WRAPPER_LINE.must_not_become`). A companion work named
  **witness_register** is being scaffolded beside the set; it is a companion,
  not a member, and this repository asserts nothing about its contents.
- Any envelope export from this package. The wrapper has no subject, no
  native verdict about a work, and no report an envelope could point at.
- Any cross-line computation over envelopes — collection, storage, ranking,
  averaging, merging, scoring. The reader compares spellings of exported enum
  member names and stops; [claim_boundaries.md](claim_boundaries.md) already
  refuses the aggregate, and the envelope convention inherits that refusal
  verbatim.


### Wave-3 update (2026-07-29, later the same day)

The settled recording pass was taken at the window's close: paper date and
record moved to 2026-07-29, the compiled volume re-assembled and re-rendered,
and the rendered text read back (`TODO.md` log records the measurements).
`docs/envelope.md`'s roster now also records, as a dated observation, that
the witness_register companion exists and accepted all four lines' exported
envelopes unmodified.

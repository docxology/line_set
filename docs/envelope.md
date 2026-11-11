# The report envelope convention

The declared line instruments use a common report-envelope convention for co-registration:
one record per native report, saying "this instrument, about this subject, at
this review moment, said this — and here is its native readout pointer."
The pointer's scope belongs to its producer. The convention came out of a design review of the collected set
("The Space Between the Lines", 2026-07-29; see
[correspondence.md](correspondence.md)). This page records the convention as
the set-level fact it is. Line Set documents it and does not implement it: a
set reading is not a line report, so the wrapper has no envelope to export.

## The shared wire shape

Each native exporter publishes these ten JSON-compatible fields under
`line.report-envelope/1.0`. Module placement, constants, dataclasses, and mappings
are producer-owned implementation choices, not shared Python interfaces.
Native return types may be mappings or local dataclasses; only the serialized
fields form the shared convention.

| Field | What it carries |
| --- | --- |
| `schema_version` | The shared transport string `line.report-envelope/1.0`. |
| `line_id` | The exporting instrument's coherent native identity; current membership is in `src/line_set/registry.py`, not a four-name whitelist. |
| `subject_id` | What was assessed, in the caller's own reference scheme; stored, not verified. |
| `review_date` | The native report's review date. |
| `registry_version` | The producer's registry or policy marker; it may be separate from the package version. |
| `registry_digest` | The producer's declared registry digest; envelope intake does not recompute its method or certify its source. |
| `native_status` | The instrument's verdict **in that instrument's own vocabulary** — see below. |
| `report_ref` | The producer-defined native readout digest, not a universal guarantee of retained inputs, context, or replay evidence. |
| `source_snapshot_refs` | Caller-supplied provenance for the material the report was about; stored, not verified. |
| `scope_and_nonclaims` | The instrument's non-claims, riding inside the envelope so a stored copy cannot outgrow what the instrument was allowed to say. |

The field *names* are shared. The *type* of `native_status` is deliberately
not: each line publishes whatever its own native projection is — a single
status word where the instrument emits one overall status, a per-record state
list where it emits a ledger. That variation is the point of the field, not a
defect in the convention.

Copper's native status carries its read-state/completeness and per-pool vector,
so rejected, empty, incomplete, and complete declarations remain distinct.
Iron retains scenario and every episode's comparison/flags, not a favorable
scenario aggregate. Main never interprets either projection. Copper and Iron
bind their complete canonical reports; Blue retains its legacy coverage-projection
digest, with normalized input, context, and full replay identity held separately
in its companion report. Consult each producer's contract before claiming
complete correspondence: a status projection or matching pointer is not replay.

A producer's numeric domain does not establish a consumer's admission budget.
Copper preserves exact integers without a decimal-digit bound; Witness accepts
only its own bounded strict JSON, including integers of at most 4096 bits.
A valid large Copper envelope can therefore receive a named Witness intake
refusal without changing Copper's native reading. Do not round, stringify, trim,
or omit the rejected values to obtain acceptance. Retain the complete native
artifact and the refusal; neither envelope export nor intake certifies universal
interoperability or the report's substantive truth.

Violet, Copper, and Iron are PRIVATE producers. Public companion exports require
separate disclosure review and empty `source_snapshot_refs`, not private source
identifiers disguised as provenance. Full native replay evidence stays private.
Empty source references do not authenticate an export or prove that an exercise
occurred. Main's source-withholding option acts on namespace readings, not on
native envelopes.

## Alignment by convention, never by import

Each native producer owns its transport literal, exporter, and serializer;
there is no shared runtime dependency. Main documents this wire convention,
not an envelope implementation. Its separate reader imports published namespace
bindings, never native evaluator or envelope implementations. Witness owns its
local by-value intake and leaves native status opaque.

Wire agreement is a published convention. An out-of-convention export does not
break a sibling's Python imports, but a by-value consumer may refuse it.

## `native_status` is not comparable across lines

`native_status` is one instrument's word in that instrument's vocabulary.
Envelopes from different lines **must not be compared, ranked, averaged,
merged, or scored on it** — the instruments answer different
questions, so a cross-line operation on their status words would be a number
with no referent, the same aggregate this package already refuses in
[claim_boundaries.md](claim_boundaries.md). An envelope is a witness record,
not a score. Anything that needs several envelopes side by side stores them
side by side, untranslated.

## Who exports it

As of 2026-07-29, checked by importing each repository's
`src/<name>/envelope.py` in that repository's own environment on that date —
by import, not file existence, because an earlier check the same day found a
file at golden_line's path that did not yet import: all four lines —
**black_line**, **golden_line**, **red_line**, and **white_line** — export
the envelope, each declaring its own literal and the same ten field names.
golden_line's module landed latest, mid-window. This roster is a dated
observation about sibling repositories, exactly like the reading block in the
manuscript: re-check it against the repositories rather than trusting this
page.

## Why the schema string cannot trip the collision scan

The reader's lexical-separation check compares one thing: the member names of
enum classes exported at each sibling package's root (`enum_tokens` in
`src/line_set/binding.py`). A module-level string constant is invisible to it,
and `"line.report-envelope/1.0"` could never be an enum member name anyway —
member names are Python identifiers, and this string is not one. So four
packages each declaring the same `ENVELOPE_SCHEMA` constant is not a
collision, needs no exemption, and changes no reading.

For the same reason the schema string is deliberately **not** an entry in
`SHARED_TOKENS`. That table exempts vocabulary tokens the collision scan can
actually see; an entry the matcher could never match would be a declaration
about nothing, dressed as a check. The convention is recorded here, as
documentation, which is the layer it lives at. The one way this spelling could
ever reach the scan is indirect: if two or more lines each exported a root
enum with an identical *member* name (say, `REPORT_ENVELOPE`), that would be
an ordinary collision like any other — `SET_COLLIDING` unless a well-formed
`SHARED_TOKENS` exemption names exactly the carrying lines with a distinct
meaning per line. The scan is not weakened for this convention and must not
be.

## Co-registration is outside the set

The 2026-07-29 review's central proposal — a shared witness register that
co-registers each line's envelope, stores cross-line relations as separate
records, and keeps history append-only without ever ranking, averaging,
merging, or overriding any line — is a separate work, deliberately outside
this one and outside every line. A companion work named **witness_register**
now exists beside the set (its own repository at
<https://github.com/docxology/witness_register>, first committed 2026-07-29):
it declares its own `line.report-envelope/1.0` intake literal and, checked
that day, accepted each of the four lines' actually-exported envelopes
unmodified (a 2026-07-29 observation about the then-four-line set, kept
here dated rather than updated in place; the set's current membership is
the registry's to state) — the convention recorded here observed working end to end. It
remains a companion, not a member — it is not in `LINE_SET`, it is not a
color, and nothing further about its contents is asserted here. This package declares the lines of the set and records this shared data contract, and that is the whole of its
part: the reader will not collect envelopes, will not store them, and will
not compute anything across them.

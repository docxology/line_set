# Optional evidence/replay profile

Profile identity: `line.evidence-replay/1.0`. Revision: 2026-10-21.
Scope: a companion record beside a native report/envelope, not a new line,
verdict, envelope exporter or shared evaluator. Opt-in only: absence does not
invalidate a native report or change any Line Set reading. This repository
documents the profile; native owners implement exporters and replay. The
[example](example.json) is hypothetical design material, not an execution receipt.

## Identity domains

Never collapse these independent identities into a trusted flag:

| Domain | Required content and identity rule |
| --- | --- |
| Source | Each entry carries an opaque `ref`, access class (`public`, `restricted`, `unavailable`), optional exact-byte digest and attributed provenance declaration. A digest can remain null where disclosure would leak protected content. A locator is not proof of contents or authorship. |
| Normalized input | `normalized_input` is a reference plus SHA-256 of its exact native canonical bytes and its native schema identity. It must change when input changes even if the output does not. Never substitute a report hash. |
| Registry | Native registry scope, version and digest, reported by its owner. A custom registry must identify itself; it cannot inherit the shipped identity by name. The wrapper does not compute a sibling registry digest. |
| Policy | Effective parameters, including defaults, not only caller overrides. Its independent canonical JSON digest changes with any effective parameter. |
| Context | Profile schema, input identity, registry identity, evaluator revision, effective policy digest, resolved review date, and native input/report/envelope schema identities. Digest this object independently of report content. |
| Report | `native_report` refers to complete unmodified native bytes with its native schema and native content digest convention. It is not proof of subject binding. Shared transport never interprets or ranks its status. |
| Envelope | `subject_bound_envelope` references the exact native subject-bound envelope bytes and a separate exact-byte SHA-256. Native strict validation must check all fields, schema and subject, separately from report correspondence. A report may correspond while an envelope is invalid. |

`schema` must be exactly the profile identity above. `line_id`, `subject_ref`,
`created_by`, `created_at`, `sources`, `normalized_input`, `registry`,
`evaluator_revision`, `effective_policy`, `resolved_review_date`, `native_schemas`,
`context`, `native_report`, `subject_bound_envelope`, `intake_dispositions`,
`verification`, `replay` and `nonclaims` are required fields. Required identities
may explicitly contain null digests with unavailable reasons; they may never
contain invented identifiers. At least one source is required. A source-free
operation must name its explicit no-external-source declaration as a source
record rather than letting an empty inventory appear checked.

An artifact reference contains `ref`, `schema`, `digest`, `digest_method`, and
`unavailable_reason`. A digest is lowercase SHA-256 when method is
`sha256-exact-bytes`; native canonical methods must name their native method and
revision. A null digest requires a nonblank unavailable reason. The input and
output bytes need not be included publicly. `registry` contains `scope`,
`version`, `digest` and `declared_by`, plus `unavailable_reason` if an identity
is absent. Effective policy is a finite passive JSON
object: strings, booleans, null, finite numbers, arrays and string-keyed objects;
never executable iterables, NaN or infinities. Dates are resolved ISO dates;
timezone assumptions and the evaluator's date resolution belong in policy.

For the profile's own policy and context digests only, canonicalize with
Python standard-library JSON: `sort_keys=True`, `ensure_ascii=True`,
`allow_nan=False`, `separators=(",", ":")`, encode UTF-8, then SHA-256.
Reject duplicate JSON object keys before canonicalization. Do not normalize
native report, envelope or source bytes using this convention unless their
owner explicitly uses it. Cross-runtime number encoding requires a new
profile revision or a documented exact canonical-byte artifact.

`context` carries both its complete object and digest. Its object has exactly
`profile`, `normalized_input`, `registry`, `evaluator_revision`, `policy_digest`,
`resolved_review_date`, `native_schemas`. Full artifact references, including
unavailability, are retained in context. The example uses null native identities
because no native experiment has run; the tests compute illustrative policy and
context identities from it rather than publishing fabricated native digests.

## Declared provenance is separate from verification

Every source carries `declared_provenance` with declarant, claim and evidence
class. Classes are submitted declaration, source reference, inspected source,
identity-verified statement and corroborated fact. An exporter records the
declaration; it cannot promote its class merely by exporting it.

`verification` is a nonempty list of independent check records, each with
`predicate`, `outcome`, `verifier`, `method`, `evidence_refs`, and `limits`.
Outcomes are `not_performed`, `unavailable`, `pass`, `fail`. A performed check
needs an identified verifier, actual method and evidence; `pass` applies only
to that predicate. Preserve separate records for source-byte match, native
report correspondence, strict envelope validity, structural reference validity,
external identity/authentication and native replay. A consistent rehash may
pass byte matching without authenticating anything. No generic trusted badge.

`intake_dispositions` is a nonempty list of native schema-tagged dispositions
or an explicit not-performed record. Never translate unknown, malformed,
out-of-scope, contradictory or set-aside inputs into favorable native results.
Do not infer agreement from absence, report equality from hash availability,
or authorization from a complete profile.

## Replay prerequisites and outcomes

`replay` contains `state`, `prerequisites`, `output_ref`, `differences` and
`limits`. State is `not_attempted`, `unavailable`, `reproduced`, `different`,
or `failed`. A nonempty prerequisite inventory names the normalized input
bytes, native registry/configuration, evaluator revision/runtime, resolved date,
native schemas and access authority. Every entry says `available`, `unavailable`
or `not_checked`, with a reason and reference. Inventory only what was inspected.
List every missing prerequisite; do not replace a restricted source with an
empty input. Unavailable replay says nothing about the truth of an assertion.

Only the native owner's execution with all prerequisites can produce a
`reproduced` result: retain exact output bytes, native comparison method and
evidence. `different` retains expected and actual identities and the exact
comparison differences without interpreting substantive correctness. `failed`
retains the execution error. `not_attempted` is the initial scaffold state.
Line Set provides no replay runner and never executes a sibling evaluator.

## Independent acceptance matrix for native owners

| Planted change | Required bounded observation |
| --- | --- |
| Policy changes, native output unchanged | Policy/context identities change, report identity can remain the same. |
| Input changes, native output unchanged | Input/context identities change, report identity can remain the same. |
| Envelope subject/schema/date changes | Strict native envelope validity is rechecked separately from report correspondence. |
| Sources or envelope are consistently rehashed | Byte consistency alone never establishes external authentication. |
| Source access unavailable | Exact missing prerequisites are reported; no assertion is labelled false. |
| Favorable sibling output added | Original native outputs and unresolved decisions remain verbatim; no aggregate. |
| Empty sources, verification checks or prerequisites | Structural acceptance fails rather than treating no scan as success. |

`tests/test_synthesis_materials.py` checks the shipped illustrative profile and
demonstrates identity separation using standard-library hashes. Those tests
are not native exporter tests, full envelope validation, authentication or a
replay receipt. The sibling-owner matrix remains required before study use.

## Privacy and compatibility

Prefer opaque references with separate access controls. Do not embed personal
source text, credentials, private locators or low-entropy protected hashes in
public records. Authentication claims need their own external evidence and
threat model; no signature scheme is invented here. Retain contradictory
statements without adjudicating them. Native reports remain interpretable if
this optional companion is absent or retired. Unknown profile versions remain
unsupported, not silently coerced. A migration preserves old bytes, names its
source and target schema and records transformed fields/losses separately; a
new digest after migration is not the old identity.

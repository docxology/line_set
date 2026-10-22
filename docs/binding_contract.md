# Binding and record contracts

The optional package-root `LINE_SET_BINDING` mapping takes precedence:

```python
LINE_SET_BINDING = {
    "schema": "line-set-binding/1",
    "vocabulary_enums": ("PublishedStatus",),
    "registry": "registry.PRIMARY",
    "digest": "registry_digest",
}
```

Names refer to attributes already exported by the package. The enum tuple must
name every distinct root enum class exactly once; it cannot hide a published
enum. Registry identity is a public attribute path and digest is a public root
callable. The reader passes that package's own registry to its own callable.
An invalid descriptor fails binding and never silently selects the heuristic.
Older packages remain readable with `binding_schema=convention-heuristic`.
Tuple aliases are deduplicated by identity before the largest-tuple rule.

Each observation retains requested/resolved package, origin, distribution and
version when available, resolver policy, binding schema, selected registry and
source revision when known. Explicit source paths refuse a cached source mismatch
without unloading modules. Pinned archive exports carry `.line-set-source.json`
with the full `revision`; origins then use paths relative to the snapshot root.
These are custody records, not authentication of package reports.

Resolve, bind, digest, enumeration-call and enumeration-iteration failures retain
bounded diagnostic text and exception type. Cancellation and process-control
exceptions propagate. `Discovery` separately records capability, attempt,
completion, retained candidate names and resolution outcomes. Partial enumeration
preserves yielded names and never becomes a completed empty scan. A collision
that fails an exemption records observed, declared and unread carriers plus
coverage. Exact carrier equality is unchanged; exempted collisions carry meanings.

Publication is all root bindings, independently of `__all__`. `__members__` names
include aliases; re-exported class objects are counted once. The census separates
declared names, canonical members and distinct spellings. Submodule-only names
remain outside this contract. In-process imports execute code and are not a sandbox.

Canonical declaration and reading schemas are `line-set-declaration/2` and
`line-set-reading/2`. The reading-record envelope is `2.0`. Declaration and
observation identity duplicates are refused. `reading_from_canonical` accepts
only the current schema, recomputes collision/status facts and checks derived
counts. `self_disjointness_from_reading` recomputes wrapper token intersections.
Every discovered candidate outside the declared package identities requires a
resolution outcome, including retained candidates from partial enumeration.
Capability, attempt and completion flags must be booleans. Enumeration failures
require an incomplete recorded attempt; candidates require enumeration capability.
Replay and the pinned-source gate share these checks, so a truthy string or a
completion claim accompanied by an enumeration failure cannot pass either boundary.
Collision exemption and observation-completeness flags also require booleans;
integer or floating-point substitutes cannot pass Python's numeric equality as
canonical flags. Replay compares normalized JSON with types intact, including
derived integer counts. Valid replayed collisions retain their figure markers.
Source revisions use the same full hexadecimal commit grammar on import,
replay and the pinned-source gate.
Optional package versions and digests must remain non-blank strings when
present; registry sizes must remain non-negative integers, excluding booleans.
Replay and the pinned-source gate reject malformed metadata rather than
counting its mere presence as a complete reading.
Derivation stage order stays intact. Reading hashes include diagnostics and
provenance and compare exact records; they are not semantic comparison handles.
Declaration hashes remain separate. Neither hash is tamper evidence.

Migration is explicit: the unversioned canonical forms and `1.0` historical
envelope remain historical evidence in
[the preserved reading](releases/evidence/reading-record-20260901-v1.json).
They are never silently upgraded. A current record requires a new pinned reading
with an explicit date. Schema fixtures and replay negative controls live in the
test suite. A diagnostic change can change the reading hash while the declaration
digest stays fixed.

"""Executed counterexamples from the 2026-10-20 review; no sibling required."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from line_set import LINE_SET, ReadCode, SetStatus, exemption_for, read_set
from line_set.binding import enum_tokens, vocabulary_census
from tests.support import (
    import_sandbox,
    load_line_package,
    resolved,
    write_line_package,
)


def test_manuscript_states_the_actual_import_execution_boundary() -> None:
    text = (
        Path(__file__).resolve().parents[1] / "docs" / "manuscript" / "05_limits.md"
    ).read_text(encoding="utf-8")
    assert "Nothing is executed" not in text
    assert "Importing a sibling executes its package code" in text
    assert "necessary condition for the separation" not in text


@pytest.mark.parametrize(
    "relative",
    [
        "docs/claim_boundaries.md",
        "docs/manuscript/01_introduction.md",
        "docs/manuscript/02a_formalism.md",
        "docs/manuscript/06_conclusion.md",
    ],
)
def test_conceptual_separation_is_not_inferred_from_a_lexical_requirement(
    relative: str,
) -> None:
    text = (Path(__file__).resolve().parents[1] / relative).read_text(encoding="utf-8")
    assert "necessary condition" not in text.lower()


@pytest.mark.parametrize(
    "lines",
    [
        (),
        (LINE_SET[0], LINE_SET[0]),
        (replace(LINE_SET[0], id=" "),),
        (replace(LINE_SET[0], package_name=" "),),
        (LINE_SET[0], replace(LINE_SET[1], package_name=LINE_SET[0].package_name)),
        (object(),),
        (replace(LINE_SET[0], question=None),),
    ],
)
def test_public_reader_rejects_ambiguous_declarations_before_resolution(lines) -> None:
    def forbidden(name):
        pytest.fail(f"invalid declaration reached resolver: {name}")

    with pytest.raises(ValueError, match="declaration"):
        read_set(lines, (), resolver=forbidden)


def test_blank_rationale_is_refused_at_the_matcher() -> None:
    from line_set import SHARED_TOKENS

    item = replace(SHARED_TOKENS[0], rationale=" ")
    assert exemption_for((item,), item.token, item.lines) is None


@pytest.mark.parametrize("alias_on_both", [False, True])
def test_aliases_collide_and_reexports_do_not_inflate_census(
    tmp_path: Path, alias_on_both: bool
) -> None:
    with import_sandbox():
        modules = {}
        for i, entry in enumerate(LINE_SET[:2]):
            extra = (
                (
                    "class Names(Enum):\n    PRIMARY = 'x'\n    SHARED = 'x'\n"
                    "Again = Names\n"
                )
                if i == 0 or alias_on_both
                else "class Names(Enum):\n    SHARED = 'y'\n"
            )
            write_line_package(tmp_path, entry.package_name, extra_source=extra)
            modules[entry.package_name] = load_line_package(
                tmp_path, entry.package_name
            )
        reading = read_set(LINE_SET[:2], (), resolver=lambda n: resolved(n, modules[n]))
        assert reading.status is SetStatus.SET_COLLIDING
        assert "SHARED" in {item.token for item in reading.collisions}
        first = modules[LINE_SET[0].package_name]
        assert enum_tokens(first) == ("PRIMARY", "SHARED")
        census = vocabulary_census(first)
        assert census.enum_classes == 2
        assert census.declared_members == 2
        assert census.canonical_members == 1


def test_valid_small_set_without_exemptions_remains_supported(tmp_path: Path) -> None:
    with import_sandbox():
        modules = {}
        for i, entry in enumerate(LINE_SET[:2]):
            write_line_package(tmp_path, entry.package_name, (f"NAME_{i}",))
            modules[entry.package_name] = load_line_package(
                tmp_path, entry.package_name
            )
        reading = read_set(LINE_SET[:2], (), resolver=lambda n: resolved(n, modules[n]))
        assert reading.status is SetStatus.SET_LEGIBLE
        assert all(o.code is ReadCode.RESOLVED for o in reading.observations)


def test_wrong_resolution_identity_is_not_attributed(tmp_path: Path) -> None:
    with import_sandbox():
        write_line_package(tmp_path, "other_line", ("NAME",))
        module = load_line_package(tmp_path, "other_line")
        reading = read_set(
            LINE_SET[:1], (), resolver=lambda n: resolved("other_line", module)
        )
        assert reading.status is SetStatus.SET_PARTIAL
        assert reading.observations[0].diagnostics[0].phase == "resolve"


def test_explicit_primary_registry_beats_a_larger_secondary(tmp_path: Path) -> None:
    with import_sandbox():
        write_line_package(
            tmp_path,
            "explicit_line",
            ("NAME",),
            registry_sizes={"PRIMARY": 1, "SECONDARY": 4},
            extra_source="LINE_SET_BINDING = {'schema': 'line-set-binding/1', 'vocabulary_enums': ('Vocabulary',), 'registry': 'registry.PRIMARY', 'digest': 'registry_digest'}",
        )
        module = load_line_package(tmp_path, "explicit_line")
        from line_set.binding import read_vocabulary

        vocabulary = read_vocabulary(module)
        assert vocabulary.registry_size == 1
        assert vocabulary.binding_schema == "line-set-binding/1"


def test_registry_tuple_alias_is_not_ambiguous(tmp_path: Path) -> None:
    with import_sandbox():
        write_line_package(
            tmp_path,
            "tuple_line",
            ("NAME",),
            registry_sizes={"PRIMARY": 2},
            extra_source="registry.ALIAS = registry.PRIMARY",
        )
        from line_set.binding import read_vocabulary

        vocabulary = read_vocabulary(load_line_package(tmp_path, "tuple_line"))
        assert vocabulary.registry_size == 2
        assert vocabulary.binding_schema == "convention-heuristic"


@pytest.mark.parametrize("failure", ["resolve", "bind"])
def test_failures_are_contained_by_phase(tmp_path: Path, failure: str) -> None:
    with import_sandbox():
        write_line_package(
            tmp_path,
            LINE_SET[0].package_name,
            ("NAME",),
            extra_source="def __getattr__(name):\n    raise RuntimeError('planted attribute failure')",
        )
        module = load_line_package(tmp_path, LINE_SET[0].package_name)

        def resolver(name):
            if failure == "resolve":
                raise RuntimeError("planted resolver failure")
            return resolved(name, module)

        reading = read_set(LINE_SET[:1], (), resolver=resolver)
        observation = reading.observations[0]
        assert observation.code is ReadCode.IMPORT_FAILED
        assert observation.diagnostics[0].phase == failure
        assert observation.diagnostics[0].exception_type == "RuntimeError"


@pytest.mark.parametrize(
    "mode", ["absent", "complete", "iterate", "invalid", "candidate"]
)
def test_discovery_uncertainty_survives_serialization(mode: str) -> None:
    from line_set import canonical_reading
    from tests.support import absent

    class Resolver:
        def __call__(self, name):
            return absent(name)

        def candidates(self):
            if mode == "iterate":

                def generate():
                    yield "extra_line"
                    raise RuntimeError("planted iteration failure")

                return generate()
            return (
                [3]
                if mode == "invalid"
                else (["extra_line"] if mode == "candidate" else [])
            )

    resolver = (lambda n: absent(n)) if mode == "absent" else Resolver()
    reading = read_set(LINE_SET[:1], (), resolver=resolver)
    discovery = reading.discovery
    assert discovery.capable is (mode != "absent")
    assert discovery.completed is (mode in {"complete", "candidate"})
    if mode in {"iterate", "invalid"}:
        assert discovery.diagnostics
    if mode == "candidate":
        assert discovery.outcomes[0].code is ReadCode.NOT_INSTALLED
    assert '"discovery"' in canonical_reading(reading)


def test_missing_exemption_carrier_is_explained(tmp_path: Path) -> None:
    from line_set import SharedToken
    from tests.support import absent

    entries = LINE_SET[:3]
    item = SharedToken(
        "SHARED",
        tuple(e.id for e in entries),
        tuple((e.id, e.question) for e in entries),
        "distinct uses",
    )
    with import_sandbox():
        answers = {}
        for entry in entries[:2]:
            write_line_package(tmp_path, entry.package_name, ("SHARED",))
            answers[entry.package_name] = resolved(
                entry.package_name, load_line_package(tmp_path, entry.package_name)
            )
        reading = read_set(
            entries, (item,), resolver=lambda n: answers.get(n, absent(n))
        )
        assert reading.status is SetStatus.SET_COLLIDING
        mismatch = reading.collisions[0]
        assert mismatch.unread_declared_carriers == (entries[2].id,)
        assert mismatch.declared_carriers == tuple(sorted(item.lines))
        assert not mismatch.fully_observed


def test_probes_cover_every_exemption_and_keep_late_duplicates() -> None:
    from line_set import SHARED_TOKENS, exemption_probes, probes_hold

    probes = exemption_probes(LINE_SET, SHARED_TOKENS)
    assert {p.declared_token for p in probes} == {t.token for t in SHARED_TOKENS}
    assert len(probes) == 7 * len(SHARED_TOKENS)
    assert not probes_hold(
        exemption_probes(LINE_SET, SHARED_TOKENS + (SHARED_TOKENS[-1],))
    )


def test_canonical_boundaries_reject_duplicate_identities() -> None:
    from line_set import canonical_registry, canonical_reading
    from tests.support import absent

    with pytest.raises(ValueError):
        canonical_registry((LINE_SET[0], LINE_SET[0]))
    reading = read_set(LINE_SET[:1], (), resolver=absent)
    with pytest.raises(ValueError):
        canonical_reading(replace(reading, observations=reading.observations * 2))


def test_hand_constructed_reading_cannot_hide_a_wrapper_collision() -> None:
    from line_set import (
        WRAPPER_LINE,
        LineObservation,
        SetReading,
        self_disjointness_from_reading,
    )

    observations = tuple(
        LineObservation(e.id, ReadCode.RESOLVED, tokens=("SHARED",))
        for e in (LINE_SET[0], WRAPPER_LINE)
    )
    reading = SetReading(
        SetStatus.SET_LEGIBLE, observations, (), (), (), "", "2026-10-21"
    )
    assert not self_disjointness_from_reading(reading).passed


def test_canonical_schemas_have_versions() -> None:
    import json
    from line_set import canonical_registry, canonical_reading
    from tests.support import absent

    assert (
        json.loads(canonical_registry(LINE_SET))["schema_version"]
        == "line-set-declaration/2"
    )
    reading = read_set(LINE_SET[:1], (), resolver=absent)
    assert (
        json.loads(canonical_reading(reading))["schema_version"] == "line-set-reading/2"
    )


def test_documented_extension_executes_without_siblings() -> None:
    import re
    import line_set

    text = (
        Path(__file__).resolve().parents[1] / "docs" / "extensibility.md"
    ).read_text()
    blocks = re.findall(r"```python\n(.*?)```", text, re.DOTALL)
    namespace = dict(vars(line_set))
    assert len(blocks) >= 2
    for block in blocks:
        exec(compile(block, "docs/extensibility.md", "exec"), namespace)
    extended = namespace["extended"]
    assert len({e.id for e in extended}) == len(extended)
    assert all(
        r.passed for r in line_set.all_invariants(extended, line_set.SHARED_TOKENS)
    )


def test_cached_package_cannot_silently_override_requested_source(
    tmp_path: Path,
) -> None:
    from line_set.binding import ImportResolver

    with import_sandbox():
        first, second = tmp_path / "first", tmp_path / "second"
        for root in (first, second):
            write_line_package(root, "cache_line", ("NAME",))
        load_line_package(first, "cache_line")
        result = ImportResolver([second])("cache_line")
        assert result.code is ReadCode.IMPORT_FAILED
        assert result.diagnostics[0].exception_type == "SourceMismatch"


def test_independent_finite_carrier_and_meaning_oracle() -> None:
    from itertools import combinations
    from line_set import SharedToken

    ids = tuple(e.id for e in LINE_SET[:3])
    for size in range(len(ids) + 1):
        for declared in combinations(ids, size):
            for observed_size in range(len(ids) + 1):
                for observed in combinations(ids, observed_size):
                    for omitted in (None, *declared):
                        item = SharedToken(
                            "WORD",
                            declared,
                            tuple((name, name) for name in declared if name != omitted),
                            "distinct uses",
                        )
                        expected = (
                            len(declared) >= 2
                            and set(observed) == set(declared)
                            and omitted is None
                        )
                        assert (
                            exemption_for((item,), "WORD", observed) is not None
                        ) == expected


def test_canonical_replay_refuses_tampered_derived_facts() -> None:
    import json
    from line_set import canonical_reading, reading_from_canonical
    from tests.support import absent

    reading = read_set(LINE_SET[:1], (), resolver=absent, as_of="2026-10-21")
    canonical = canonical_reading(reading)
    assert canonical_reading(reading_from_canonical(canonical)) == canonical
    payload = json.loads(canonical)
    payload["status"] = "set_legible"
    with pytest.raises(ValueError):
        reading_from_canonical(json.dumps(payload))
    payload["schema_version"] = "line-set-reading/1"
    with pytest.raises(ValueError, match="schema"):
        reading_from_canonical(json.dumps(payload))


def test_diagnostic_hash_change_does_not_claim_registry_drift() -> None:
    from line_set import reading_digest
    from tests.support import absent

    reading = read_set(LINE_SET[:1], (), resolver=absent)
    changed = replace(
        reading,
        observations=(replace(reading.observations[0], detail="different diagnostic"),),
    )
    assert changed.set_digest == reading.set_digest
    assert reading_digest(changed) != reading_digest(reading)


def test_schema_golden_fixture_is_exact_and_replayable() -> None:
    import json
    from line_set import (
        LineEntry,
        canonical_registry,
        canonical_reading,
        reading_from_canonical,
    )
    from tests.support import absent

    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "canonical-schemas-v2.json").read_text()
    )
    entry = LineEntry(
        "example_line",
        "example",
        "Which names?",
        "Read names",
        "A substantive evaluator",
        None,
        1,
        "example_line",
        "entries",
        "status",
    )
    reading = read_set((entry,), (), resolver=absent, as_of="2026-10-21")
    assert json.loads(canonical_registry((entry,), ())) == fixture["declaration"]
    assert json.loads(canonical_reading(reading)) == fixture["reading"]
    assert canonical_reading(
        reading_from_canonical(json.dumps(fixture["reading"]))
    ) == canonical_reading(reading)


def test_pinned_integration_gate_has_real_positive_and_negative_inputs(
    tmp_path: Path,
) -> None:
    import json
    from line_set import check_pinned_sources
    from line_set.binding import ImportResolver
    from tests.support import absent

    assert not check_pinned_sources(read_set(LINE_SET[:1], (), resolver=absent)).passed
    with import_sandbox():
        name = LINE_SET[0].package_name
        write_line_package(
            tmp_path / "src", name, ("NAME",), registry_sizes={"PRIMARY": 1}
        )
        receipt = tmp_path / ".line-set-source.json"
        receipt.write_text(json.dumps({"revision": "a" * 40}))
        reading = read_set(
            LINE_SET[:1],
            (),
            resolver=ImportResolver([tmp_path / "src"]),
            as_of="2026-10-21",
        )
        assert check_pinned_sources(reading).passed
        assert (
            reading.observations[0].provenance.module_origin
            == f"{name}/src/{name}/__init__.py"
        )
        bad = replace(reading, discovery=replace(reading.discovery, completed=False))
        assert not check_pinned_sources(bad).passed
        empty = replace(reading, observations=())
        assert not check_pinned_sources(empty).passed


@pytest.mark.parametrize(
    "descriptor",
    [
        "42",
        "{'schema':'unknown'}",
        "{'schema':'line-set-binding/1', 'vocabulary_enums': ()}",
        "{'schema':'line-set-binding/1', 'vocabulary_enums': ('Vocabulary', 'Vocabulary')}",
        "{'schema':'line-set-binding/1', 'vocabulary_enums': ('Vocabulary',), 'registry': '_private'}",
        "{'schema':'line-set-binding/1', 'vocabulary_enums': ('Vocabulary',), 'registry': '__version__'}",
        "{'schema':'line-set-binding/1', 'vocabulary_enums': ('Vocabulary',), 'registry': 'registry.PRIMARY', 'digest': 7}",
        "{'schema':'line-set-binding/1', 'vocabulary_enums': ('Vocabulary',), 'registry': 'registry.PRIMARY', 'digest': 'Vocabulary'}",
    ],
)
def test_invalid_descriptor_never_silently_selects_heuristic(
    tmp_path: Path, descriptor: str
) -> None:
    with import_sandbox():
        entry = LINE_SET[0]
        extra = (
            f"LINE_SET_BINDING = {descriptor}\nVocabulary = None"
            if "'digest': 'Vocabulary'" in descriptor
            else f"LINE_SET_BINDING = {descriptor}"
        )
        write_line_package(
            tmp_path,
            entry.package_name,
            ("NAME",),
            registry_sizes={"PRIMARY": 1},
            extra_source=extra,
        )
        module = load_line_package(tmp_path, entry.package_name)
        reading = read_set((entry,), (), resolver=lambda n: resolved(n, module))
        assert reading.observations[0].code is ReadCode.IMPORT_FAILED
        assert reading.observations[0].diagnostics[0].phase == "bind"


@pytest.mark.parametrize("explicit", [False, True])
def test_digest_failure_is_structured_without_inventing_a_digest(
    tmp_path: Path, explicit: bool
) -> None:
    with import_sandbox():
        entry = LINE_SET[0]
        extra = (
            "LINE_SET_BINDING = {'schema':'line-set-binding/1', 'vocabulary_enums': ('Vocabulary',), 'registry':'registry.PRIMARY', 'digest':'registry_digest'}"
            if explicit
            else ""
        )
        write_line_package(
            tmp_path,
            entry.package_name,
            ("NAME",),
            registry_sizes={"PRIMARY": 1},
            digest_body="raise RuntimeError('planted digest failure')",
            extra_source=extra,
        )
        module = load_line_package(tmp_path, entry.package_name)
        reading = read_set((entry,), (), resolver=lambda n: resolved(n, module))
        observation = reading.observations[0]
        assert observation.code is ReadCode.RESOLVED
        assert observation.registry_digest is None
        assert observation.diagnostics[0].phase == "digest"
        assert observation.diagnostics[0].exception_type == "RuntimeError"


def test_process_control_is_not_converted_to_absence() -> None:
    def resolver(name):
        raise KeyboardInterrupt("cancel")

    with pytest.raises(KeyboardInterrupt):
        read_set(LINE_SET[:1], (), resolver=resolver)


def test_malformed_exemption_fields_fail_before_import() -> None:
    from line_set import SharedToken

    malformed = SharedToken("WORD", 7, (), "reason")

    def resolver(name):
        pytest.fail("malformed declaration reached import")

    with pytest.raises(ValueError, match="declaration"):
        read_set(LINE_SET[:1], (malformed,), resolver=resolver)


def test_carrier_identity_is_not_coerced_to_text() -> None:
    from line_set import SharedToken

    item = SharedToken(
        "WORD", ("1", "2"), (("1", "first use"), ("2", "second use")), "distinct uses"
    )
    assert exemption_for((item,), "WORD", (1, 2)) is None


def test_alias_introduction_changes_tokens_and_exact_reading_hash(
    tmp_path: Path,
) -> None:
    from enum import Enum
    from line_set import reading_digest

    with import_sandbox():
        entry = LINE_SET[0]
        write_line_package(tmp_path, entry.package_name, ("PRIMARY",))
        module = load_line_package(tmp_path, entry.package_name)
        first = read_set(
            (entry,), (), resolver=lambda n: resolved(n, module), as_of="2026-10-21"
        )
        module.Vocabulary = Enum("Vocabulary", {"PRIMARY": "x", "ALIAS": "x"})
        second = read_set(
            (entry,), (), resolver=lambda n: resolved(n, module), as_of="2026-10-21"
        )
        assert second.observations[0].tokens == ("ALIAS", "PRIMARY")
        assert first.set_digest == second.set_digest
        assert reading_digest(first) != reading_digest(second)


def test_observation_permutations_preserve_canonical_bytes(tmp_path: Path) -> None:
    from line_set import canonical_reading

    with import_sandbox():
        answers = {}
        for index, entry in enumerate(LINE_SET[:2]):
            write_line_package(tmp_path, entry.package_name, (f"NAME_{index}",))
            answers[entry.package_name] = load_line_package(
                tmp_path, entry.package_name
            )
        reading = read_set(LINE_SET[:2], (), resolver=lambda n: resolved(n, answers[n]))
        assert canonical_reading(reading) == canonical_reading(
            replace(reading, observations=tuple(reversed(reading.observations)))
        )


def test_replay_rejects_duplicate_exemptions_and_inconsistent_discovery() -> None:
    from line_set import SHARED_TOKENS, canonical_reading
    from tests.support import absent

    reading = read_set(LINE_SET, SHARED_TOKENS, resolver=absent)
    for invalid in (
        replace(reading, exemptions=SHARED_TOKENS + (SHARED_TOKENS[-1],)),
        replace(reading, discovery=replace(reading.discovery, completed=True)),
    ):
        with pytest.raises(ValueError):
            canonical_reading(invalid)


@pytest.mark.parametrize(
    "case",
    [
        "counts",
        "extra_field",
        "missing_field",
        "tokens",
        "code",
        "collision",
        "candidates",
        "outcomes",
        "undeclared",
        "date",
    ],
)
def test_imported_records_refuse_inconsistent_or_malformed_facts(case: str) -> None:
    import json
    from line_set import canonical_reading, reading_from_canonical
    from tests.support import absent

    payload = json.loads(
        canonical_reading(
            read_set(LINE_SET[:1], (), resolver=absent, as_of="2026-10-21")
        )
    )
    if case == "counts":
        payload["counts"]["not_installed"] += 1
    elif case == "extra_field":
        payload["unsupported"] = True
    elif case == "missing_field":
        del payload["discovery"]
    elif case == "tokens":
        payload["observations"][0]["tokens"] = None
    elif case == "code":
        payload["observations"][0]["code"] = "resolved"
    elif case == "collision":
        payload["collisions"] = [
            {
                "token": "UNOBSERVED",
                "lines": ["one_line", "two_line"],
                "exempted": False,
                "rationale": "",
                "meanings": [],
                "declared_carriers": [],
                "unread_declared_carriers": [],
                "fully_observed": True,
            }
        ]
    elif case == "candidates":
        payload["discovery"]["candidates"] = [3]
    elif case == "outcomes":
        payload["discovery"]["outcomes"] = [
            {"package_name": "extra_line", "code": "resolved", "diagnostics": []}
        ]
    elif case == "undeclared":
        payload["undeclared_lines"] = ["extra_line"]
    else:
        payload["read_as_of"] = "undated"
    with pytest.raises(ValueError):
        reading_from_canonical(json.dumps(payload))


def test_admission_does_not_relabel_an_independent_id_check() -> None:
    from line_set import all_invariants, check_distinct_line_ids

    lines = (replace(LINE_SET[0], package_name=" "), *LINE_SET[1:])
    results = all_invariants(lines)
    identity_result = next(
        result for result in results if result.name == "distinct_line_ids"
    )
    assert identity_result == check_distinct_line_ids(lines)
    assert any(
        result.name == "declaration_admission" and not result.passed
        for result in results
    )


def test_case_invariant_probe_still_changes_input() -> None:
    from line_set import SharedToken, exemption_probes, probes_hold

    item = SharedToken(
        "123",
        tuple(e.id for e in LINE_SET[:2]),
        tuple((e.id, e.question) for e in LINE_SET[:2]),
        "distinct uses",
    )
    probes = exemption_probes(LINE_SET[:2], (item,))
    assert probes_hold(probes)
    assert probes[2].query_token != item.token


def _pinned_audit_reading(root: Path, extra: bool = False):
    import json
    from line_set.binding import ImportResolver

    name = "audit_declared_line"
    write_line_package(root / "src", name, ("DECLARED",), registry_sizes={"PRIMARY": 1})
    if extra:
        write_line_package(root / "src", "audit_extra_line", ("EXTRA",))
    (root / ".line-set-source.json").write_text(json.dumps({"revision": "a" * 40}))
    return read_set(
        (replace(LINE_SET[0], id=name, package_name=name),),
        (),
        resolver=ImportResolver([root / "src"]),
        as_of="2026-10-21",
    )


def test_replay_requires_an_outcome_for_every_extra_candidate(tmp_path: Path) -> None:
    import json
    from line_set import canonical_reading, reading_from_canonical

    with import_sandbox():
        reading = _pinned_audit_reading(tmp_path, extra=True)
        assert reading.status is SetStatus.SET_UNDECLARED
        payload = json.loads(canonical_reading(reading))
        payload["discovery"]["outcomes"] = []
        payload["undeclared_lines"] = []
        payload["status"] = "set_legible"
        with pytest.raises(ValueError, match="outcome"):
            reading_from_canonical(json.dumps(payload))


@pytest.mark.parametrize("revision", ["not-a-revision", "f" * 39, "g" * 40, 12])
def test_replay_and_pinned_gate_reject_malformed_revisions(
    tmp_path: Path, revision
) -> None:
    import json
    from line_set import canonical_reading, check_pinned_sources, reading_from_canonical

    with import_sandbox():
        reading = _pinned_audit_reading(tmp_path)
        assert check_pinned_sources(reading).passed
        malformed = replace(
            reading,
            observations=(
                replace(
                    reading.observations[0],
                    provenance=replace(
                        reading.observations[0].provenance, source_revision=revision
                    ),
                ),
            ),
        )
        assert not check_pinned_sources(malformed).passed
        payload = json.loads(canonical_reading(reading))
        payload["observations"][0]["provenance"]["source_revision"] = revision
        with pytest.raises(ValueError, match="revision"):
            reading_from_canonical(json.dumps(payload))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("version", 7),
        ("version", " "),
        ("registry_digest", []),
        ("registry_digest", ""),
        ("registry_size", True),
        ("registry_size", -1),
        ("registry_size", "eleven"),
        ("registry_size", 1.5),
    ],
)
def test_replay_and_pinned_gate_reject_malformed_package_metadata(
    tmp_path: Path, field: str, value
) -> None:
    import json
    from line_set import canonical_reading, check_pinned_sources, reading_from_canonical

    with import_sandbox():
        reading = _pinned_audit_reading(tmp_path)
        assert check_pinned_sources(reading).passed
        malformed = replace(
            reading,
            observations=(replace(reading.observations[0], **{field: value}),),
        )
        assert not check_pinned_sources(malformed).passed
        payload = json.loads(canonical_reading(reading))
        payload["observations"][0][field] = value
        with pytest.raises(ValueError, match="metadata"):
            reading_from_canonical(json.dumps(payload))


def test_full_table_query_mutations_do_not_hit_other_valid_exemptions() -> None:
    from line_set import SharedToken, exemption_probes, probes_hold

    ids = tuple(e.id for e in LINE_SET[:2])
    meanings = tuple((name, "distinct use " + name) for name in ids)
    shared = tuple(
        SharedToken(token, ids, meanings, "distinct meanings")
        for token in ("WORD", "WOR", "word", "WORD_mutation")
    )
    assert all(exemption_for(shared, e.token, ids) is e for e in shared)
    probes = exemption_probes(LINE_SET[:2], shared)
    assert probes_hold(probes)
    assert all(
        probe.query_token not in {item.token for item in shared}
        for probe in probes
        if probe.name in {"changed token spelling", "changed token case or spelling"}
    )


@pytest.mark.parametrize("phase", ["import", "find_spec"])
def test_real_importer_preserves_caught_exception_type(
    tmp_path: Path, phase: str
) -> None:
    from line_set.binding import ImportResolver, resolve_package

    with import_sandbox():
        name = "audit_broken_line"
        write_line_package(tmp_path, name, raise_on_import="planted import failure")
        requested = name if phase == "import" else name + ".nested"
        result = resolve_package(ImportResolver([tmp_path]), requested)
        assert result.code is ReadCode.IMPORT_FAILED
        assert result.diagnostics[0].exception_type == "RuntimeError"
        assert result.diagnostics[0].phase == "resolve"

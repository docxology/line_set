"""Guard hypothetical design material; demonstrate identities, not native replay."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "docs" / "admission" / "cases.json"
EXAMPLE = ROOT / "docs" / "evidence" / "example.json"


def checked_cases(document: dict) -> None:
    """Guard this revision's unexecuted corpus, never future study findings."""
    assert document["schema"] == "line-set.admission-cases/1.0"
    assert document["execution"] == "not_run"
    assert document["case_class"] == "hypothetical_design_material"
    cases = document["cases"]
    assert cases, "empty case scan"
    ids = [case["id"] for case in cases]
    assert len(set(ids)) == len(ids), "duplicate identity"
    assert Counter(case["group"] for case in cases) == {
        "repair": 6, "control": 6, "ambiguous": 6,
    }
    for case in cases:
        for field in ("id", "title", "scenario", "question", "constraint"):
            assert case[field].strip(), f"missing {field}"
        assert case["source_class"] == "hypothetical"
        assert case["contrast_design"]["held_fixed"].strip()
        assert case["contrast_design"]["varied"].strip()
        assert case["contrast_design"]["execution"] == "not_run"
        assert case["matched_case"] is None or case["matched_case"] in ids
        for field in (
            "existing_family_representation", "witness_relations_and_returns",
            "missing_distinction_hypothesis", "minimal_native_extension",
            "separate_repair_record", "study_result",
        ):
            assert case[field] is None, f"manufactured {field}"
        for field in ("native_outputs", "evidence_profile_refs", "reviewer_results"):
            assert case[field] == [], f"manufactured {field}"


def checked_profile(document: dict) -> None:
    """Check the illustrative inventory, not general native envelope validity."""
    assert document["schema"] == "line.evidence-replay/1.0"
    assert document["sources"], "empty source scan"
    assert document["intake_dispositions"], "empty intake scan"
    for source in document["sources"]:
        assert source["digest"] is None and source["unavailable_reason"].strip()
        assert source["declared_provenance"]["evidence_class"] == "submitted declaration"
    for field in ("normalized_input", "native_report", "subject_bound_envelope"):
        assert document[field]["digest"] is None
        assert document[field]["unavailable_reason"].strip()
    checks = document["verification"]
    assert checks, "empty verification scan"
    assert {item["predicate"] for item in checks} == {
        "source-byte match", "native report correspondence", "strict envelope validity",
        "structural reference validity", "external identity/authentication", "native replay",
    }
    assert len({item["predicate"] for item in checks}) == len(checks)
    for item in checks:
        assert item["outcome"] == "not_performed"
        assert item["verifier"] is None and item["method"] is None
        assert item["evidence_refs"] == [] and item["limits"].strip()
    replay = document["replay"]
    assert replay["state"] == "not_attempted"
    assert replay["output_ref"] is None and replay["differences"] == []
    assert replay["prerequisites"], "empty prerequisite scan"
    assert {item["name"] for item in replay["prerequisites"]} == {
        "normalized input bytes", "native registry/configuration",
        "evaluator revision/runtime", "resolved date", "native schemas", "access authority",
    }
    for item in replay["prerequisites"]:
        assert item["state"] in {"unavailable", "not_checked"}
        assert item["reason"].strip()
    assert document["nonclaims"]


def identity(value: object) -> str:
    """Reference policy/context convention; no native canonicalizer."""
    payload = json.dumps(
        value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def context(profile: dict) -> dict:
    return {
        "profile": profile["schema"],
        "normalized_input": profile["normalized_input"],
        "registry": profile["registry"],
        "evaluator_revision": profile["evaluator_revision"],
        "policy_digest": identity(profile["effective_policy"]),
        "resolved_review_date": profile["resolved_review_date"],
        "native_schemas": profile["native_schemas"],
    }


def test_shipped_materials_are_hypothetical_and_unexecuted() -> None:
    checked_cases(json.loads(CORPUS.read_text(encoding="utf-8")))
    checked_profile(json.loads(EXAMPLE.read_text(encoding="utf-8")))


@pytest.mark.parametrize("defect", ["empty", "duplicate", "result", "constraint", "label"])
def test_corpus_guard_rejects_planted_bad_material(defect: str) -> None:
    document = json.loads(CORPUS.read_text(encoding="utf-8"))
    if defect == "empty":
        document["cases"] = []
    elif defect == "duplicate":
        document["cases"][1]["id"] = document["cases"][0]["id"]
    elif defect == "result":
        document["cases"][0]["study_result"] = "admit"
    elif defect == "constraint":
        document["cases"][0]["constraint"] = " "
    else:
        document["cases"][0]["source_class"] = "observed"
    with pytest.raises(AssertionError):
        checked_cases(document)


@pytest.mark.parametrize("field", ["sources", "verification", "prerequisites", "intake"])
def test_profile_guard_refuses_empty_scan_sets(field: str) -> None:
    document = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    if field == "prerequisites":
        document["replay"][field] = []
    else:
        document["intake_dispositions" if field == "intake" else field] = []
    with pytest.raises(AssertionError):
        checked_profile(document)


def test_profile_cannot_turn_consistency_into_authentication() -> None:
    document = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    document["verification"][4]["outcome"] = "pass"
    with pytest.raises(AssertionError):
        checked_profile(document)


@pytest.mark.parametrize("field", ["effective_policy", "normalized_input", "registry",
                                  "evaluator_revision", "resolved_review_date", "native_schemas"])
def test_context_changes_independently_of_report_content(field: str) -> None:
    original = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    changed = copy.deepcopy(original)
    if field in {"evaluator_revision", "resolved_review_date"}:
        changed[field] = "illustrative-change"
    else:
        changed[field]["illustrative_change"] = True
    assert identity(context(changed)) != identity(context(original))
    assert changed["native_report"] == original["native_report"]
    reordered = dict(reversed(list(context(original).items())))
    assert identity(reordered) == identity(context(original))


def test_byte_identities_remain_distinct(tmp_path: Path) -> None:
    artifacts = [tmp_path / name for name in ("input", "report", "envelope")]
    for artifact in artifacts:
        artifact.write_bytes(artifact.name.encode())
    before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in artifacts]
    artifacts[0].write_bytes(b"changed-input")
    artifacts[2].write_bytes(b"changed-subject-bound-envelope")
    after = [hashlib.sha256(path.read_bytes()).hexdigest() for path in artifacts]
    assert before[0] != after[0] and before[2] != after[2]
    assert before[1] == after[1]
    # Byte comparison establishes neither native validity nor authorship.


def test_nonfinite_policy_is_rejected() -> None:
    with pytest.raises(ValueError):
        identity({"limit": float("nan")})

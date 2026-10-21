"""Historical producer metadata must not conceal any measurement disagreement."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from line_set.record_identity import record_matches, record_text_matches

RECORD = Path(__file__).resolve().parents[1] / "docs" / "manuscript" / "reading_record.json"


def test_only_producer_version_may_differ() -> None:
    held = json.loads(RECORD.read_text(encoding="utf-8"))
    current = copy.deepcopy(held)
    current["package_version"] = "99.0.0"
    assert record_matches(held, current)
    assert held == json.loads(RECORD.read_text(encoding="utf-8"))
    for key in held.keys() - {"package_version"}:
        changed = copy.deepcopy(current)
        changed[key] = {"planted": "measurement disagreement"}
        assert not record_matches(held, changed), key
        missing = copy.deepcopy(current)
        del missing[key]
        assert not record_matches(held, missing), key
    current["unexpected"] = "planted"
    assert not record_matches(held, current)


@pytest.mark.parametrize("version", [None, "", "not-a-version", 1])
def test_absent_or_malformed_producer_is_refused(version: object) -> None:
    held = json.loads(RECORD.read_text(encoding="utf-8"))
    current = copy.deepcopy(held)
    current["package_version"] = version
    assert not record_matches(held, current)
    assert not record_matches(current, held)
    assert not record_matches({}, {})


def test_text_comparison_preserves_canonical_byte_check() -> None:
    text = RECORD.read_text(encoding="utf-8")
    current = json.loads(text)
    current["package_version"] = "99.0.0"
    assert record_text_matches(text, current)
    assert not record_text_matches(text + " ", current)
    assert not record_text_matches("{", current)
    assert not record_text_matches("[]", current)
    assert not record_text_matches("{}", current)
    duplicated = text.replace('"package_version":', '"package_version": "1.2.3", "package_version":')
    assert not record_text_matches(duplicated, current)

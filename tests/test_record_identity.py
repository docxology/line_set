"""Historical producer metadata must not conceal any measurement disagreement."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from line_set.record_identity import record_bytes_match, record_matches
from line_set.registry import LINE_SET
from tests.support import write_line_package

RECORD = (
    Path(__file__).resolve().parents[1] / "docs" / "manuscript" / "reading_record.json"
)


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


def test_empty_measurements_are_refused() -> None:
    held = {"package_version": "1.0.0"}
    current = {"package_version": "2.0.0"}
    complete = json.loads(RECORD.read_bytes())
    assert not record_matches(held, current)
    assert not record_matches(held, complete)
    assert not record_matches(complete, current)
    payload = (json.dumps(held, indent=2, sort_keys=True) + "\n").encode("utf-8")
    assert not record_bytes_match(payload, current)


def test_comparison_preserves_canonical_bytes() -> None:
    payload = RECORD.read_bytes()
    current = json.loads(payload)
    current["package_version"] = "99.0.0"
    assert record_bytes_match(payload, current)
    for malformed in (
        payload + b" ",
        b"{",
        b"[]",
        b"{}",
        b"\xff",
        payload.replace(b"\n", b"\r\n"),
        payload.replace(b"\n", b"\r"),
        b"\xef\xbb\xbf" + payload,
        payload.decode("utf-8").encode("utf-16"),
    ):
        assert not record_bytes_match(malformed, current)
    duplicated = payload.replace(
        b'"package_version":', b'"package_version": "1.2.3", "package_version":'
    )
    assert not record_bytes_match(duplicated, current)


@pytest.mark.parametrize("newline", [b"\r\n", b"\r"])
def test_cli_refuses_noncanonical_line_endings(tmp_path: Path, newline: bytes) -> None:
    root = Path(__file__).resolve().parents[1]
    siblings = tmp_path / "siblings"
    for index, line in enumerate(LINE_SET):
        write_line_package(
            siblings / line.package_name / "src",
            line.package_name,
            tokens=(f"TOKEN_{index}",),
        )
    env = {
        **os.environ,
        "LINE_SET_SIBLINGS": str(siblings),
        "PYTHONPATH": str(root / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    held = tmp_path / "reading.json"
    command = [
        sys.executable,
        str(root / "scripts" / "record_reading.py"),
        "--as-of",
        "2026-09-01",
        "--out",
        str(held),
    ]
    written = subprocess.run(command, env=env, capture_output=True, text=True)
    assert written.returncode == 0, written.stderr
    checked = subprocess.run(
        command + ["--check"], env=env, capture_output=True, text=True
    )
    assert checked.returncode == 0, checked.stderr
    canonical = held.read_bytes()
    held.write_bytes(canonical.replace(b"\n", newline))
    refused = subprocess.run(
        command + ["--check"], env=env, capture_output=True, text=True
    )
    assert refused.returncode != 0, refused.stdout
    assert "disagrees" in refused.stderr

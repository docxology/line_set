"""Compare dated measurements without relabeling their historical producer.

Producer version is metadata, not a measurement identity. This comparison
neither rewrites the held record nor authenticates who produced it.
"""

from __future__ import annotations

import json
import re


def _same_measurement(left: object, right: object) -> bool:
    """Compare nested measurements without Python's boolean/numeric coercion."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            _same_measurement(value, right[key]) for key, value in left.items()
        )
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(
            _same_measurement(a, b) for a, b in zip(left, right)
        )
    return left == right


def record_matches(held: dict[str, object], current: dict[str, object]) -> bool:
    for record in (held, current):
        version = record.get("package_version")
        if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
            return False
        if not record.keys() - {"package_version"}:
            return False
    return _same_measurement(
        {key: value for key, value in held.items() if key != "package_version"},
        {key: value for key, value in current.items() if key != "package_version"},
    )


def record_bytes_match(payload: bytes, current: dict[str, object]) -> bool:
    try:
        held = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False
    if not isinstance(held, dict) or not record_matches(held, current):
        return False
    expected = {**current, "package_version": held["package_version"]}
    canonical = (
        json.dumps(expected, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    )
    return payload == canonical.encode("utf-8")

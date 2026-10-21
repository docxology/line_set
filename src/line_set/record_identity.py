"""Compare dated measurements without relabelling their historical producer.

Producer version is metadata, not a measurement identity. This comparison
neither rewrites the held record nor authenticates who produced it.
"""

from __future__ import annotations

import json
import re


def record_matches(held: dict[str, object], current: dict[str, object]) -> bool:
    for record in (held, current):
        version = record.get("package_version")
        if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
            return False
    return {key: value for key, value in held.items() if key != "package_version"} == {
        key: value for key, value in current.items() if key != "package_version"
    }


def record_text_matches(text: str, current: dict[str, object]) -> bool:
    try:
        held = json.loads(text)
    except json.JSONDecodeError:
        return False
    if not isinstance(held, dict) or not record_matches(held, current):
        return False
    expected = {**current, "package_version": held["package_version"]}
    return text == json.dumps(expected, indent=2, ensure_ascii=False, sort_keys=True) + "\n"

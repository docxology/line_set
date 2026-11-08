"""Published API names resolve and version metadata remains coherent."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import line_set

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_every_exported_name_resolves() -> None:
    assert line_set.__all__
    for name in line_set.__all__:
        assert getattr(line_set, name) is not None, name


def test_the_export_list_is_sorted_and_free_of_duplicates() -> None:
    assert line_set.__all__ == sorted(set(line_set.__all__))


def test_the_package_version_matches_the_project_metadata() -> None:
    text = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    declared = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert declared is not None, "pyproject.toml declares no version"
    assert line_set.__version__ == declared.group(1)


def test_the_set_version_is_a_real_review_date() -> None:
    """The declaration is dated so a digest can be discussed against a revision."""
    parsed = datetime.strptime(line_set.SET_VERSION, "%Y.%m.%d").date()
    assert parsed.isoformat()
    assert line_set.SET_VERSION != line_set.__version__



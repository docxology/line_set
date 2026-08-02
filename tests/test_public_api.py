"""The public surface: importable, sorted, complete, and honestly versioned.

The completeness test is derived rather than listed. It walks each submodule,
collects the names that submodule actually defines, and requires them to be
re-exported. A hand-kept list of expected names would pass forever after
someone added a function and forgot the export.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from types import ModuleType

import line_set
from line_set import (
    binding,
    invariants,
    models,
    probes,
    reader,
    registry,
    serialization,
    version,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SUBMODULES = (
    binding,
    invariants,
    models,
    probes,
    reader,
    registry,
    serialization,
    version,
)


def _public_definitions(module: ModuleType) -> set[str]:
    """Names this module defines itself and that a caller could reasonably want.

    Classes and functions are attributed by ``__module__`` so that a name
    imported from elsewhere is not demanded back out of this module. Simple
    text and tuple constants are attributed by their upper-case spelling.
    """
    names: set[str] = set()
    for name, value in vars(module).items():
        if name == "__version__":
            names.add(name)
            continue
        if name.startswith("_"):
            continue
        if isinstance(value, type) or callable(value):
            if getattr(value, "__module__", None) == module.__name__:
                names.add(name)
        elif name.isupper() and isinstance(value, (str, tuple)):
            names.add(name)
    return names


def test_every_exported_name_resolves() -> None:
    assert line_set.__all__
    for name in line_set.__all__:
        assert getattr(line_set, name) is not None, name


def test_the_export_list_is_sorted_and_free_of_duplicates() -> None:
    assert line_set.__all__ == sorted(set(line_set.__all__))


def test_every_submodule_definition_is_re_exported() -> None:
    exported = set(line_set.__all__)
    for module in SUBMODULES:
        defined = _public_definitions(module)
        assert defined, module.__name__
        missing = sorted(defined - exported)
        assert not missing, f"{module.__name__} defines unexported names: {missing}"


def test_every_structural_check_is_publicly_exported() -> None:
    """A caller checking a candidate declaration should not have to reach in."""
    checks = {name for name in dir(invariants) if name.startswith("check_")}
    assert checks
    assert checks <= set(line_set.__all__)


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


OVERCLAIMS = ("validates", "guarantees", "certifies", "proves", "attests")


def test_the_package_docstring_does_not_promise_evaluation() -> None:
    """The wrapper reads declarations; the module header must not say more.

    The rule is shown able to fire before it is applied, so a green result here
    means the words are absent rather than that the check does nothing.
    """
    assert OVERCLAIMS
    planted = "This package validates and certifies the sibling instruments."
    assert [word for word in OVERCLAIMS if word in planted.lower()]

    assert line_set.__doc__ is not None
    lowered = line_set.__doc__.lower()
    assert "evaluates anything" in lowered
    assert not [word for word in OVERCLAIMS if word in lowered]


def test_the_submodules_are_reachable_as_attributes() -> None:
    for module in SUBMODULES:
        attribute = module.__name__.rsplit(".", 1)[-1]
        assert getattr(line_set, attribute) is module


def test_the_registry_module_is_the_only_place_the_lines_are_declared() -> None:
    assert registry.LINE_SET is line_set.LINE_SET
    assert registry.SHARED_TOKENS is line_set.SHARED_TOKENS
    assert models.OPUS_STAGE_ORDER is line_set.OPUS_STAGE_ORDER

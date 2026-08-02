"""Lexical guards: no patching or test-double library anywhere in this project.

The policy is absolute, so the guard is lexical rather than conventional. Every
Python file under ``src`` and ``tests`` is read and required not to contain the
syntax of a patching library. A resolver injected as an argument is a real
object and is not caught by any rule here, which is the point: the suite gets
its absent, failing, and extra packages from real files on disk, not from
substitutes for them.

Every needle is assembled from fragments, so this module never contains the
text it forbids and therefore scans itself like any other file. Joining the
fragments back into literals would blind the guards to their own source.

One rule the sibling projects carry is deliberately absent here: this project's
binding layer prepends caller-supplied directories to the import path on
purpose, so a blanket ban on import-path insertion would be wrong. The narrower
rule is kept instead — the tests must not do it themselves, and they do not,
because :class:`line_set.binding.ImportResolver` does it for them and records
what it added.

The scan set is checked before any rule runs. A guard over zero files reports
no violations for the uninteresting reason, so an empty scan fails.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEARCH_ROOTS = ("src", "tests", "scripts")
REQUIRED_ROOTS = ("src", "tests")
SKIP_DIRS = frozenset({"__pycache__", ".venv", ".pytest_cache", ".ruff_cache"})


def _python_files(roots: tuple[str, ...] = SEARCH_ROOTS) -> tuple[Path, ...]:
    """Return every Python file the guards below apply to."""
    files: list[Path] = []
    for relative_root in roots:
        root = PROJECT_ROOT / relative_root
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            # Judge exclusion on the path inside the project only: an ancestor
            # directory sharing a skipped name must not empty the whole scan.
            if SKIP_DIRS.isdisjoint(path.relative_to(PROJECT_ROOT).parts):
                files.append(path)
    assert files, f"lexical guards scanned zero Python files under {list(roots)}"
    return tuple(files)


def _text_pattern(*fragments: str) -> re.Pattern[str]:
    """Compile an exact-text rule from fragments."""
    return re.compile(re.escape("".join(fragments)))


def _name_pattern(*fragments: str) -> re.Pattern[str]:
    """Compile a rule matching fragments at the head of a word or identifier.

    The lookbehind admits a leading underscore, so an underscore-prefixed name
    is caught alongside the plain form, while mid-word matches are refused.
    """
    return re.compile(
        r"(?<![A-Za-z0-9])" + re.escape("".join(fragments)), re.IGNORECASE
    )


def _locations(
    patterns: tuple[re.Pattern[str], ...],
    roots: tuple[str, ...] = SEARCH_ROOTS,
) -> tuple[str, ...]:
    """Return ``path:line`` for every scanned line matching any pattern."""
    found: list[str] = []
    for path in _python_files(roots):
        relative = path.relative_to(PROJECT_ROOT)
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if any(pattern.search(line) for pattern in patterns):
                found.append(f"{relative}:{lineno}")
    return tuple(found)


def _assert_absent(
    description: str,
    *patterns: re.Pattern[str],
    roots: tuple[str, ...] = SEARCH_ROOTS,
) -> None:
    """Fail naming every offending location, so the failure is actionable."""
    locations = _locations(patterns, roots)
    assert not locations, f"{description} found at: {', '.join(locations)}"


def test_the_scan_set_covers_both_source_and_tests() -> None:
    """A guard over nothing is not a guard; prove there is something to guard."""
    scanned = {path.relative_to(PROJECT_ROOT).parts[0] for path in _python_files()}
    for required in REQUIRED_ROOTS:
        assert required in scanned, f"nothing was scanned under {required}/"
        assert _python_files((required,)), required
    assert PROJECT_ROOT / "src" / "line_set" / "reader.py" in set(_python_files())
    assert Path(__file__).resolve() in set(_python_files())


def test_patching_tooling_is_absent() -> None:
    """No module reaches for a patching or test-double library."""
    _assert_absent(
        "patching tooling",
        _text_pattern("unit", "test", ".", "mock"),
        _text_pattern("from unit", "test import"),
        _text_pattern("pytest", "_", "mock"),
        _text_pattern("Magic", "Mock"),
        _text_pattern("Async", "Mock"),
        _text_pattern("NonCallable", "Mock"),
        _text_pattern("mocker", ".", "patch"),
        _text_pattern("mock", ".", "patch"),
        _text_pattern("create_", "autospec"),
        _text_pattern("Monkey", "Patch"),
        _name_pattern("monkey", "patch"),
    )


def test_placeholder_prefixed_names_are_absent() -> None:
    """No module defines a stand-in named as a substitute for the real thing."""
    _assert_absent("placeholder-prefixed names", _name_pattern("fa", "ke", "_"))
    _assert_absent("placeholder-prefixed names", _name_pattern("du", "mmy", "_"))


def test_superseded_code_branding_is_absent() -> None:
    """No module brands its own code or tests as superseded."""
    _assert_absent("superseded-code branding", _name_pattern("leg", "acy"))


def test_machine_local_paths_are_absent() -> None:
    """No module hardcodes one machine's package-manager prefix."""
    _assert_absent(
        "machine-local path hardcodes",
        _text_pattern("/", "opt", "/", "homebrew"),
        _text_pattern("/", "usr", "/", "local", "/", "Cellar"),
        _text_pattern("/", "Users", "/"),
    )


def test_the_tests_do_not_rewrite_the_import_path_themselves() -> None:
    """The binding layer inserts paths on request; nothing else may.

    ``src`` is exempt from this rule by design — inserting a caller-supplied
    directory is what :class:`line_set.binding.ImportResolver` is for — so the
    rule is applied to the suite alone.
    """
    _assert_absent(
        "import-path insertion in the suite",
        _text_pattern("sys", ".", "path", ".", "insert"),
        _text_pattern("sys", ".", "path", ".", "append"),
        roots=("tests",),
    )


def test_exactly_one_module_is_allowed_to_reach_the_import_path() -> None:
    """The seam stays a seam: one file, named, and no other."""
    inserting = {
        location.split(":", 1)[0]
        for location in _locations(
            (_text_pattern("sys", ".", "path", ".", "insert"),), ("src",)
        )
    }
    assert inserting == {str(Path("src") / "line_set" / "binding.py")}

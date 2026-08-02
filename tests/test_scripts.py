"""The operator commands: each one runs, and each one refuses garbage.

A gate that exits zero on a broken input is not a gate. These tests run every
script in ``scripts/`` as a subprocess — the way an operator or a CI job runs
it — and require two things of each: a clean run on good input, and a non-zero
exit on input that is deliberately wrong.

"Deliberately wrong" is taken seriously rather than tested only at the argument
parser. An unknown flag is the cheap case and is checked, but each script is
also given the failure it actually exists to catch: a declaration that violates
a structural check, a set whose lines cannot be read, a rasterizer that is not
there, a reading record that disagrees with the set. Those are the cases where
exiting zero would be a silent lie rather than a usability annoyance.

The broken inputs are real. The project is copied to a real temporary
directory and its declaration is genuinely edited there, so the script under
test resolves a genuinely different package. Nothing under the working tree is
written to and no patching library is involved.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from line_set import LINE_SET, SHARED_TOKENS, ReadCode, read_set, registry_digest
from line_set.binding import SIBLING_BASE_ENV

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT_ROOT / "scripts"


def isolated_env(**overrides: str) -> dict[str, str]:
    """The ambient environment with the sibling-base override removed.

    ``copy_project`` isolates a run *positionally* — the copy sits alone, so
    there is nothing beside it to read. ``LINE_SET_SIBLINGS`` overrides that
    positional answer, so an operator who exports it would silently re-point
    these subprocesses at the real set and turn the fail-closed negative
    controls below into passes. The isolation has to be enforced here, not
    merely arranged on disk.
    """
    env = {key: value for key, value in os.environ.items() if key != SIBLING_BASE_ENV}
    env.update(overrides)
    return env


#: Directories a working checkout carries that a copy of it does not need.
NOT_COPIED = (".venv", "__pycache__", ".git", "output", ".pytest_cache", ".ruff_cache")


def every_script() -> tuple[Path, ...]:
    """Every operator command in ``scripts/``."""
    found = tuple(
        path for path in sorted(SCRIPTS.glob("*.py")) if path.name != "__init__.py"
    )
    assert found, "no scripts were found; every gate below would be vacuous"
    return found


def run(
    script: Path, *args: str, cwd: Path, source: Path
) -> subprocess.CompletedProcess:
    """Run one script as a subprocess, resolving ``line_set`` from ``source``."""
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=isolated_env(PYTHONPATH=str(source)),
    )


def copy_project(destination: Path) -> Path:
    """Copy the project to a real directory with no sibling checkouts beside it.

    The copy sits alone, so ``sibling_path_resolver`` finds nothing there. That
    is the honest reproduction of a machine that has this package and none of
    the lines it describes.
    """
    root = destination / "line_set"
    shutil.copytree(
        PROJECT_ROOT,
        root,
        ignore=shutil.ignore_patterns(*NOT_COPIED),
    )
    return root


def siblings_are_readable() -> bool:
    """Whether this machine can read every declared line."""
    from line_set import sibling_path_resolver

    reading = read_set(
        LINE_SET,
        SHARED_TOKENS,
        resolver=sibling_path_resolver(entry.package_name for entry in LINE_SET),
    )
    return all(
        observation.code is ReadCode.RESOLVED for observation in reading.observations
    )


# ---------------------------------------------------- every script, uniformly


@pytest.mark.parametrize("script", every_script(), ids=lambda path: path.name)
def test_every_script_refuses_an_argument_it_does_not_understand(
    script: Path,
) -> None:
    """A flag a gate silently ignores is a flag the operator thinks it honoured."""
    result = run(
        script, "--line-set-no-such-flag", cwd=PROJECT_ROOT, source=PROJECT_ROOT / "src"
    )
    assert result.returncode != 0, (
        f"{script.name} accepted an unknown flag and exited 0:\n{result.stdout}"
    )
    assert "--line-set-no-such-flag" in result.stderr


@pytest.mark.parametrize("script", every_script(), ids=lambda path: path.name)
def test_every_script_documents_itself(script: Path) -> None:
    """``--help`` is the surface an operator reaches for first."""
    result = run(script, "--help", cwd=PROJECT_ROOT, source=PROJECT_ROOT / "src")
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout


# ------------------------------------------------------------ check_registry


def test_check_registry_passes_on_the_shipped_declaration() -> None:
    result = run(
        SCRIPTS / "check_registry.py", cwd=PROJECT_ROOT, source=PROJECT_ROOT / "src"
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert registry_digest(LINE_SET, SHARED_TOKENS) in result.stdout
    assert "FAIL" not in result.stdout


def test_check_registry_needs_no_sibling(tmp_path: Path) -> None:
    """The offline gate means the same thing on a machine with no lines."""
    root = copy_project(tmp_path)
    result = run(root / "scripts" / "check_registry.py", cwd=root, source=root / "src")
    assert result.returncode == 0, result.stdout + result.stderr


def test_check_registry_fails_closed_on_a_broken_declaration(tmp_path: Path) -> None:
    """A planted-bad declaration, in a real copy, must exit non-zero."""
    root = copy_project(tmp_path)
    declaration = root / "src" / "line_set" / "registry.py"
    source = declaration.read_text(encoding="utf-8")
    target = LINE_SET[2].must_not_become
    assert f'must_not_become="{target}"' in source, "the plant site moved"
    declaration.write_text(
        source.replace(f'must_not_become="{target}"', 'must_not_become="   "', 1),
        encoding="utf-8",
    )

    result = run(root / "scripts" / "check_registry.py", cwd=root, source=root / "src")
    assert result.returncode != 0, result.stdout
    assert "FAIL must_not_become_declared" in result.stdout
    assert LINE_SET[2].id in result.stdout


# ----------------------------------------------------------------- check_set


def test_check_set_fails_closed_when_the_lines_cannot_be_read(tmp_path: Path) -> None:
    """An unchecked contract is not a held one, so a partial read is not a pass.

    This is the case the gate exists for and the one most likely to be got
    wrong: a machine with none of the lines installed produces no collision, and
    a gate that reported "no collisions found" would be reporting on an empty
    comparison.
    """
    root = copy_project(tmp_path)
    result = run(root / "scripts" / "check_set.py", cwd=root, source=root / "src")
    assert result.returncode != 0, result.stdout
    assert "set_partial" in result.stdout
    assert "FAIL self_disjointness" in result.stdout


def test_check_set_imports_only_refuses_what_an_ordinary_import_cannot_find() -> None:
    """The declared lines are not installed as packages; only the checkouts exist."""
    result = run(
        SCRIPTS / "check_set.py",
        "--imports-only",
        cwd=PROJECT_ROOT,
        source=PROJECT_ROOT / "src",
    )
    if result.returncode == 0:
        assert "set_legible" in result.stdout
        return
    assert "FAIL self_disjointness" in result.stdout


def test_check_set_passes_where_every_line_can_be_read() -> None:
    if not siblings_are_readable():
        pytest.skip(
            "this check needs every declared line package readable; the "
            "fail-closed direction is covered above and runs everywhere"
        )
    result = run(
        SCRIPTS / "check_set.py", cwd=PROJECT_ROOT, source=PROJECT_ROOT / "src"
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "set_legible" in result.stdout
    assert "PASS self_disjointness" in result.stdout
    assert "FAIL" not in result.stdout


# ------------------------------------------------------------ build_figures


def test_build_figures_fails_closed_without_a_rasterizer(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "build_figures.py"),
            "--project-root",
            str(tmp_path / "root"),
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env=isolated_env(
            PYTHONPATH=str(PROJECT_ROOT / "src"),
            LINE_SET_RSVG_CONVERT="line-set-no-such-rasterizer",
        ),
    )
    assert result.returncode != 0
    assert "librsvg" in result.stderr
    assert not (tmp_path / "root").exists(), "a refused build left output behind"


# ---------------------------------------------------------- record_reading


def test_record_reading_refuses_to_record_a_reading_it_could_not_take(
    tmp_path: Path,
) -> None:
    """A partial reading is not a record of the set, so nothing is written."""
    root = copy_project(tmp_path)
    target = tmp_path / "written.json"
    result = run(
        root / "scripts" / "record_reading.py",
        "--out",
        str(target),
        cwd=root,
        source=root / "src",
    )
    assert result.returncode != 0, result.stdout
    assert "REFUSED" in result.stderr
    assert not target.exists(), "a refused record was written anyway"


def test_record_reading_check_fails_when_there_is_no_record(tmp_path: Path) -> None:
    """``--check`` over a missing file is a failure, never a quiet success."""
    if not siblings_are_readable():
        pytest.skip("--check needs a readable set before it can compare anything")
    result = run(
        SCRIPTS / "record_reading.py",
        "--as-of",
        "2026-07-27",
        "--check",
        "--out",
        str(tmp_path / "absent.json"),
        cwd=PROJECT_ROOT,
        source=PROJECT_ROOT / "src",
    )
    assert result.returncode != 0
    assert "no record" in result.stderr


def test_record_reading_check_fails_on_a_record_that_disagrees(tmp_path: Path) -> None:
    if not siblings_are_readable():
        pytest.skip("--check needs a readable set before it can compare anything")
    stale = tmp_path / "stale.json"
    held = json.loads(
        (PROJECT_ROOT / "manuscript" / "reading_record.json").read_text(
            encoding="utf-8"
        )
    )
    held["vocabulary_census"]["distinct_names"] += 1
    stale.write_text(
        json.dumps(held, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result = run(
        SCRIPTS / "record_reading.py",
        "--as-of",
        held["recorded_on"],
        "--check",
        "--out",
        str(stale),
        cwd=PROJECT_ROOT,
        source=PROJECT_ROOT / "src",
    )
    assert result.returncode != 0
    assert "disagrees" in result.stderr


def test_record_reading_check_agrees_with_the_record_that_ships() -> None:
    """The freshness gate, run the way a release check would run it."""
    if not siblings_are_readable():
        pytest.skip("this check re-measures the installed line packages")
    held = json.loads(
        (PROJECT_ROOT / "manuscript" / "reading_record.json").read_text(
            encoding="utf-8"
        )
    )
    result = run(
        SCRIPTS / "record_reading.py",
        "--as-of",
        held["recorded_on"],
        "--check",
        cwd=PROJECT_ROOT,
        source=PROJECT_ROOT / "src",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "agrees" in result.stdout


def test_an_ambient_sibling_override_cannot_defeat_the_isolated_runs(
    tmp_path: Path,
) -> None:
    """An exported ``LINE_SET_SIBLINGS`` must not reach an isolated subprocess.

    ``copy_project`` isolates positionally: the copy sits alone, so there is
    nothing beside it to read and ``check_set.py`` must fail closed. That
    arrangement is defeated by an ambient override, which would silently point
    the subprocess back at the real set and turn this file's fail-closed
    negative controls into passes. The control below is the reason
    ``isolated_env`` exists rather than ``{**os.environ, ...}``.

    The variable is set on the real environment and restored in ``finally``
    rather than through a patching fixture, because this file's own contract
    forbids patching tooling and because the leak under test is a property of
    the real environment a subprocess inherits.
    """
    previous = os.environ.get(SIBLING_BASE_ENV)
    os.environ[SIBLING_BASE_ENV] = str(PROJECT_ROOT.parent)
    try:
        # The override is genuinely visible to this process...
        assert os.environ[SIBLING_BASE_ENV] == str(PROJECT_ROOT.parent)
        # ...and genuinely absent from the environment handed to a subprocess.
        assert SIBLING_BASE_ENV not in isolated_env(PYTHONPATH="x")

        source = copy_project(tmp_path)
        result = run(SCRIPTS / "check_set.py", cwd=source.parent, source=source / "src")
    finally:
        if previous is None:
            os.environ.pop(SIBLING_BASE_ENV, None)
        else:
            os.environ[SIBLING_BASE_ENV] = previous
    assert result.returncode != 0, (
        "the isolated copy has no siblings beside it, so check_set.py must fail "
        "closed; exiting zero here means the ambient override leaked through"
    )

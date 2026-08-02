"""Session setup: build the figures the on-disk gates read.

Two gates in this suite measure artifacts rather than objects.
``test_every_embedded_figure_exists_and_no_built_figure_is_orphaned`` resolves
each manuscript embed against the file it names, and
``test_every_shipped_plate_clears_the_rendered_floor`` measures the text in
each shipped SVG. Both need ``output/figures`` to be populated, and
``output/`` is disposable by design: the template pipeline wipes it in its
first stage and only rebuilds it during project analysis, which runs *after*
the project tests. A suite that assumed the directory had survived would fail
for a reason that has nothing to do with the properties it is checking.

So the prerequisite is built here rather than assumed.

**The build runs in a subprocess, and that is not incidental.**
:func:`line_set.figures.build_figures` resolves the siblings through
:func:`line_set.binding.sibling_path_resolver`, which prepends the sibling
source checkouts to ``sys.path`` the first time it is used. Building in
process would leave those roots on the path and the real sibling packages in
``sys.modules`` for the rest of the session, so every test that hands the
reader a synthetic ``red_line`` or a fictional fifth colour would silently
bind to the real package instead and assert against the wrong vocabulary.
Running the operator script as a separate process keeps the build's import
side effects entirely outside the test interpreter.

This provisions the input; it does not soften the check. The builder writes
only the plates it declares, so an embed naming a file the builder does not
produce still resolves to a missing path and still fails, and a plate whose
labels fall under the floor is still measured at its rendered size and still
fails. A build that cannot run — no rasterizer, an unreadable declaration —
raises here rather than being swallowed, because a suite that silently
skipped its own prerequisite would report a floor over plates it never read.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: The operator-facing build command, run as its own process.
BUILD_SCRIPT = PROJECT_ROOT / "scripts" / "build_figures.py"


@pytest.fixture(scope="session", autouse=True)
def built_figures() -> Path:
    """Build the shipped plates once, before any gate reads them from disk."""
    completed = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{BUILD_SCRIPT.name} failed with exit code {completed.returncode}; "
            "the figure gates would otherwise measure a directory that was "
            f"never built.\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return PROJECT_ROOT / "output" / "figures"

"""Write the Line Set figure artifacts. Fails closed before it writes anything.

The build takes one reading of the set and hands it to every plate that needs
one, so all five plates describe the same moment rather than five separate
readings taken at slightly different times.

Three properties this module is responsible for:

**It fails closed.** The external rasterizer is located and the display maps
are checked for coverage *before* the first SVG is written. A missing
``rsvg-convert`` raises with install guidance; it never skips a figure, writes
a partial set, or reports success over an unrasterized plate.

**It is byte-reproducible.** No plate carries a clock reading. The reading's
own ``read_as_of`` is deliberately kept out of the SVG bodies: it is a property
of the reading, available from :func:`line_set.reader.read_set`, and putting it
on a plate would make two builds of an unchanged declaration differ. The
digests that do appear are declaration digests, which change only when the
declaration does.

**It resolves siblings explicitly.** With no ``resolver`` argument the build
uses :func:`line_set.binding.sibling_path_resolver`, which is this module
asking, out loud, for the sibling source checkouts to be searched in addition
to the ordinary import system. Pass ``binding.default_resolver`` to see only
what an ordinary import would find.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import date
from pathlib import Path

from ..binding import PackageResolver, sibling_path_resolver
from ..models import LineEntry, SetReading, SharedToken
from ..reader import read_set
from ..registry import LINE_SET, SHARED_TOKENS, WRAPPER_LINE
from ..serialization import canonical_registry, registry_digest
from ..version import SET_VERSION, __version__
from .palette import verify_coverage
from .plates import FigurePlate, figure_plates

#: The rasterizer this build shells out to, unless the environment names another.
RSVG_CONVERT = "rsvg-convert"

#: The environment variable that overrides the rasterizer.
RSVG_ENV_VAR = "LINE_SET_RSVG_CONVERT"

#: Named in ``figure_registry.json`` as the user-facing build entry point.
BUILD_PROVENANCE = "scripts/build_figures.py"

#: The project root, when the caller names none.
PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]


def _resolve_rasterizer() -> str:
    """Locate the rasterizer, or refuse the build with install guidance."""
    requested = os.environ.get(RSVG_ENV_VAR, RSVG_CONVERT)
    found = shutil.which(requested)
    if found is not None:
        return found
    candidate = Path(requested)
    if candidate.is_file() and os.access(candidate, os.X_OK):
        # Resolved, not passed through. A bare relative name reaches this
        # branch when it names a file in the working directory, and handing
        # that string to ``subprocess`` raises FileNotFoundError — the build
        # would then refuse a rasterizer it had just located.
        return str(candidate.resolve())
    raise RuntimeError(
        f"{requested!r} is not an executable on PATH, so the Line Set figures "
        "cannot be rasterized. Install librsvg (macOS: 'brew install librsvg'; "
        "Debian or Ubuntu: 'apt-get install librsvg2-bin'; Fedora: "
        "'dnf install librsvg2-tools') so that 'rsvg-convert' is on PATH, or "
        f"set {RSVG_ENV_VAR} to the executable to use. The build writes no "
        "figure rather than reporting a figure it could not render."
    )


def _rasterize(executable: str, svg_path: Path, png_path: Path, figure: str) -> None:
    """Rasterize one plate, or name the prerequisite that failed."""
    try:
        subprocess.run(
            [executable, "-o", str(png_path), str(svg_path)],
            check=True,
        )
    except FileNotFoundError as error:
        raise RuntimeError(
            f"{executable!r} disappeared while rendering {figure}; install or "
            f"repair librsvg, or set {RSVG_ENV_VAR}, and rerun the figure build."
        ) from error
    except subprocess.CalledProcessError as error:
        raise RuntimeError(
            f"{executable!r} failed while rendering {figure} (exit "
            f"{error.returncode}); repair librsvg and rerun the figure build."
        ) from error


def _write_set_registry(
    figure_dir: Path,
    lines: tuple[LineEntry, ...],
    shared: tuple[SharedToken, ...],
) -> Path:
    """Write the canonical declaration beside the plates."""
    path = figure_dir / "set_registry.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "package_version": __version__,
                "set_version": SET_VERSION,
                "digest": registry_digest(lines, shared),
                "declaration": json.loads(canonical_registry(lines, shared)),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_figure_registry(
    figure_dir: Path,
    metadata: list[dict[str, str]],
    lines: tuple[LineEntry, ...],
    shared: tuple[SharedToken, ...],
    reading: SetReading,
) -> Path:
    """Write the figure manifest the manuscript embeds read."""
    path = figure_dir / "figure_registry.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.2",
                "package_version": __version__,
                "set_version": SET_VERSION,
                "registry_digest": registry_digest(lines, shared),
                "set_status": reading.status.value,
                "read_codes": reading.counts(),
                "figures": metadata,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def build_figures(
    project_root: Path | None = None,
    *,
    lines: tuple[LineEntry, ...] = LINE_SET,
    shared: tuple[SharedToken, ...] = SHARED_TOKENS,
    wrapper: LineEntry = WRAPPER_LINE,
    resolver: PackageResolver | None = None,
    as_of: str | date | None = None,
) -> list[Path]:
    """Build every plate, its PNG, and the two JSON manifests beside them.

    Returns every path written, PNG before SVG per figure and the manifests
    last, so a caller can report what landed without guessing at names.
    """
    verify_coverage()
    executable = _resolve_rasterizer()
    if resolver is None:
        resolver = sibling_path_resolver(entry.package_name for entry in lines)
    reading = read_set(lines, shared, resolver=resolver, as_of=as_of)
    # The self-application plate needs the reading the self-check runs, which is
    # over the declaration with the wrapper appended. Taking it here rather than
    # inside the plate keeps every plate free of import side effects and keeps
    # the two readings pinned to one review date.
    self_reading = read_set((*lines, wrapper), shared, resolver=resolver, as_of=as_of)
    plates: tuple[FigurePlate, ...] = figure_plates(
        lines, shared, reading, wrapper, self_reading
    )

    root = PROJECT_ROOT if project_root is None else Path(project_root)
    figure_dir = root / "output" / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    produced: list[Path] = []
    metadata: list[dict[str, str]] = []
    source_digest = registry_digest(lines, shared)
    for plate in plates:
        svg_path = figure_dir / f"{plate.name}.svg"
        png_path = figure_dir / f"{plate.name}.png"
        svg_path.write_text(plate.render(), encoding="utf-8")
        _rasterize(executable, svg_path, png_path, plate.name)
        produced.extend([png_path, svg_path])
        metadata.append(
            {
                "label": plate.label,
                "filename": png_path.name,
                "caption": plate.caption,
                "alt": plate.alt,
                "source": plate.source,
                "generated_by": BUILD_PROVENANCE,
                "format": "PNG rasterized from deterministic SVG",
                "source_digest": source_digest,
            }
        )
    produced.append(_write_set_registry(figure_dir, lines, shared))
    produced.append(
        _write_figure_registry(figure_dir, metadata, lines, shared, reading)
    )
    return produced


def figure_summary(paths: list[Path]) -> str:
    """One line naming what a build produced; used by the CLI wrapper."""
    pngs = [path for path in paths if path.suffix == ".png"]
    svgs = [path for path in paths if path.suffix == ".svg"]
    manifests = [path for path in paths if path.suffix == ".json"]
    directory = paths[0].parent if paths else Path()
    return (
        f"wrote {len(svgs)} SVG, {len(pngs)} PNG, and {len(manifests)} JSON "
        f"artifacts under {directory}"
    )


__all__ = [
    "BUILD_PROVENANCE",
    "PROJECT_ROOT",
    "RSVG_CONVERT",
    "RSVG_ENV_VAR",
    "build_figures",
    "figure_summary",
]

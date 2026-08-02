#!/usr/bin/env python3
"""Build the deterministic Line Set figures.

The package owns the drawing, the reading, and the artifact protocol; this
script supplies the operator-facing command only. A missing rasterizer raises
out of the package with install guidance rather than being skipped here.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from line_set.figures import build_figures, figure_summary


def main() -> None:
    """Build the figures under an optional project root and report what landed."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        type=Path,
        help="root that receives output/figures (defaults to this project)",
    )
    args = parser.parse_args()
    paths = build_figures(args.project_root)
    print(figure_summary(paths))
    for path in paths:
        print(f"  {path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Assemble the declared works into one compiled volume under ``output/``.

The package owns the assembly, the gates, and the honesty checks; this script
supplies the operator-facing command only.

Writing is opt-in. A bare invocation plans the volume, runs every gate over the
plan, prints what it would write, and touches nothing — because writing
``output/manuscript/`` replaces what the render toolchain renders for this
project, and the analysis stage runs every script in this directory with no
arguments. Pass ``--write`` to commit the plan to disk.

The command fails, loudly and non-zero, when a plate basename is shipped by two
works, when a bibliography key names two different works, when a cross-reference
survives un-rewritten, or when the assembling work's own manuscript is missing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from line_set.omnibus import OmnibusError, assemble


def main() -> None:
    """Plan or write the volume, then report what was counted."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="commit the assembled volume to output/manuscript (default: plan only)",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="root that receives output/manuscript (defaults to this project)",
    )
    parser.add_argument(
        "--base",
        type=Path,
        help="directory holding the declared works' checkouts (defaults to the siblings)",
    )
    args = parser.parse_args()

    try:
        report = assemble(
            args.project_root,
            args.base,
            write=args.write,
        )
    except OmnibusError as error:
        print(f"omnibus refused to assemble: {error}", file=sys.stderr)
        sys.exit(1)

    print(report.summary())
    if not args.write:
        print("planned only; nothing was written. Pass --write to commit the volume.")
        return
    for name in report.files:
        print(f"  {name}")


if __name__ == "__main__":
    main()

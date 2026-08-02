#!/usr/bin/env python3
"""Check the set declaration offline and print its digest.

This gate imports no sibling line package and reaches no network. It runs the
structural checks over the declaration alone, so it means the same thing on a
machine where every line is installed and on one where none is. Use
``check_set.py`` for the live non-overlap check.
"""

from __future__ import annotations

import argparse
import sys

from line_set import (
    LINE_SET,
    SET_VERSION,
    SHARED_TOKENS,
    __version__,
    all_invariants,
    registry_digest,
)


def main() -> None:
    """Run the offline checks, print each result, and exit non-zero on any failure.

    The gate takes no options. It still parses its command line, because a gate
    that ignores an argument it was given cannot be told apart from one that
    honoured it, and the failure mode is a run that looks like it checked
    something it never looked at.
    """
    argparse.ArgumentParser(description=__doc__).parse_args()
    results = all_invariants(LINE_SET, SHARED_TOKENS)
    for result in results:
        print(f"{'PASS' if result.passed else 'FAIL'} {result.name}: {result.detail}")
    print(
        f"package_version={__version__} set_version={SET_VERSION} "
        f"lines={len(LINE_SET)} shared_tokens={len(SHARED_TOKENS)} "
        f"digest={registry_digest(LINE_SET, SHARED_TOKENS)}"
    )
    if not all(result.passed for result in results):
        sys.exit(1)


if __name__ == "__main__":
    main()

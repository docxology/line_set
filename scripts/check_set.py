#!/usr/bin/env python3
"""Read the installed line packages and check that the set stayed separate.

This gate is live: it needs the declared line packages to be importable. It
exits zero only when the reading is ``set_legible`` and every check in the live
battery passed. A partial installation therefore does not pass — the
non-overlap contract was not checked, and an unchecked contract is not a held
one. Use ``check_registry.py`` for the offline structural checks, which mean
the same thing with no line installed.

By default the resolver also searches the sibling source checkouts named in the
declaration. ``--imports-only`` restricts it to what an ordinary import finds.
"""

from __future__ import annotations

import argparse
import sys

from line_set import (
    LINE_SET,
    SET_VERSION,
    SHARED_TOKENS,
    SetStatus,
    default_resolver,
    live_invariants,
    read_set,
    reading_digest,
    sibling_path_resolver,
)


def main() -> None:
    """Print the reading and the live battery, then exit on their verdict."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--imports-only",
        action="store_true",
        help="resolve through the ordinary import system only",
    )
    args = parser.parse_args()
    resolver = (
        default_resolver
        if args.imports_only
        else sibling_path_resolver(entry.package_name for entry in LINE_SET)
    )

    reading = read_set(LINE_SET, SHARED_TOKENS, resolver=resolver)
    for observation in sorted(reading.observations, key=lambda item: item.line_id):
        print(
            f"{observation.line_id:<12} {observation.code.value:<14} "
            f"version={observation.version} "
            f"registry_size={observation.registry_size} "
            f"tokens={len(observation.tokens)} "
            f"digest={observation.registry_digest}"
        )
    for collision in (*reading.collisions, *reading.exempted_collisions):
        print(
            f"{'EXEMPT   ' if collision.exempted else 'COLLISION'} "
            f"{collision.token} over {sorted(collision.lines)}"
        )
    for stage in reading.derivation:
        print(f"[{stage.name}] {stage.detail}")

    results = live_invariants(LINE_SET, SHARED_TOKENS, resolver=resolver)
    for result in results:
        print(f"{'PASS' if result.passed else 'FAIL'} {result.name}: {result.detail}")
    print(
        f"set_version={SET_VERSION} status={reading.status.value} "
        f"read_as_of={reading.read_as_of} set_digest={reading.set_digest} "
        f"reading_digest={reading_digest(reading)}"
    )

    if reading.status is not SetStatus.SET_LEGIBLE or not all(
        result.passed for result in results
    ):
        sys.exit(1)


if __name__ == "__main__":
    main()

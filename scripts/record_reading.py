#!/usr/bin/env python3
"""Record the dated reading the manuscript quotes, as a checkable artifact.

The manuscript reports numbers it measured on the review date: sibling
versions, registry sizes, per-line token counts, digests, and the token
arithmetic that carries the paper's one empirical claim. Those numbers cannot
be re-derived on a machine where the sibling packages are absent, which is most
machines the manuscript will ever reach — so on those machines the claim would
travel entirely unchecked.

This script closes that gap by splitting the check in two. It writes what the
reading actually said into ``docs/manuscript/reading_record.json``. The suite then
binds the prose to the record everywhere, and binds the record to a live
reading wherever the siblings can be read. Neither half is the whole check and
neither half is vacuous: prose drift fails on any machine, and a stale record
fails on the review machine.

The record is not evidence that the numbers were right when they were taken.
It is a dated statement of what this package read, carried alongside the prose
that quotes it, so that the two can be compared without the packages present.

The date it records is the manuscript's review date, read from
``docs/manuscript/config.yaml``, and not the day the script happens to run. The
record belongs to the paper that quotes it, so re-recording an unchanged set
reproduces the shipped file byte for byte and re-running this script is
idempotent. Defaulting to today instead would move ``recorded_on`` and the
digest derived from it on every run, which would leave the record disagreeing
with the prose that quotes it and with its own freshness check the next
morning. Taking a reading for a *new* review date is a deliberate act: pass
``--as-of`` and update the manuscript date, the set version, and any prose
whose numbers moved.

It fails closed. A reading that is not ``set_legible`` — because a line was not
installed, or because the vocabularies collided — is not a record of the set,
and writing one would put an incomplete measurement where a complete one is
expected. The script refuses and exits non-zero instead.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from line_set import (
    LINE_SET,
    SET_VERSION,
    SHARED_TOKENS,
    ReadCode,
    SetStatus,
    __version__,
    canonical_reading,
    read_set,
    reading_digest,
    registry_digest,
    sibling_path_resolver,
    vocabulary_census,
)

#: Where the record lives, beside the prose that quotes it.
RECORD_PATH = (
    Path(__file__).resolve().parents[1] / "docs" / "manuscript" / "reading_record.json"
)

#: The manuscript configuration that carries the review date.
CONFIG_PATH = (
    Path(__file__).resolve().parents[1] / "docs" / "manuscript" / "config.yaml"
)


def review_date(config_path: Path = CONFIG_PATH) -> str:
    """Return the manuscript's review date, or refuse to guess one.

    Read from the manuscript rather than taken from the clock, so the record
    stays pinned to the paper it is filed beside. A missing or dateless config
    raises instead of falling back to today: a silent fallback would write a
    record dated to whenever the script last ran, which is the drift this
    function exists to prevent.
    """
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError as error:
        raise SystemExit(
            f"cannot read {config_path} for the review date: {error}"
        ) from error
    found = re.search(
        r'^\s*date:\s*"?([0-9]{4}-[0-9]{2}-[0-9]{2})"?', text, re.MULTILINE
    )
    if found is None:
        raise SystemExit(
            f"{config_path} declares no ISO review date, so there is no date to "
            "record against; add a paper.date field or pass --as-of explicitly"
        )
    return found.group(1)


#: Bumped when the record's shape changes, so a reader can tell which it holds.
SCHEMA_VERSION = "1.0"

#: How the census was taken, recorded so the numbers are not bare.
CENSUS_METHOD = (
    "Every enum exported at each declared package's root was counted, together "
    "with the members it declares. declared_members counts repeats; "
    "distinct_names is what survives deduplication within one line, which is "
    "what the collision scan compares."
)


def build_record(as_of: str | None) -> tuple[dict[str, object], list[str]]:
    """Read the set live and assemble the record, plus any refusal reasons."""
    resolver = sibling_path_resolver(entry.package_name for entry in LINE_SET)
    reading = read_set(LINE_SET, SHARED_TOKENS, resolver=resolver, as_of=as_of)

    refusals: list[str] = []
    unread = sorted(
        observation.line_id
        for observation in reading.observations
        if observation.code is not ReadCode.RESOLVED
    )
    if unread:
        refusals.append(f"these declared lines could not be read: {unread}")
    if reading.status is not SetStatus.SET_LEGIBLE:
        refusals.append(f"the reading is {reading.status.value}, not set_legible")

    census: dict[str, dict[str, int]] = {}
    if not refusals:
        for entry in LINE_SET:
            module = sys.modules[entry.package_name]
            counted = vocabulary_census(module)
            census[entry.id] = {
                "enum_classes": counted.enum_classes,
                "declared_members": counted.declared_members,
                "distinct_names": counted.distinct_names,
                "within_line_repeats": counted.within_line_repeats,
            }

    pairs = sum(len(observation.tokens) for observation in reading.observations)
    distinct = len(
        {token for observation in reading.observations for token in observation.tokens}
    )
    record = {
        "schema_version": SCHEMA_VERSION,
        "package_version": __version__,
        "set_version": SET_VERSION,
        "recorded_on": reading.read_as_of,
        "set_digest": registry_digest(LINE_SET, SHARED_TOKENS),
        "reading_digest": reading_digest(reading),
        "reading": json.loads(canonical_reading(reading)),
        "vocabulary_census": {
            "method": CENSUS_METHOD,
            "per_line": census,
            "enum_classes": sum(item["enum_classes"] for item in census.values()),
            "declared_members": sum(
                item["declared_members"] for item in census.values()
            ),
            "line_and_name_pairs": pairs,
            "distinct_names": distinct,
            "names_carried_by_more_than_one_line": sorted(
                collision.token
                for collision in (*reading.collisions, *reading.exempted_collisions)
            ),
        },
    }
    return record, refusals


def main() -> None:
    """Write the record, or refuse and say which prerequisite was missing."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--as-of",
        help=(
            "ISO review date to record (defaults to the manuscript's review "
            "date from config.yaml, never to today)"
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=RECORD_PATH,
        help="where to write the record (defaults to docs/manuscript/reading_record.json)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare against the record on disk without rewriting it",
    )
    args = parser.parse_args()

    record, refusals = build_record(args.as_of or review_date())
    if refusals:
        for reason in refusals:
            print(f"REFUSED {reason}", file=sys.stderr)
        print(
            "A partial or colliding reading is not a record of the set. Install "
            "the declared line packages and rerun.",
            file=sys.stderr,
        )
        sys.exit(1)

    rendered = json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.check:
        if not args.out.exists():
            print(f"FAIL no record at {args.out}", file=sys.stderr)
            sys.exit(1)
        if args.out.read_text(encoding="utf-8") != rendered:
            print(
                f"FAIL {args.out} disagrees with a live reading; rerun without "
                "--check to refresh it",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"OK {args.out} agrees with a live reading taken now")
        return

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(rendered, encoding="utf-8")
    census = record["vocabulary_census"]
    print(f"wrote {args.out}")
    print(
        f"  recorded_on={record['recorded_on']} "
        f"reading_digest={record['reading_digest'][:16]}"
    )
    print(
        f"  {census['enum_classes']} enum classes, "
        f"{census['declared_members']} declared members, "
        f"{census['line_and_name_pairs']} line-and-name pairs, "
        f"{census['distinct_names']} distinct names"
    )


if __name__ == "__main__":
    main()

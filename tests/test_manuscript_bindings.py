"""Publication references and recorded measurement integrity, not prose wording.

Authored sentences are reviewed against their dated evidence. These checks
exercise reference resolution, canonical reading replay, census consistency,
and conditional comparison with the actual pinned source packages.
"""

from __future__ import annotations

import enum
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pytest

from line_set import (
    LINE_SET,
    SET_VERSION,
    SHARED_TOKENS,
    ReadCode,
    SetStatus,
    check_pinned_sources,
    read_set,
    reading_digest,
    reading_from_canonical,
    registry_digest,
)
from line_set.binding import Resolution
from line_set.figures import figure_plates
from line_set.record_identity import record_bytes_match
from line_set.recording import build_record
from line_set.registry import WRAPPER_LINE
from tests.support import environment, import_sandbox, write_line_package

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = PROJECT_ROOT / "docs" / "manuscript"
RECORD_PATH = MANUSCRIPT / "reading_record.json"


def record() -> dict:
    return json.loads(RECORD_PATH.read_bytes())


def _absent(name: str) -> Resolution:
    return Resolution(name, ReadCode.NOT_INSTALLED, None, "not installed here")


def _pinned_live_record(held: dict) -> dict:
    current, refusals = build_record(held["recorded_on"])
    reading = reading_from_canonical(json.dumps(current["reading"]))
    pinned = check_pinned_sources(reading)
    if not pinned.passed:
        pytest.skip("pinned source comparison unavailable: " + pinned.detail)
    assert not refusals, "; ".join(refusals)
    withheld = tuple(held.get("withheld_sources", ()))
    if withheld:
        current, refusals = build_record(held["recorded_on"], withheld_sources=withheld)
        assert not refusals, "; ".join(refusals)
    return current


def test_bibliography_references_resolve() -> None:
    from tests.test_formalism import blocks

    prefixes = {block.label.partition(":")[0] for block in blocks() if block.label}
    prefixes |= {"sec", "fig"}
    keys = set(
        re.findall(r"@\w+\{([^,]+),", (MANUSCRIPT / "references.bib").read_text())
    )
    cited = {
        name
        for path in MANUSCRIPT.glob("*.md")
        for name in re.findall(r"\[?@([A-Za-z][A-Za-z0-9_:\-]*)", path.read_text())
        if name.partition(":")[0] not in prefixes
    }
    assert keys and cited
    assert cited == keys


def test_embedded_figures_resolve_to_declared_plates() -> None:
    held = record()
    review_date = held["recorded_on"]
    reading = read_set(resolver=_absent, as_of=review_date)
    self_reading = read_set(
        (*LINE_SET, WRAPPER_LINE), resolver=_absent, as_of=review_date
    )
    plates = figure_plates(LINE_SET, SHARED_TOKENS, reading, WRAPPER_LINE, self_reading)
    declared = {f"{plate.name}.png": plate.label for plate in plates}
    config = (MANUSCRIPT / "config.yaml").read_text()
    cover = Path(re.search(r'image:\s*"([^"]+)"', config).group(1)).name
    assert cover in declared
    embedded = {}
    for source in MANUSCRIPT.glob("*.md"):
        for target, label in re.findall(
            r"!\[[^\]]*\]\(([^)]+)\)\{#([^\s}]+)", source.read_text()
        ):
            resolved = (MANUSCRIPT / target).resolve()
            assert resolved.is_file(), (source.name, target)
            assert resolved.name not in embedded
            embedded[resolved.name] = label
    assert embedded
    assert embedded == {
        name: label for name, label in declared.items() if name != cover
    }


def test_record_replays_with_its_declared_identity_and_source_disclosures() -> None:
    held = record()
    reading = reading_from_canonical(json.dumps(held["reading"]))
    assert reading.status is SetStatus.SET_LEGIBLE
    withheld = set(held.get("withheld_sources", ()))
    assert withheld <= {entry.id for entry in LINE_SET}
    if withheld:
        assert held["schema_version"] == "2.0-public"
        assert not check_pinned_sources(reading).passed
        for observation in reading.observations:
            if observation.line_id in withheld:
                assert observation.provenance.source_revision is None
                assert observation.provenance.module_origin is None
    else:
        assert check_pinned_sources(reading).passed
    assert reading_digest(reading) == held["reading_digest"]
    assert (
        reading.set_digest
        == held["set_digest"]
        == registry_digest(LINE_SET, SHARED_TOKENS)
    )
    assert held["set_version"] == SET_VERSION
    assert reading.read_as_of == held["recorded_on"]
    assert {item.line_id for item in reading.observations} == {
        entry.id for entry in LINE_SET
    }
    assert held["source_revisions"] == {
        item.line_id: item.provenance.source_revision for item in reading.observations
    }


def test_recorded_census_closes_over_observed_names() -> None:
    held = record()
    observations = held["reading"]["observations"]
    census = held["vocabulary_census"]
    per_line = census["per_line"]
    assert set(per_line) == {item["line_id"] for item in observations}
    carriers = Counter(token for item in observations for token in item["tokens"])
    assert census["line_and_name_pairs"] == sum(carriers.values())
    assert census["distinct_names"] == len(carriers)
    assert census["names_carried_by_more_than_one_line"] == sorted(
        token for token, count in carriers.items() if count > 1
    )
    for field in ("enum_classes", "declared_members", "canonical_members"):
        assert census[field] == sum(item[field] for item in per_line.values())
    for observation in observations:
        counts = per_line[observation["line_id"]]
        assert counts["distinct_names"] == len(observation["tokens"])
        assert counts["within_line_repeats"] == (
            counts["declared_members"] - counts["distinct_names"]
        )
        assert 0 < counts["canonical_members"] <= counts["declared_members"]


def test_record_matches_a_current_pinned_measurement_without_rewriting() -> None:
    held_bytes = RECORD_PATH.read_bytes()
    with import_sandbox():
        current = _pinned_live_record(json.loads(held_bytes))
        assert record_bytes_match(held_bytes, current)
    assert RECORD_PATH.read_bytes() == held_bytes


def test_independent_root_enum_census_matches_the_record() -> None:
    held = record()
    with import_sandbox():
        _pinned_live_record(held)
        classes = declared = canonical = 0
        per_line = {}
        for entry in LINE_SET:
            names = set()
            seen = set()
            for value in vars(sys.modules[entry.package_name]).values():
                if (
                    isinstance(value, type)
                    and issubclass(value, enum.Enum)
                    and value.__module__ != enum.__name__
                    and id(value) not in seen
                ):
                    seen.add(id(value))
                    classes += 1
                    declared += len(value.__members__)
                    canonical += len(value)
                    names.update(value.__members__)
            per_line[entry.id] = names
        census = held["vocabulary_census"]
        carriers = Counter(token for names in per_line.values() for token in names)
        assert classes == census["enum_classes"]
        assert declared == census["declared_members"]
        assert canonical == census["canonical_members"]
        assert sum(map(len, per_line.values())) == census["line_and_name_pairs"]
        assert len(carriers) == census["distinct_names"]
        assert (
            sorted(token for token, count in carriers.items() if count > 1)
            == (census["names_carried_by_more_than_one_line"])
        )


@pytest.mark.parametrize("withheld_sources", [(), ("violet_line",)])
def test_readable_pinned_collisions_fail_instead_of_skipping(
    tmp_path: Path, withheld_sources: tuple[str, ...]
) -> None:
    for index, entry in enumerate(LINE_SET):
        token = "CROSS_LINE_BOUNDARY" if index < 2 else f"ONLY_{index}"
        write_line_package(
            tmp_path / entry.package_name / "src",
            entry.package_name,
            (token,),
            registry_sizes={"PRIMARY": 1},
            source_revision=f"{index + 1:040x}",
        )
    with import_sandbox(), environment("LINE_SET_SIBLINGS", str(tmp_path)):
        try:
            with pytest.raises(AssertionError):
                _pinned_live_record(
                    {
                        "recorded_on": "2026-11-06",
                        "withheld_sources": withheld_sources,
                    }
                )
        except pytest.skip.Exception as error:
            pytest.fail(f"available pinned disagreement was skipped: {error}")

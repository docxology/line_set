"""Calendar-only reader admission and serializable injected resolution outcomes."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from line_set import (
    LINE_SET,
    ReadCode,
    SetStatus,
    canonical_reading,
    read_set,
    reading_digest,
    reading_from_canonical,
)
from line_set.binding import ImportResolver, Resolution
from line_set.models import BindingProvenance, Diagnostic
from tests.support import ListingResolver, absent, import_sandbox, write_line_package


@pytest.fixture
def imported_resolution(tmp_path: Path):
    entry = replace(LINE_SET[0], id="core_boundary", package_name="core_boundary_line")
    source = tmp_path / "src"
    with import_sandbox():
        write_line_package(
            source,
            entry.package_name,
            ("OBSERVED",),
            registry_sizes={"PRIMARY": 1},
            source_revision="a" * 40,
        )
        result = ImportResolver([source])(entry.package_name)
        assert result.code is ReadCode.RESOLVED, result.detail
        yield entry, result


@pytest.mark.parametrize(
    "as_of",
    [
        datetime(2026, 11, 9),
        datetime(2026, 11, 9, 23, 59, 59),
        datetime(2026, 11, 9, tzinfo=timezone.utc),
        datetime(2026, 11, 9, tzinfo=timezone(timedelta(hours=14))),
    ],
)
def test_datetime_is_refused_before_any_resolution(as_of: datetime) -> None:
    def must_not_resolve(name: str):
        pytest.fail(f"datetime input reached resolution of {name}")

    with pytest.raises(TypeError):
        read_set(LINE_SET[:1], (), resolver=must_not_resolve, as_of=as_of)


def test_calendar_date_and_string_have_identical_serializable_readings() -> None:
    by_date = read_set(LINE_SET[:1], (), resolver=absent, as_of=date(2026, 11, 9))
    by_string = read_set(LINE_SET[:1], (), resolver=absent, as_of="2026-11-09")
    assert by_date.read_as_of == "2026-11-09"
    assert by_date == by_string
    assert canonical_reading(by_date) == canonical_reading(by_string)
    assert reading_digest(by_date) == reading_digest(by_string)
    assert reading_from_canonical(canonical_reading(by_date)) == by_date


@pytest.mark.parametrize(
    "field,value",
    [
        ("requested_package", 7),
        ("resolved_package", 7),
        ("module_origin", 7),
        ("distribution", 7),
        ("distribution_version", 7),
        ("resolver_policy", 7),
        ("binding_schema", 7),
        ("registry_identity", 7),
        ("source_revision", 12),
        ("source_revision", ""),
        ("source_revision", "a" * 39),
        ("source_revision", "A" * 40),
        ("source_revision", "g" * 40),
    ],
)
@pytest.mark.parametrize("code", [ReadCode.RESOLVED, ReadCode.NOT_INSTALLED])
def test_malformed_injected_provenance_becomes_serializable_import_failure(
    imported_resolution, field: str, value: object, code: ReadCode
) -> None:
    entry, original = imported_resolution
    result = replace(
        original,
        code=code,
        module=original.module if code is ReadCode.RESOLVED else None,
        provenance=replace(original.provenance, **{field: value}),
    )
    reading = read_set((entry,), (), resolver=lambda name: result, as_of="2026-11-09")
    observation = reading.observations[0]
    assert reading.status is SetStatus.SET_PARTIAL
    assert observation.code is ReadCode.IMPORT_FAILED
    assert observation.tokens == ()
    assert (
        observation.version,
        observation.registry_size,
        observation.registry_digest,
    ) == (None, None, None)
    assert observation.provenance.source_revision is None
    assert observation.provenance.requested_package == entry.package_name
    assert observation.diagnostics[0].phase == "resolve"
    assert observation.diagnostics[0].exception_type == "ValueError"
    assert len(observation.diagnostics[0].detail) <= 500
    replay = reading_from_canonical(canonical_reading(reading))
    assert replay == reading
    assert reading_digest(replay) == reading_digest(reading)


@pytest.mark.parametrize(
    "diagnostics",
    [
        (Diagnostic(7, "Failure", "detail"),),
        (Diagnostic("resolve", 7, "detail"),),
        (Diagnostic("resolve", "Failure", 7),),
        (Diagnostic("resolve", "Failure", "detail"), "not a diagnostic"),
        [Diagnostic("resolve", "Failure", "detail")],
    ],
)
@pytest.mark.parametrize(
    "code", [ReadCode.RESOLVED, ReadCode.NOT_INSTALLED, ReadCode.IMPORT_FAILED]
)
def test_malformed_injected_diagnostics_are_contained(
    imported_resolution, diagnostics: object, code: ReadCode
) -> None:
    entry, original = imported_resolution
    result = replace(
        original,
        code=code,
        module=original.module if code is ReadCode.RESOLVED else None,
        diagnostics=diagnostics,
    )
    reading = read_set((entry,), (), resolver=lambda name: result, as_of="2026-11-09")
    observation = reading.observations[0]
    assert reading.status is SetStatus.SET_PARTIAL
    assert observation.code is ReadCode.IMPORT_FAILED
    assert observation.diagnostics[0].phase == "resolve"
    assert observation.diagnostics[0].exception_type == "ValueError"
    assert len(observation.diagnostics[0].detail) <= 500
    assert reading_from_canonical(canonical_reading(reading)) == reading
    reading_digest(reading)


def test_valid_injected_resolution_preserves_actual_import_provenance(
    imported_resolution,
) -> None:
    entry, result = imported_resolution
    reading = read_set((entry,), (), resolver=lambda name: result, as_of="2026-11-09")
    observation = reading.observations[0]
    assert reading.status is SetStatus.SET_LEGIBLE
    assert observation.code is ReadCode.RESOLVED
    assert observation.tokens == ("OBSERVED",)
    assert observation.version == vars(result.module)["__version__"]
    assert observation.registry_size == 1
    assert observation.registry_digest is not None
    assert (
        replace(
            observation.provenance,
            binding_schema=result.provenance.binding_schema,
            registry_identity=result.provenance.registry_identity,
        )
        == result.provenance
    )
    assert observation.provenance.source_revision == "a" * 40
    assert observation.provenance.module_origin == (
        f"{entry.package_name}/{entry.package_name}/__init__.py"
    )
    assert reading_from_canonical(canonical_reading(reading)) == reading
    reading_digest(reading)


@pytest.mark.parametrize("code", [ReadCode.NOT_INSTALLED, ReadCode.IMPORT_FAILED])
def test_valid_unavailable_resolution_preserves_injected_metadata(
    code: ReadCode,
) -> None:
    entry = LINE_SET[0]
    provenance = BindingProvenance(
        requested_package=entry.package_name, resolver_policy="injected"
    )
    diagnostics = (Diagnostic("resolve", "ReportedFailure", "retained detail"),)
    result = Resolution(
        entry.package_name, code, None, "unavailable", provenance, diagnostics
    )
    reading = read_set((entry,), (), resolver=lambda name: result, as_of="2026-11-09")
    observation = reading.observations[0]
    assert reading.status is SetStatus.SET_PARTIAL
    assert observation.code is code
    assert observation.provenance == provenance
    assert observation.diagnostics == diagnostics
    assert reading_from_canonical(canonical_reading(reading)) == reading
    reading_digest(reading)


def test_malformed_discovered_resolution_records_failure_without_undeclared_claim(
    imported_resolution,
) -> None:
    entry, result = imported_resolution
    declared = replace(entry, id="absent_boundary", package_name="absent_boundary_line")
    malformed = replace(result, diagnostics=(Diagnostic("resolve", "Failure", 7),))
    resolver = ListingResolver(
        {entry.package_name: malformed}, listed=(entry.package_name,)
    )
    reading = read_set((declared,), (), resolver=resolver, as_of="2026-11-09")
    assert reading.status is SetStatus.SET_PARTIAL
    assert reading.undeclared_lines == ()
    assert reading.discovery.completed
    (outcome,) = reading.discovery.outcomes
    assert outcome.package_name == entry.package_name
    assert outcome.code is ReadCode.IMPORT_FAILED
    assert outcome.diagnostics[0].phase == "resolve"
    assert outcome.diagnostics[0].exception_type == "ValueError"
    assert reading_from_canonical(canonical_reading(reading)) == reading
    reading_digest(reading)


def test_module_origin_enrichment_is_admitted_before_observation(
    imported_resolution,
) -> None:
    entry, original = imported_resolution
    original.module.__file__ = 7
    supplied = replace(
        original, provenance=replace(original.provenance, module_origin=None)
    )
    reading = read_set(
        (entry,), (), resolver=lambda name: supplied, as_of="2026-11-10"
    )
    observation = reading.observations[0]
    assert observation.code is ReadCode.IMPORT_FAILED
    assert observation.provenance.module_origin is None
    assert observation.diagnostics[0].phase == "resolve"
    assert reading_from_canonical(canonical_reading(reading)) == reading


def test_unprintable_resolver_failure_retains_original_exception_identity() -> None:
    class BrokenMessage(Exception):
        def __str__(self):
            raise RuntimeError("formatting failed")

    def resolver(name):
        raise BrokenMessage()

    reading = read_set(
        LINE_SET[:1], (), resolver=resolver, as_of="2026-11-10"
    )
    observation = reading.observations[0]
    assert observation.code is ReadCode.IMPORT_FAILED
    assert observation.diagnostics[0].exception_type == "BrokenMessage"
    assert len(observation.diagnostics[0].detail) <= 500
    assert reading_from_canonical(canonical_reading(reading)) == reading


def test_process_control_during_failure_formatting_still_propagates() -> None:
    class InterruptedMessage(Exception):
        def __str__(self):
            raise KeyboardInterrupt()

    def resolver(name):
        raise InterruptedMessage()

    with pytest.raises(KeyboardInterrupt):
        read_set(LINE_SET[:1], (), resolver=resolver, as_of="2026-11-10")

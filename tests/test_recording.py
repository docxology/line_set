"""Recorder controls use real package sources and files, without siblings."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from line_set import (
    LINE_SET,
    SetStatus,
    check_pinned_sources,
    reading_digest,
    reading_from_canonical,
)
from line_set.recording import build_record, main, review_date
from tests.support import environment, import_sandbox, write_line_package


def test_review_date_refuses_missing_or_dateless_configuration(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    with pytest.raises(SystemExit):
        review_date(path)
    path.write_text("paper:\n  title: Example\n")
    with pytest.raises(SystemExit):
        review_date(path)
    path.write_text('paper:\n  date: "2026-10-21"\n')
    assert review_date(path) == "2026-10-21"


def test_recorder_refuses_absence_without_writing(tmp_path: Path) -> None:
    with import_sandbox(), environment("LINE_SET_SIBLINGS", str(tmp_path)):
        target = tmp_path / "absent.json"
        with pytest.raises(SystemExit) as exc:
            main(["--as-of", "2026-10-21", "--out", str(target)])
        assert exc.value.code == 1
        assert not target.exists()


def test_recorder_refuses_readable_but_unpinned_sources(tmp_path: Path) -> None:
    for index, entry in enumerate(LINE_SET):
        write_line_package(
            tmp_path / entry.package_name / "src",
            entry.package_name,
            (f"NAME_{index}",),
            registry_sizes={"PRIMARY": index + 1},
        )
    target = tmp_path / "unpinned.json"
    with import_sandbox(), environment("LINE_SET_SIBLINGS", str(tmp_path)):
        record, _ = build_record("2026-11-06")
        assert record["reading"]["status"] == SetStatus.SET_LEGIBLE.value
        with pytest.raises(SystemExit) as exc:
            main(["--as-of", "2026-11-06", "--out", str(target)])
        assert exc.value.code == 1
        assert not target.exists()


def test_recorder_writes_rechecks_and_rejects_changed_or_missing_records(
    tmp_path: Path,
) -> None:
    for index, entry in enumerate(LINE_SET):
        write_line_package(
            tmp_path / entry.package_name / "src",
            entry.package_name,
            (f"NAME_{index}",),
            registry_sizes={"PRIMARY": index + 1},
            source_revision=f"{index + 1:040x}",
        )
    target = tmp_path / "record.json"
    args = ["--as-of", "2026-10-21", "--out", str(target)]
    with import_sandbox(), environment("LINE_SET_SIBLINGS", str(tmp_path)):
        with pytest.raises(SystemExit) as exc:
            main([*args, "--check"])
        assert exc.value.code == 1
        main(args)
        original = target.read_bytes()
        main([*args, "--check"])
        assert target.read_bytes() == original
        record = json.loads(original)
        record["vocabulary_census"]["distinct_names"] += 1
        target.write_text(json.dumps(record))
        with pytest.raises(SystemExit) as exc:
            main([*args, "--check"])
        assert exc.value.code == 1


def test_public_view_withholds_identity_without_erasing_private_record(
    tmp_path: Path,
) -> None:
    hidden = "violet_line"
    for index, entry in enumerate(LINE_SET):
        write_line_package(
            tmp_path / entry.package_name / "src",
            entry.package_name,
            (f"NAME_{index}",),
            registry_sizes={"PRIMARY": index + 1},
            source_revision="a" * 40 if entry.id == hidden else f"{index + 1:040x}",
        )
    private_path = tmp_path / "private.json"
    public_path = tmp_path / "public.json"
    args = ["--as-of", "2026-11-06"]
    with import_sandbox(), environment("LINE_SET_SIBLINGS", str(tmp_path)):
        main([*args, "--out", str(private_path)])
        private_bytes = private_path.read_bytes()
        private = json.loads(private_bytes)
        private_reading = reading_from_canonical(json.dumps(private["reading"]))
        assert check_pinned_sources(private_reading).passed
        source = next(
            item for item in private_reading.observations if item.line_id == hidden
        )
        public_args = [
            *args,
            "--out",
            str(public_path),
            "--withhold-source",
            hidden,
        ]
        main(public_args)
        public_bytes = public_path.read_bytes()
        public = json.loads(public_bytes)
        assert public["schema_version"] == "2.0-public"
        assert public["withheld_sources"] == [hidden]
        assert public["source_revisions"][hidden] is None
        reading = reading_from_canonical(json.dumps(public["reading"]))
        observation = next(
            item for item in reading.observations if item.line_id == hidden
        )
        assert observation.provenance.source_revision is None
        assert observation.provenance.module_origin is None
        assert source.provenance.source_revision.encode() not in public_bytes
        assert source.provenance.module_origin.encode() not in public_bytes
        assert reading.status is SetStatus.SET_LEGIBLE
        assert reading_digest(reading) == public["reading_digest"]
        assert not check_pinned_sources(reading).passed
        main([*public_args, "--check"])
        assert public_path.read_bytes() == public_bytes
        assert private_path.read_bytes() == private_bytes
        with pytest.raises(SystemExit) as exc:
            main([*args, "--out", str(public_path), "--check"])
        assert exc.value.code == 1


@pytest.mark.parametrize("defect", ["absent", "unpinned", "collision"])
def test_public_view_does_not_bypass_withheld_source_admission(
    tmp_path: Path, defect: str
) -> None:
    for index, entry in enumerate(LINE_SET):
        if entry.id == "violet_line" and defect == "absent":
            continue
        token = (
            "NAME_0"
            if entry.id == "violet_line" and defect == "collision"
            else f"NAME_{index}"
        )
        revision = (
            None
            if entry.id == "violet_line" and defect == "unpinned"
            else f"{index + 1:040x}"
        )
        write_line_package(
            tmp_path / entry.package_name / "src",
            entry.package_name,
            (token,),
            registry_sizes={"PRIMARY": index + 1},
            source_revision=revision,
        )
    target = tmp_path / "public.json"
    with import_sandbox(), environment("LINE_SET_SIBLINGS", str(tmp_path)):
        with pytest.raises(SystemExit) as exc:
            main(
                [
                    "--as-of",
                    "2026-11-06",
                    "--out",
                    str(target),
                    "--withhold-source",
                    "violet_line",
                ]
            )
        assert exc.value.code == 1
        assert not target.exists()


def test_public_view_check_rejects_changed_withheld_vocabulary(tmp_path: Path) -> None:
    for index, entry in enumerate(LINE_SET):
        write_line_package(
            tmp_path / entry.package_name / "src",
            entry.package_name,
            (f"NAME_{index}",),
            registry_sizes={"PRIMARY": index + 1},
            source_revision=f"{index + 1:040x}",
        )
    target = tmp_path / "public.json"
    args = [
        "--as-of",
        "2026-11-06",
        "--out",
        str(target),
        "--withhold-source",
        "violet_line",
    ]
    with import_sandbox(), environment("LINE_SET_SIBLINGS", str(tmp_path)):
        main(args)
    before = target.read_bytes()
    write_line_package(
        tmp_path / "violet_line" / "src",
        "violet_line",
        ("CHANGED_NAMESPACE",),
        registry_sizes={"PRIMARY": 7},
        source_revision="b" * 40,
    )
    with import_sandbox(), environment("LINE_SET_SIBLINGS", str(tmp_path)):
        with pytest.raises(SystemExit) as exc:
            main([*args, "--check"])
        assert exc.value.code == 1
    assert target.read_bytes() == before


def test_unknown_source_withholding_refuses_before_writing(tmp_path: Path) -> None:
    target = tmp_path / "public.json"
    with pytest.raises(ValueError):
        build_record("2026-11-06", withheld_sources=("undeclared_line",))
    with pytest.raises(SystemExit) as exc:
        main(["--out", str(target), "--withhold-source", "undeclared_line"])
    assert exc.value.code == 2
    assert not target.exists()


def test_only_private_record_detects_withheld_revision_only_change(
    tmp_path: Path,
) -> None:
    hidden_index = next(
        index for index, entry in enumerate(LINE_SET) if entry.id == "violet_line"
    )
    for index, entry in enumerate(LINE_SET):
        write_line_package(
            tmp_path / entry.package_name / "src",
            entry.package_name,
            (f"NAME_{index}",),
            registry_sizes={"PRIMARY": index + 1},
            source_revision=f"{index + 1:040x}",
        )
    private = tmp_path / "private.json"
    public = tmp_path / "public.json"
    args = ["--as-of", "2026-11-06"]
    public_args = [
        *args,
        "--out",
        str(public),
        "--withhold-source",
        "violet_line",
    ]
    with import_sandbox(), environment("LINE_SET_SIBLINGS", str(tmp_path)):
        main([*args, "--out", str(private)])
        main(public_args)
    public_before = public.read_bytes()
    private_before = private.read_bytes()
    write_line_package(
        tmp_path / "violet_line" / "src",
        "violet_line",
        (f"NAME_{hidden_index}",),
        registry_sizes={"PRIMARY": hidden_index + 1},
        source_revision="c" * 40,
    )
    with import_sandbox(), environment("LINE_SET_SIBLINGS", str(tmp_path)):
        main([*public_args, "--check"])
        with pytest.raises(SystemExit) as exc:
            main([*args, "--out", str(private), "--check"])
        assert exc.value.code == 1
    assert public.read_bytes() == public_before
    assert private.read_bytes() == private_before

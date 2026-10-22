"""Recorder controls use real package sources and files, without siblings."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from line_set import LINE_SET
from line_set.recording import build_record, main, review_date
from tests.support import environment, import_sandbox, write_line_package


def test_review_date_refuses_missing_or_dateless_configuration(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    with pytest.raises(SystemExit, match="cannot read"):
        review_date(path)
    path.write_text("paper:\n  title: Example\n")
    with pytest.raises(SystemExit, match="no ISO review date"):
        review_date(path)
    path.write_text('paper:\n  date: "2026-10-21"\n')
    assert review_date(path) == "2026-10-21"


def test_recorder_refuses_absence_without_writing(tmp_path: Path) -> None:
    with import_sandbox(), environment("LINE_SET_SIBLINGS", str(tmp_path)):
        record, refusals = build_record("2026-10-21")
        assert refusals
        assert record["vocabulary_census"]["per_line"] == {}
        target = tmp_path / "absent.json"
        with pytest.raises(SystemExit) as exc:
            main(["--as-of", "2026-10-21", "--out", str(target)])
        assert exc.value.code == 1
        assert not target.exists()


def test_recorder_writes_rechecks_and_rejects_changed_or_missing_records(
    tmp_path: Path, capsys
) -> None:
    for index, entry in enumerate(LINE_SET):
        write_line_package(
            tmp_path / entry.package_name / "src",
            entry.package_name,
            (f"NAME_{index}",),
            registry_sizes={"PRIMARY": index + 1},
        )
    target = tmp_path / "record.json"
    args = ["--as-of", "2026-10-21", "--out", str(target)]
    with import_sandbox(), environment("LINE_SET_SIBLINGS", str(tmp_path)):
        with pytest.raises(SystemExit) as exc:
            main([*args, "--check"])
        assert exc.value.code == 1
        assert "no record" in capsys.readouterr().err
        main(args)
        original = target.read_bytes()
        main([*args, "--check"])
        assert "agrees" in capsys.readouterr().out
        assert target.read_bytes() == original
        record = json.loads(original)
        assert record["schema_version"] == "2.0"
        assert len(record["vocabulary_census"]["per_line"]) == len(LINE_SET)
        record["vocabulary_census"]["distinct_names"] += 1
        target.write_text(json.dumps(record))
        with pytest.raises(SystemExit) as exc:
            main([*args, "--check"])
        assert exc.value.code == 1
        assert "disagrees" in capsys.readouterr().err

"""Bind ``data/formalism_claim_ledger.json`` to the manuscript and the record.

The external publication engine's evidence registry knows ``fig:``/``sec:``/
``tbl:``/``eq:``/``lst:`` label prefixes and treats every other ``[@x]`` as a
bibliography key, so a formalism reference is reported as an unsupported
citation unless the project declares it. ``data/formalism_claim_ledger.json``
is that declaration; this module re-derives the whole set from the manuscript
and the recorded reading so a block added, renamed, or removed without the
ledger following fails here rather than surfacing as a red output-validation
report after a render.

Nothing is asserted that was not first executed: the declared labels are
parsed from the real manuscript, and the numeric rows are re-read from the
recorded vocabulary census (itself re-derived from the live packages by
``scripts/record_reading.py``). Negative controls prove each gate can fail.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANUSCRIPT = ROOT / "manuscript"
LEDGER = ROOT / "data" / "formalism_claim_ledger.json"
READING_RECORD = MANUSCRIPT / "reading_record.json"

#: A formalism block opener: ``::: {.definition #def:x title="X"}``.
_BLOCK = re.compile(r"^::: \{(?P<attrs>[^}]*)\}\s*$", re.M)
_LABEL = re.compile(r"#([a-z]+:[a-z0-9-]+)")
#: The reference syntax the engine's citation check sees.
_REFERENCE = re.compile(
    r"\[@((?:def|prop|thm|lem|cor|rem|ax|clm|ex):[a-z0-9-]+)\]"
)


def _body_files() -> list[Path]:
    """Every manuscript body file except the preamble and the record."""

    return [
        path
        for path in sorted(MANUSCRIPT.glob("*.md"))
        if path.name not in ("preamble.md", "reading_record.json")
    ]


def _declared_labels() -> set[str]:
    """Every formalism-block label declared anywhere in the manuscript."""

    labels: set[str] = set()
    for path in _body_files():
        for match in _BLOCK.finditer(path.read_text(encoding="utf-8")):
            label = _LABEL.search(match.group("attrs"))
            if label:
                labels.add(label.group(1))
    return labels


def _referenced_labels() -> set[str]:
    """Every ``[@prefix:label]`` formalism reference in the manuscript."""

    refs: set[str] = set()
    for path in _body_files():
        refs.update(_REFERENCE.findall(path.read_text(encoding="utf-8")))
    return refs


def _ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def _ledger_citations() -> set[str]:
    return {
        row["value"]
        for row in _ledger()["claims"]
        if row["kind"] == "citation"
    }


def _census() -> dict[str, int]:
    """The recorded vocabulary census, re-read from the record."""

    record = json.loads(READING_RECORD.read_text(encoding="utf-8"))
    return {
        key: record["vocabulary_census"][key]
        for key in (
            "declared_members",
            "line_and_name_pairs",
            "distinct_names",
        )
    }


def _ledger_numbers() -> dict[str, int]:
    return {
        row["claim_id"]: row["value"]
        for row in _ledger()["claims"]
        if row["kind"] == "number"
    }


# -------------------------------------------------------------------- gates


def test_every_declared_label_is_in_the_ledger() -> None:
    """A block declared in the manuscript must be declared to the engine too."""

    declared = _declared_labels()

    assert declared, "no labels declared; this gate would be vacuous"
    assert _ledger_citations() == declared, sorted(
        _ledger_citations() ^ declared
    )


def test_every_ledger_citation_is_a_declared_block() -> None:
    """The ledger cannot declare a label the manuscript does not carry."""

    assert _ledger_citations() <= _declared_labels(), sorted(
        _ledger_citations() - _declared_labels()
    )


def test_every_referenced_label_is_both_declared_and_ledgered() -> None:
    """A reference the prose makes resolves on both sides of the contract."""

    declared = _declared_labels()
    referenced = _referenced_labels()

    assert referenced, "no formalism references found; this gate would be vacuous"
    assert referenced <= declared, sorted(referenced - declared)
    assert referenced <= _ledger_citations(), sorted(
        referenced - _ledger_citations()
    )


def test_every_ledger_source_path_exists() -> None:
    """A row pointing at a file that is not there is dead evidence."""

    for row in _ledger()["claims"]:
        assert (ROOT / row["source_path"]).is_file(), row["claim_id"]
        assert row["freshness"] == "active", row["claim_id"]


def test_ledger_claim_ids_are_unique() -> None:
    rows = _ledger()["claims"]

    assert len({row["claim_id"] for row in rows}) == len(rows)


def test_number_rows_match_the_recorded_census() -> None:
    """The vocabulary-census numbers are the record's, not restated prose."""

    census = _census()
    numbers = _ledger_numbers()

    assert numbers["census_declared_members"] == census["declared_members"]
    assert numbers["census_line_and_name_pairs"] == census["line_and_name_pairs"]
    assert numbers["census_distinct_names"] == census["distinct_names"]


# ------------------------------------------------------- negative controls


def test_negative_control_label_gap_fails() -> None:
    """Removing a citation row must break the declared-labels gate."""

    ledger = _ledger()
    ledger["claims"] = [
        row for row in ledger["claims"] if row["value"] != "def:reading"
    ]
    citations = {
        row["value"] for row in ledger["claims"] if row["kind"] == "citation"
    }

    assert citations != _declared_labels()


def test_negative_control_wrong_number_fails() -> None:
    """A restated (not derived) number must break the numeric gate."""

    ledger = _ledger()
    for row in ledger["claims"]:
        if row["claim_id"] == "census_declared_members":
            row["value"] = row["value"] + 1

    census = _census()
    numbers = {
        row["claim_id"]: row["value"]
        for row in ledger["claims"]
        if row["kind"] == "number"
    }
    assert numbers["census_declared_members"] != census["declared_members"]

"""Keep publication formalism references resolvable through the evidence ledger.

The external engine needs explicit declarations for definition/proposition
citations. These checks cover reference closure, evidence paths, and unique
claim identities. The numeric rows are generated from the canonical reading;
its independent census and replay contracts are checked in
``test_manuscript_bindings.py`` rather than testing copies of those numbers.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANUSCRIPT = ROOT / "docs" / "manuscript"
LEDGER = ROOT / "data" / "formalism_claim_ledger.json"

#: A formalism block opener: ``::: {.definition #def:x title="X"}``.
_BLOCK = re.compile(r"^::: \{(?P<attrs>[^}]*)\}\s*$", re.M)
_LABEL = re.compile(r"#([a-z]+:[a-z0-9-]+)")
#: The reference syntax the engine's citation check sees.
_REFERENCE = re.compile(r"\[@((?:def|prop|thm|lem|cor|rem|ax|clm|ex):[a-z0-9-]+)\]")


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
    return {row["value"] for row in _ledger()["claims"] if row["kind"] == "citation"}


# -------------------------------------------------------------------- gates


def test_every_declared_label_is_in_the_ledger() -> None:
    """A block declared in the manuscript must be declared to the engine too."""

    declared = _declared_labels()

    assert declared, "no labels declared; this gate would be vacuous"
    assert _ledger_citations() == declared, sorted(_ledger_citations() ^ declared)


def test_every_referenced_label_is_both_declared_and_ledgered() -> None:
    """A reference the prose makes resolves on both sides of the contract."""

    declared = _declared_labels()
    referenced = _referenced_labels()

    assert referenced, "no formalism references found; this gate would be vacuous"
    assert referenced <= declared, sorted(referenced - declared)
    assert referenced <= _ledger_citations(), sorted(referenced - _ledger_citations())


def test_every_ledger_source_path_exists() -> None:
    """A row pointing at a file that is not there is dead evidence."""

    for row in _ledger()["claims"]:
        assert (ROOT / row["source_path"]).is_file(), row["claim_id"]
        assert row["freshness"] == "active", row["claim_id"]


def test_ledger_claim_ids_are_unique() -> None:
    rows = _ledger()["claims"]

    assert len({row["claim_id"] for row in rows}) == len(rows)

"""Derivation of ``data/formalism_claim_ledger.json`` from the manuscript and the record.

Every row is derived, never hand-authored: citation rows from the formalism
blocks declared in the manuscript, census number rows from
``docs/manuscript/reading_record.json`` (itself re-derived from the live
packages by ``scripts/record_reading.py``). Tests re-derive the whole set and
fail on drift.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANUSCRIPT = ROOT / "docs" / "manuscript"
READING_RECORD = MANUSCRIPT / "reading_record.json"
LEDGER = ROOT / "data" / "formalism_claim_ledger.json"

#: A formalism block opener: ``::: {.definition #def:x title="X"}``.
_LAB = re.compile(
    r"^::: \{[^}]*#((?:def|prop|thm|lem|cor|rem|ax|clm|ex):[a-zA-Z0-9_-]+)",
    re.MULTILINE,
)

#: The census keys the ledger declares, in the order the binding test reads them.
_CENSUS_KEYS = ("declared_members", "line_and_name_pairs", "distinct_names")


def declared_labels() -> list[tuple[str, Path]]:
    """Every formalism-block label declared in the manuscript."""

    labels: list[tuple[str, Path]] = []
    for path in sorted(MANUSCRIPT.glob("*.md")):
        if path.name == "preamble.md":
            continue
        for match in _LAB.finditer(path.read_text(encoding="utf-8")):
            labels.append((match.group(1), path))
    return labels


def citation_row(label: str, path: Path) -> dict[str, str]:
    """The declaration the engine's evidence registry reads for one label."""

    return {
        "claim_id": label.replace(":", "_"),
        "kind": "citation",
        "value": label,
        "source": (
            f"docs/manuscript/{path.name}: formalism block declared with this label"
        ),
        "source_path": f"docs/manuscript/{path.name}",
        "source_tier": "manuscript_formalism_block",
        "freshness": "active",
    }


def number_rows() -> list[dict[str, object]]:
    """The recorded vocabulary census, re-read from the record."""

    record = json.loads(READING_RECORD.read_text(encoding="utf-8"))
    return [
        {
            "claim_id": f"census_{key}",
            "kind": "number",
            "value": record["vocabulary_census"][key],
            "source": (
                "docs/manuscript/reading_record.json vocabulary_census."
                f"{key} (re-derived from the live packages by "
                "scripts/record_reading.py)"
            ),
            "source_path": "docs/manuscript/reading_record.json",
            "source_tier": "recorded_reading_census",
            "freshness": "active",
        }
        for key in _CENSUS_KEYS
    ]


def build_ledger() -> str:
    """Regenerate the ledger from the manuscript and the recorded reading.

    Returns the summary line the CLI prints.
    """
    claims: list[dict[str, object]] = [
        citation_row(*row) for row in sorted(declared_labels())
    ]
    claims += number_rows()
    payload = {
        "schema_version": "1.0",
        "purpose": (
            "Declares the manuscript's formalism-block labels and the "
            "vocabulary-census numbers the prose states, so the render "
            "engine's evidence registry can resolve those "
            "[@def:...]/[@prop:...] cross-references and counts instead of "
            "reporting them as unsupported citations. Every row is derived "
            "from the manuscript or the recorded reading; "
            "tests/test_formalism_claim_ledger.py re-derives the whole set "
            "and fails if a block is added, renamed, or removed without this "
            "file following."
        ),
        "boundary": (
            "A row here records that a label is declared and that a number "
            "is re-derivable. It is not evidence that the proposition it "
            "names is true, and it grants no claim any weight."
        ),
        "claims": claims,
    }
    LEDGER.write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    return f"wrote {LEDGER.relative_to(ROOT)} with {len(claims)} claims"

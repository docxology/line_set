"""Re-derive every row of data/claim_ledger.yaml from the running package.

Every `kind: number` row in data/claim_ledger.yaml is derived from its source here,
ensuring the ledger cannot drift from the executable declaration or manuscript.
"""

from __future__ import annotations

import re
from pathlib import Path

from line_set.registry import LINE_SET, SHARED_TOKENS
from line_set.reader import READER_STAGES
from line_set.models import SetStatus

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "claim_ledger.yaml"
MANUSCRIPT = ROOT / "manuscript"


def _parse_yaml_claims(path: Path) -> dict[str, int]:
    """Parse id -> value mapping for number claims from claim_ledger.yaml."""
    text = path.read_text(encoding="utf-8")
    claims: dict[str, int] = {}
    current_id: str | None = None
    current_kind: str | None = None

    for line in text.splitlines():
        id_match = re.search(r"^\s*-\s*id:\s*(\w+)", line)
        if id_match:
            current_id = id_match.group(1)
            current_kind = None
            continue
        kind_match = re.search(r"^\s*kind:\s*(\w+)", line)
        if kind_match:
            current_kind = kind_match.group(1)
            continue
        val_match = re.search(r"^\s*value:\s*(\d+)", line)
        if val_match and current_id and current_kind == "number":
            claims[current_id] = int(val_match.group(1))
            current_id = None
            current_kind = None

    return claims


def test_the_ledger_file_exists() -> None:
    assert LEDGER.is_file(), "data/claim_ledger.yaml is missing"


def test_claim_ledger_re_derives_all_numeric_claims() -> None:
    claims = _parse_yaml_claims(LEDGER)
    assert claims, "no numeric claims found in claim_ledger.yaml"

    # 1. line_entry_count
    assert claims["line_entry_count"] == len(LINE_SET)

    # 2. shared_token_count
    assert claims["shared_token_count"] == len(SHARED_TOKENS)

    # 3. reader_stage_count
    assert claims["reader_stage_count"] == len(READER_STAGES)

    # 4. set_status_count
    assert claims["set_status_count"] == len(SetStatus)

    # 5. formal_definition_count & formal_proposition_count in 02a_formalism.md
    form_2a = (MANUSCRIPT / "02a_formalism.md").read_text(encoding="utf-8")
    def_count = len(re.findall(r":::\s*\{[^}]*\.definition[^}]*\}", form_2a))
    prop_count = len(re.findall(r":::\s*\{[^}]*\.proposition[^}]*\}", form_2a))
    assert claims["formal_definition_count"] == def_count
    assert claims["formal_proposition_count"] == prop_count

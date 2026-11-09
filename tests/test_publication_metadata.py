"""Publication metadata: consistent versions, canonical URLs, edition boundaries.

These local contracts bind package/config/citation versions and repository
identities. They do not independently verify an external archive or deposit.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from line_set import __version__

ROOT = Path(__file__).resolve().parents[1]
CITATION = ROOT / "CITATION.cff"
ZENODO = ROOT / ".zenodo.json"
CONFIG = ROOT / "docs" / "manuscript" / "config.yaml"
LICENSE = ROOT / "LICENSE"

SELF = "line_set"
SIBLINGS = ("red_line", "black_line", "golden_line", "white_line", "witness_register")


#: A DOI as the registries publish them.
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")


def _config_paper_version() -> str:
    text = CONFIG.read_text(encoding="utf-8")
    in_paper = False
    for line in text.splitlines():
        if line.strip() and not line.startswith((" ", "#")):
            in_paper = line.strip() == "paper:"
            continue
        if in_paper:
            match = re.match(r'\s+version:\s*"([^"]+)"\s*$', line)
            if match:
                return match.group(1)
    raise AssertionError("paper.version not found in docs/manuscript/config.yaml")


def _cff_field(name: str) -> str:
    for line in CITATION.read_text(encoding="utf-8").splitlines():
        match = re.match(rf'{name}:\s*"([^"]+)"\s*$', line)
        if match:
            return match.group(1)
    raise AssertionError(f"{name} not found in CITATION.cff")


def test_the_four_version_statements_agree() -> None:
    """Package, manuscript, CITATION.cff, and .zenodo.json state one version."""

    zenodo = json.loads(ZENODO.read_text(encoding="utf-8"))
    assert _cff_field("version") == __version__
    assert zenodo["version"] == __version__
    assert _config_paper_version() == __version__


def test_the_citation_names_this_repository_exactly() -> None:
    expected = f"https://github.com/docxology/{SELF}"
    assert _cff_field("repository-code") == expected
    zenodo = json.loads(ZENODO.read_text(encoding="utf-8"))
    supplements = [
        item["identifier"]
        for item in zenodo["related_identifiers"]
        if item["relation"] == "isSupplementTo"
    ]
    assert supplements == [expected]


def test_the_archived_doi_cannot_identify_the_current_candidate() -> None:
    config = CONFIG.read_text(encoding="utf-8")
    publication = config.split("publication:\n", 1)[1].split("\n\n", 1)[0]
    current_doi = re.search(r'^  doi: "([^"]*)"$', publication, re.MULTILINE)
    archive_doi = re.search(r'archived_version_doi: "([^"]+)"', publication).group(1)
    archive_version = re.search(r'archived_version: "([^"]+)"', publication).group(1)
    assert current_doi is None or current_doi.group(1) != archive_doi
    assert archive_version != __version__
    citation, references = CITATION.read_text(encoding="utf-8").split(
        "references:\n", 1
    )
    assert archive_doi not in DOI_PATTERN.findall(citation)
    archives = references.split("  - type: software")[1:]
    assert any(
        f'version: "{archive_version}"' in archive
        and f'doi: "{archive_doi}"' in archive
        for archive in archives
    )


def test_retained_citation_cohort_uses_canonical_urls() -> None:
    """Every retained citation reference uses its canonical public URL."""

    citation = CITATION.read_text(encoding="utf-8")
    zenodo = json.loads(ZENODO.read_text(encoding="utf-8"))
    identifiers = {item["identifier"] for item in zenodo["related_identifiers"]}
    for sibling in SIBLINGS:
        url = f"https://github.com/docxology/{sibling}"
        assert f'repository-code: "{url}"' in citation, sibling
        assert url in identifiers, sibling


def test_the_license_declares_both_halves() -> None:
    text = LICENSE.read_text(encoding="utf-8")
    assert "MIT License" in text
    assert "CC BY 4.0" in text or "CC-BY-4.0" in text
    assert "creativecommons.org/licenses/by/4.0" in text
    assert "Permission is hereby granted, free of charge" in text


def test_no_absolute_local_path_is_shipped() -> None:
    """A path from the author's machine is both noise and a small leak."""

    skip_dirs = {
        ".git",
        ".venv",
        "output",
        "htmlcov",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
        "graft",
    }
    text_suffixes = {
        ".py",
        ".md",
        ".toml",
        ".cff",
        ".json",
        ".yaml",
        ".yml",
        ".bib",
        ".txt",
        ".sh",
        ".cfg",
    }
    offenders = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in text_suffixes:
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.name == "test_publication_metadata.py":
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        # Derive the machine-local prefix at runtime to avoid hardcoding
        # a path literal that would trip the lexical no-local-path guards.
        _home_parent = str(Path.home().parent) + "/"
        if _home_parent in content:
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, f"absolute local paths in: {offenders}"

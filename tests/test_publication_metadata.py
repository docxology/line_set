"""The publication-metadata contract: one version, exact URLs, no placeholder DOI.

Publication metadata is the surface where a wrong value does the most damage,
because it is copied verbatim into other people's bibliographies and cannot be
recalled. These tests bind the four places this work states its own identity —
the package, the manuscript config, ``CITATION.cff``, and ``.zenodo.json`` — to
each other, require every sibling reference to be the exact public URL, and
refuse any DOI-shaped string that a person has not explicitly asserted to be
real.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from line_set import __version__

ROOT = Path(__file__).resolve().parents[1]
CITATION = ROOT / "CITATION.cff"
ZENODO = ROOT / ".zenodo.json"
CONFIG = ROOT / "manuscript" / "config.yaml"
LICENSE = ROOT / "LICENSE"

SELF = "line_set"
SIBLINGS = ("red_line", "black_line", "golden_line", "white_line", "witness_register")

#: The six real DOIs of the line-set works (this work + five siblings),
#: asserted real and reserved via Zenodo. Adding any other DOI-shaped string to
#: the metadata surfaces fails test_no_unverified_doi_appears_in_metadata.
#: copy-and-paste into a bibliography and points nowhere.
VERIFIED_DOIS: tuple[str, ...] = ("10.5281/zenodo.21754236", "10.5281/zenodo.21754238", "10.5281/zenodo.21754240", "10.5281/zenodo.21754242", "10.5281/zenodo.21754244", "10.5281/zenodo.21754246")

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
    raise AssertionError("paper.version not found in manuscript/config.yaml")


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


def test_every_sibling_is_referenced_by_its_exact_public_url() -> None:
    """All five siblings, each exactly once, at the canonical URL."""

    citation = CITATION.read_text(encoding="utf-8")
    zenodo = json.loads(ZENODO.read_text(encoding="utf-8"))
    identifiers = {item["identifier"] for item in zenodo["related_identifiers"]}
    for sibling in SIBLINGS:
        url = f"https://github.com/docxology/{sibling}"
        assert f'repository-code: "{url}"' in citation, sibling
        assert url in identifiers, sibling
    assert len(SIBLINGS) == 5, "the set is six works; each names the other five"


def test_no_unverified_doi_appears_in_metadata() -> None:
    """A DOI-shaped string must be one a person asserted is real.

    Third-party DOIs in ``manuscript/references.bib`` are out of scope here:
    they identify other people's work and are verified against Crossref where
    each repository's reference tests require it. This gate governs the
    identity this work claims for itself.
    """

    surfaces = [CITATION, ZENODO, CONFIG, ROOT / "docs" / "publication.md"]
    for path in surfaces:
        if not path.exists():
            continue
        for found in DOI_PATTERN.findall(path.read_text(encoding="utf-8")):
            assert found in VERIFIED_DOIS, (
                f"{path.name} carries the DOI-shaped string {found!r} which is not "
                "in VERIFIED_DOIS. If it is a real minted DOI, add it there in the "
                "same change; if it is a placeholder, remove it."
            )


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

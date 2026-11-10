"""Consumer geometry regressions; native raster checks are intentionally real."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from line_set import LINE_SET, ReadCode, SetStatus, read_set
from line_set.figures import build_figures
from line_set.binding import Resolution
from line_set.figures.canvas import (
    MIN_TEXT_UNITS,
    exact_lines,
    text_block,
    wrap_to_width,
)
from line_set.figures.plates.application import self_application
from line_set.figures.plates.cover import cover_svg
from line_set.figures.plates.declaration import set_compass, two_orders
from line_set.figures.plates.exemption import exemption_gate
from line_set.figures.plates.reading import installation_surface, vocabulary_matrix
from line_set.models import LineObservation, SetReading, SharedToken
from line_set.registry import WRAPPER_LINE
from tests.support import absent
from tests.test_figure_layout import SVG, _layout_problems


def test_exact_fragments_preserve_long_identity_without_smaller_fonts() -> None:
    value = "W" * 203
    rows = exact_lines(value, 240, 24)
    assert "".join(rows) == value
    assert all(len(row) * 24 <= 240 for row in rows)
    assert all(len(row) * 24 <= 144 for row in wrap_to_width(value, 144, 24))
    authored = value + "_identity  tail"
    assert "".join(exact_lines(authored, 240, 24)) == authored
    assert exact_lines("golden_line", 240, 24) == ["golden_line"]


@pytest.mark.parametrize("value", ["&" * 16, "?&&&&&&~&&&&&&!&&&&"])
def test_wide_punctuation_labels_fit_native_rendered_card(
    tmp_path: Path, value: str
) -> None:
    parts, _ = text_block(20, 40, value, 240, 24, weight="700")
    source = tmp_path / "wide-punctuation.svg"
    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 280 180" width="280" height="180">'
        '<rect x="20" y="0" width="240" height="180" fill="none"/>'
        + "".join(parts)
        + "</svg>"
    )
    root = ET.parse(source).getroot()
    assert "".join(node.text or "" for node in root.iter(SVG + "text")) == value
    scratch = tmp_path / "measured"
    scratch.mkdir()
    assert not _layout_problems(source, scratch)


@pytest.mark.parametrize("count", [12, 13, 37])
def test_extended_cover_strokes_remain_separate_and_labels_remain_complete(
    tmp_path: Path,
    count: int,
) -> None:
    entries = tuple(
        replace(
            LINE_SET[0],
            id=f"line_{i}",
            package_name=f"line_{i}",
            color=f"color_{i}",
            working_position=i + 1,
        )
        for i in range(count)
    )
    root = ET.fromstring(cover_svg(entries))
    groups = [
        node for node in root.iter(SVG + "g") if "data-cover-color" in node.attrib
    ]
    assert {node.attrib["data-cover-color"] for node in groups} == {
        entry.color for entry in entries
    }
    strokes = []
    for group in groups:
        assert (
            "".join(node.text or "" for node in group.iter(SVG + "text"))
            == group.attrib["data-cover-color"]
        )
        stroke = next(
            node
            for node in group.iter(SVG + "line")
            if float(node.attrib["stroke-width"]) == 6
        )
        strokes.append(tuple(float(stroke.attrib[key]) for key in ("y1", "x1", "x2")))
    for y in {stroke[0] for stroke in strokes}:
        segments = sorted((left, right) for row, left, right in strokes if row == y)
        assert all(
            right < next_left
            for (_, right), (next_left, _) in zip(segments, segments[1:])
        )
    source = tmp_path / "cover.svg"
    source.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")
    scratch = tmp_path / "measured"
    scratch.mkdir()
    assert not _layout_problems(source, scratch)


@pytest.mark.parametrize("plate", ["compass", "installation"])
def test_shipped_declaration_and_absent_reading_clear_the_authored_page_floor(
    tmp_path: Path,
    plate: str,
) -> None:
    from line_set.figures.legibility import (
        measure_plate,
        parse_height_fraction,
        parse_page_geometry,
    )

    reading = read_set(
        LINE_SET,
        (),
        resolver=lambda name: Resolution(
            name,
            ReadCode.NOT_INSTALLED,
            None,
            "Intentional standalone absence control; not a native verdict.",
        ),
        as_of="2026-11-09",
    )
    body = (
        set_compass(LINE_SET, WRAPPER_LINE)
        if plate == "compass"
        else installation_surface(LINE_SET, reading)
    )
    source = tmp_path / f"{plate}.svg"
    source.write_text(body, encoding="utf-8")
    config = (
        Path(__file__).resolve().parents[1] / "docs" / "manuscript" / "config.yaml"
    ).read_text(encoding="utf-8")
    measured = measure_plate(
        source,
        f"fig:{plate}",
        f"{plate}.png",
        1.0,
        parse_page_geometry(config),
        parse_height_fraction(config),
    )
    assert measured.legible, measured
    scratch = tmp_path / "measured"
    scratch.mkdir()
    assert not _layout_problems(source, scratch)


@pytest.mark.parametrize(
    "plate",
    [
        "compass",
        "orders",
        "matrix",
        "installation",
        "application",
        "exemption",
        "cover",
    ],
)
def test_long_dynamic_text_is_complete_and_native_layout_stays_in_bounds(
    tmp_path: Path,
    plate: str,
) -> None:
    identity = "W" * 201
    token = "LONG_TOKEN_" + "W" * 203
    entry = replace(
        LINE_SET[0],
        id=identity,
        package_name=identity,
        color=identity,
        question=identity,
        job=identity,
        registry_noun=identity,
        verdict_noun=identity,
        must_not_become=identity,
        opus_stage=None,
    )
    other = replace(LINE_SET[1], working_position=2)
    lines = (entry, other)
    tokens = tuple(sorted([token, *(f"WRAPPER_TOKEN_{i:03}" for i in range(41))]))
    reading = SetReading(
        status=SetStatus.SET_LEGIBLE,
        observations=(
            LineObservation(
                entry.id,
                ReadCode.RESOLVED,
                version=identity,
                registry_size=1,
                registry_digest="a" * 64,
                tokens=(token,),
                detail=identity,
            ),
            LineObservation(
                other.id,
                ReadCode.RESOLVED,
                version="1",
                registry_size=1,
                registry_digest="b" * 64,
                tokens=("OTHER_TOKEN",),
            ),
            LineObservation(WRAPPER_LINE.id, ReadCode.RESOLVED, tokens=tokens),
        ),
        collisions=(),
        exempted_collisions=(),
        undeclared_lines=(identity,),
        set_digest="c" * 64,
        read_as_of="2026-01-01",
    )
    shared = (
        SharedToken(
            token,
            (entry.id, other.id),
            ((entry.id, "first meaning"), (other.id, "second meaning")),
            "Two declared meanings",
        ),
    )
    builders = {
        "compass": lambda: set_compass(lines, WRAPPER_LINE),
        "orders": lambda: two_orders(lines),
        "matrix": lambda: vocabulary_matrix(lines, reading),
        "installation": lambda: installation_surface(lines, reading),
        "application": lambda: self_application(lines, WRAPPER_LINE, reading),
        "exemption": lambda: exemption_gate(lines, shared),
        "cover": lambda: cover_svg(lines),
    }
    body = builders[plate]()
    root = ET.fromstring(body)
    texts = list(root.iter(SVG + "text"))
    assert texts
    assert all(
        float(node.attrib["font-size"].removesuffix("px")) >= MIN_TEXT_UNITS
        for node in texts
    )
    assert all(
        0 < float(node.attrib["y"]) < float(root.attrib["height"]) for node in texts
    )
    values = [
        node.attrib["data-full-text"]
        for node in root.iter(SVG + "g")
        if "data-full-text" in node.attrib
    ]
    if plate == "matrix":
        group = next(
            node
            for node in root.iter(SVG + "g")
            if node.attrib.get("data-token") == token
        )
        name = next(node for node in group if node.attrib.get("class") == "token-name")
        assert "".join(node.text or "" for node in name) == token
    elif plate == "cover":
        group = next(
            node
            for node in root.iter(SVG + "g")
            if node.attrib.get("data-cover-color") == identity
        )
        assert "".join(node.text or "" for node in group.iter(SVG + "text")) == identity
    else:
        assert any(
            (token if plate == "exemption" else identity) in value for value in values
        ) or (
            plate == "orders" and identity in "".join(node.text or "" for node in texts)
        )
    source = tmp_path / f"{plate}.svg"
    source.write_text(body, encoding="utf-8")
    scratch = tmp_path / "measured"
    scratch.mkdir()
    assert not _layout_problems(source, scratch)


@pytest.mark.parametrize(
    "destination",
    [
        "output",
        "figures",
        "set_compass.svg",
        "set_compass.png",
        "figure_registry.json",
        "set_registry.json",
    ],
)
def test_real_builder_refuses_output_symlinks_without_touching_external_bytes(
    tmp_path: Path,
    destination: str,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    sentinel = external / "sentinel"
    sentinel.write_bytes(b"unrelated source bytes")
    if destination == "output":
        (root / "output").symlink_to(external, target_is_directory=True)
    elif destination == "figures":
        (root / "output").mkdir()
        (root / "output" / "figures").symlink_to(external, target_is_directory=True)
    else:
        figures = root / "output" / "figures"
        figures.mkdir(parents=True)
        (figures / destination).symlink_to(sentinel)
    with pytest.raises(ValueError, match="symlink"):
        build_figures(root, resolver=absent, as_of="2026-01-01")
    assert sentinel.read_bytes() == b"unrelated source bytes"
    assert sorted(path.name for path in external.iterdir()) == ["sentinel"]


def test_output_preflight_allows_regular_local_files_and_leaves_unrelated_files(
    tmp_path: Path,
) -> None:
    from line_set.figures.build import _check_output_paths

    figures = tmp_path / "output" / "figures"
    figures.mkdir(parents=True)
    (figures / "set_compass.svg").write_text(
        "previous owned artifact", encoding="utf-8"
    )
    note = figures / "operator-note.txt"
    note.write_bytes(b"keep")
    assert _check_output_paths(tmp_path, ("set_compass.svg",)) == figures
    assert note.read_bytes() == b"keep"

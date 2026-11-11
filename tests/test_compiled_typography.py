"""Consumer regressions for real cross-owner font forms and cover placement."""

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from line_set import LINE_SET
from line_set.figures.legibility import (
    PageGeometry,
    measure_plate,
    measure_surface,
    parse_embed_text,
)
from line_set.figures.plates.cover import cover_svg
from line_set.omnibus import SourcePaper, part_heading


@pytest.mark.parametrize("font_attribute", ['font-size="17"', "font-size='17px'"])
def test_numeric_svg_labels_remain_measurable_at_their_real_placement(
    tmp_path: Path, font_attribute: str
) -> None:
    source = tmp_path / "native.svg"
    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="360">'
        f'<text x="48" y="140" {font_attribute}>Visible native label</text></svg>',
        encoding="utf-8",
    )
    geometry = PageGeometry(text_width_pt=566.6, text_height_pt=747.3)
    reduced = measure_plate(source, "fig:native", "native.png", 0.7, geometry, 0.92)
    full = measure_plate(source, "fig:native", "native.png", 1.0, geometry, 0.92)
    assert reduced.min_font_units == full.min_font_units == 17
    assert not reduced.legible
    assert full.legible


def test_a_smaller_css_label_cannot_hide_behind_a_larger_attribute(
    tmp_path: Path,
) -> None:
    source = tmp_path / "mixed.svg"
    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="500">'
        "<style>text { font-size: 12px; }</style>"
        '<text x="20" y="30">Small body label</text>'
        '<text x="20" y="80" font-size="32px">Larger heading</text></svg>',
        encoding="utf-8",
    )
    measured = measure_plate(
        source,
        "fig:mixed",
        "mixed.png",
        1.0,
        PageGeometry(text_width_pt=400, text_height_pt=700),
        0.92,
    )
    assert measured.min_font_units == 12
    assert measured.rendered_min_pt == pytest.approx(4.8)
    assert not measured.legible


def test_compiled_cover_placement_preserves_native_label_legibility(
    tmp_path: Path,
) -> None:
    source = tmp_path / "native-cover.svg"
    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1100">'
        '<text x="100" y="1000" font-size="20px">Native cover boundary</text></svg>',
        encoding="utf-8",
    )
    paper = SourcePaper(
        entry=LINE_SET[0],
        root=tmp_path,
        config=None,
        sections=(),
        references_only=(),
        bib=None,
        preamble=None,
        figures=(),
        cover_image=source,
        absence="",
    )
    occurrences = parse_embed_text(part_heading(paper, 1), source="compiled-part.md")
    measured = measure_surface(
        occurrences,
        config_text=(
            'geometry: "left=0.33in,right=0.33in,top=0.33in,bottom=0.33in"\n'
            "rendering:\n  figure_height_fraction: 0.92\n"
        ),
        svg_sources={occurrences[0].image_path: source},
        surface="compiled",
    )[0]
    assert measured.legible


def test_the_native_cover_keeps_ordinary_declared_color_names_whole() -> None:
    svg = "{http://www.w3.org/2000/svg}"
    root = ET.fromstring(cover_svg(LINE_SET))
    groups = [
        node for node in root.iter(svg + "g") if "data-cover-color" in node.attrib
    ]
    labels = {
        group.attrib["data-cover-color"]: tuple(
            node.text for node in group.iter(svg + "text")
        )
        for group in groups
    }
    assert labels == {entry.color: (entry.color,) for entry in LINE_SET}

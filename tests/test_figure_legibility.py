"""The rendered-legibility gate: does the smallest label survive the page?

``canvas.MIN_TEXT_UNITS`` stops a label being authored too small in canvas
units. That is not the same question as whether the label is readable, because a
canvas unit is not a unit the page has: the same 18-unit label is comfortable on
a plate embedded at full text width and unreadable on one the renderer has
squeezed into half a column. Until this module existed, nothing in the tree
measured the second question, and the plates were landing at 4.27pt — below the
6.0pt floor the sibling line projects hold their figures to.

Three things are checked here.

**The derivation is right.** The identity that converts canvas units to page
points is exercised on inputs whose answer can be computed by hand, including
the case where the height cap binds before the declared width and shrinks the
whole plate.

**The shipped plates clear the floor.** Measured from the SVGs in
``output/figures`` and the widths the manuscript actually declares, not from a
number typed into prose.

**The gate can fail.** The load-bearing test is the planted one: an SVG whose
smallest label is below the floor must be reported illegible. A gate that has
only ever seen good input is compatible with one that returns ``True``
unconditionally, and this project's own documentation calls that out as the
most common way a check stops being a check.

The measurement reads files. No patching library is used anywhere: the planted
cases are real SVG and real config text written to a real temporary directory.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from line_set.figures import canvas, legibility
from line_set.figures.legibility import (
    MIN_LEGIBLE_PT,
    PageGeometry,
    illegible,
    measure_plate,
    measure_project,
    parse_embeds,
    parse_height_fraction,
    parse_page_geometry,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: A plate whose smallest label sits exactly at the shipped canvas floor.
_SVG_TEMPLATE = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
    'viewBox="0 0 {width} {height}">'
    '<text x="10" y="10" font-family="Arial, sans-serif" font-size="{small}px" '
    'font-weight="400" fill="#000" text-anchor="start">small</text>'
    '<text x="10" y="40" font-family="Arial, sans-serif" font-size="40px" '
    'font-weight="700" fill="#000" text-anchor="start">large</text>'
    "</svg>"
)

_CONFIG = """paper:
  title: "Planted"

rendering:
  figure_height_fraction: {fraction}

metadata:
  geometry: "left=0.42in,right=0.42in,top=0.55in,bottom=0.55in"
"""


def _plant(
    root: Path,
    *,
    small: int,
    width: int,
    height: int,
    fraction: float,
    embed_width: str,
) -> Path:
    """Write a whole minimal project: config, one embed, one SVG."""
    manuscript = root / "manuscript"
    manuscript.mkdir(parents=True, exist_ok=True)
    (manuscript / "config.yaml").write_text(
        _CONFIG.format(fraction=fraction), encoding="utf-8"
    )
    (manuscript / "01_body.md").write_text(
        f"![A planted plate.](../output/figures/planted.png)"
        f"{{#fig:planted{embed_width}}}\n",
        encoding="utf-8",
    )
    figures = root / "output" / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    (figures / "planted.svg").write_text(
        _SVG_TEMPLATE.format(width=width, height=height, small=small),
        encoding="utf-8",
    )
    return root


# ------------------------------------------------------- the derivation


def test_the_page_geometry_is_derived_from_the_declared_margins() -> None:
    geometry = parse_page_geometry(_CONFIG.format(fraction=0.92))
    # 8.5in - 0.84in of margin, and 11in - 1.10in, both in TeX points.
    assert geometry.text_width_pt == pytest.approx(7.66 * 72.27)
    assert geometry.text_height_pt == pytest.approx(9.90 * 72.27)


def test_a_config_with_no_geometry_is_refused_rather_than_defaulted() -> None:
    """Guessing the margins would produce a number that looks derived."""
    with pytest.raises(ValueError) as error:
        parse_page_geometry('paper:\n  title: "no geometry here"\n')
    assert "geometry" in str(error.value)


def test_a_geometry_missing_a_margin_is_refused() -> None:
    with pytest.raises(ValueError) as error:
        parse_page_geometry('metadata:\n  geometry: "left=0.5in,top=0.5in"\n')
    assert "right" in str(error.value)


def test_an_undeclared_height_fraction_falls_back_to_the_template_default() -> None:
    """The cap is injected into the generated LaTeX, so its default matters."""
    assert parse_height_fraction("rendering:\n  formats:\n    pdf: true\n") == (
        legibility.DEFAULT_FIGURE_HEIGHT_FRACTION
    )
    assert parse_height_fraction(_CONFIG.format(fraction=0.92)) == 0.92


def test_an_embed_with_no_width_attribute_takes_the_full_text_width(
    tmp_path: Path,
) -> None:
    _plant(tmp_path, small=18, width=1600, height=1000, fraction=0.92, embed_width="")
    assert parse_embeds(tmp_path / "manuscript") == {
        "planted.png": ("fig:planted", 1.0)
    }


def test_a_width_attribute_is_read_as_a_fraction(tmp_path: Path) -> None:
    _plant(
        tmp_path,
        small=18,
        width=1600,
        height=1000,
        fraction=0.92,
        embed_width=" width=95%",
    )
    assert parse_embeds(tmp_path / "manuscript") == {
        "planted.png": ("fig:planted", 0.95)
    }


def test_the_rendered_point_size_is_the_declared_width_ratio(tmp_path: Path) -> None:
    """The whole identity, on numbers that can be checked by hand."""
    root = _plant(
        tmp_path, small=18, width=1600, height=1000, fraction=0.92, embed_width=""
    )
    (measured,) = measure_project(root)
    text_width = 7.66 * 72.27
    assert measured.rendered_width_pt == pytest.approx(text_width)
    assert measured.height_bound is False
    assert measured.rendered_min_pt == pytest.approx(18 * text_width / 1600)
    assert measured.legible


def test_a_tall_plate_is_bound_by_the_height_cap_and_shrinks(tmp_path: Path) -> None:
    """The failure this module exists to catch: nothing in the SVG shows it."""
    root = _plant(
        tmp_path, small=18, width=1600, height=4000, fraction=0.92, embed_width=""
    )
    (measured,) = measure_project(root)
    text_height = 9.90 * 72.27
    assert measured.height_bound is True
    assert measured.rendered_width_pt == pytest.approx(0.92 * text_height * 1600 / 4000)
    assert measured.rendered_min_pt < MIN_LEGIBLE_PT
    assert not measured.legible


# ------------------------------------------------------- proof of detection


def test_a_plate_below_the_floor_is_reported_illegible(tmp_path: Path) -> None:
    """The load-bearing direction. A gate that cannot fail is not a gate.

    Twelve canvas units at full text width lands at about 4.15pt, which is the
    order of size the shipped plates were at before the floor was raised.
    """
    root = _plant(
        tmp_path, small=12, width=1600, height=1000, fraction=0.92, embed_width=""
    )
    measured = measure_project(root)
    failing = illegible(measured)
    assert [item.label for item in failing] == ["fig:planted"]
    assert failing[0].rendered_min_pt < MIN_LEGIBLE_PT
    assert failing[0].rendered_min_pt == pytest.approx(12 * 7.66 * 72.27 / 1600)


def test_the_same_plate_one_unit_larger_passes(tmp_path: Path) -> None:
    """Bracketing the floor, so the check is not simply always failing."""
    root = _plant(
        tmp_path, small=18, width=1600, height=1000, fraction=0.92, embed_width=""
    )
    assert illegible(measure_project(root)) == ()


def test_a_narrow_embed_of_a_legible_plate_becomes_illegible(tmp_path: Path) -> None:
    """The embed width is part of the measurement, not a constant."""
    root = _plant(
        tmp_path,
        small=18,
        width=1600,
        height=1000,
        fraction=0.92,
        embed_width=" width=50%",
    )
    (measured,) = measure_project(root)
    assert measured.width_fraction == 0.5
    assert not measured.legible


# ------------------------------------------------------- empty and missing


def test_a_project_with_no_embed_fails_rather_than_passing_vacuously(
    tmp_path: Path,
) -> None:
    """A floor over zero plates is green for the uninteresting reason."""
    manuscript = tmp_path / "manuscript"
    manuscript.mkdir(parents=True)
    (manuscript / "config.yaml").write_text(
        _CONFIG.format(fraction=0.92), encoding="utf-8"
    )
    (manuscript / "01_body.md").write_text("No figure here.\n", encoding="utf-8")
    with pytest.raises(ValueError) as error:
        measure_project(tmp_path)
    assert "no figure embed" in str(error.value)


def test_an_embed_whose_plate_is_missing_is_an_error_not_a_skip(
    tmp_path: Path,
) -> None:
    root = _plant(
        tmp_path, small=18, width=1600, height=1000, fraction=0.92, embed_width=""
    )
    (root / "output" / "figures" / "planted.svg").unlink()
    with pytest.raises(FileNotFoundError) as error:
        measure_project(root)
    assert "fig:planted" in str(error.value)


def test_a_plate_with_no_text_cannot_report_a_legible_minimum(tmp_path: Path) -> None:
    svg = tmp_path / "blank.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" '
        'viewBox="0 0 100 100"><rect x="0" y="0" width="10" height="10"/></svg>',
        encoding="utf-8",
    )
    with pytest.raises(ValueError) as error:
        measure_plate(
            svg,
            "fig:blank",
            "blank.png",
            1.0,
            PageGeometry(text_width_pt=553.6, text_height_pt=715.5),
            0.92,
        )
    assert "no text" in str(error.value)


def test_an_svg_with_no_declared_canvas_size_is_refused(tmp_path: Path) -> None:
    svg = tmp_path / "sizeless.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><text>x</text></svg>', encoding="utf-8"
    )
    with pytest.raises(ValueError) as error:
        measure_plate(
            svg,
            "fig:sizeless",
            "sizeless.png",
            1.0,
            PageGeometry(text_width_pt=553.6, text_height_pt=715.5),
            0.92,
        )
    assert "canvas width" in str(error.value)


# ------------------------------------------------------- the shipped plates


@pytest.mark.skipif(
    shutil.which("rsvg-convert") is None
    and not (PROJECT_ROOT / "output" / "figures").exists(),
    reason="no built figures and no rasterizer to build them with",
)
def test_every_shipped_plate_clears_the_rendered_floor() -> None:
    """The measurement that matters, over the plates this paper embeds."""
    measured = measure_project(PROJECT_ROOT)
    assert measured, "the scan found no plate; the floor check would be vacuous"
    failing = [
        f"{item.label} {item.rendered_min_pt:.4f}pt" for item in illegible(measured)
    ]
    assert not failing, failing
    assert len(measured) == len(parse_embeds(PROJECT_ROOT / "docs" / "manuscript"))


def test_the_canvas_floor_is_chosen_so_a_full_width_embed_clears_the_page_floor() -> (
    None
):
    """The two floors are related, and the relation is arithmetic, not hope."""
    geometry = parse_page_geometry(
        (PROJECT_ROOT / "docs" / "manuscript" / "config.yaml").read_text(
            encoding="utf-8"
        )
    )
    at_full_width = canvas.MIN_TEXT_UNITS * geometry.text_width_pt / canvas.WIDTH
    assert at_full_width >= MIN_LEGIBLE_PT, at_full_width
    # And one unit lower would not clear it, so the canvas floor is not simply
    # set far above what the page needs.
    assert (canvas.MIN_TEXT_UNITS - 1) * geometry.text_width_pt / canvas.WIDTH < (
        MIN_LEGIBLE_PT
    )

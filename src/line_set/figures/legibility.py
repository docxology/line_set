"""Derive the point size each plate's smallest label reaches on the page.

Every plate in this project repeats its colour encoding in a shape and a word,
so the distinctions survive a greyscale print. That mitigation is worth nothing
if the repeated word is too small to read once the plate has been scaled down
into a column of text, and a floor stated in canvas units cannot tell you
whether it has been: a canvas unit is not a unit the page has.

:mod:`line_set.figures.canvas` holds the canvas-unit floor, which stops a label
being *authored* too small. This module holds the other half, and it is the
binding one — it derives, from files that already exist in the checkout, the
size at which each plate's smallest label lands in the rendered document:

``rendered_pt = min_font_units * rendered_width_pt / canvas_width_units``

The identity holds because the renderer scales the whole plate to one declared
width, so a canvas unit and a point are related by a single ratio across the
plate. ``rendered_width_pt`` is the smaller of two bounds, matching the
``\\includegraphics[width=...,height=...,keepaspectratio]`` the shared render
template emits:

* the ``width=NN%`` attribute on the figure's markdown embed, as a fraction of
  the text width; and
* the height cap ``rendering.figure_height_fraction`` times the text height,
  converted back into a width through the plate's own aspect ratio.

When the height cap binds first the whole plate shrinks and every label shrinks
with it, which is the failure this module exists to catch and which no
inspection of the SVG alone would reveal.

Nothing here reads a rendered PDF. Page geometry comes from
``docs/manuscript/config.yaml`` and the embed widths from the manuscript sources, so
the derivation runs on a fresh checkout with nothing built but the figures —
which is the point, because the render is the step most likely not to have
happened. Lengths are TeX points (``1in = 72.27pt``), the unit both the
``geometry`` package and LaTeX font sizes use; the conversion cancels out of the
ratio above but is kept explicit so intermediate values match a render log.

What this establishes is that the smallest *authored* label clears the floor. It
does not establish that a person has read the plate, that the glyphs a
substituted font would produce are the ones measured, or that the plate is
informative. Those stay in ``TODO.md``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

#: TeX points per inch. The ``geometry`` package and LaTeX font sizes agree on
#: this unit, so no conversion is needed anywhere downstream.
TEX_PT_PER_INCH = 72.27

#: US Letter, the ``geometry`` default this manuscript inherits.
PAPER_WIDTH_IN = 8.5
PAPER_HEIGHT_IN = 11.0

#: Floor for the smallest in-plate label, in rendered TeX points.
#:
#: Below this the "shape and word repeat the meaning" mitigation stops working:
#: the word is in the raster but not readable at print scale. Six points is the
#: smallest size this figure set treats as readable body-adjacent text, and it
#: is the same floor the sibling line projects hold their plates to, so a
#: reader moving between the papers meets one standard rather than five.
MIN_LEGIBLE_PT = 6.0

#: Height cap the shared render template applies when a project declares no
#: ``rendering.figure_height_fraction``. Recorded because the cap is invisible
#: in this project's own sources — it is injected into the generated LaTeX —
#: and it is the single largest cause of a plate shrinking without anyone
#: editing it.
DEFAULT_FIGURE_HEIGHT_FRACTION = 0.50

_GEOMETRY_RE = re.compile(r'geometry:\s*"([^"]+)"')
_GEOMETRY_KEY_RE = re.compile(r"(left|right|top|bottom)\s*=\s*([0-9.]+)in")
_HEIGHT_FRACTION_RE = re.compile(
    r"^\s{2,}figure_height_fraction:\s*([0-9.]+)\s*$", re.MULTILINE
)
_EMBED_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)\{#(fig:[a-z0-9-]+)([^}]*)\}", re.DOTALL)
_WIDTH_ATTR_RE = re.compile(r"width=([0-9.]+)%")
_FONT_SIZE_RE = re.compile(r'font-size="([0-9.]+)px"')
_SVG_SIZE_RE = re.compile(r'<svg[^>]*?width="([0-9.]+)"[^>]*?height="([0-9.]+)"')


@dataclass(frozen=True)
class PageGeometry:
    """The text block of the rendered page, in TeX points."""

    text_width_pt: float
    text_height_pt: float


@dataclass(frozen=True)
class FigureLegibility:
    """One plate's smallest label, measured through to the rendered page.

    Attributes:
        label: The ``fig:`` cross-reference label on the embed.
        filename: The embedded raster's filename.
        canvas_width: SVG canvas width, in canvas units.
        canvas_height: SVG canvas height, in canvas units.
        min_font_units: Smallest ``font-size`` the plate emitted.
        width_fraction: The ``width=NN%`` attribute on the embed, as a fraction.
        rendered_width_pt: Width the plate occupies on the page.
        height_bound: True when the height cap, not the declared width,
            decided ``rendered_width_pt`` — the shrink-the-whole-plate case.
        rendered_min_pt: ``min_font_units`` as it lands on the page.
    """

    label: str
    filename: str
    canvas_width: float
    canvas_height: float
    min_font_units: float
    width_fraction: float
    rendered_width_pt: float
    height_bound: bool
    rendered_min_pt: float

    @property
    def legible(self) -> bool:
        """True when the smallest label clears :data:`MIN_LEGIBLE_PT`."""
        return self.rendered_min_pt >= MIN_LEGIBLE_PT


def parse_page_geometry(config_text: str) -> PageGeometry:
    """Derive the text block from a manuscript ``config.yaml``.

    A config that declares no ``geometry`` string is refused rather than
    defaulted: guessing the margins would produce a number that looks derived
    and is not.
    """
    match = _GEOMETRY_RE.search(config_text)
    if match is None:
        raise ValueError(
            "the manuscript config declares no 'geometry:' string, so the text "
            "block cannot be derived; the rendered point size of every label "
            "depends on it and this module will not guess it"
        )
    margins = {
        key: float(value) for key, value in _GEOMETRY_KEY_RE.findall(match.group(1))
    }
    missing = sorted({"left", "right", "top", "bottom"} - set(margins))
    if missing:
        raise ValueError(
            f"the geometry string names no {missing} margin, so the text block "
            "cannot be derived"
        )
    return PageGeometry(
        text_width_pt=(PAPER_WIDTH_IN - margins["left"] - margins["right"])
        * TEX_PT_PER_INCH,
        text_height_pt=(PAPER_HEIGHT_IN - margins["top"] - margins["bottom"])
        * TEX_PT_PER_INCH,
    )


def parse_height_fraction(config_text: str) -> float:
    """Return the declared figure height cap, or the template's default."""
    match = _HEIGHT_FRACTION_RE.search(config_text)
    return DEFAULT_FIGURE_HEIGHT_FRACTION if match is None else float(match.group(1))


def parse_embeds(manuscript_dir: Path) -> dict[str, tuple[str, float]]:
    """Map each embedded raster filename to its label and width fraction.

    An embed with no ``width=`` attribute occupies the full text width, which
    is what the renderer does with it.
    """
    embeds: dict[str, tuple[str, float]] = {}
    for source in sorted(manuscript_dir.glob("*.md")):
        for path, label, attributes in _EMBED_RE.findall(
            source.read_text(encoding="utf-8")
        ):
            width = _WIDTH_ATTR_RE.search(attributes)
            fraction = 1.0 if width is None else float(width.group(1)) / 100
            embeds[Path(path).name] = (label, fraction)
    return embeds


def measure_plate(
    svg_path: Path,
    label: str,
    filename: str,
    width_fraction: float,
    geometry: PageGeometry,
    height_fraction: float,
) -> FigureLegibility:
    """Derive one plate's rendered minimum point size from its SVG."""
    body = svg_path.read_text(encoding="utf-8")
    size_match = _SVG_SIZE_RE.search(body)
    if size_match is None:
        raise ValueError(f"{svg_path} declares no canvas width and height")
    canvas_width = float(size_match.group(1))
    canvas_height = float(size_match.group(2))
    sizes = [float(value) for value in _FONT_SIZE_RE.findall(body)]
    if not sizes:
        raise ValueError(
            f"{svg_path} carries no text, so its legibility cannot be measured; "
            "a plate with no label is not a plate that passed this check"
        )
    by_width = width_fraction * geometry.text_width_pt
    by_height = (
        height_fraction * geometry.text_height_pt * (canvas_width / canvas_height)
    )
    rendered_width_pt = min(by_width, by_height)
    return FigureLegibility(
        label=label,
        filename=filename,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        min_font_units=min(sizes),
        width_fraction=width_fraction,
        rendered_width_pt=rendered_width_pt,
        height_bound=by_height < by_width,
        rendered_min_pt=min(sizes) * rendered_width_pt / canvas_width,
    )


def measure_project(project_root: Path) -> tuple[FigureLegibility, ...]:
    """Measure every plate the manuscript embeds, in label order.

    An embed whose SVG is absent is an error rather than a skip. A gate that
    quietly measured four of five plates would report a floor that no longer
    covers the set it claims to cover, and the plate it dropped is exactly the
    one a reader would want measured.
    """
    manuscript = project_root / "docs" / "manuscript"
    if not manuscript.is_dir():
        manuscript = project_root / "manuscript"
    config_text = (manuscript / "config.yaml").read_text(encoding="utf-8")
    geometry = parse_page_geometry(config_text)
    height_fraction = parse_height_fraction(config_text)
    embeds = parse_embeds(manuscript)
    if not embeds:
        raise ValueError(
            f"no figure embed was found under {manuscript}; a legibility check "
            "over no figure passes for the uninteresting reason"
        )
    figures = project_root / "output" / "figures"
    measured = []
    for filename, (label, fraction) in sorted(embeds.items()):
        svg_path = figures / f"{Path(filename).stem}.svg"
        if not svg_path.exists():
            raise FileNotFoundError(
                f"{label} embeds {filename} but {svg_path} is missing; rebuild "
                "the figures before measuring their legibility"
            )
        measured.append(
            measure_plate(
                svg_path, label, filename, fraction, geometry, height_fraction
            )
        )
    return tuple(sorted(measured, key=lambda item: item.label))


def illegible(measured: tuple[FigureLegibility, ...]) -> tuple[FigureLegibility, ...]:
    """Return every plate whose smallest label lands below the floor."""
    return tuple(item for item in measured if not item.legible)


__all__ = [
    "DEFAULT_FIGURE_HEIGHT_FRACTION",
    "MIN_LEGIBLE_PT",
    "PAPER_HEIGHT_IN",
    "PAPER_WIDTH_IN",
    "TEX_PT_PER_INCH",
    "FigureLegibility",
    "PageGeometry",
    "illegible",
    "measure_plate",
    "measure_project",
    "parse_embeds",
    "parse_height_fraction",
    "parse_page_geometry",
]

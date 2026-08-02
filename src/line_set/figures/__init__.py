"""Deterministic Line Set figures. Importing this module reads nothing.

The plates are assembled by :func:`line_set.figures.plates.figure_plates` when
a build asks for them, so importing this package neither imports a sibling line
package nor touches ``sys.path``. Two of the five plates are drawn from a live
reading; the other three are drawn from the declaration and from the reader's
own stage and precedence tuples.
"""

from __future__ import annotations

from .build import (
    BUILD_PROVENANCE,
    RSVG_CONVERT,
    RSVG_ENV_VAR,
    build_figures,
    figure_summary,
)
from .legibility import (
    MIN_LEGIBLE_PT,
    FigureLegibility,
    illegible,
    measure_project,
)
from .plates import FigurePlate, figure_plates

__all__ = [
    "BUILD_PROVENANCE",
    "MIN_LEGIBLE_PT",
    "RSVG_CONVERT",
    "RSVG_ENV_VAR",
    "FigureLegibility",
    "FigurePlate",
    "build_figures",
    "figure_plates",
    "figure_summary",
    "illegible",
    "measure_project",
]

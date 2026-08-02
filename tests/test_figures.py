"""The figure machinery: derived from the declaration, deterministic, fail-closed.

Three properties are worth testing here and one is not.

**Derived.** Every plate is drawn from the declaration or from a reading handed
to it, never from a list of four lines written into a builder. The binding for
that is a fifth entry appended at runtime: the plates that describe the set must
change, and the plate that describes the reader's own contract must not.

**Deterministic.** Two builds of an unchanged declaration must be byte-identical,
which means no clock reading may reach an artifact. The test plants an
unmistakable review date and requires it to appear nowhere.

**Fail closed.** A missing rasterizer, and a rasterizer that runs and fails, must
each raise with the prerequisite named and must leave nothing behind. A build
that wrote four plates and reported success over the fifth would be worse than
one that refused.

What is *not* tested here is that a plate is legible, informative, or well
composed. Those are judgements a person makes by looking at the PNG. What these
tests establish is that the file was produced, that it says what the reading
said, and that the machinery refuses rather than improvises when it cannot
finish. A green run here is not evidence that a figure is good.

No patching library is used. The rasterizer seam is exercised with a real
executable script written to a real temporary directory: the build genuinely
shells out to it, and it genuinely writes or genuinely fails. The environment
override is a real assignment to ``os.environ``, restored on the way out.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from line_set import (
    LINE_SET,
    SHARED_TOKENS,
    LineEntry,
    ReadCode,
    SetStatus,
    read_set,
    reading_digest,
    registry_digest,
)
from line_set.binding import Resolution
from line_set.figures import (
    FigurePlate,
    build_figures,
    figure_plates,
    figure_summary,
)
from line_set.figures import canvas, palette
from line_set.figures.build import RSVG_ENV_VAR
from line_set.models import SetReading
from line_set.reader import READER_STAGES, STATUS_PRECEDENCE
from line_set.registry import WRAPPER_LINE
from tests.support import (
    absent,
    canned_resolver,
    import_sandbox,
    load_line_package,
    resolved,
    write_line_package,
)

FIGURES_SOURCE = Path(canvas.__file__).resolve().parent

#: A date no build could plausibly produce, used to prove none reaches a plate.
PLANTED_DATE = "1999-12-31"

FIFTH = LineEntry(
    id="teal_line",
    color="teal",
    question="Who else is affected?",
    job="Standing record of parties the work touches and never consulted",
    must_not_become="A consent receipt or a substitute for asking them",
    opus_stage=None,
    working_position=5,
    package_name="teal_line",
    registry_noun="affected parties",
    verdict_noun="consultation status",
)


# ---------------------------------------------------------------- fixtures


@contextmanager
def environment_override(name: str, value: str | None) -> Iterator[None]:
    """Set or clear one environment variable, restoring it on the way out.

    A real assignment to the real process environment. The build reads
    ``os.environ`` when it looks for its rasterizer, so this is the seam a
    caller actually has, exercised the way a caller would exercise it.
    """
    had = name in os.environ
    previous = os.environ.get(name)
    try:
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
        yield
    finally:
        if had:
            os.environ[name] = previous  # type: ignore[arg-type]
        else:
            os.environ.pop(name, None)


def write_rasterizer(directory: Path, *, exit_code: int = 0) -> Path:
    """Write a real, executable stand-in rasterizer and return its path.

    It is a genuine program: the build finds it on disk, runs it as a
    subprocess, and depends on its exit status. Its output is derived from the
    SVG it was given, so a byte-identical pair of SVGs yields a byte-identical
    pair of outputs and the determinism assertion below is not weakened by
    using it.

    The real ``rsvg-convert`` is exercised separately, in
    :func:`test_the_real_rasterizer_produces_a_real_png`.
    """
    script = directory / f"rasterizer_exit_{exit_code}.py"
    script.write_text(
        "\n".join(
            [
                f"#!{sys.executable}",
                "import sys",
                "argv = sys.argv[1:]",
                f"code = {exit_code}",
                "if code == 0:",
                "    out = argv[argv.index('-o') + 1]",
                "    source = open(argv[-1], 'rb').read()",
                "    open(out, 'wb').write(b'\\x89PNG\\r\\n\\x1a\\n' + source)",
                "sys.exit(code)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def make_reading(
    lines: tuple[LineEntry, ...] = LINE_SET,
    answers: dict[str, Resolution] | None = None,
    *,
    as_of: str = PLANTED_DATE,
) -> SetReading:
    """A reading driven entirely by an injected plain-callable resolver."""
    return read_set(
        lines,
        SHARED_TOKENS,
        resolver=canned_resolver(answers or {}),
        as_of=as_of,
    )


def make_self_reading(
    lines: tuple[LineEntry, ...] = LINE_SET,
    answers: dict[str, Resolution] | None = None,
    *,
    as_of: str = PLANTED_DATE,
) -> SetReading:
    """A reading over the declaration plus the wrapper's own entry.

    The wrapper resolves to the genuinely imported ``line_set`` module rather
    than to a package written for the occasion, so the tokens compared are the
    ones this package really publishes. Writing a second package under the same
    name would put a different ``line_set`` in ``sys.modules`` for the duration
    and would compare the suite against a fiction of itself.
    """
    import line_set as wrapper_package

    combined = dict(answers or {})
    combined.setdefault(
        WRAPPER_LINE.package_name,
        resolved(WRAPPER_LINE.package_name, wrapper_package),
    )
    return read_set(
        (*lines, WRAPPER_LINE),
        SHARED_TOKENS,
        resolver=canned_resolver(combined),
        as_of=as_of,
    )


def plates_for(
    lines: tuple[LineEntry, ...],
    reading: SetReading,
    self_reading: SetReading | None = None,
) -> dict[str, FigurePlate]:
    """Every plate for one declaration and its two readings, keyed by name.

    ``self_reading`` defaults to ``reading``, which carries no wrapper
    observation and therefore drives the self-application plate down its
    unestablished branch. That is the honest default for a test that is not
    about self-application; the tests that are about it pass a real one.
    """
    return {
        plate.name: plate
        for plate in figure_plates(
            lines,
            SHARED_TOKENS,
            reading,
            WRAPPER_LINE,
            reading if self_reading is None else self_reading,
        )
    }


def rendered(
    lines: tuple[LineEntry, ...],
    reading: SetReading,
    self_reading: SetReading | None = None,
) -> dict[str, str]:
    """Every plate's SVG body for one declaration and its readings."""
    return {
        name: plate.render()
        for name, plate in plates_for(lines, reading, self_reading).items()
    }


@contextmanager
def live_reading(tmp_path: Path) -> Iterator[SetReading]:
    """A reading over four real packages written to a real temporary directory."""
    with import_sandbox():
        modules = {}
        vocabularies = {
            "red_line": ("REFUSED", "PERMITTED", "OUTSIDE_SCOPE"),
            "black_line": ("STRONG", "WEAK", "OUTSIDE_SCOPE"),
            "golden_line": ("TOWARD", "AWAY"),
            "white_line": ("ABSENT", "WITHHELD"),
        }
        for name, tokens in vocabularies.items():
            write_line_package(
                tmp_path, name, tokens, version="1.2.3", registry_sizes={"ITEMS": 3}
            )
            modules[name] = resolved(name, load_line_package(tmp_path, name))
        yield make_reading(LINE_SET, modules)


# ---------------------------------------------------- the display-map gate


def test_verify_coverage_passes_on_the_shipped_maps() -> None:
    """The build's first gate holds for the package as it stands."""
    palette.verify_coverage()


def test_the_coverage_gate_names_what_a_deficient_map_is_missing() -> None:
    """The gate must reject, not merely accept. Both directions, both named."""
    with pytest.raises(ValueError) as missing:
        palette._require_exact({}, ReadCode, "PLANTED_MAP")
    text = str(missing.value)
    assert "PLANTED_MAP" in text
    for member in ReadCode:
        assert str(member) in text, f"{member} was not named as missing"

    with pytest.raises(ValueError) as unexpected:
        palette._require_exact(
            {member: "x" for member in ReadCode} | {"invented": "x"},
            ReadCode,
            "PLANTED_MAP",
        )
    assert "invented" in str(unexpected.value)


def test_every_enumeration_keyed_display_map_is_guarded() -> None:
    """A new display map added without being guarded fails this test.

    Without it the gate is only as good as whoever last remembered to extend
    it, and a map that fell out of the gate would drift silently — which is the
    exact failure the gate exists to prevent.
    """
    import inspect

    guarded = inspect.getsource(palette.verify_coverage)
    keyed = {
        name
        for name in palette.__all__
        if isinstance(getattr(palette, name), dict)
        and getattr(palette, name)
        and all(
            isinstance(key, (ReadCode, SetStatus)) or key in READER_STAGES
            for key in getattr(palette, name)
        )
    }
    assert keyed, "no enumeration-keyed display map was found; the scan is vacuous"
    for name in sorted(keyed):
        assert name in guarded, f"{name} is not checked by verify_coverage()"


def test_the_build_runs_the_coverage_gate_before_it_writes(tmp_path: Path) -> None:
    """The gate is at build entry, so a drifted map cannot leave partial output."""
    import inspect

    source = inspect.getsource(build_figures)
    body = source.split(":\n", 1)[1]
    assert body.index("verify_coverage()") < body.index("write_text"), (
        "verify_coverage() must run before the first write"
    )


# ------------------------------------------------------------ plate shape


def test_every_declared_plate_renders_well_formed_svg(tmp_path: Path) -> None:
    with live_reading(tmp_path) as reading:
        bodies = rendered(LINE_SET, reading, make_self_reading())
    assert sorted(bodies) == [
        "exemption_gate",
        "installation_surface",
        "self_application",
        "set_compass",
        "set_reading_pipeline",
        "two_orders",
        "vocabulary_matrix",
    ]
    for name, body in bodies.items():
        assert body.startswith("<svg "), name
        assert body.rstrip().endswith("</svg>"), name
        assert body.count("<svg") == body.count("</svg>") == 1, name


def test_plate_provenance_is_complete_and_unique(tmp_path: Path) -> None:
    with live_reading(tmp_path) as reading:
        plates = plates_for(LINE_SET, reading, make_self_reading())
    labels = [plate.label for plate in plates.values()]
    assert len(set(labels)) == len(labels), labels
    for plate in plates.values():
        assert plate.caption.strip(), plate.name
        assert plate.alt.strip(), plate.name
        assert plate.source.strip(), plate.name
        assert plate.label.startswith("fig:"), plate.name


def test_rendering_a_plate_twice_gives_the_same_bytes(tmp_path: Path) -> None:
    with live_reading(tmp_path) as reading:
        self_reading = make_self_reading()
        first = rendered(LINE_SET, reading, self_reading)
        second = rendered(LINE_SET, reading, self_reading)
    assert first == second


def test_no_plate_carries_the_reading_date_or_the_dated_digest(
    tmp_path: Path,
) -> None:
    """The determinism invariant, planted rather than assumed.

    ``read_as_of`` and ``reading_digest`` both move with the clock. If either
    reached a plate, two builds of an unchanged declaration would differ across
    midnight, so the build deliberately draws neither.
    """
    with live_reading(tmp_path) as reading:
        bodies = rendered(LINE_SET, reading, make_self_reading())
    assert reading.read_as_of == PLANTED_DATE, "the plant must actually be in place"
    dated_digest = reading_digest(reading)
    for name, body in bodies.items():
        assert PLANTED_DATE not in body, f"{name} carries the reading date"
        assert dated_digest not in body, f"{name} carries the dated reading digest"


def test_every_text_run_clears_the_legibility_floor(tmp_path: Path) -> None:
    with live_reading(tmp_path) as reading:
        bodies = rendered(LINE_SET, reading, make_self_reading())
    sizes: list[int] = []
    for body in bodies.values():
        sizes.extend(int(size) for size in re.findall(r'font-size="(\d+)px"', body))
    assert sizes, "no text was found in any plate; the floor check would be vacuous"
    assert min(sizes) >= canvas.MIN_TEXT_UNITS, min(sizes)


def test_the_canvas_refuses_a_marker_shape_it_cannot_draw() -> None:
    """An unknown shape is a defect in the caller, not a circle to substitute."""
    with pytest.raises(ValueError) as error:
        canvas.glyph("trapezoid", 0, 0, 5, "#000", "#000")
    assert "trapezoid" in str(error.value)
    for shape in palette.SHAPE_CYCLE:
        assert canvas.glyph(shape, 0, 0, 5, "#000", "#000").startswith("<")


def test_the_header_omits_its_note_line_when_there_is_no_note() -> None:
    assert len(canvas.header("K", "T", "S")) == 3
    assert len(canvas.header("K", "T", "S", "N")) == 4


def test_wrapping_blank_text_yields_one_empty_line() -> None:
    """A caller that wraps nothing gets a line to place, not an empty list."""
    assert canvas.wrap("   ", 20) == [""]
    assert canvas.wrap("a b c", 3) == ["a b", "c"]


def test_plural_follows_the_live_count() -> None:
    assert canvas.plural(1, "line") == "1 line"
    assert canvas.plural(0, "line") == "0 lines"
    assert canvas.plural(len(LINE_SET), "line") == f"{len(LINE_SET)} lines"


def test_plural_inflects_the_nouns_that_do_not_simply_take_an_s() -> None:
    """The direction the old test could not see.

    Exercising only ``line`` left the helper's whole irregular class unchecked,
    and it was wrong there: ``status`` came out ``statuss`` and ``entry`` came
    out ``entrys``, both in a shipped caption and its alt text.
    """
    assert canvas.plural(4, "status") == "4 statuses"
    assert canvas.plural(4, "entry") == "4 entries"
    assert canvas.plural(1, "status") == "1 status"
    assert canvas.plural(1, "entry") == "1 entry"
    assert canvas.plural(2, "box") == "2 boxes"
    assert canvas.plural(2, "match") == "2 matches"
    assert canvas.plural(2, "dish") == "2 dishes"
    # A vowel before the y keeps the y.
    assert canvas.plural(2, "day") == "2 days"
    # Only the head noun inflects in a compound.
    assert canvas.plural(2, "declared line") == "2 declared lines"
    assert canvas.plural(2, "set status") == "2 set statuses"


def test_no_generated_caption_or_alt_text_carries_a_malformed_plural(
    tmp_path: Path,
) -> None:
    """The gate over the text that actually ships, not over the helper alone.

    Captions and alt text are the copy a reader and a screen reader receive, so
    a plural that reads as a typo there is a defect in the artifact, not only in
    the function that produced it.
    """
    with live_reading(tmp_path) as reading:
        plates = plates_for(LINE_SET, reading)
    prose = " ".join(
        f"{plate.caption} {plate.alt} {plate.label}" for plate in plates.values()
    )
    assert prose.strip(), "no caption text was collected; this check would be vacuous"
    for malformed in ("statuss", "entrys", "(s)", "  "):
        assert malformed not in prose, f"{malformed!r} in generated caption text"


def test_the_canvas_refuses_illegible_text_rather_than_resizing_it() -> None:
    """A primitive that clamped would let an unreadable label pass as a good one."""
    with pytest.raises(ValueError) as error:
        canvas.text(0, 0, "too small to read", canvas.MIN_TEXT_UNITS - 1)
    assert str(canvas.MIN_TEXT_UNITS) in str(error.value)
    assert canvas.text(0, 0, "legible", canvas.MIN_TEXT_UNITS).startswith("<text ")


def test_plate_text_is_escaped_rather_than_injected(tmp_path: Path) -> None:
    """A declaration is data. A line whose prose held markup must not become markup."""
    hostile = dataclasses.replace(FIFTH, question='<script>"&"</script>')
    reading = make_reading((*LINE_SET, hostile))
    body = plates_for((*LINE_SET, hostile), reading)["set_compass"].render()
    assert "<script>" not in body
    assert "&lt;script&gt;" in body


# ----------------------------------------------------- derived, not typed


def test_appending_a_colour_changes_the_set_plates_and_not_the_contract_plate(
    tmp_path: Path,
) -> None:
    """The extensibility claim, bound at the figure layer.

    ``set_reading_pipeline`` draws the reader's stages and precedence, which a
    fifth line does not touch. It is the control: if it moved too, the other
    four moving would be evidence of nothing in particular.
    """
    with live_reading(tmp_path) as four_reading:
        answers = {
            observation.line_id: resolved(
                observation.line_id,
                load_line_package(tmp_path, observation.line_id),
            )
            for observation in four_reading.observations
        }
        four = rendered(LINE_SET, four_reading, make_self_reading(LINE_SET, answers))
        extended = (*LINE_SET, FIFTH)
        five_reading = make_reading(extended, answers)
        five = rendered(extended, five_reading, make_self_reading(extended, answers))

    for name in (
        "set_compass",
        "two_orders",
        "vocabulary_matrix",
        "installation_surface",
        "self_application",
    ):
        assert four[name] != five[name], f"{name} did not respond to a fifth line"
    assert four["set_reading_pipeline"] == five["set_reading_pipeline"], (
        "the reader's own contract plate must not move when the set grows"
    )
    assert FIFTH.id in five["set_compass"]
    assert FIFTH.id in five["installation_surface"]


def test_no_figure_module_names_an_individual_line(tmp_path: Path) -> None:
    """The other half of the claim: the builders do not know the lines by name.

    Whole-word matching, for the reason ``test_extensibility`` records: a bare
    substring search reports on English rather than on what the module refers
    to.

    Line *ids* are the subject. Colour names are deliberately not, because
    ``palette`` keeps a table of preferred inks for the colours declared today
    and falls back deterministically for any other — a lookup with a default,
    not a dependency. The test below proves the fallback is real, which is what
    makes the table safe to keep.
    """
    sources = sorted(FIGURES_SOURCE.rglob("*.py"))
    assert sources, "no figure module was scanned; the guard would be vacuous"
    subjects = [entry.id for entry in LINE_SET]
    assert subjects, "an empty subject set would make this check vacuous"
    for path in sources:
        text = path.read_text(encoding="utf-8")
        for word in subjects:
            pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(word)}(?![A-Za-z0-9_])")
            assert not pattern.search(text), f"{path.name} names {word}"


def test_an_undeclared_colour_still_gets_ink_a_fill_and_a_marker() -> None:
    """The palette's colour table is a preference, not a requirement.

    A fifth colour nobody anticipated must still draw. It gets a stable
    accent chosen from the colour's own name, so two builds agree, and a
    marker shape from its working position, so the plates keep reading in
    greyscale.
    """
    assert FIFTH.color not in palette.LINE_FILL, "the plant must be genuinely unknown"
    assert FIFTH.color not in palette.LINE_INK
    fill, ink = palette.line_fill(FIFTH.color), palette.line_ink(FIFTH.color)
    assert fill and ink and fill != ink
    assert (fill, ink) == (
        palette.line_fill(FIFTH.color),
        palette.line_ink(FIFTH.color),
    )
    assert palette.shape_for(FIFTH.working_position) in palette.SHAPE_CYCLE
    assert palette.dash_for(FIFTH.working_position) in palette.DASH_CYCLE


def test_the_pipeline_plate_is_drawn_from_the_reader_itself() -> None:
    body = plates_for(LINE_SET, make_reading())["set_reading_pipeline"].render()
    assert READER_STAGES, "an empty stage tuple would make this vacuous"
    for stage in READER_STAGES:
        assert stage in body, stage
    for status in STATUS_PRECEDENCE:
        assert status.value in body, status


def test_captions_report_the_reading_they_were_built_from(tmp_path: Path) -> None:
    with live_reading(tmp_path) as reading:
        plates = plates_for(LINE_SET, reading, make_self_reading())
    assert reading.status is SetStatus.SET_LEGIBLE
    assert reading.status.value in plates["installation_surface"].caption

    partial = make_reading(LINE_SET, {})
    assert partial.status is SetStatus.SET_PARTIAL
    assert (
        partial.status.value
        in plates_for(LINE_SET, partial)["installation_surface"].caption
    )


# ---------------------------------------------------- honest when absent


def test_the_matrix_refuses_to_draw_a_grid_it_could_not_fill() -> None:
    """Fewer than two vocabularies is not a disjointness result; it is no result."""
    reading = make_reading(LINE_SET, {})
    plate = plates_for(LINE_SET, reading)["vocabulary_matrix"]
    assert "not evidence" in plate.caption, plate.caption
    body = plate.render()
    assert "two are needed" in body
    assert "not evidence that the declared vocabularies are disjoint" in body
    for observation in reading.observations:
        entry = next(item for item in LINE_SET if item.id == observation.line_id)
        assert entry.color in body, (
            f"{entry.id} was omitted rather than reported absent"
        )
        assert observation.code.value in body, (
            f"{entry.id} was listed without the code that explains its absence"
        )


def test_the_matrix_draws_the_grid_once_two_lines_are_legible(tmp_path: Path) -> None:
    """The refusal above would be uninformative if the grid never drew at all."""
    with live_reading(tmp_path) as reading:
        plate = plates_for(LINE_SET, reading)["vocabulary_matrix"]
    assert "not evidence" not in plate.caption
    body = plate.render()
    assert "OUTSIDE_SCOPE" in body
    assert "REFUSED" in body


def test_an_unresolved_row_shows_no_metric_rather_than_a_zero() -> None:
    """A line that could not be read has no size, not a size of zero."""
    reading = make_reading(
        LINE_SET,
        {
            "red_line": Resolution(
                "red_line", ReadCode.IMPORT_FAILED, None, "import raised RuntimeError"
            )
        },
    )
    body = plates_for(LINE_SET, reading)["installation_surface"].render()
    for observation in reading.observations:
        assert observation.registry_size is None
        assert observation.version is None
        assert observation.line_id in body
        assert observation.code.value in body
    assert "&#8212;" in body or "—" in body, "no em dash marked the absent metrics"


def test_the_exempted_cell_is_distinguished_by_shape_and_label(
    tmp_path: Path,
) -> None:
    """Nothing in the set may be encoded by colour alone.

    The reading is planted so both kinds are present at once: the declared
    ``OUTSIDE_SCOPE`` over its exactly two lines, and a second word a third
    line adopted that no declaration covers. If only one kind were drawn the
    distinction would be untested, because a single legend row cannot be
    confused with another one that is not there.
    """
    with import_sandbox():
        vocabularies = {
            "red_line": ("OUTSIDE_SCOPE", "BORROWED", "REFUSED"),
            "black_line": ("OUTSIDE_SCOPE", "STRONG"),
            "golden_line": ("BORROWED", "TOWARD"),
            "white_line": ("ABSENT",),
        }
        answers = {}
        for name, tokens in vocabularies.items():
            write_line_package(tmp_path, name, tokens, registry_sizes={"ITEMS": 2})
            answers[name] = resolved(name, load_line_package(tmp_path, name))
        reading = make_reading(LINE_SET, answers)
        body = plates_for(LINE_SET, reading)["vocabulary_matrix"].render()

    assert [item.token for item in reading.exempted_collisions] == ["OUTSIDE_SCOPE"]
    assert [item.token for item in reading.collisions] == ["BORROWED"]
    assert reading.status is SetStatus.SET_COLLIDING

    from line_set.figures.plates.reading import (
        COLLISION_LABEL,
        COLLISION_SHAPE,
        EXEMPT_LABEL,
        EXEMPT_SHAPE,
    )

    assert EXEMPT_SHAPE != COLLISION_SHAPE, "shape must carry the distinction too"
    for fragment in (EXEMPT_LABEL, COLLISION_LABEL):
        assert canvas.escape_text(fragment) in body, fragment


def test_a_grid_with_no_shared_token_says_so_rather_than_leaving_the_band_blank(
    tmp_path: Path,
) -> None:
    """The band above the grid must report an empty finding, not be absent.

    A missing band and a band reporting nothing read identically to someone
    skimming, and only one of them is a result.
    """
    with import_sandbox():
        answers = {}
        for name, tokens in (
            ("red_line", ("REFUSED", "PERMITTED")),
            ("black_line", ("STRONG", "WEAK")),
            ("golden_line", ("TOWARD",)),
            ("white_line", ("ABSENT",)),
        ):
            write_line_package(tmp_path, name, tokens, registry_sizes={"ITEMS": 1})
            answers[name] = resolved(name, load_line_package(tmp_path, name))
        reading = make_reading(LINE_SET, answers)
        body = plates_for(LINE_SET, reading)["vocabulary_matrix"].render()
    assert reading.status is SetStatus.SET_LEGIBLE
    assert not reading.collisions and not reading.exempted_collisions
    assert "No token in the grid below is carried by two lines." in body


def test_every_plate_renders_for_every_reading_status(tmp_path: Path) -> None:
    """No status may be a shape the figure layer cannot draw."""
    with import_sandbox():
        for name, tokens in (
            ("red_line", ("SHARED", "REFUSED")),
            ("black_line", ("SHARED", "STRONG")),
        ):
            write_line_package(tmp_path, name, tokens, registry_sizes={"ITEMS": 2})
        modules = {
            name: resolved(name, load_line_package(tmp_path, name))
            for name in ("red_line", "black_line")
        }
        readings = {
            SetStatus.SET_PARTIAL: make_reading(LINE_SET, {}),
            SetStatus.SET_COLLIDING: make_reading(LINE_SET, modules),
            SetStatus.SET_LEGIBLE: read_set(
                LINE_SET[:2],
                (),
                resolver=canned_resolver(
                    {
                        "red_line": resolved(
                            "red_line", load_line_package(tmp_path, "red_line")
                        ),
                        "black_line": absent("black_line"),
                    }
                ),
                as_of=PLANTED_DATE,
            ),
        }
        del readings[SetStatus.SET_LEGIBLE]
        for status, reading in readings.items():
            assert reading.status is status, (status, reading.status)
            for name, body in rendered(LINE_SET, reading).items():
                assert body.startswith("<svg "), (status, name)


# ------------------------------------------------------------- the build


def test_a_build_writes_every_declared_plate_two_manifests_and_nothing_else(
    tmp_path: Path,
) -> None:
    """The plate count is read off the builder, never typed in here.

    A number written into this test would pass forever after someone added a
    plate and forgot to build it, which is the drift the whole figure layer is
    arranged to prevent.
    """
    root = tmp_path / "root"
    with environment_override(RSVG_ENV_VAR, str(write_rasterizer(tmp_path))):
        produced = build_figures(root, resolver=canned_resolver({}), as_of=PLANTED_DATE)

    declared = len(plates_for(LINE_SET, make_reading()))
    assert declared, "the builder declares no plate; every count below is vacuous"
    figures = root / "output" / "figures"
    assert sorted(path.name for path in figures.iterdir()) == sorted(
        path.name for path in produced
    )
    assert len([path for path in produced if path.suffix == ".svg"]) == declared
    assert len([path for path in produced if path.suffix == ".png"]) == declared
    assert sorted(path.name for path in produced if path.suffix == ".json") == [
        "figure_registry.json",
        "set_registry.json",
    ]
    assert f"{declared} SVG, {declared} PNG, and 2 JSON" in figure_summary(produced)


def test_two_builds_of_one_declaration_are_byte_identical(tmp_path: Path) -> None:
    rasterizer = str(write_rasterizer(tmp_path))
    digests = []
    for index in ("first", "second"):
        root = tmp_path / index
        with environment_override(RSVG_ENV_VAR, rasterizer):
            produced = build_figures(
                root, resolver=canned_resolver({}), as_of=PLANTED_DATE
            )
        digests.append(
            {
                path.name: path.read_bytes()
                for path in sorted(produced, key=lambda p: p.name)
            }
        )
    assert digests[0] == digests[1]


def test_two_builds_on_different_dates_are_still_byte_identical(
    tmp_path: Path,
) -> None:
    """The reason no date is drawn, stated as a test rather than as a comment."""
    rasterizer = str(write_rasterizer(tmp_path))
    bodies = []
    for index, as_of in (("a", "2001-01-01"), ("b", "2099-12-31")):
        root = tmp_path / index
        with environment_override(RSVG_ENV_VAR, rasterizer):
            produced = build_figures(root, resolver=canned_resolver({}), as_of=as_of)
        bodies.append(
            {
                path.name: path.read_bytes()
                for path in produced
                if path.suffix != ".json"
            }
        )
    assert bodies[0] == bodies[1]


def test_the_figure_registry_binds_to_the_declaration_it_was_built_from(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    with environment_override(RSVG_ENV_VAR, str(write_rasterizer(tmp_path))):
        build_figures(root, resolver=canned_resolver({}), as_of=PLANTED_DATE)
    manifest = json.loads(
        (root / "output" / "figures" / "figure_registry.json").read_text()
    )
    expected = registry_digest(LINE_SET, SHARED_TOKENS)
    assert manifest["registry_digest"] == expected
    assert manifest["set_status"] == SetStatus.SET_PARTIAL.value
    assert len(manifest["figures"]) == len(plates_for(LINE_SET, make_reading()))
    for record in manifest["figures"]:
        assert record["source_digest"] == expected
        assert (root / "output" / "figures" / record["filename"]).exists()

    declaration = json.loads(
        (root / "output" / "figures" / "set_registry.json").read_text()
    )
    assert declaration["digest"] == expected
    assert len(declaration["declaration"]["lines"]) == len(LINE_SET)


def test_a_build_with_no_sibling_reports_partial_rather_than_omitting_rows(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    with environment_override(RSVG_ENV_VAR, str(write_rasterizer(tmp_path))):
        build_figures(root, resolver=canned_resolver({}), as_of=PLANTED_DATE)
    manifest = json.loads(
        (root / "output" / "figures" / "figure_registry.json").read_text()
    )
    assert manifest["read_codes"]["not_installed"] == len(LINE_SET)
    surface = (root / "output" / "figures" / "installation_surface.svg").read_text()
    for entry in LINE_SET:
        assert entry.id in surface, f"{entry.id} was omitted rather than shown absent"


# -------------------------------------------------------- failing closed


def test_a_missing_rasterizer_refuses_the_build_and_writes_nothing(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    with environment_override(RSVG_ENV_VAR, "line-set-no-such-rasterizer"):
        with pytest.raises(RuntimeError) as error:
            build_figures(root, resolver=canned_resolver({}), as_of=PLANTED_DATE)
    message = str(error.value)
    assert "line-set-no-such-rasterizer" in message
    assert RSVG_ENV_VAR in message
    assert "librsvg" in message
    assert not (root / "output" / "figures").exists(), (
        "the lookup must run before the first write"
    )


def test_a_rasterizer_that_fails_refuses_the_build(tmp_path: Path) -> None:
    """A non-zero exit is not a figure. Reporting one would be the worse bug."""
    root = tmp_path / "root"
    failing = str(write_rasterizer(tmp_path, exit_code=3))
    with environment_override(RSVG_ENV_VAR, failing):
        with pytest.raises(RuntimeError) as error:
            build_figures(root, resolver=canned_resolver({}), as_of=PLANTED_DATE)
    message = str(error.value)
    assert "exit 3" in message
    assert "librsvg" in message or RSVG_ENV_VAR in message
    pngs = sorted((root / "output" / "figures").glob("*.png"))
    assert not pngs, f"a failed rasterization left {pngs} behind"


def test_an_executable_named_by_absolute_path_is_honoured(tmp_path: Path) -> None:
    """The override takes a path, not only a name on PATH."""
    root = tmp_path / "root"
    rasterizer = write_rasterizer(tmp_path)
    assert rasterizer.is_absolute()
    with environment_override(RSVG_ENV_VAR, str(rasterizer)):
        produced = build_figures(root, resolver=canned_resolver({}), as_of=PLANTED_DATE)
    assert len([path for path in produced if path.suffix == ".png"]) == len(
        plates_for(LINE_SET, make_reading())
    )


def test_an_executable_off_the_search_path_is_still_honoured(tmp_path: Path) -> None:
    """``shutil.which`` is the first lookup, not the only one.

    A bare name that is not on ``PATH`` still resolves when it names a real
    executable relative to the working directory, so the fallback branch is
    reachable by an operator and is exercised here.
    """
    rasterizer = write_rasterizer(tmp_path)
    previous = Path.cwd()
    try:
        os.chdir(tmp_path)
        with environment_override(RSVG_ENV_VAR, rasterizer.name):
            assert shutil.which(rasterizer.name) is None, (
                "the plant must not be findable on PATH, or the fallback is untested"
            )
            produced = build_figures(
                tmp_path / "root", resolver=canned_resolver({}), as_of=PLANTED_DATE
            )
    finally:
        os.chdir(previous)
    assert len([path for path in produced if path.suffix == ".png"]) == len(
        plates_for(LINE_SET, make_reading())
    )


def test_a_rasterizer_that_vanishes_mid_build_refuses_rather_than_continues(
    tmp_path: Path,
) -> None:
    """It resolved, then it was gone. That is a refusal, not four-fifths of a set."""
    rasterizer = tmp_path / "self_deleting.py"
    rasterizer.write_text(
        "\n".join(
            [
                f"#!{sys.executable}",
                "import os, sys",
                "os.unlink(__file__)",
                "argv = sys.argv[1:]",
                "open(argv[argv.index('-o') + 1], 'wb').write(b'once')",
                "",
            ]
        ),
        encoding="utf-8",
    )
    rasterizer.chmod(0o755)
    with environment_override(RSVG_ENV_VAR, str(rasterizer)):
        with pytest.raises(RuntimeError) as error:
            build_figures(
                tmp_path / "root", resolver=canned_resolver({}), as_of=PLANTED_DATE
            )
    message = str(error.value)
    assert "disappeared" in message
    assert RSVG_ENV_VAR in message


def test_the_build_asks_for_the_siblings_when_no_resolver_is_named(
    tmp_path: Path,
) -> None:
    """The default is the build asking out loud for the sibling checkouts.

    The assertion is deliberately about shape rather than about which siblings
    happen to be beside this checkout: the reading must be real and complete,
    and it must be a status the reader can actually return. A test that
    required four resolved lines here would pass only inside one working tree.
    """
    with environment_override(RSVG_ENV_VAR, str(write_rasterizer(tmp_path))):
        build_figures(tmp_path / "root", as_of=PLANTED_DATE)
    manifest = json.loads(
        (tmp_path / "root" / "output" / "figures" / "figure_registry.json").read_text()
    )
    assert manifest["set_status"] in {status.value for status in SetStatus}
    assert sum(manifest["read_codes"].values()) == len(LINE_SET)


def test_a_non_executable_file_is_refused(tmp_path: Path) -> None:
    """Existing is not the same as being runnable."""
    inert = tmp_path / "not_executable"
    inert.write_text("this file is not a program\n", encoding="utf-8")
    inert.chmod(0o644)
    with environment_override(RSVG_ENV_VAR, str(inert)):
        with pytest.raises(RuntimeError):
            build_figures(
                tmp_path / "root", resolver=canned_resolver({}), as_of=PLANTED_DATE
            )


# ------------------------------------------------ the real rasterizer


def test_the_real_rasterizer_produces_a_real_png(tmp_path: Path) -> None:
    """The stand-in above proves the pipeline; this proves librsvg is wired to it.

    Skipped rather than failed when librsvg is genuinely not installed, because
    that is a missing system prerequisite rather than a defect in this package.
    Everything else in this module runs regardless, so no coverage depends on it.
    """
    real = shutil.which("rsvg-convert")
    if real is None:
        pytest.skip("rsvg-convert is not installed; install librsvg to run this check")
    root = tmp_path / "root"
    with environment_override(RSVG_ENV_VAR, real):
        produced = build_figures(root, resolver=canned_resolver({}), as_of=PLANTED_DATE)
    pngs = [path for path in produced if path.suffix == ".png"]
    assert len(pngs) == len(plates_for(LINE_SET, make_reading()))
    for path in pngs:
        assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", path


def test_the_operator_command_builds_and_reports_what_landed(tmp_path: Path) -> None:
    """The CLI is a surface too; run it as an operator would."""
    project_root = Path(canvas.__file__).resolve().parents[3]
    result = subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "build_figures.py"),
            "--project-root",
            str(tmp_path / "root"),
        ],
        capture_output=True,
        text=True,
        env={
            **os.environ,
            RSVG_ENV_VAR: str(write_rasterizer(tmp_path)),
            "PYTHONPATH": str(project_root / "src"),
        },
    )
    assert result.returncode == 0, result.stderr
    declared = len(plates_for(LINE_SET, make_reading()))
    assert f"{declared} SVG, {declared} PNG, and 2 JSON" in result.stdout
    assert (tmp_path / "root" / "output" / "figures" / "set_compass.png").exists()

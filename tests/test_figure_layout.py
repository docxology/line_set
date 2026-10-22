from __future__ import annotations

import os
import json
import struct
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

SVG = "{http://www.w3.org/2000/svg}"


def _layout_problems(source: Path, scratch: Path) -> list[str]:
    root = ET.parse(source).getroot()
    width = float(root.attrib["viewBox"].split()[2])
    frames = [
        tuple(float(node.attrib.get(key, 0)) for key in ("x", "y", "width", "height"))
        for node in root.iter(SVG + "rect")
        if float(node.attrib.get("width", 0)) > 100
        and float(node.attrib.get("height", 0)) > 0
    ]
    texts = [node for node in root.iter(SVG + "text") if (node.text or "").strip()]
    assert texts, "no text was measured"
    for index, node in enumerate(texts):
        node.set("id", f"layout-text-{index}")
    measured = scratch / source.name
    ET.ElementTree(root).write(measured, encoding="utf-8", xml_declaration=True)
    boxes = []
    problems = []
    widths = {}
    for index, node in enumerate(texts):
        key = (
            node.text,
            tuple(
                sorted(
                    (name, value)
                    for name, value in node.attrib.items()
                    if name not in {"id", "x", "y", "text-anchor"}
                )
            ),
        )
        if key not in widths:
            result = subprocess.run(
                [
                    os.environ.get("LINE_SET_RSVG_CONVERT", "rsvg-convert"),
                    "--export-id",
                    f"layout-text-{index}",
                    str(measured),
                ],
                capture_output=True,
                check=True,
                timeout=30,
            )
            widths[key] = struct.unpack(">II", result.stdout[16:24])[0]
        ink_width = widths[key]
        x, y = (float(node.attrib[key]) for key in ("x", "y"))
        size = float(node.attrib["font-size"].removesuffix("px"))
        anchor = node.attrib.get("text-anchor", "start")
        left = x - (
            ink_width if anchor == "end" else ink_width / 2 if anchor == "middle" else 0
        )
        right = left + ink_width
        value = node.text or ""
        if left < -2 or right > width + 2:
            problems.append(f"viewport overflow: {value!r} at {left:g}..{right:g}")
        containing = [
            frame
            for frame in frames
            if frame[0] <= x <= frame[0] + frame[2]
            and frame[1] <= y <= frame[1] + frame[3]
        ]
        if containing:
            frame = min(containing, key=lambda box: box[2] * box[3])
            if left < frame[0] - 2 or right > frame[0] + frame[2] + 2:
                problems.append(f"card overflow: {value!r} at {left:g}..{right:g}")
        for (
            previous_left,
            previous_right,
            previous_y,
            previous_size,
            previous_value,
        ) in boxes:
            if (
                abs(y - previous_y) < min(size, previous_size) / 2
                and min(right, previous_right) - max(left, previous_left) > 2
            ):
                problems.append(f"text overlap: {previous_value!r} / {value!r}")
        boxes.append((left, right, y, size, value))
    return problems


def test_every_built_plate_keeps_rendered_text_within_horizontal_bounds(
    built_figures: Path, tmp_path: Path
) -> None:
    registry = json.loads((built_figures / "figure_registry.json").read_text())
    paths = sorted(
        {
            (built_figures / item["filename"]).with_suffix(".svg")
            for item in registry["figures"]
        }
    )
    assert paths, "no plates were scanned"
    problems = {
        path.name: found
        for path in paths
        if (found := _layout_problems(path, tmp_path))
    }
    assert not problems, json.dumps(problems, indent=2)


def test_rendered_layout_gate_detects_real_overflow_and_overlap(tmp_path: Path) -> None:
    source = tmp_path / "planted.svg"
    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100" width="200" height="100">'
        '<text x="10" y="40" font-size="24px">A deliberately wide sentence that cannot fit</text>'
        '<text x="20" y="40" font-size="24px">Overlapping</text></svg>'
    )
    scratch = tmp_path / "measured"
    scratch.mkdir()
    problems = _layout_problems(source, scratch)
    assert any("viewport overflow" in item for item in problems)
    assert any("text overlap" in item for item in problems)

#!/usr/bin/env python3
"""DAG visualizer: parse a .nk file and render the node graph as a PNG.

Requires:
    nuke_parser  (pip install from https://github.com/maxWiklund/nuke_parser)
    ImageMagick  (system package — provides the ``convert`` command)

Usage:
    python3 tests/dag_viz.py path/to/script.nk [output.png]

If output path is omitted, writes to <input_stem>.png next to the .nk file.
The rendered PNG can be read back by Claude's Read tool for visual inspection.
"""

import json
import os
import subprocess
import sys

from nuke_parser.parser import parseNk

# ---------------------------------------------------------------------------
# Node dimension constants (matches Nuke defaults)
# ---------------------------------------------------------------------------
_NODE_W = 80
_NODE_H = 28
_DOT_W = 12
_DOT_H = 12

# ---------------------------------------------------------------------------
# Freeze-group colour palette (dark-background safe)
# ---------------------------------------------------------------------------
_FREEZE_COLORS = [
    "#e06c75",  # red
    "#61afef",  # blue
    "#98c379",  # green
    "#e5c07b",  # yellow
    "#c678dd",  # purple
    "#56b6c2",  # cyan
    "#d19a66",  # orange
]
_UNFROZEN_FILL = "#4b5263"
_UNFROZEN_STROKE = "#8b92a5"
_FROZEN_STROKE = "#ffffff"
_WRITE_FILL = "#2d4a6e"
_MERGE_FILL = "#4a3728"
_DOT_FILL = "#888888"
_BG_COLOR = "#282c34"
_WIRE_COLOR = "#636d83"
_TEXT_COLOR = "#abb2bf"
_FONT = "DejaVu Sans"

_CLASS_FILLS = {
    "Write": _WRITE_FILL,
    "Write2": _WRITE_FILL,
    "Merge": _MERGE_FILL,
    "Merge2": _MERGE_FILL,
    "Dot": _DOT_FILL,
}


def _node_dims(node_class):
    if node_class == "Dot":
        return _DOT_W, _DOT_H
    return _NODE_W, _NODE_H


def _node_center(xpos, ypos, node_class):
    w, h = _node_dims(node_class)
    return xpos + w / 2, ypos + h / 2


def _node_output_port(xpos, ypos, node_class):
    """Bottom-centre of node bounding box."""
    w, h = _node_dims(node_class)
    return xpos + w / 2, ypos + h


def _node_input_port(xpos, ypos, node_class, slot_index, total_inputs):
    """Top-centre of node, offset per slot for multi-input nodes."""
    w, _ = _node_dims(node_class)
    if total_inputs <= 1:
        return xpos + w / 2, ypos
    # Spread input ports evenly across top edge
    step = w / (total_inputs + 1)
    return xpos + step * (slot_index + 1), ypos


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _rect(x, y, w, h, fill, stroke, rx=4, opacity=1.0, extra=""):
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="1.5" rx="{rx}" '
        f'opacity="{opacity}" {extra}/>'
    )


def _text(x, y, content, font_size=9, anchor="middle", fill=_TEXT_COLOR, bold=False):
    weight = "bold" if bold else "normal"
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="{_FONT}" font-size="{font_size}" font-weight="{weight}" '
        f'fill="{fill}">{_esc(content)}</text>'
    )


def _line(x1, y1, x2, y2, color=_WIRE_COLOR, width=1.5):
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{color}" stroke-width="{width}" opacity="0.8"/>'
    )


def _polyline(points, color=_WIRE_COLOR, width=1.5):
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return (
        f'<polyline points="{pts}" fill="none" '
        f'stroke="{color}" stroke-width="{width}" opacity="0.8"/>'
    )


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_dag(nk_path, output_png=None, title=None):
    """Render the DAG in *nk_path* to a PNG at *output_png*.

    Returns the path to the written PNG.
    """
    if output_png is None:
        stem = os.path.splitext(nk_path)[0]
        output_png = stem + ".png"

    root = parseNk(nk_path)
    nodes = list(root.allNodes())

    if not nodes:
        raise ValueError(f"No nodes found in {nk_path}")

    # --- Assign freeze-group colours ---
    freeze_uuid_to_color = {}
    color_index = 0
    node_data = []  # list of dicts with rendering info

    for node in nodes:
        name = node.name()
        node_class = node.Class()
        xpos = node.knob("xpos") or 0
        ypos = node.knob("ypos") or 0

        state_raw = node.knob("node_layout_state")
        freeze_uuid = None
        if state_raw:
            try:
                state = json.loads(state_raw)
                freeze_uuid = state.get("freeze_group")
            except (ValueError, TypeError):
                pass

        if freeze_uuid and freeze_uuid not in freeze_uuid_to_color:
            freeze_uuid_to_color[freeze_uuid] = _FREEZE_COLORS[
                color_index % len(_FREEZE_COLORS)
            ]
            color_index += 1

        fill = _CLASS_FILLS.get(node_class, _UNFROZEN_FILL)
        stroke = _FROZEN_STROKE if freeze_uuid else _UNFROZEN_STROKE
        if freeze_uuid:
            fill = freeze_uuid_to_color[freeze_uuid]

        w, h = _node_dims(node_class)
        node_data.append(
            {
                "name": name,
                "class": node_class,
                "xpos": xpos,
                "ypos": ypos,
                "w": w,
                "h": h,
                "fill": fill,
                "stroke": stroke,
                "freeze_uuid": freeze_uuid,
                "inputs": node.inputs(),
            }
        )

    # --- Compute bounding box ---
    pad = 60
    all_x = [d["xpos"] for d in node_data] + [d["xpos"] + d["w"] for d in node_data]
    all_y = [d["ypos"] for d in node_data] + [d["ypos"] + d["h"] for d in node_data]
    min_x, max_x = min(all_x) - pad, max(all_x) + pad
    min_y, max_y = min(all_y) - pad, max(all_y) + pad
    canvas_w = max_x - min_x
    canvas_h = max_y - min_y + (80 if freeze_uuid_to_color else 0)  # legend space

    # Offset: shift all coords so bounding box starts at (pad, pad)
    ox, oy = -min_x, -min_y

    svg_parts = []

    # Background
    svg_parts.append(
        f'<rect width="{canvas_w:.0f}" height="{canvas_h:.0f}" fill="{_BG_COLOR}"/>'
    )

    # Grid lines (subtle)
    for gx in range(int(min_x) - int(min_x) % 100, int(max_x), 100):
        svg_parts.append(
            f'<line x1="{gx + ox:.1f}" y1="0" x2="{gx + ox:.1f}" '
            f'y2="{canvas_h}" stroke="#333740" stroke-width="0.5"/>'
        )
    for gy in range(int(min_y) - int(min_y) % 100, int(max_y), 100):
        svg_parts.append(
            f'<line x1="0" y1="{gy + oy:.1f}" x2="{canvas_w}" '
            f'y2="{gy + oy:.1f}" stroke="#333740" stroke-width="0.5"/>'
        )

    # Build lookup: name -> node_data entry (for connection drawing)
    by_name = {d["name"]: d for d in node_data}

    # --- Draw connections ---
    for downstream in node_data:
        total_inputs = len(downstream["inputs"])
        for slot, upstream_node in enumerate(downstream["inputs"]):
            if upstream_node is None:
                continue
            up_name = upstream_node.name()
            if up_name not in by_name:
                continue
            up = by_name[up_name]

            ox1, oy1 = _node_output_port(up["xpos"] + ox, up["ypos"] + oy, up["class"])
            ix1, iy1 = _node_input_port(
                downstream["xpos"] + ox,
                downstream["ypos"] + oy,
                downstream["class"],
                slot,
                total_inputs,
            )

            # Draw a simple elbow: vertical from output, then to input
            mid_y = (oy1 + iy1) / 2
            svg_parts.append(
                _polyline(
                    [(ox1, oy1), (ox1, mid_y), (ix1, mid_y), (ix1, iy1)],
                    color=_WIRE_COLOR,
                )
            )

    # --- Draw nodes ---
    for d in node_data:
        x, y = d["xpos"] + ox, d["ypos"] + oy
        w, h = d["w"], d["h"]
        node_class = d["class"]
        name = d["name"]

        if node_class == "Dot":
            # Dots render as circles
            cx, cy = x + w / 2, y + h / 2
            r = w / 2
            svg_parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
                f'fill="{d["fill"]}" stroke="{d["stroke"]}" stroke-width="1.5"/>'
            )
        else:
            svg_parts.append(_rect(x, y, w, h, d["fill"], d["stroke"]))

            # Node name (bold, primary label)
            label_y = y + h / 2 + 3
            svg_parts.append(_text(x + w / 2, label_y, name, font_size=9, bold=True))

            # Node class (smaller, below name — only if different from name)
            if node_class != name:
                svg_parts.append(
                    _text(x + w / 2, y + h + 11, node_class, font_size=8, fill="#636d83")
                )

    # --- Legend ---
    if freeze_uuid_to_color or title:
        legend_y = max_y + oy + 10
        if title:
            svg_parts.append(
                _text(canvas_w / 2, legend_y + 12, title, font_size=11, bold=True, fill="#abb2bf")
            )
            legend_y += 20
        for uuid, color in freeze_uuid_to_color.items():
            short_uuid = uuid[:8] + "..."
            svg_parts.append(
                f'<rect x="10" y="{legend_y:.0f}" width="12" height="12" '
                f'fill="{color}" rx="2"/>'
            )
            svg_parts.append(
                _text(28, legend_y + 10, f"freeze: {short_uuid}", font_size=9, anchor="start")
            )
            legend_y += 18

    # --- Coordinate labels (helpful for debugging) ---
    for d in node_data:
        x, y = d["xpos"] + ox, d["ypos"] + oy
        coord_label = f"({d['xpos']},{d['ypos']})"
        svg_parts.append(
            _text(x, y - 3, coord_label, font_size=7, anchor="start", fill="#636d83")
        )

    # --- Assemble SVG ---
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{canvas_w:.0f}" height="{canvas_h:.0f}">\n'
        + "\n".join(svg_parts)
        + "\n</svg>"
    )

    svg_path = output_png.replace(".png", ".svg")
    with open(svg_path, "w") as f:
        f.write(svg)

    # Convert SVG → PNG via ImageMagick
    result = subprocess.run(
        ["convert", "-density", "150", svg_path, output_png],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ImageMagick convert failed:\n{result.stderr}")

    return output_png


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: dag_viz.py <script.nk> [output.png]")
        sys.exit(1)

    nk_file = sys.argv[1]
    out_file = sys.argv[2] if len(sys.argv) > 2 else None
    path = render_dag(nk_file, out_file, title=os.path.basename(nk_file))
    print(f"Written: {path}")

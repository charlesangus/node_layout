"""Headless builder for documentation DAG fixtures.

Run with:
    nuke -t docs/screenshots/build_dag_fixtures.py

This is stage 1 of the two-stage screenshot pipeline. It constructs small,
deliberately-arranged Nuke node graphs that illustrate each layout feature and
saves them as committed, hand-editable ``.nk`` fixtures under
``docs/screenshots/fixtures/``. Stage 2 (``make screenshots``) renders those
fixtures to PNGs and is a separate task -- this script never renders images.

Each fixture wraps every region it wants captured in a ``BackdropNode`` whose
label starts with ``screenshot:``; the screenshotter keys off that prefix and
frames the render to the backdrop's bounding box.

Because ``nuke -t`` performs no autoplace, every node's ``xpos``/``ypos`` is set
explicitly here, which makes the resulting geometry fully deterministic.

Part of the node_layout project (GPL-3.0).
"""
import os
import sys

# ---------------------------------------------------------------------------
# sys.path: make the repo root importable so make_room et al. resolve.
# This file lives at docs/screenshots/, so the repo root is two directories up.
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import make_room  # noqa: E402, I001
import nuke  # noqa: E402 (must come after sys.path setup; provided by Nuke runtime)

# ---------------------------------------------------------------------------
# Fixture output location. This is anchored to _REPO_ROOT (not the process
# CWD) so the script writes to the correct place regardless of where it is
# launched from, e.g. `nuke -t /abs/path/to/build_dag_fixtures.py` run from
# an unrelated directory. The repo-relative form of this path (with forward
# slashes) is what gets written into the committed .nk's Root `name` knob,
# so no machine-local absolute path leaks into version control.
# ---------------------------------------------------------------------------
FIXTURES_DIR = os.path.join(_REPO_ROOT, "docs", "screenshots", "fixtures")
FIXTURES_DIR_RELATIVE = "docs/screenshots/fixtures"

# Nuke node tiles are roughly this size in DAG units. screenWidth()/screenHeight()
# are used when available (they may return 0 under -t); these are the fallbacks.
DEFAULT_NODE_WIDTH = 80
DEFAULT_NODE_HEIGHT = 18

# Margin, in DAG units, added around a region's nodes when sizing its backdrop.
BACKDROP_MARGIN = 60


def _node_extent(node):
    """Return (width, height) of a node's tile in DAG units.

    Falls back to DEFAULT_NODE_WIDTH/HEIGHT when the GUI-only screen size APIs
    are unavailable or report zero (as they can under ``nuke -t``).
    """
    width = 0
    height = 0
    try:
        width = node.screenWidth()
        height = node.screenHeight()
    except Exception:
        width = 0
        height = 0
    if not width:
        width = DEFAULT_NODE_WIDTH
    if not height:
        height = DEFAULT_NODE_HEIGHT
    return width, height


def wrap_region_in_backdrop(region_nodes, label):
    """Create a BackdropNode that fully encloses ``region_nodes``.

    Bounds are computed from the nodes' positions plus their tile extent and a
    fixed margin. Remember the DAG is Y-down: the minimum ypos is the TOP edge.
    """
    min_x = min(node.xpos() for node in region_nodes)
    min_y = min(node.ypos() for node in region_nodes)
    max_x = max(node.xpos() + _node_extent(node)[0] for node in region_nodes)
    max_y = max(node.ypos() + _node_extent(node)[1] for node in region_nodes)

    backdrop = nuke.createNode("BackdropNode", inpanel=False)
    backdrop["label"].setValue(label)
    backdrop.setXpos(int(min_x - BACKDROP_MARGIN))
    backdrop.setYpos(int(min_y - BACKDROP_MARGIN))
    backdrop["bdwidth"].setValue(int((max_x - min_x) + 2 * BACKDROP_MARGIN))
    backdrop["bdheight"].setValue(int((max_y - min_y) + 2 * BACKDROP_MARGIN))
    return backdrop


def _build_messy_cluster(x_origin, y_origin):
    r"""Build one compact "messy" cluster with explicit positions.

    Layout (Y-down: upstream/inputs are higher on screen = more negative Y):

        Read_source        Read_matte
             |                  |
          Grade               /
             |               /
          Blur             /
              \           /
               \         /
                 Merge          <- split point: this and below are downstream
                   |
                 Write

    Returns (upstream_nodes, downstream_nodes). Positions are relative to
    (x_origin, y_origin) so the cluster can be dropped anywhere in the DAG.
    """
    read_source = nuke.createNode("Read", inpanel=False)
    read_source.setXpos(x_origin)
    read_source.setYpos(y_origin)

    grade = nuke.createNode("Grade", inpanel=False)
    grade.setInput(0, read_source)
    grade.setXpos(x_origin)
    grade.setYpos(y_origin + 90)

    blur = nuke.createNode("Blur", inpanel=False)
    blur.setInput(0, grade)
    blur.setXpos(x_origin)
    blur.setYpos(y_origin + 180)

    read_matte = nuke.createNode("Read", inpanel=False)
    read_matte.setXpos(x_origin + 140)
    read_matte.setYpos(y_origin + 90)

    merge = nuke.createNode("Merge2", inpanel=False)
    merge.setInput(0, blur)
    merge.setInput(1, read_matte)
    merge.setXpos(x_origin)
    merge.setYpos(y_origin + 300)

    write = nuke.createNode("Write", inpanel=False)
    write.setInput(0, merge)
    write.setXpos(x_origin)
    write.setYpos(y_origin + 390)

    upstream_nodes = [read_source, grade, blur, read_matte]
    downstream_nodes = [merge, write]
    return upstream_nodes, downstream_nodes


def build_make_room_scenario():
    """Build the Make Room before/after fixture and save it.

    Two identical clusters are placed side by side. The right ("after") cluster
    has make_room applied to its downstream half, opening a visible vertical gap
    between the upstream and downstream nodes -- the "room made".
    """
    nuke.scriptClear()

    # ---- Before region (left) --------------------------------------------
    before_upstream, before_downstream = _build_messy_cluster(0, 0)

    # ---- After region (right) --------------------------------------------
    # Offset well to the right so the two backdrops never overlap in X. The
    # cluster spans ~220 units wide (0..140 plus a node tile); +1200 leaves a
    # comfortable gap.
    after_x_offset = 1200
    after_upstream, after_downstream = _build_messy_cluster(after_x_offset, 0)

    # ---- Apply make_room to the AFTER copy's downstream half only ---------
    # make_room translates nuke.selectedNodes(), so the selection must contain
    # ONLY the after cluster's downstream nodes. direction="down" adds +Y,
    # pushing them further down-screen and opening vertical space above them.
    # amount=300 is large enough to read clearly while keeping the cluster
    # compact (the untouched gap between blur and merge is ~120 units).
    make_room_amount = 300
    make_room_direction = "down"
    for node in nuke.allNodes():
        node.setSelected(False)
    for node in after_downstream:
        node.setSelected(True)
    make_room.make_room(amount=make_room_amount, direction=make_room_direction)

    # ---- Wrap each region in a labelled BackdropNode ---------------------
    wrap_region_in_backdrop(
        before_upstream + before_downstream,
        "screenshot:make-room-before",
    )
    wrap_region_in_backdrop(
        after_upstream + after_downstream,
        "screenshot:make-room-after",
    )


def main():
    if not os.path.isdir(FIXTURES_DIR):
        os.makedirs(FIXTURES_DIR)

    build_make_room_scenario()

    output_path = os.path.join(FIXTURES_DIR, "make_room.nk")
    relative_output_path = "/".join([FIXTURES_DIR_RELATIVE, "make_room.nk"])
    nuke.scriptSaveAs(output_path, overwrite=1)

    # nuke.scriptSaveAs records the script's ABSOLUTE path (the one we just
    # saved to) in the Root `name` knob, which would leak a machine-local
    # path into the committed fixture. Rewrite that one line to the
    # repo-relative path so the .nk is portable.
    _rewrite_root_name(output_path, relative_output_path)
    print("[build_dag_fixtures] Saved: {}".format(output_path))


def _rewrite_root_name(nk_path, relative_name):
    """Replace the Root `name` line's absolute path with a portable value."""
    with open(nk_path, "r") as handle:
        lines = handle.readlines()

    inside_root = False
    for index, line in enumerate(lines):
        if line.startswith("Root {"):
            inside_root = True
        elif inside_root and line.strip() == "}":
            break
        elif inside_root and line.lstrip().startswith("name "):
            indent = line[: len(line) - len(line.lstrip())]
            lines[index] = "{}name {}\n".format(indent, relative_name)
            break

    with open(nk_path, "w") as handle:
        handle.writelines(lines)


if __name__ == "__main__":
    main()

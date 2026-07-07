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
import itertools
import os
import sys
import uuid

# ---------------------------------------------------------------------------
# sys.path: make the repo root importable so make_room et al. resolve.
# This file lives at docs/screenshots/, so the repo root is two directories up.
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import make_room  # noqa: E402, I001
import node_layout  # noqa: E402
import nuke  # noqa: E402 (must come after sys.path setup; provided by Nuke runtime)

# ---------------------------------------------------------------------------
# Terminal-mode patches (mirrors nuke_tests/run_layout.py).
#
# The layout_upstream / layout_selected commands reach GUI-only Nuke APIs that
# raise under `nuke -t`. Patch them here, before any layout runs, so the layout
# logic executes normally. make_room does not touch these, so this is inert for
# the Make Room scenario.
#
# 1. node_layout._build_toolbar_folder_map() calls nuke.menu(), which raises
#    "not in GUI mode". The map is only a spacing hint; an empty dict makes
#    same_toolbar_folder() fall back to True for every node pair.
# 2. nuke.lastHitGroup() may return None in terminal mode. The layout functions
#    call it first for undo scoping; redirect it to the root group.
# 3. node_layout.freeze_selected() tags every frozen node with a random
#    uuid.uuid4() freeze-group id. That randomness is hidden internal state
#    with no effect on the rendered screenshot, but it would make the saved
#    freeze fixture churn on every rebuild even though its geometry is fully
#    fixed. Replace uuid4 with a deterministic counter-based sequence so the
#    committed fixtures stay byte-stable across rebuilds; the concrete id
#    values are irrelevant, only their stability matters. Scoped to
#    node_layout's own ``uuid`` reference (via a shim module object) rather
#    than mutating the global stdlib ``uuid`` module, so other code that
#    imports ``uuid`` is unaffected.
# ---------------------------------------------------------------------------
node_layout._build_toolbar_folder_map = lambda: {}
nuke.lastHitGroup = lambda: nuke.root()

_deterministic_uuid_counter = itertools.count(1)


class _DeterministicUuidShim:
    """Stand-in for the ``uuid`` module used only by node_layout.

    Exposes a deterministic ``uuid4`` and delegates everything else (e.g.
    ``UUID``) to the real ``uuid`` module, so node_layout's behaviour is
    unchanged except for the source of its freeze-group ids.
    """

    @staticmethod
    def uuid4():
        return uuid.UUID(int=next(_deterministic_uuid_counter))

    def __getattr__(self, attribute_name):
        return getattr(uuid, attribute_name)


node_layout.uuid = _DeterministicUuidShim()

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


# X position (DAG units) at which each scenario's "after" region is anchored
# on its left edge. The "before" region is built near x=0 and spans only a few
# hundred units, so anchoring the tidied "after" graph out here guarantees the
# two labelled backdrops never overlap in X regardless of where the layout
# command chose to place the tidied nodes.
AFTER_REGION_LEFT_X = 1000


def _build_messy_tree(x_origin, y_origin):
    r"""Build one deliberately MESSY compositing tree with explicit positions.

    Under ``nuke -t`` there is no autoplace, so every position is set by hand.
    The columns are intentionally mis-aligned and some tiles overlap, so that a
    tidy-up command produces a visibly different "after".

    Topology (Y-down: upstream/inputs are higher on screen = more negative Y):

        read_foreground   read_background        read_matte
              |                 |                    |
        grade_foreground        |                 blur_matte
               \                /                    /
                \              /                    /
                 merge_over  <-------.             /
                      |               \           /
                      |                merge_key <-
                      |                     |
                      +------------------ write_out

    ``merge_over`` combines the graded foreground over the background;
    ``merge_key`` combines that result with the blurred matte branch;
    ``write_out`` is the single most-downstream (root) node.

    Positions are relative to (x_origin, y_origin). Returns
    ``(all_nodes, root_node)`` where ``root_node`` is ``write_out``.
    """
    read_foreground = nuke.createNode("Read", inpanel=False)
    read_foreground.setXpos(x_origin + 0)
    read_foreground.setYpos(y_origin + 0)

    # Offset diagonally so it overlaps its neighbour column -- deliberately messy.
    read_background = nuke.createNode("Read", inpanel=False)
    read_background.setXpos(x_origin + 45)
    read_background.setYpos(y_origin + 35)

    grade_foreground = nuke.createNode("Grade", inpanel=False)
    grade_foreground.setInput(0, read_foreground)
    grade_foreground.setXpos(x_origin + 15)
    grade_foreground.setYpos(y_origin + 120)

    merge_over = nuke.createNode("Merge2", inpanel=False)
    merge_over.setInput(0, grade_foreground)
    merge_over.setInput(1, read_background)
    merge_over.setXpos(x_origin + 70)
    merge_over.setYpos(y_origin + 210)

    read_matte = nuke.createNode("Read", inpanel=False)
    read_matte.setXpos(x_origin + 230)
    read_matte.setYpos(y_origin + 55)

    # Crooked relative to read_matte above it.
    blur_matte = nuke.createNode("Blur", inpanel=False)
    blur_matte.setInput(0, read_matte)
    blur_matte.setXpos(x_origin + 255)
    blur_matte.setYpos(y_origin + 150)

    merge_key = nuke.createNode("Merge2", inpanel=False)
    merge_key.setInput(0, merge_over)
    merge_key.setInput(1, blur_matte)
    merge_key.setXpos(x_origin + 105)
    merge_key.setYpos(y_origin + 320)

    write_out = nuke.createNode("Write", inpanel=False)
    write_out.setInput(0, merge_key)
    write_out.setXpos(x_origin + 135)
    write_out.setYpos(y_origin + 420)

    all_nodes = [
        read_foreground,
        read_background,
        grade_foreground,
        merge_over,
        read_matte,
        blur_matte,
        merge_key,
        write_out,
    ]
    return all_nodes, write_out


def _select_only(nodes):
    """Deselect everything, then select exactly ``nodes``."""
    for node in nuke.allNodes():
        node.setSelected(False)
    for node in nodes:
        node.setSelected(True)


def _translate_nodes(nodes, dx, dy):
    """Shift every node in ``nodes`` by (dx, dy) DAG units."""
    for node in nodes:
        node.setXpos(node.xpos() + dx)
        node.setYpos(node.ypos() + dy)


def _move_region_left_edge_to(nodes, target_left_x):
    """Translate ``nodes`` as a group so their leftmost xpos lands on target."""
    current_left_x = min(node.xpos() for node in nodes)
    _translate_nodes(nodes, target_left_x - current_left_x, 0)


def build_make_room_scenario():
    """Build the Make Room before/after fixture in the current script.

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


def build_layout_upstream_scenario():
    """Build the Layout Upstream before/after fixture in the current script.

    ``layout_upstream`` tidies the upstream tree of the SELECTED node, so the
    "after" graph selects the single root (write_out) and runs the command.

    The after graph is built and laid out FIRST, while it is the only graph in
    the script -- the layout command may push surrounding nodes to make room, so
    keeping the before region out of the script during layout guarantees it is
    never disturbed. The tidied after graph is then translated far to the right,
    and only then is the static messy before graph built at the left.
    """
    nuke.scriptClear()

    # ---- After region: build messy, lay out upstream, then move aside -------
    # layout_upstream may insert side-routing Dot nodes, so capture the WHOLE
    # laid-out graph via allNodes() (the script is otherwise empty here) rather
    # than the pre-layout node list -- otherwise those Dots would be left behind
    # outside the after backdrop and could overlap the before region.
    _, after_root = _build_messy_tree(0, 0)
    _select_only([after_root])
    node_layout.layout_upstream()
    after_nodes = nuke.allNodes()
    _move_region_left_edge_to(after_nodes, AFTER_REGION_LEFT_X)

    # ---- Before region: static messy tree at the left -----------------------
    before_nodes, _ = _build_messy_tree(0, 0)

    # ---- Wrap each region in a labelled BackdropNode ------------------------
    wrap_region_in_backdrop(before_nodes, "screenshot:layout-upstream-before")
    wrap_region_in_backdrop(after_nodes, "screenshot:layout-upstream-after")


def build_layout_selected_scenario():
    """Build the Layout Selected before/after fixture in the current script.

    This scenario is designed to illustrate what makes ``layout_selected``
    distinct from ``layout_upstream``: it arranges ONLY the explicitly selected
    nodes and leaves every unselected node exactly where it was. So instead of
    selecting the whole tree (which would just reproduce the upstream result),
    the "after" graph selects a single sub-branch -- the foreground/left
    upstream branch (read_foreground, read_background, grade_foreground,
    merge_over) -- and lays out just that. The matte branch and the downstream
    spine (read_matte, blur_matte, merge_key, write_out) stay messy, so the
    image reads as "the selected corner got tidied, the rest was untouched".

    That branch is the first four nodes returned by _build_messy_tree, in build
    order. Ordering (after graph built + laid out first, then translated aside,
    then the static before graph) matches build_layout_upstream_scenario so the
    layout's make-room step can never disturb the before region.
    """
    nuke.scriptClear()

    # ---- After region: build messy, lay out ONLY the selected sub-branch -----
    # Capture the full graph via allNodes() so any Dot nodes the command inserts
    # are moved and enclosed with the rest; this also keeps the untouched matte
    # branch + spine in the after region to demonstrate they stayed put.
    messy_nodes, _ = _build_messy_tree(0, 0)
    foreground_branch = messy_nodes[:4]
    _select_only(foreground_branch)
    node_layout.layout_selected()
    after_nodes = nuke.allNodes()
    _move_region_left_edge_to(after_nodes, AFTER_REGION_LEFT_X)

    # ---- Before region: static messy tree at the left -----------------------
    before_nodes, _ = _build_messy_tree(0, 0)

    # ---- Wrap each region in a labelled BackdropNode ------------------------
    wrap_region_in_backdrop(before_nodes, "screenshot:layout-selected-before")
    wrap_region_in_backdrop(after_nodes, "screenshot:layout-selected-after")


def build_layout_selected_horizontal_scenario():
    """Build the Layout Selected Horizontal before/after fixture.

    ``layout_selected_horizontal`` arranges the selection along a LEFT-TO-RIGHT
    horizontal spine rather than the default top-to-bottom vertical one, so the
    "after" reads as a wide chain instead of a tall column. The whole messy tree
    is selected and laid out. Ordering (after graph built + laid out first, then
    translated aside, then the static before graph) matches the other scenarios
    so the layout's make-room step can never disturb the before region.
    """
    nuke.scriptClear()

    # ---- After region: build messy, lay out horizontally, then move aside ---
    # Capture the full laid-out graph via allNodes() so any Dot nodes the command
    # inserts are moved and enclosed with the rest.
    messy_nodes, _ = _build_messy_tree(0, 0)
    _select_only(messy_nodes)
    node_layout.layout_selected_horizontal()
    after_nodes = nuke.allNodes()
    _move_region_left_edge_to(after_nodes, AFTER_REGION_LEFT_X)

    # ---- Before region: static messy tree at the left -----------------------
    before_nodes, _ = _build_messy_tree(0, 0)

    # ---- Wrap each region in a labelled BackdropNode ------------------------
    wrap_region_in_backdrop(
        before_nodes, "screenshot:layout-selected-horizontal-before",
    )
    wrap_region_in_backdrop(
        after_nodes, "screenshot:layout-selected-horizontal-after",
    )


# Packed RGBA (0xRRGGBBAA) bright-orange highlight painted on BOTH members of the
# frozen block in the Freeze scenario, so the reader can see the whole locked
# unit. Freezing itself makes no visual change; the colour is only a tracking aid.
FROZEN_NODE_HIGHLIGHT_COLOR = 0xFFAA00FF

# Internal arrangement of the 2-node freeze block: the frozen Grade is placed to
# the SIDE of (and slightly above) the frozen Merge it feeds, rather than the
# directly-overhead spot a tidy layout would use. This deliberately non-standard
# offset is what makes the "locked shape" obvious once everything else tidies.
FREEZE_BLOCK_GRADE_OFFSET_X = 260
FREEZE_BLOCK_GRADE_OFFSET_Y = -20


def _arrange_and_highlight_freeze_block(grade_node, merge_node):
    """Place ``grade_node`` off to the side of ``merge_node`` and highlight both.

    Returns the internal offset (grade - merge) that the freeze block must keep
    rigid through a layout.
    """
    grade_node.setXpos(merge_node.xpos() + FREEZE_BLOCK_GRADE_OFFSET_X)
    grade_node.setYpos(merge_node.ypos() + FREEZE_BLOCK_GRADE_OFFSET_Y)
    grade_node["tile_color"].setValue(FROZEN_NODE_HIGHLIGHT_COLOR)
    merge_node["tile_color"].setValue(FROZEN_NODE_HIGHLIGHT_COLOR)
    return (
        grade_node.xpos() - merge_node.xpos(),
        grade_node.ypos() - merge_node.ypos(),
    )


def build_freeze_scenario():
    """Build the Freeze before/after fixture -- GENUINE engine behaviour.

    Demonstrates the real freeze signature: a multi-node freeze block keeps its
    INTERNAL relative arrangement as a rigid unit while every non-frozen node is
    tidied around it. The block here is a Grade and the Merge it feeds
    (grade_foreground -> merge_over), arranged with the Grade offset out to the
    SIDE of the Merge rather than directly overhead. Both members are highlighted.

    In the "after" (real ``layout_selected`` output) the non-frozen nodes snap
    into a tidy vertical spine, but the two highlighted nodes retain their
    hand-set side-by-side offset -- visibly locked together, off the spine. This
    is not fixture-placed: the offset is preserved by the engine's freeze logic,
    which this function asserts by comparing the offset immediately before and
    after the ``layout_selected`` call.
    """
    nuke.scriptClear()

    # ---- After region: freeze the 2-node block, then lay out for real --------
    messy_nodes, _ = _build_messy_tree(0, 0)
    frozen_grade = messy_nodes[2]   # grade_foreground
    frozen_merge = messy_nodes[3]   # merge_over (grade_foreground feeds this)
    offset_before = _arrange_and_highlight_freeze_block(frozen_grade, frozen_merge)

    _select_only([frozen_grade, frozen_merge])
    node_layout.freeze_selected()

    # A non-frozen witness node, to prove the layout actually moved things.
    # (Not the root write_out: the root is the anchor and lands back on its own
    # current position, so it would not move.)
    witness_node = messy_nodes[1]   # read_background
    witness_before = (witness_node.xpos(), witness_node.ypos())

    _select_only(messy_nodes)
    node_layout.layout_selected()

    offset_after = (
        frozen_grade.xpos() - frozen_merge.xpos(),
        frozen_grade.ypos() - frozen_merge.ypos(),
    )
    witness_after = (witness_node.xpos(), witness_node.ypos())
    if offset_before != offset_after:
        raise AssertionError(
            "Freeze block internal offset changed across layout: "
            "{} -> {}".format(offset_before, offset_after)
        )
    if witness_before == witness_after:
        raise AssertionError(
            "Layout did not move the non-frozen witness node "
            "{} (stayed at {})".format(witness_node.name(), witness_before)
        )
    print(
        "[build_dag_fixtures] Freeze: block internal offset preserved "
        "{} -> {}; witness {} moved {} -> {}".format(
            offset_before, offset_after, witness_node.name(),
            witness_before, witness_after,
        )
    )

    after_nodes = nuke.allNodes()
    _move_region_left_edge_to(after_nodes, AFTER_REGION_LEFT_X)

    # ---- Before region: the messy pre-layout graph, block already frozen -----
    before_nodes, _ = _build_messy_tree(0, 0)
    before_grade = before_nodes[2]
    before_merge = before_nodes[3]
    _arrange_and_highlight_freeze_block(before_grade, before_merge)
    _select_only([before_grade, before_merge])
    node_layout.freeze_selected()

    # ---- Wrap each region in a labelled BackdropNode ------------------------
    wrap_region_in_backdrop(before_nodes, "screenshot:freeze-before")
    wrap_region_in_backdrop(after_nodes, "screenshot:freeze-after")


def _build_clean_tree(x_origin, y_origin):
    r"""Build one TIDY, comfortably-spaced two-branch tree with explicit positions.

    Unlike _build_messy_tree, this is already a clean layout with generous
    spacing -- the "before" for the shrink scenario is meant to read as a normal,
    well-spread graph, not a mess. Two source->grade branches merge into a Write.

    Topology (Y-down: inputs higher on screen = more negative Y):

        read_left        read_right
            |                |
        grade_left       grade_right
             \              /
              \            /
                 merge_ab
                    |
                 write_out

    Positions are relative to (x_origin, y_origin). Returns
    ``(all_nodes, root_node)`` where ``root_node`` is ``write_out``.
    """
    read_left = nuke.createNode("Read", inpanel=False)
    read_left.setXpos(x_origin + 0)
    read_left.setYpos(y_origin + 0)

    read_right = nuke.createNode("Read", inpanel=False)
    read_right.setXpos(x_origin + 220)
    read_right.setYpos(y_origin + 0)

    grade_left = nuke.createNode("Grade", inpanel=False)
    grade_left.setInput(0, read_left)
    grade_left.setXpos(x_origin + 0)
    grade_left.setYpos(y_origin + 120)

    grade_right = nuke.createNode("Grade", inpanel=False)
    grade_right.setInput(0, read_right)
    grade_right.setXpos(x_origin + 220)
    grade_right.setYpos(y_origin + 120)

    merge_ab = nuke.createNode("Merge2", inpanel=False)
    merge_ab.setInput(0, grade_left)
    merge_ab.setInput(1, grade_right)
    merge_ab.setXpos(x_origin + 110)
    merge_ab.setYpos(y_origin + 260)

    write_out = nuke.createNode("Write", inpanel=False)
    write_out.setInput(0, merge_ab)
    write_out.setXpos(x_origin + 110)
    write_out.setYpos(y_origin + 380)

    all_nodes = [
        read_left, read_right, grade_left, grade_right, merge_ab, write_out,
    ]
    return all_nodes, write_out


def _selection_spread_and_center(nodes):
    """Return (spread_x, spread_y, center_x, center_y) of ``nodes``' bounding box."""
    min_x = min(node.xpos() for node in nodes)
    min_y = min(node.ypos() for node in nodes)
    max_x = max(node.xpos() + _node_extent(node)[0] for node in nodes)
    max_y = max(node.ypos() + _node_extent(node)[1] for node in nodes)
    return (max_x - min_x, max_y - min_y, (min_x + max_x) // 2, (min_y + max_y) // 2)


def build_shrink_selected_scenario():
    """Build the Shrink Selected before/after fixture.

    ``shrink_selected`` scales the selected nodes closer together, keeping the
    arrangement's shape, so the "after" is a more COMPACT copy of the same tree.

    Engine note: the scale is anchored on the most-downstream selected node (the
    root ``write_out``), which stays fixed -- every other node moves toward it by
    the SHRINK_FACTOR. So the bounding box shrinks in both axes and its midpoint
    shifts slightly toward that fixed anchor (it is an anchor-centred scale, not
    a bbox-midpoint-centred one). This function asserts the real invariants: both
    spreads shrink and the anchor node does not move.
    """
    nuke.scriptClear()

    # ---- After region: build a clean tree, then shrink it for real ----------
    after_nodes, anchor_node = _build_clean_tree(0, 0)
    spread_x_before, spread_y_before, center_x_before, center_y_before = (
        _selection_spread_and_center(after_nodes)
    )
    anchor_before = (anchor_node.xpos(), anchor_node.ypos())

    _select_only(after_nodes)
    node_layout.shrink_selected()

    after_nodes = nuke.allNodes()
    spread_x_after, spread_y_after, center_x_after, center_y_after = (
        _selection_spread_and_center(after_nodes)
    )
    anchor_after = (anchor_node.xpos(), anchor_node.ypos())

    if not (spread_x_after < spread_x_before and spread_y_after < spread_y_before):
        raise AssertionError(
            "Shrink did not reduce both spreads: x {}->{}, y {}->{}".format(
                spread_x_before, spread_x_after, spread_y_before, spread_y_after,
            )
        )
    if anchor_before != anchor_after:
        raise AssertionError(
            "Shrink anchor (scale centre) moved: {} -> {}".format(
                anchor_before, anchor_after,
            )
        )
    print(
        "[build_dag_fixtures] Shrink: spread x {}->{} y {}->{}; "
        "bbox centre ({}, {})->({}, {}); anchor {} fixed".format(
            spread_x_before, spread_x_after, spread_y_before, spread_y_after,
            center_x_before, center_y_before, center_x_after, center_y_after,
            anchor_after,
        )
    )

    _move_region_left_edge_to(after_nodes, AFTER_REGION_LEFT_X)

    # ---- Before region: the same clean tree at its normal spread ------------
    before_nodes, _ = _build_clean_tree(0, 0)

    # ---- Wrap each region in a labelled BackdropNode ------------------------
    wrap_region_in_backdrop(before_nodes, "screenshot:shrink-before")
    wrap_region_in_backdrop(after_nodes, "screenshot:shrink-after")


def _save_current_script(filename):
    """Save the current script to FIXTURES_DIR/filename as a portable fixture.

    nuke.scriptSaveAs records the script's ABSOLUTE path in the Root `name`
    knob, which would leak a machine-local path into the committed fixture, so
    the name line is rewritten to the repo-relative path afterwards.
    """
    output_path = os.path.join(FIXTURES_DIR, filename)
    relative_output_path = "/".join([FIXTURES_DIR_RELATIVE, filename])
    nuke.scriptSaveAs(output_path, overwrite=1)
    _rewrite_root_name(output_path, relative_output_path)
    print("[build_dag_fixtures] Saved: {}".format(output_path))


def main():
    if not os.path.isdir(FIXTURES_DIR):
        os.makedirs(FIXTURES_DIR)

    build_make_room_scenario()
    _save_current_script("make_room.nk")

    build_layout_upstream_scenario()
    _save_current_script("layout_upstream.nk")

    build_layout_selected_scenario()
    _save_current_script("layout_selected.nk")

    build_layout_selected_horizontal_scenario()
    _save_current_script("layout_selected_horizontal.nk")

    build_freeze_scenario()
    _save_current_script("freeze.nk")

    build_shrink_selected_scenario()
    _save_current_script("shrink_selected.nk")


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

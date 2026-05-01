"""Algorithm A — leaf-first bbox composition layout engine ("bbox").

This is an independent, from-scratch implementation of the Nuke node-layout
contract. It does NOT delegate placement to ``node_layout.compute_dims`` or
``node_layout.place_subtree``; it runs its own post-order DFS that builds
``Subtree`` objects (bounding box + nodes-dict) and merges them into the
parent frame.

What is reused from the legacy module (orthogonal helpers):

* ``insert_dot_nodes``                 — diamond resolution (preserves DAG topology)
* ``_detect_freeze_groups``            — freeze UUID -> member list
* ``_build_freeze_blocks``             — FreezeBlock objects with rigid offsets
* ``_expand_scope_for_freeze_groups``  — pull whole groups into the selection
* ``push_nodes_to_make_room``          — shove surrounding DAG nodes
* ``collect_subtree_nodes``            — upstream walk respecting hide_input
* ``compute_node_bounding_box``        — bbox of arbitrary node list
* ``vertical_gap_between``             — color-aware vertical gap
* ``_subtree_margin``, ``_horizontal_margin`` — gap/margin formulas
* ``_is_mask_input``, ``_reorder_inputs_mask_last``, ``_is_fan_active``
* ``_hides_inputs``, ``_passes_node_filter``, ``_get_input_slot_pairs``
* ``get_inputs``, ``_center_x``, ``find_selection_roots``
* ``get_dag_snap_threshold``

Coordinate system (from CLAUDE.md): Nuke's DAG has positive Y DOWN. Inputs sit
at smaller Y values than the consumer they feed.
"""
from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import Optional

import nuke

import node_layout
import node_layout_engine
import node_layout_prefs
import node_layout_state

# ---------------------------------------------------------------------------
# Subtree value type — the unit of the bbox-composition recursion.
# ---------------------------------------------------------------------------

@dataclass
class Subtree:
    """Result of ``layout(node)``.

    ``nodes`` maps ``id(node) -> (xpos, ypos)`` in the SUBTREE-LOCAL frame
    where the root (``node``) sits at ``(root_x, root_y)``. When a parent
    pulls a child into its own frame it adds a translation ``(dx, dy)`` to
    every entry in ``nodes`` and to the bbox/anchors.

    bbox = (min_x, min_y, max_x, max_y) of the SUBTREE in the same local frame.

    anchor_out is the (x, y) where this subtree's root tile is placed — the
    point a downstream consumer will hook to. anchor_in_per_slot is unused
    in vertical mode (children consult the child's anchor_out instead) but
    kept for symmetry / future horizontal use.
    """
    bbox: tuple[int, int, int, int]
    anchor_out: tuple[int, int]
    nodes: dict[int, tuple[int, int]]
    root_node: object  # the actual Nuke node object at anchor_out
    anchor_in_per_slot: dict[int, tuple[int, int]] = field(default_factory=dict)


def _translate(subtree: Subtree, dx: int, dy: int) -> Subtree:
    """Return a new Subtree shifted by (dx, dy)."""
    new_nodes = {nid: (x + dx, y + dy) for nid, (x, y) in subtree.nodes.items()}
    new_bbox = (
        subtree.bbox[0] + dx,
        subtree.bbox[1] + dy,
        subtree.bbox[2] + dx,
        subtree.bbox[3] + dy,
    )
    new_anchor_out = (subtree.anchor_out[0] + dx, subtree.anchor_out[1] + dy)
    new_anchors_in = {
        slot: (ax + dx, ay + dy) for slot, (ax, ay) in subtree.anchor_in_per_slot.items()
    }
    return Subtree(
        bbox=new_bbox,
        anchor_out=new_anchor_out,
        nodes=new_nodes,
        root_node=subtree.root_node,
        anchor_in_per_slot=new_anchors_in,
    )


# ---------------------------------------------------------------------------
# Layout context — bundles all the per-call state the recursion needs.
# ---------------------------------------------------------------------------

@dataclass
class LayoutContext:
    snap_threshold: int
    node_count: int
    node_filter: Optional[set]
    per_node_scheme: dict
    per_node_h_scale: dict
    per_node_v_scale: dict
    dimension_overrides: dict  # id(root) -> FreezeBlock
    spine_set: Optional[set] = None  # for horizontal mode
    horizontal_root_id: Optional[int] = None
    all_member_ids: set = field(default_factory=set)
    # Populated by the dispatcher: every node that ended up in a horizontal
    # spine across the whole recursion. Used post-layout for output-dot
    # placement and state write-back.
    horizontal_seeds: list = field(default_factory=list)
    all_horizontal_ids: set = field(default_factory=set)

    def scheme_for(self, node) -> float:
        return self.per_node_scheme.get(
            id(node),
            node_layout_prefs.prefs_singleton.get("normal_multiplier"),
        )

    def h_scale_for(self, node) -> float:
        return self.per_node_h_scale.get(id(node), 1.0)

    def v_scale_for(self, node) -> float:
        return self.per_node_v_scale.get(id(node), 1.0)

    def passes_filter(self, node) -> bool:
        if self.node_filter is None:
            return True
        return node_layout._passes_node_filter(node, self.node_filter)


# ---------------------------------------------------------------------------
# Per-node mode dispatch.
#
# The recursion never asks "is this child a horizontal subtree?" — it just
# calls ``layout(node, ctx)``. The dispatcher reads the node's stored mode
# and routes to the appropriate packer; horizontal subtrees come back with
# a Subtree whose bbox extends leftward from the rightmost spine node, and
# the parent's vertical packer treats that bbox like any other child's.
# ---------------------------------------------------------------------------

def _spine_set_from(seed_node, all_member_ids):
    """Walk input(0) from ``seed_node`` collecting horizontal-mode nodes.

    Stops at the first non-horizontal node, or at any frozen non-root member.
    The seed itself is always included (even if its stored mode is missing —
    callers only invoke this when seed is known to be a horizontal seed).
    """
    spine = set()
    cursor = seed_node
    while cursor is not None:
        if id(cursor) in all_member_ids and id(cursor) != id(seed_node):
            break
        if cursor is not seed_node:
            state = node_layout_state.read_node_state(cursor)
            if state.get("mode") != "horizontal":
                break
        spine.add(id(cursor))
        cursor = cursor.input(0)
    return spine


def layout(node, ctx: LayoutContext) -> "Subtree":
    """Dispatch to vertical or horizontal layout based on ``node``'s stored mode.

    This is the single entry point used by every recursion site so that nested
    horizontal subtrees compose naturally inside vertical parents (and vice
    versa).
    """
    state = node_layout_state.read_node_state(node)
    if state.get("mode") == "horizontal":
        spine_set = _spine_set_from(node, ctx.all_member_ids)
        local_ctx = LayoutContext(
            snap_threshold=ctx.snap_threshold,
            node_count=ctx.node_count,
            node_filter=ctx.node_filter,
            per_node_scheme=ctx.per_node_scheme,
            per_node_h_scale=ctx.per_node_h_scale,
            per_node_v_scale=ctx.per_node_v_scale,
            dimension_overrides=ctx.dimension_overrides,
            spine_set=spine_set,
            horizontal_root_id=id(node),
            all_member_ids=ctx.all_member_ids,
            horizontal_seeds=ctx.horizontal_seeds,
            all_horizontal_ids=ctx.all_horizontal_ids,
        )
        ctx.horizontal_seeds.append(node)
        ctx.all_horizontal_ids.update(spine_set)
        return layout_horizontal(node, local_ctx)
    return layout_vertical(node, ctx)


# ---------------------------------------------------------------------------
# Per-node child list — applies node_filter, mask-reorder, fan logic.
# ---------------------------------------------------------------------------

def _filtered_input_pairs(node, ctx: LayoutContext):
    """Return (slot, input_node) pairs after node_filter, mask-reorder, and
    fan handling — exactly what ``compute_dims`` / ``place_subtree`` see.
    """
    if node_layout._hides_inputs(node):
        return [], False, False
    raw_pairs = [
        (slot, node.input(slot))
        for slot in range(node.inputs())
        if node.input(slot) is not None
    ]
    if ctx.node_filter is not None:
        raw_pairs = [
            (slot, inp) for slot, inp in raw_pairs
            if node_layout._passes_node_filter(inp, ctx.node_filter)
        ]
    all_side = node_layout._primary_slot_externally_occupied(node, ctx.node_filter)
    fan_active = node_layout._is_fan_active(raw_pairs, node)
    pairs = node_layout._reorder_inputs_mask_last(
        raw_pairs, node, all_side, fan_active=fan_active
    )
    return pairs, all_side, fan_active


# ---------------------------------------------------------------------------
# Vertical packing — the main recursion.
# ---------------------------------------------------------------------------

def _block_local_extents(block):
    """Compute a block's bounding box in its root-local frame.

    The block's root sits at (0, 0). Returns ``(left, top, right, bottom)``
    where ``left = -left_overhang``, ``right = right_extent``, ``top`` is the
    Y of the block's topmost edge (typically negative — non-root members
    sit above the root in Nuke's positive-Y-down DAG), and ``bottom`` is
    the Y of the block's bottommost edge (>= root.screenHeight()).
    """
    root = block.root
    block_min_y = min(m.ypos() for m in block.members)
    block_max_y = max(m.ypos() + m.screenHeight() for m in block.members)
    return (
        -block.left_overhang,
        block_min_y - root.ypos(),
        block.right_extent,
        block_max_y - root.ypos(),
    )


def layout_vertical(node, ctx: LayoutContext) -> Subtree:
    """Post-order DFS: build a Subtree for ``node``.

    Local frame convention: ``node``'s top-left is placed at (0, 0). The
    returned Subtree is in this frame; the parent caller translates it.
    """
    # --- Freeze block detection ---
    block = ctx.dimension_overrides.get(id(node))
    is_block_root = block is not None and id(node) == block.root_id

    pairs, all_side, fan_active = _filtered_input_pairs(node, ctx)

    if is_block_root and not pairs:
        # Block root with no in-filter external inputs: opaque rigid leaf.
        # Members keep their stored relative offsets; root sits at (0, 0).
        nodes = {id(block.root): (0, 0)}
        for member in block.members:
            if id(member) == block.root_id:
                continue
            dx_off, dy_off = block.offsets.get(id(member), (0, 0))
            nodes[id(member)] = (dx_off, dy_off)
        bbox = _block_local_extents(block)
        return Subtree(
            bbox=bbox,
            anchor_out=(0, 0),
            nodes=nodes,
            root_node=node,
        )

    if not pairs:
        # Plain leaf
        w = node.screenWidth()
        h = node.screenHeight()
        return Subtree(
            bbox=(0, 0, w, h),
            anchor_out=(0, 0),
            nodes={id(node): (0, 0)},
            root_node=node,
        )

    # Recurse on each child. Children are returned with root at (0, 0) in their
    # own local frame.
    actual_slots = [slot for slot, _ in pairs]
    inputs = [inp for _, inp in pairs]
    n = len(inputs)
    child_subtrees = [layout(inp, ctx) for inp in inputs]

    h_scale = ctx.h_scale_for(node)
    v_scale = ctx.v_scale_for(node)
    scheme = ctx.scheme_for(node)

    side_margins_h = [
        int(node_layout._horizontal_margin(node, slot) * h_scale)
        for slot in actual_slots
    ]
    # Use the prefs' reference node-count so ``_subtree_margin`` returns a
    # value independent of the layout-scope size. Without this the margin
    # scales as ``sqrt(node_count) / sqrt(reference_count)``, so running
    # ``layout_upstream`` from a subtree root produces tighter spacing
    # than running from the full graph's root — same DAG, different
    # spacing depending on where you start, which is surprising.
    margin_reference_count = node_layout_prefs.prefs_singleton.get(
        "scaling_reference_count"
    )
    side_margins_v = [
        int(
            node_layout._subtree_margin(
                node, slot, margin_reference_count, mode_multiplier=scheme,
            )
            * v_scale
        )
        for slot in actual_slots
    ]

    node_w = node.screenWidth()
    node_h = node.screenHeight()
    snap = ctx.snap_threshold

    # When the consumer is a freeze block root, side-input X allocation must
    # start from the block's right edge (not the root tile's), and input
    # bands must clear the block's upper edge (not the root tile's top), or
    # children collide with the block's non-root members.
    if is_block_root:
        block_left, block_top, block_right, block_bottom = _block_local_extents(block)
        consumer_right = max(node_w, block_right)
        consumer_left = min(0, block_left)
        consumer_top = min(0, block_top)
    else:
        block_left = block_right = 0
        block_top = 0
        block_bottom = node_h
        consumer_right = node_w
        consumer_left = 0
        consumer_top = 0

    # ----- Determine fan-mode parameters -----
    is_fan = fan_active and n >= 3
    mask_count = sum(1 for slot, _ in pairs if node_layout._is_mask_input(node, slot))

    # ----- Y placement: compute child Y offsets in the parent frame. -----
    # In the parent frame, node's top-left is (0, 0). Children sit at smaller Y.
    if is_fan:
        # Mask(s) at front, non-mask after the reorder. All non-mask share the
        # same Y row; masks each get their own band but typically a single row too.
        non_mask_start = mask_count
        raw_gap_b = node_layout.vertical_gap_between(
            inputs[non_mask_start], node, snap, scheme
        )
        gap_to_fan = max(snap - 1, int(raw_gap_b * v_scale))
        gap_to_fan = max(gap_to_fan, side_margins_v[non_mask_start])
        # Each non-mask child placed so its bottom sits at consumer_top - gap.
        # consumer_top accounts for any block-root upper extent.
        y_positions = [0] * n
        for i in range(non_mask_start, n):
            y_positions[i] = consumer_top - gap_to_fan - inputs[i].screenHeight()
        for i in range(mask_count):
            raw_gap_mask = node_layout.vertical_gap_between(
                inputs[i], node, snap, scheme
            )
            gap_mask = max(snap - 1, int(raw_gap_mask * v_scale))
            gap_mask = max(gap_mask, side_margins_v[i])
            y_positions[i] = consumer_top - gap_mask - inputs[i].screenHeight()
    else:
        # Staircase: backward walk so input[n-1] is closest to the consumer.
        raw_gap_closest = node_layout.vertical_gap_between(
            inputs[n - 1], node, snap, scheme
        )
        gap_closest = max(snap - 1, int(raw_gap_closest * v_scale))
        # The standard chain spacing (vertical_gap_between) is fairly tight.
        # Bump to the subtree margin in three cases where the upstream is
        # logically separated from the consumer (a routing-Dot consumer is
        # always a separator between upstream and the next consumer below):
        #   - n > 1: there are sibling staircase bands (use subtree margin).
        #   - all_side: every input is a side input (likewise).
        #   - consumer is itself a Dot: it acts as a routing element, so
        #     the upstream above it should sit at the standard subtree
        #     spacing above the Dot, not at chain spacing.
        if n > 1 or all_side or node.Class() == 'Dot':
            gap_closest = max(gap_closest, side_margins_v[n - 1])
        # bottom_y_per_slot is the Y of the bottom of each child SUBTREE BBOX
        # (in the parent frame) — bands stack upward.  child.bbox is in the
        # child's local frame with root at (0, 0). In that frame the bbox
        # height is bbox[3] - bbox[1], with the root sitting somewhere inside
        # (typically bbox[1]==0 means root is at the top of its own bbox).
        # consumer_top accounts for any block-root upper extent.
        bottom_y = [0] * n
        bottom_y[n - 1] = consumer_top - gap_closest
        for i in range(n - 2, -1, -1):
            child_h = child_subtrees[i + 1].bbox[3] - child_subtrees[i + 1].bbox[1]
            bottom_y[i] = bottom_y[i + 1] - child_h - side_margins_v[i + 1]
        # Y of each input root: bottom-of-band - root_height
        # The child's bbox bottom (in child-local frame) is bbox[3]; root is at (0, 0).
        # We want child root translated so child bbox bottom in parent frame == bottom_y[i].
        # That means dy + child.bbox[3] == bottom_y[i]  =>  dy = bottom_y[i] - child.bbox[3].
        y_positions = [
            bottom_y[i] - child_subtrees[i].bbox[3] for i in range(n)
        ]

        # When a side-input slot's root IS a Dot, position the Dot at the
        # consumer's mid-Y instead of the staircase Y. Same rule as the
        # auto-inserted routing dots — the Dot is the bottom-of-subtree
        # routing element. The subtree above the Dot rides along (its
        # relative offsets within the subtree's local frame are unchanged).
        for i in range(n):
            if i == 0 and not all_side:
                continue
            if inputs[i].Class() != 'Dot':
                continue
            y_positions[i] = (node_h - inputs[i].screenHeight()) // 2

    # ----- X placement -----
    # consumer_right / consumer_left bound the allocation on each side; for a
    # plain node they're the tile edges, for a freeze-block root they're the
    # block's right/left edges so siblings clear the block's full extent.
    if all_side:
        x_positions = []
        cur_alloc = consumer_right + side_margins_h[0]
        for i in range(n):
            child_w_total = child_subtrees[i].bbox[2] - child_subtrees[i].bbox[0]
            child_root_offset_in_alloc = -child_subtrees[i].bbox[0]
            x_positions.append(cur_alloc + child_root_offset_in_alloc)
            if i + 1 < n:
                cur_alloc += child_w_total + side_margins_h[i + 1]
    elif n == 1:
        x_positions = [
            node_layout._center_x(inputs[0].screenWidth(), 0, node_w)
        ]
    elif n == 2:
        root_x_0 = node_layout._center_x(inputs[0].screenWidth(), 0, node_w)
        cur_alloc = consumer_right + side_margins_h[1]
        child_w_total_1 = child_subtrees[1].bbox[2] - child_subtrees[1].bbox[0]
        child_root_offset_1 = -child_subtrees[1].bbox[0]
        _ = child_w_total_1  # silence — used implicitly via bbox below
        x_positions = [root_x_0, cur_alloc + child_root_offset_1]
    elif is_fan:
        non_mask_start = mask_count
        x_positions = [0] * n
        root_x_b = node_layout._center_x(
            inputs[non_mask_start].screenWidth(), 0, node_w
        )
        x_positions[non_mask_start] = root_x_b
        # Allocation right edge after B: max(consumer right, B's bbox right).
        b_alloc_left = root_x_b + child_subtrees[non_mask_start].bbox[0]
        b_alloc_right = b_alloc_left + (
            child_subtrees[non_mask_start].bbox[2]
            - child_subtrees[non_mask_start].bbox[0]
        )
        cur_alloc = max(consumer_right, b_alloc_right) + (
            side_margins_h[non_mask_start + 1] if non_mask_start + 1 < n else 0
        )
        for i in range(non_mask_start + 1, n):
            child_w_total = child_subtrees[i].bbox[2] - child_subtrees[i].bbox[0]
            child_root_offset = -child_subtrees[i].bbox[0]
            x_positions[i] = cur_alloc + child_root_offset
            if i + 1 < n:
                cur_alloc += child_w_total + side_margins_h[i + 1]
        # Mask(s) placed LEFT of consumer: alloc band ends at consumer_left - mask_gap_h.
        for i in range(mask_count):
            mask_gap_h = side_margins_h[i]
            child_w_total = child_subtrees[i].bbox[2] - child_subtrees[i].bbox[0]
            child_root_offset = -child_subtrees[i].bbox[0]
            alloc_left = consumer_left - mask_gap_h - child_w_total
            x_positions[i] = alloc_left + child_root_offset
    else:
        # n >= 3 staircase
        root_x_0 = node_layout._center_x(inputs[0].screenWidth(), 0, node_w)
        x_positions = [root_x_0]
        cur_alloc = consumer_right + side_margins_h[1]
        for i in range(1, n):
            child_w_total = child_subtrees[i].bbox[2] - child_subtrees[i].bbox[0]
            child_root_offset = -child_subtrees[i].bbox[0]
            x_positions.append(cur_alloc + child_root_offset)
            if i + 1 < n:
                cur_alloc += child_w_total + side_margins_h[i + 1]

    # ----- Insert routing Dots for side inputs (non-primary). -----
    # Reuse the same logic as legacy: deselect-everything-then-create avoids
    # auto-connection.  After insertion, replace inputs[i] with the dot but
    # keep the dot's upstream subtree at (x_positions[i], y_positions[i]).
    new_dots: dict[int, object] = {}  # i -> dot node (for those replaced)

    def _is_side_index(i: int) -> bool:
        if all_side:
            return True
        if is_fan:
            return True  # fan: dots for all
        return i > 0

    for selected in nuke.selectedNodes():
        with contextlib.suppress(KeyError, AttributeError):
            selected['selected'].setValue(False)

    for i in range(n):
        if not _is_side_index(i):
            continue
        if inputs[i].Class() == 'Dot':
            continue
        try:
            dot = nuke.nodes.Dot()
        except AttributeError:
            # Stub-mode fallback (no nuke.nodes).
            dot = None
        if dot is None:
            continue
        for auto_slot in range(dot.inputs()):
            dot.setInput(auto_slot, None)
        dot.setInput(0, inputs[i])
        node.setInput(actual_slots[i], dot)
        new_dots[i] = dot

    # ----- Merge children + place dots into this node's frame. -----
    # Translate each child by (x_positions[i], y_positions[i]) and merge.
    nodes_dict: dict[int, tuple[int, int]] = {id(node): (0, 0)}
    bbox_left, bbox_top, bbox_right, bbox_bottom = 0, 0, node_w, node_h
    anchor_in_per_slot: dict[int, tuple[int, int]] = {}

    for i, child in enumerate(child_subtrees):
        translated = _translate(child, x_positions[i], y_positions[i])
        nodes_dict.update(translated.nodes)
        bbox_left = min(bbox_left, translated.bbox[0])
        bbox_top = min(bbox_top, translated.bbox[1])
        bbox_right = max(bbox_right, translated.bbox[2])
        bbox_bottom = max(bbox_bottom, translated.bbox[3])
        anchor_in_per_slot[actual_slots[i]] = translated.anchor_out

        # If a routing dot was inserted at slot i, position it now.
        # The routing dot is the bottom-of-subtree node — it should be
        # centered in Y on the consuming node and centered in X on its
        # input subtree's root (anchor_out_x + upstream_width/2). For fan
        # mode the visualization is different (dots in a row above the
        # consumer), so we keep the legacy fan-mode placement.
        if i in new_dots:
            dot = new_dots[i]
            dot_w = dot.screenWidth()
            dot_h = dot.screenHeight()
            child_root_x_in_parent = translated.anchor_out[0]
            actual_upstream_w = inputs[i].screenWidth()
            dot_center_x = child_root_x_in_parent + actual_upstream_w // 2
            # Fan mode places dots in a row above the consumer; staircase
            # mode centers each dot in Y on the consumer regardless of its
            # staircase position. The subtree above each dot keeps its
            # staircase Y.
            dot_y = (
                -(snap - 1) - dot_h if is_fan else (node_h - dot_h) // 2
            )
            dot_x = dot_center_x - dot_w // 2
            nodes_dict[id(dot)] = (dot_x, dot_y)
            bbox_left = min(bbox_left, dot_x)
            bbox_top = min(bbox_top, dot_y)
            bbox_right = max(bbox_right, dot_x + dot_w)
            bbox_bottom = max(bbox_bottom, dot_y + dot_h)

    # If this node is a freeze block root with external inputs, fold the rigid
    # block geometry into the result: add non-root members at their stored
    # offsets and widen the bbox to include the full block extent.
    if is_block_root:
        for member in block.members:
            if id(member) == block.root_id:
                continue
            dx_off, dy_off = block.offsets.get(id(member), (0, 0))
            nodes_dict[id(member)] = (dx_off, dy_off)
            bbox_left = min(bbox_left, dx_off)
            bbox_top = min(bbox_top, dy_off)
            bbox_right = max(bbox_right, dx_off + member.screenWidth())
            bbox_bottom = max(bbox_bottom, dy_off + member.screenHeight())
        # Reserve at least the block's pre-baked extents on all four sides.
        bbox_left = min(bbox_left, block_left)
        bbox_top = min(bbox_top, block_top)
        bbox_right = max(bbox_right, block_right)
        bbox_bottom = max(bbox_bottom, block_bottom)

    return Subtree(
        bbox=(bbox_left, bbox_top, bbox_right, bbox_bottom),
        anchor_out=(0, 0),
        nodes=nodes_dict,
        root_node=node,
        anchor_in_per_slot=anchor_in_per_slot,
    )


# ---------------------------------------------------------------------------
# Horizontal packing — spine (input[0] chain) extends rightward from root,
# side inputs stack vertically above each spine node.
# ---------------------------------------------------------------------------

def layout_horizontal(root, ctx: LayoutContext) -> Subtree:
    """Lay out a horizontal chain rooted at ``root``.

    The spine is the chain of ``input[0]`` ancestors whose ids are in
    ``ctx.spine_set``.  ``root`` is the most-downstream spine node and is
    placed at (0, 0) in the returned Subtree's local frame.  Earlier spine
    nodes are placed leftward (more negative X).  Each spine node's side
    inputs (slots >= 1) are laid out vertically above it.
    """
    prefs = node_layout_prefs.prefs_singleton
    scheme = ctx.scheme_for(root)
    step_x = int(prefs.get("horizontal_subtree_gap") * scheme)
    side_v_gap = prefs.get("horizontal_side_vertical_gap")

    # Build spine (rightmost first): root, root.input(0), input(0).input(0), ...
    spine_nodes = []
    cursor = root
    spine_set = ctx.spine_set
    while cursor is not None:
        if spine_set is not None and id(cursor) not in spine_set:
            break
        spine_nodes.append(cursor)
        cursor = cursor.input(0)

    nodes_dict: dict[int, tuple[int, int]] = {}
    bbox_l, bbox_t, bbox_r, bbox_b = 0, 0, 0, 0
    cur_y = 0

    # Side-input recursion context shared by the per-spine-node pre-pass
    # below and by the leftward-extension code further down.
    side_ctx = LayoutContext(
        snap_threshold=ctx.snap_threshold,
        node_count=ctx.node_count,
        node_filter=ctx.node_filter,
        per_node_scheme=ctx.per_node_scheme,
        per_node_h_scale=ctx.per_node_h_scale,
        per_node_v_scale=ctx.per_node_v_scale,
        dimension_overrides=ctx.dimension_overrides,
        spine_set=None,
        horizontal_root_id=None,
        all_member_ids=ctx.all_member_ids,
        horizontal_seeds=ctx.horizontal_seeds,
        all_horizontal_ids=ctx.all_horizontal_ids,
    )

    h_gap = int(prefs.get("horizontal_subtree_gap") * scheme)

    # ----- Pre-pass: build each spine node's "segment" in spine-tile-local
    # frame (spine tile at (0, cur_y); side inputs above it). The segment's
    # bbox tells the spine placement how much horizontal room it needs, so
    # adjacent spine nodes can step apart by at least max(step_x, side input
    # widths + gap). Without this, wide side input subtrees overlap with
    # neighbouring spine nodes' columns.
    segments: list[dict] = []
    for spine_node in spine_nodes:
        seg_nodes: dict[int, tuple[int, int]] = {
            id(spine_node): (0, cur_y),
        }
        seg_l = 0
        seg_t = cur_y
        seg_r = spine_node.screenWidth()
        seg_b = cur_y + spine_node.screenHeight()

        slot_count = spine_node.inputs()
        side_slot_pairs = []
        for slot in range(1, slot_count):
            inp = spine_node.input(slot)
            if inp is None:
                continue
            if ctx.node_filter is not None and not node_layout._passes_node_filter(
                inp, ctx.node_filter
            ):
                continue
            side_slot_pairs.append((slot, inp))

        target_bbox_bottom = -side_v_gap
        if len(side_slot_pairs) == 1:
            _slot, side_root = side_slot_pairs[0]
            child_subtree = layout(side_root, side_ctx)
            center_x = spine_node.screenWidth() // 2
            child_root_x = center_x - side_root.screenWidth() // 2
            translated = _translate(
                child_subtree,
                child_root_x,
                target_bbox_bottom - child_subtree.bbox[3],
            )
            seg_nodes.update(translated.nodes)
            seg_l = min(seg_l, translated.bbox[0])
            seg_t = min(seg_t, translated.bbox[1])
            seg_r = max(seg_r, translated.bbox[2])
            seg_b = max(seg_b, translated.bbox[3])
        elif side_slot_pairs:
            cur_alloc = spine_node.screenWidth()
            for _slot, side_root in side_slot_pairs:
                child_subtree = layout(side_root, side_ctx)
                child_w_total = child_subtree.bbox[2] - child_subtree.bbox[0]
                child_root_x = cur_alloc - child_subtree.bbox[0]
                translated = _translate(
                    child_subtree,
                    child_root_x,
                    target_bbox_bottom - child_subtree.bbox[3],
                )
                seg_nodes.update(translated.nodes)
                seg_l = min(seg_l, translated.bbox[0])
                seg_t = min(seg_t, translated.bbox[1])
                seg_r = max(seg_r, translated.bbox[2])
                seg_b = max(seg_b, translated.bbox[3])
                cur_alloc += child_w_total + h_gap

        segments.append({
            "nodes": seg_nodes,
            "bbox": (seg_l, seg_t, seg_r, seg_b),
        })

    # Spine placement: walk left-to-right (i=0 is rightmost root).
    # spine_x[i] is bounded BOTH by the standard step_x rule AND by the
    # constraint that segment[i]'s right edge must be at least h_gap to the
    # left of segment[i-1]'s left edge — so wide side input subtrees push
    # spine nodes further apart instead of colliding.
    spine_x_per_index: list[int] = []
    for i, spine_node in enumerate(spine_nodes):
        if i == 0:
            spine_x = 0
        else:
            prev_x = spine_x_per_index[i - 1]
            prev_seg_left_world = prev_x + segments[i - 1]["bbox"][0]
            cur_seg_right_local = segments[i]["bbox"][2]
            adaptive_x = prev_seg_left_world - cur_seg_right_local - h_gap
            standard_x = prev_x - step_x - spine_node.screenWidth()
            spine_x = min(adaptive_x, standard_x)
        spine_x_per_index.append(spine_x)

        # Translate this segment's nodes into the world frame.
        seg = segments[i]
        for nid, (lx, ly) in seg["nodes"].items():
            nodes_dict[nid] = (spine_x + lx, ly)
        seg_bbox = seg["bbox"]
        bbox_l = min(bbox_l, spine_x + seg_bbox[0])
        bbox_t = min(bbox_t, seg_bbox[1])
        bbox_r = max(bbox_r, spine_x + seg_bbox[2])
        bbox_b = max(bbox_b, seg_bbox[3])

    # Leftward extension: input(0) of the leftmost spine node, when non-spine
    # and eligible, is laid out as its own subtree (the dispatcher handles
    # mode). A routing Dot is inserted between the leftmost spine node and
    # its input(0) — unless input(0) is already a Dot — so the wire turn at
    # the spine boundary stays clean. The Dot sits centered in Y on the
    # leftmost spine and centered in X on its input.
    if spine_nodes:
        leftmost = spine_nodes[-1]
        leftmost_x = spine_x_per_index[-1]
        zero = leftmost.input(0)
        zero_eligible = (
            zero is not None
            and (spine_set is None or id(zero) not in spine_set)
            and (
                ctx.node_filter is None
                or node_layout._passes_node_filter(zero, ctx.node_filter)
            )
        )
        if zero_eligible:
            zero_subtree = layout(zero, side_ctx)
            # Decide whether to insert a routing Dot between the spine and
            # the input(0) subtree. Skip if input(0) is itself a Dot (no
            # need to add another). Per the user's invariant, the boundary
            # always wants a Dot for routing.
            inserted_dot = None
            if zero.Class() != 'Dot':
                try:
                    new_dot = nuke.nodes.Dot()
                except AttributeError:
                    new_dot = None
                if new_dot is not None:
                    for auto_slot in range(new_dot.inputs()):
                        new_dot.setInput(auto_slot, None)
                    new_dot.setInput(0, zero)
                    leftmost.setInput(0, new_dot)
                    inserted_dot = new_dot

            # Right edge of the leftward extension: clear the spine tile by
            # step_x, AND clear the leftmost spine's segment bbox (which
            # extends further left when its side input subtrees contain
            # horizontal nodes) by h_gap.
            leftmost_seg_left_world = (
                leftmost_x + segments[-1]["bbox"][0]
            )
            target_zero_bbox_right = min(
                leftmost_x - step_x,
                leftmost_seg_left_world - h_gap,
            )
            if inserted_dot is not None:
                # The new Dot acts as the routing element at the spine
                # boundary: centred-in-Y on the leftmost spine tile,
                # centred-in-X on the input subtree's root tile. The
                # input subtree itself sits ABOVE the Dot, not at the
                # Dot's Y, so they don't overlap.
                dot_w = inserted_dot.screenWidth()
                dot_h = inserted_dot.screenHeight()
                dot_y = (
                    cur_y + leftmost.screenHeight() // 2 - dot_h // 2
                )
                # Position zero's tile so its right edge clears the spine
                # by step_x; the Dot sits to the right of zero's column,
                # centred-in-X on zero's tile.
                zero_root_x = target_zero_bbox_right - zero_subtree.bbox[2]
                dot_x = zero_root_x + zero.screenWidth() // 2 - dot_w // 2
                nodes_dict[id(inserted_dot)] = (dot_x, dot_y)
                bbox_l = min(bbox_l, dot_x)
                bbox_t = min(bbox_t, dot_y)
                bbox_r = max(bbox_r, dot_x + dot_w)
                bbox_b = max(bbox_b, dot_y + dot_h)
                # Place zero subtree so its bbox bottom sits side_v_gap
                # above the Dot's top — i.e., the Dot is the bottom of the
                # leftward column.
                target_zero_root_y = (
                    dot_y - side_v_gap - zero_subtree.bbox[3]
                )
            else:
                # input(0) was already a Dot; treat that Dot as the routing
                # element and centre it in Y on the leftmost spine tile.
                # zero IS the dot here, so zero_subtree.nodes[id(zero)] is
                # the Dot tile at (0, 0) in local frame.
                target_zero_root_y = (
                    cur_y + leftmost.screenHeight() // 2 - zero.screenHeight() // 2
                )
                zero_root_x = target_zero_bbox_right - zero_subtree.bbox[2]

            translated = _translate(
                zero_subtree,
                zero_root_x,
                target_zero_root_y,
            )
            nodes_dict.update(translated.nodes)
            bbox_l = min(bbox_l, translated.bbox[0])
            bbox_t = min(bbox_t, translated.bbox[1])
            bbox_r = max(bbox_r, translated.bbox[2])
            bbox_b = max(bbox_b, translated.bbox[3])

    return Subtree(
        bbox=(bbox_l, bbox_t, bbox_r, bbox_b),
        anchor_out=(0, cur_y),
        nodes=nodes_dict,
        root_node=root,
    )


# ---------------------------------------------------------------------------
# Application — write x/y back to Nuke nodes from a Subtree.
# ---------------------------------------------------------------------------

def apply_subtree(subtree: Subtree, anchor_x: int, anchor_y: int):
    """Translate ``subtree`` so its anchor_out lands at (anchor_x, anchor_y),
    then call ``setXYpos`` on every node in the dict.

    Looks up each id() in the live Nuke graph by scanning subtree.nodes plus
    any per-node objects we cached during recursion.  Since we only stored
    ``id(node)`` keys we need a side-channel to resolve those ids back to
    objects — handled by ``_id_to_node_map`` populated during the recursion.
    """
    raise NotImplementedError("Use apply_with_lookup() — apply_subtree needs id-map.")


def apply_with_lookup(
    subtree: Subtree, anchor_x: int, anchor_y: int, id_to_node: dict[int, object]
):
    """Place every node in ``subtree`` so the root sits at (anchor_x, anchor_y)."""
    dx = anchor_x - subtree.anchor_out[0]
    dy = anchor_y - subtree.anchor_out[1]
    for node_id, (lx, ly) in subtree.nodes.items():
        node_obj = id_to_node.get(node_id)
        if node_obj is None:
            continue
        node_obj.setXpos(lx + dx)
        node_obj.setYpos(ly + dy)


def collect_id_to_node(subtree: Subtree, extra_nodes=()) -> dict[int, object]:
    """Build id->node map. Walks ``root_node`` plus any extras provided.

    The recursion stores id() keys in ``subtree.nodes`` but we also keep
    references to actual node objects via ``root_node`` on each Subtree. To
    resolve all ids we walk the whole upstream of ``subtree.root_node``
    using the same get_inputs traversal.
    """
    id_map: dict[int, object] = {}

    def _walk(node):
        if node is None or id(node) in id_map:
            return
        id_map[id(node)] = node
        for inp in node_layout.get_inputs(node):
            _walk(inp)

    _walk(subtree.root_node)
    for extra in extra_nodes:
        _walk(extra)
    return id_map


# ---------------------------------------------------------------------------
# Engine — wires up the dispatcher.
# ---------------------------------------------------------------------------

@node_layout_engine.register("bbox")
class BboxEngine(node_layout_engine.LayoutEngine):

    # ------------------------------------------------------------------
    # layout_upstream — selected node anchors, all upstream gets recomposed.
    # ------------------------------------------------------------------
    def layout_upstream(self, scheme_multiplier=None):
        node_layout._clear_color_cache()
        current_group = nuke.lastHitGroup()
        root = nuke.selectedNode()

        nuke.Undo.name("Layout Upstream (bbox)")
        nuke.Undo.begin()
        try:
            with current_group:
                self._run_upstream(root, scheme_multiplier, current_group)
        except Exception:
            nuke.Undo.cancel()
            raise
        else:
            nuke.Undo.end()

    def _run_upstream(self, root, scheme_multiplier, current_group):
        # Phase 0: gather upstream + freeze preprocessing.
        all_upstream = node_layout.collect_subtree_nodes(root)
        freeze_scope = node_layout._expand_scope_for_freeze_groups(
            all_upstream, current_group
        )
        freeze_group_map, _ = node_layout._detect_freeze_groups(freeze_scope)
        freeze_blocks, dimension_overrides, all_non_root_ids, all_member_ids = (
            node_layout._build_freeze_blocks(freeze_group_map)
        )

        original_nodes = node_layout.collect_subtree_nodes(root)
        bbox_before = node_layout.compute_node_bounding_box(original_nodes)

        # Phase 1: persistent diamond Dots.
        node_layout.insert_dot_nodes(root)

        # Refresh upstream walk after dot insertion.
        upstream_after_dots = node_layout.collect_subtree_nodes(root)
        node_count = len(upstream_after_dots)

        # Phase 2: per-node scheme/scale resolution.
        prefs = node_layout_prefs.prefs_singleton
        per_node_scheme = {}
        per_node_h_scale = {}
        per_node_v_scale = {}
        for n in upstream_after_dots:
            stored = node_layout_state.read_node_state(n)
            if scheme_multiplier is not None:
                per_node_scheme[id(n)] = scheme_multiplier
            else:
                per_node_scheme[id(n)] = node_layout_state.scheme_name_to_multiplier(
                    stored["scheme"], prefs
                )
            per_node_h_scale[id(n)] = stored["h_scale"]
            per_node_v_scale[id(n)] = stored["v_scale"]

        snap = node_layout.get_dag_snap_threshold()

        # Phase 3: build LayoutContext. Mode detection now happens per-node
        # inside the dispatcher (``layout``); the top level always anchors on
        # the originally selected node and lets the recursion compose vertical
        # and horizontal subtrees as needed.
        original_selected = root
        if all_non_root_ids:
            vertical_filter = {n for n in upstream_after_dots
                               if id(n) not in all_non_root_ids}
        else:
            vertical_filter = None

        ctx = LayoutContext(
            snap_threshold=snap,
            node_count=node_count,
            node_filter=vertical_filter,
            per_node_scheme=per_node_scheme,
            per_node_h_scale=per_node_h_scale,
            per_node_v_scale=per_node_v_scale,
            dimension_overrides=dimension_overrides,
            all_member_ids=all_member_ids,
        )

        # Phase 4: run recursion. The dispatcher picks vertical vs horizontal
        # based on each node's stored mode, so a vertical consumer with a
        # horizontal input subtree composes correctly.
        subtree = layout(root, ctx)

        # Phase 5: apply. Anchor: original_selected stays where it is.
        id_to_node = collect_id_to_node(
            subtree,
            extra_nodes=[m for b in freeze_blocks for m in b.members],
        )
        if id(root) in subtree.nodes:
            local_x, local_y = subtree.nodes[id(root)]
            dx = root.xpos() - local_x
            dy = root.ypos() - local_y
        else:
            dx = root.xpos() - subtree.anchor_out[0]
            dy = root.ypos() - subtree.anchor_out[1]

        for node_id, (lx, ly) in subtree.nodes.items():
            obj = id_to_node.get(node_id)
            if obj is None:
                continue
            obj.setXpos(lx + dx)
            obj.setYpos(ly + dy)

        # Phase 5b: place/reposition routing Dots for every horizontal subtree
        # the dispatcher entered. The helper finds each spine root's downstream
        # consumer in the live DAG and inserts/repositions a Dot between them.
        for seed in ctx.horizontal_seeds:
            node_layout._place_output_dot_for_horizontal_root(
                seed, current_group, snap, prefs.get("normal_multiplier"),
            )

        # (Former "Phase 6c" deleted — the recursion now handles the consumer's
        # mixed vertical+horizontal inputs natively. A vertical consumer with
        # one horizontal input subtree and one vertical input subtree composes
        # both via the dispatcher; nothing to do here.)

        # Phase 7: restore freeze block member positions (their offsets are
        # baked into nodes_dict, but if any block root was a leaf, we already
        # placed them as a unit — this is a safety net for blocks the
        # recursion didn't touch via nodes_dict).
        for block in freeze_blocks:
            if id(block.root) not in subtree.nodes:
                continue
            block.restore_positions()

        # Phase 7b: lay out non-frozen subtrees that feed into freeze blocks
        # from outside.  Each external input to a NON-root member is laid out
        # vertically and placed above its connecting block member (which is
        # already at its final pos after restore_positions).  External inputs
        # to the BLOCK ROOT are handled in-recursion (the root is processed
        # as a normal node with its in-filter inputs as side inputs).
        for block in freeze_blocks:
            external_inputs = block.get_external_inputs(node_layout.get_inputs)
            for entry_node, connecting_member in external_inputs:
                if id(connecting_member) == block.root_id:
                    continue
                upstream_subtree_nodes = node_layout.collect_subtree_nodes(entry_node)
                upstream_filter = set(upstream_subtree_nodes)
                upstream_ctx = LayoutContext(
                    snap_threshold=snap,
                    node_count=len(upstream_subtree_nodes),
                    node_filter=upstream_filter,
                    per_node_scheme=per_node_scheme,
                    per_node_h_scale=per_node_h_scale,
                    per_node_v_scale=per_node_v_scale,
                    dimension_overrides=dimension_overrides,
                    all_member_ids=all_member_ids,
                )
                entry_subtree = layout(entry_node, upstream_ctx)
                # Place entry centered above connecting_member.
                entry_h = entry_subtree.bbox[3] - entry_subtree.bbox[1]
                raw_gap = node_layout.vertical_gap_between(
                    entry_node, connecting_member, snap,
                    scheme_multiplier=per_node_scheme.get(
                        id(entry_node), prefs.get("normal_multiplier")
                    ),
                )
                gap = max(snap - 1, raw_gap)
                entry_x = node_layout._center_x(
                    entry_node.screenWidth(),
                    connecting_member.xpos(),
                    connecting_member.screenWidth(),
                )
                # The bottom of entry's bbox should sit `gap` above connecting member's top.
                bbox_bottom_target = connecting_member.ypos() - gap
                # entry_subtree root sits at (0,0) in its local frame.
                # We want the root placed at (entry_x, ?) such that
                # bbox_bottom in world = bbox_bottom_target.
                # entry_subtree.nodes[id(entry_node)] = (0, 0) in local frame;
                # bbox bottom in local = entry_subtree.bbox[3].
                # World root y = (bbox_bottom_target - entry_subtree.bbox[3])
                root_y = bbox_bottom_target - entry_subtree.bbox[3]
                upstream_id_map = collect_id_to_node(entry_subtree)
                # Translate so entry_node lands at (entry_x, root_y).
                local_root_x, local_root_y = entry_subtree.nodes[id(entry_node)]
                ux = entry_x - local_root_x
                uy = root_y - local_root_y
                _ = entry_h
                for nid, (lx, ly) in entry_subtree.nodes.items():
                    obj = upstream_id_map.get(nid)
                    if obj is None:
                        continue
                    obj.setXpos(lx + ux)
                    obj.setYpos(ly + uy)

        # Phase 8: state write-back.
        final_nodes = node_layout.collect_subtree_nodes(original_selected)
        for n in final_nodes:
            stored = node_layout_state.read_node_state(n)
            n_scheme = per_node_scheme.get(id(n), prefs.get("normal_multiplier"))
            stored["scheme"] = node_layout_state.multiplier_to_scheme_name(
                n_scheme, prefs
            )
            stored["mode"] = (
                "horizontal" if id(n) in ctx.all_horizontal_ids else "vertical"
            )
            node_layout_state.write_node_state(n, stored)

        # Phase 9: push surrounding nodes.
        final_node_ids = {id(n) for n in final_nodes}
        bbox_after_nodes = list(final_nodes)
        for block in freeze_blocks:
            for member in block.members:
                if id(member) not in final_node_ids:
                    bbox_after_nodes.append(member)
                    final_node_ids.add(id(member))
        bbox_after = node_layout.compute_node_bounding_box(bbox_after_nodes)
        if bbox_before is not None and bbox_after is not None:
            node_layout.push_nodes_to_make_room(
                final_node_ids, bbox_before, bbox_after,
                current_group=current_group,
                freeze_blocks=freeze_blocks,
            )

    def _find_horizontal_ancestor(self, root, all_member_ids):
        """BFS upstream looking for a node whose stored mode is 'horizontal'.

        Returns the ancestor node, or None.
        """
        if node_layout._hides_inputs(root):
            return None
        queue = [root.input(s) for s in range(root.inputs())
                 if root.input(s) is not None]
        visited = {id(root)}
        while queue:
            cur = queue.pop(0)
            if id(cur) in visited:
                continue
            visited.add(id(cur))
            if id(cur) in all_member_ids:
                if not node_layout._hides_inputs(cur):
                    for s in range(cur.inputs()):
                        nxt = cur.input(s)
                        if nxt is not None and id(nxt) not in visited:
                            queue.append(nxt)
                continue
            if node_layout_state.read_node_state(cur).get("mode") == "horizontal":
                return cur
            if not node_layout._hides_inputs(cur):
                for s in range(cur.inputs()):
                    nxt = cur.input(s)
                    if nxt is not None and id(nxt) not in visited:
                        queue.append(nxt)
        return None

    def _build_spine_set(self, root, all_member_ids):
        """Walk input(0) collecting horizontal-mode nodes."""
        spine = set()
        cursor = root
        while cursor is not None:
            if id(cursor) in all_member_ids and id(cursor) != id(root):
                break
            state = node_layout_state.read_node_state(cursor)
            if state.get("mode") != "horizontal":
                # The root may be the horizontal seed even if its mode hasn't been
                # written yet — include it.
                if cursor is root:
                    spine.add(id(cursor))
                break
            spine.add(id(cursor))
            cursor = cursor.input(0)
        return spine

    # ------------------------------------------------------------------
    # layout_selected — multiple selected roots, each laid out independently
    # within the selection.  Simplification: run vertical recursion per root
    # using the selected set as node_filter.
    # ------------------------------------------------------------------
    def layout_selected(self, scheme_multiplier=None):
        node_layout._clear_color_cache()
        current_group = nuke.lastHitGroup()
        selected = nuke.selectedNodes()
        if len(selected) < 2:
            return

        nuke.Undo.name("Layout Selected (bbox)")
        nuke.Undo.begin()
        try:
            with current_group:
                self._run_selected(selected, scheme_multiplier, current_group)
        except Exception:
            nuke.Undo.cancel()
            raise
        else:
            nuke.Undo.end()

    def _run_selected(self, selected, scheme_multiplier, current_group):
        node_filter = set(selected)
        expanded = node_layout._expand_scope_for_freeze_groups(
            list(node_filter), current_group
        )
        node_filter = set(expanded)
        selected = list(node_filter)
        freeze_group_map, _ = node_layout._detect_freeze_groups(list(node_filter))
        freeze_blocks, dimension_overrides, all_non_root_ids, all_member_ids = (
            node_layout._build_freeze_blocks(freeze_group_map)
        )

        bbox_before = node_layout.compute_node_bounding_box(selected)

        if all_non_root_ids:
            node_filter = {n for n in node_filter if id(n) not in all_non_root_ids}
            selected = [n for n in selected if id(n) not in all_non_root_ids]

        roots = node_layout.find_selection_roots(selected)
        roots.sort(key=lambda n: n.xpos())

        prefs = node_layout_prefs.prefs_singleton
        per_node_scheme = {}
        per_node_h_scale = {}
        per_node_v_scale = {}
        for n in selected:
            stored = node_layout_state.read_node_state(n)
            if scheme_multiplier is not None:
                per_node_scheme[id(n)] = scheme_multiplier
            else:
                per_node_scheme[id(n)] = node_layout_state.scheme_name_to_multiplier(
                    stored["scheme"], prefs
                )
            per_node_h_scale[id(n)] = stored["h_scale"]
            per_node_v_scale[id(n)] = stored["v_scale"]

        snap = node_layout.get_dag_snap_threshold()
        node_count = len(selected)

        # Accumulators for horizontal seeds discovered across all roots; used
        # for output-dot placement and mode write-back after the loop.
        all_horizontal_seeds: list = []
        all_horizontal_ids: set = set()

        for root in roots:
            ctx = LayoutContext(
                snap_threshold=snap,
                node_count=node_count,
                node_filter=node_filter,
                per_node_scheme=per_node_scheme,
                per_node_h_scale=per_node_h_scale,
                per_node_v_scale=per_node_v_scale,
                dimension_overrides=dimension_overrides,
                all_member_ids=all_member_ids,
                horizontal_seeds=all_horizontal_seeds,
                all_horizontal_ids=all_horizontal_ids,
            )
            subtree = layout(root, ctx)
            id_to_node = collect_id_to_node(
                subtree,
                extra_nodes=[m for b in freeze_blocks for m in b.members],
            )
            anchor_x = root.xpos()
            anchor_y = root.ypos()
            local_root_x, local_root_y = subtree.nodes.get(
                id(root), subtree.anchor_out
            )
            dx = anchor_x - local_root_x
            dy = anchor_y - local_root_y
            for node_id, (lx, ly) in subtree.nodes.items():
                obj = id_to_node.get(node_id)
                if obj is None:
                    continue
                obj.setXpos(lx + dx)
                obj.setYpos(ly + dy)

        # Place/reposition routing Dots for each horizontal subtree.
        for seed in all_horizontal_seeds:
            node_layout._place_output_dot_for_horizontal_root(
                seed, current_group, snap, prefs.get("normal_multiplier"),
            )

        # State write-back
        for n in selected:
            stored = node_layout_state.read_node_state(n)
            n_scheme = per_node_scheme.get(id(n), prefs.get("normal_multiplier"))
            stored["scheme"] = node_layout_state.multiplier_to_scheme_name(
                n_scheme, prefs
            )
            stored["mode"] = (
                "horizontal" if id(n) in all_horizontal_ids else "vertical"
            )
            node_layout_state.write_node_state(n, stored)

        # Restore freeze members
        for block in freeze_blocks:
            block.restore_positions()

        # Push surrounding nodes
        all_after_nodes = list(selected)
        for block in freeze_blocks:
            for m in block.members:
                if m not in all_after_nodes:
                    all_after_nodes.append(m)
        bbox_after = node_layout.compute_node_bounding_box(all_after_nodes)
        if bbox_before is not None and bbox_after is not None:
            node_layout.push_nodes_to_make_room(
                {id(n) for n in all_after_nodes}, bbox_before, bbox_after,
                current_group=current_group,
                freeze_blocks=freeze_blocks,
            )

    # ------------------------------------------------------------------
    # layout_selected_horizontal — selection laid out as horizontal chain.
    # ------------------------------------------------------------------
    def layout_selected_horizontal(self, scheme_multiplier=None):
        self._run_selected_horizontal(
            scheme_multiplier, side_layout_mode="recursive",
            undo_label="Layout Selected Horizontal (bbox)",
        )

    def layout_selected_horizontal_place_only(self, scheme_multiplier=None):
        self._run_selected_horizontal(
            scheme_multiplier, side_layout_mode="place_only",
            undo_label="Layout Selected Horizontal Place-Only (bbox)",
        )

    def _run_selected_horizontal(self, scheme_multiplier, side_layout_mode, undo_label):
        node_layout._clear_color_cache()
        current_group = nuke.lastHitGroup()
        selected = nuke.selectedNodes()
        if not selected:
            return

        nuke.Undo.name(undo_label)
        nuke.Undo.begin()
        try:
            with current_group:
                node_filter = set(selected)
                expanded = node_layout._expand_scope_for_freeze_groups(
                    list(node_filter), current_group
                )
                node_filter = set(expanded)
                selected = list(node_filter)
                freeze_group_map, _ = node_layout._detect_freeze_groups(
                    list(node_filter)
                )
                freeze_blocks, dim_overrides, all_non_root_ids, all_member_ids = (
                    node_layout._build_freeze_blocks(freeze_group_map)
                )

                bbox_before = node_layout.compute_node_bounding_box(selected)

                if all_non_root_ids:
                    node_filter = {n for n in node_filter
                                   if id(n) not in all_non_root_ids}
                    selected = [n for n in selected
                                if id(n) not in all_non_root_ids]

                # Find the most-downstream selected as the chain root.
                roots = node_layout.find_selection_roots(selected)
                if not roots:
                    return
                # Single chain root preferred; if multiple, pick rightmost
                roots.sort(key=lambda n: -n.xpos())
                root = roots[0]

                prefs = node_layout_prefs.prefs_singleton
                per_node_scheme = {}
                per_node_h_scale = {}
                per_node_v_scale = {}
                for n in selected:
                    stored = node_layout_state.read_node_state(n)
                    if scheme_multiplier is not None:
                        per_node_scheme[id(n)] = scheme_multiplier
                    else:
                        per_node_scheme[id(n)] = (
                            node_layout_state.scheme_name_to_multiplier(
                                stored["scheme"], prefs
                            )
                        )
                    per_node_h_scale[id(n)] = stored["h_scale"]
                    per_node_v_scale[id(n)] = stored["v_scale"]

                # Build spine_set: walk input[0] through selected nodes only.
                spine_set = set()
                cursor = root
                while cursor is not None and cursor in node_filter:
                    spine_set.add(id(cursor))
                    cursor = cursor.input(0)

                # Expand the layout scope to include the full upstream of every
                # spine node, so side inputs (slot >= 1 of each spine node) and
                # the leftmost spine node's input(0) subtree get laid out by
                # the recursion. Without this they'd be excluded by
                # ``node_filter`` and never repositioned.
                wider_filter = set(node_filter)
                for sid in spine_set:
                    spine_node_obj = next(
                        (n for n in selected if id(n) == sid), None,
                    )
                    if spine_node_obj is None:
                        continue
                    wider_filter.update(
                        node_layout.collect_subtree_nodes(spine_node_obj)
                    )

                # Re-detect freeze groups against the wider scope. Freeze
                # blocks living entirely upstream of the spine (no member in
                # the original selection) were invisible to the first pass,
                # so the recursion would have laid out their members as
                # regular nodes — breaking the rigid offsets and (because
                # state write-back never restored them) leaving the block
                # visually disassembled. Pulling them in here makes them
                # opaque leaves to the recursion. ``_expand_scope_for_freeze_groups``
                # also pulls partial blocks into full blocks before detection.
                wider_filter = set(node_layout._expand_scope_for_freeze_groups(
                    list(wider_filter), current_group
                ))
                wider_freeze_map, _ = node_layout._detect_freeze_groups(
                    list(wider_filter)
                )
                freeze_blocks, dim_overrides, all_non_root_ids, all_member_ids = (
                    node_layout._build_freeze_blocks(wider_freeze_map)
                )
                # Frozen non-root members are folded into their block roots
                # by the recursion; they must not appear in the recursion
                # filter as standalone nodes.
                if all_non_root_ids:
                    wider_filter = {n for n in wider_filter
                                    if id(n) not in all_non_root_ids}
                    selected = [n for n in selected
                                if id(n) not in all_non_root_ids]

                # Resolve scheme/scale defaults for the newly-included nodes.
                for n in wider_filter:
                    if id(n) in per_node_scheme:
                        continue
                    stored = node_layout_state.read_node_state(n)
                    if scheme_multiplier is not None:
                        per_node_scheme[id(n)] = scheme_multiplier
                    else:
                        per_node_scheme[id(n)] = (
                            node_layout_state.scheme_name_to_multiplier(
                                stored["scheme"], prefs
                            )
                        )
                    per_node_h_scale[id(n)] = stored["h_scale"]
                    per_node_v_scale[id(n)] = stored["v_scale"]

                snap = node_layout.get_dag_snap_threshold()
                ctx = LayoutContext(
                    snap_threshold=snap,
                    node_count=len(wider_filter),
                    node_filter=wider_filter,
                    per_node_scheme=per_node_scheme,
                    per_node_h_scale=per_node_h_scale,
                    per_node_v_scale=per_node_v_scale,
                    dimension_overrides=dim_overrides,
                    spine_set=spine_set,
                    horizontal_root_id=id(root),
                    all_member_ids=all_member_ids,
                )

                subtree = layout_horizontal(root, ctx)
                id_to_node = collect_id_to_node(
                    subtree,
                    extra_nodes=[m for b in freeze_blocks for m in b.members],
                )
                anchor_x = root.xpos()
                anchor_y = root.ypos()
                local_root_x, local_root_y = subtree.nodes.get(
                    id(root), subtree.anchor_out
                )
                dx = anchor_x - local_root_x
                dy = anchor_y - local_root_y
                for node_id, (lx, ly) in subtree.nodes.items():
                    obj = id_to_node.get(node_id)
                    if obj is None:
                        continue
                    obj.setXpos(lx + dx)
                    obj.setYpos(ly + dy)

                # State write-back
                for n in selected:
                    stored = node_layout_state.read_node_state(n)
                    n_scheme = per_node_scheme.get(
                        id(n), prefs.get("normal_multiplier")
                    )
                    stored["scheme"] = node_layout_state.multiplier_to_scheme_name(
                        n_scheme, prefs
                    )
                    stored["mode"] = (
                        "horizontal" if id(n) in spine_set else "vertical"
                    )
                    node_layout_state.write_node_state(n, stored)

                for block in freeze_blocks:
                    block.restore_positions()

                bbox_after = node_layout.compute_node_bounding_box(selected)
                if bbox_before is not None and bbox_after is not None:
                    node_layout.push_nodes_to_make_room(
                        {id(n) for n in selected}, bbox_before, bbox_after,
                        current_group=current_group,
                        freeze_blocks=freeze_blocks,
                    )

                _ = side_layout_mode  # currently both modes share this path
        except Exception:
            nuke.Undo.cancel()
            raise
        else:
            nuke.Undo.end()

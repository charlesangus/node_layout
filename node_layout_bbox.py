"""Algorithm A — leaf-first bbox composition layout engine ("bbox").

This is an independent, from-scratch implementation of the Nuke node-layout
contract. It does NOT delegate placement to ``node_layout.compute_dims`` or
``node_layout.place_subtree``; it runs its own post-order DFS that builds
``Subtree`` objects (bounding box + nodes-dict) and merges them into the
parent frame.

What is reused from the shared node_layout module (orthogonal helpers):

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

    ``nodes`` maps live node objects to ``(xpos, ypos)`` in the SUBTREE-LOCAL frame
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
    nodes: dict[object, tuple[int, int]]
    root_node: object  # the actual Nuke node object at anchor_out
    anchor_in_per_slot: dict[int, tuple[int, int]] = field(default_factory=dict)


def _translate(subtree: Subtree, dx: int, dy: int) -> Subtree:
    """Return a new Subtree shifted by (dx, dy)."""
    new_nodes = {node: (x + dx, y + dy) for node, (x, y) in subtree.nodes.items()}
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
    side_layout_mode: str = "recursive"
    all_member_ids: set = field(default_factory=set)
    # Populated by the dispatcher: every node that ended up in a horizontal
    # spine across the whole recursion. Used post-layout for output-dot
    # placement and state write-back.
    horizontal_seeds: list = field(default_factory=list)
    all_horizontal_ids: set = field(default_factory=set)
    local_node_counts: dict[int, int] = field(default_factory=dict)

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
        if node_layout._passes_node_filter(node, self.node_filter):
            return True
        return (
            _is_layout_routing_dot(node)
            and node.input(0) is not None
            and self.passes_filter(node.input(0))
        )

    def node_count_for(self, node) -> int:
        """Count the node's own upstream layout scope for local margin scaling."""
        key = id(node)
        if key in self.local_node_counts:
            return self.local_node_counts[key]

        seen = set()
        count = 0

        def _walk(cursor):
            nonlocal count
            if cursor is None or id(cursor) in seen or not self.passes_filter(cursor):
                return
            seen.add(id(cursor))
            if not _is_layout_routing_dot(cursor):
                count += 1
            if node_layout._hides_inputs(cursor):
                return
            for slot in range(cursor.inputs()):
                _walk(cursor.input(slot))

        _walk(node)
        self.local_node_counts[key] = max(1, count)
        return self.local_node_counts[key]


_SIDE_DOT_KNOB_NAME = "node_layout_bbox_side_dot"
_SIDE_DOT_VERTICAL_GAPS: dict[int, int] = {}


def _is_layout_routing_dot(node) -> bool:
    if node is None or node.Class() != "Dot":
        return False
    return (
        node.knob(_SIDE_DOT_KNOB_NAME) is not None
        or node.knob(node_layout._OUTPUT_DOT_KNOB_NAME) is not None
        or node.knob(node_layout._LEFTMOST_DOT_KNOB_NAME) is not None
        or node.knob("node_layout_diamond_dot") is not None
    )


def _deselect_all():
    for selected in nuke.selectedNodes():
        with contextlib.suppress(KeyError, AttributeError):
            selected["selected"].setValue(False)


def _add_invisible_marker(dot, knob_name: str, label: str):
    if dot.knob(knob_name) is not None:
        return
    with contextlib.suppress(Exception):
        tab = nuke.Tab_Knob("node_layout_tab", "Node Layout")
        tab.setFlag(nuke.INVISIBLE)
        dot.addKnob(tab)
    marker = nuke.Int_Knob(knob_name, label)
    marker.setFlag(nuke.INVISIBLE)
    dot.addKnob(marker)
    dot[knob_name].setValue(1)


def _make_side_dot(upstream):
    _deselect_all()
    try:
        dot = nuke.nodes.Dot()
    except AttributeError:
        return None
    for auto_slot in range(dot.inputs()):
        dot.setInput(auto_slot, None)
    _add_invisible_marker(dot, _SIDE_DOT_KNOB_NAME, "BBox Side Dot Marker")
    dot.setInput(0, upstream)
    return dot


def _record_side_dot_gap(dot, consumer, slot: int, ctx: LayoutContext):
    gap = int(
        node_layout._subtree_margin(
            consumer,
            slot,
            ctx.node_count_for(consumer),
            mode_multiplier=ctx.scheme_for(consumer),
        ) * ctx.v_scale_for(consumer)
    )
    _SIDE_DOT_VERTICAL_GAPS[id(dot)] = max(ctx.snap_threshold - 1, gap)


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
            side_layout_mode=ctx.side_layout_mode,
            all_member_ids=ctx.all_member_ids,
            horizontal_seeds=ctx.horizontal_seeds,
            all_horizontal_ids=ctx.all_horizontal_ids,
            local_node_counts=ctx.local_node_counts,
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
            if ctx.passes_filter(inp)
        ]
    primary_input = node.input(0) if node.inputs() else None
    all_side = (
        ctx.node_filter is not None
        and primary_input is not None
        and not ctx.passes_filter(primary_input)
    )
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


def _merge_translated(
    target_nodes: dict[object, tuple[int, int]],
    bbox: tuple[int, int, int, int],
    subtree: Subtree,
    dx: int,
    dy: int,
) -> tuple[int, int, int, int]:
    translated = _translate(subtree, dx, dy)
    target_nodes.update(translated.nodes)
    return (
        min(bbox[0], translated.bbox[0]),
        min(bbox[1], translated.bbox[1]),
        max(bbox[2], translated.bbox[2]),
        max(bbox[3], translated.bbox[3]),
    )


def _fold_freeze_block_geometry(
    block,
    ctx: LayoutContext,
    nodes_dict: dict[object, tuple[int, int]],
    bbox: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    """Add a freeze block's rigid members and non-root external inputs.

    The returned bbox describes the whole block-local layout, so callers do not
    need a post-placement ``restore_positions`` or external-input pass.
    """
    bbox_left, bbox_top, bbox_right, bbox_bottom = bbox
    for member in block.members:
        if id(member) == block.root_id:
            member_x, member_y = 0, 0
        else:
            member_x, member_y = block.offsets.get(id(member), (0, 0))
        nodes_dict[member] = (member_x, member_y)
        bbox_left = min(bbox_left, member_x)
        bbox_top = min(bbox_top, member_y)
        bbox_right = max(bbox_right, member_x + member.screenWidth())
        bbox_bottom = max(bbox_bottom, member_y + member.screenHeight())

    for entry_node, connecting_member in block.get_external_inputs(node_layout.get_inputs):
        if id(connecting_member) == block.root_id:
            continue
        if not ctx.passes_filter(entry_node):
            continue
        entry_subtree = layout(entry_node, ctx)
        member_x, member_y = block.offsets.get(id(connecting_member), (0, 0))
        raw_gap = node_layout.vertical_gap_between(
            entry_node, connecting_member, ctx.snap_threshold,
            scheme_multiplier=ctx.scheme_for(entry_node),
        )
        gap = max(ctx.snap_threshold - 1, raw_gap)
        entry_x = node_layout._center_x(
            entry_node.screenWidth(),
            member_x,
            connecting_member.screenWidth(),
        )
        entry_y = member_y - gap - entry_subtree.bbox[3]
        bbox_left, bbox_top, bbox_right, bbox_bottom = _merge_translated(
            nodes_dict,
            (bbox_left, bbox_top, bbox_right, bbox_bottom),
            entry_subtree,
            entry_x,
            entry_y,
        )

    block_left, block_top, block_right, block_bottom = _block_local_extents(block)
    return (
        min(bbox_left, block_left),
        min(bbox_top, block_top),
        max(bbox_right, block_right),
        max(bbox_bottom, block_bottom),
    )


def _snapshot_existing_subtree(root, ctx: LayoutContext) -> Subtree:
    """Return a rigid snapshot of current positions, root-local."""
    found = {}

    def _walk(node):
        if node is None or id(node) in found or not ctx.passes_filter(node):
            return
        found[id(node)] = node
        block = ctx.dimension_overrides.get(id(node))
        if block is not None and id(node) == block.root_id:
            for member in block.members:
                found[id(member)] = member
        if node_layout._hides_inputs(node):
            return
        for slot in range(node.inputs()):
            _walk(node.input(slot))

    _walk(root)
    nodes = list(found.values()) or [root]
    root_x = root.xpos()
    root_y = root.ypos()
    local_nodes = {n: (n.xpos() - root_x, n.ypos() - root_y) for n in nodes}
    bbox = (
        min(x for x, _ in local_nodes.values()),
        min(y for _, y in local_nodes.values()),
        max(x + n.screenWidth() for n, (x, _) in local_nodes.items()),
        max(y + n.screenHeight() for n, (_, y) in local_nodes.items()),
    )
    return Subtree(
        bbox=bbox,
        anchor_out=(0, 0),
        nodes=local_nodes,
        root_node=root,
    )


def _layout_side_dot(node, ctx: LayoutContext, pairs) -> Subtree:
    """Layout a pre-created routing Dot and its upstream subtree.

    Side Dots are centered on their downstream consumer by the parent packer.
    In the Dot-local frame, the upstream subtree's bbox bottom sits exactly one
    recorded subtree gap above the Dot top.
    """
    slot, upstream = pairs[0]
    _ = slot
    child = layout(upstream, ctx)
    gap = _SIDE_DOT_VERTICAL_GAPS.get(id(node), ctx.snap_threshold - 1)
    dot_w = node.screenWidth()
    dot_h = node.screenHeight()
    child_x = node_layout._center_x(upstream.screenWidth(), 0, dot_w)
    child_y = -gap - child.bbox[3]
    nodes_dict: dict[object, tuple[int, int]] = {node: (0, 0)}
    bbox = _merge_translated(nodes_dict, (0, 0, dot_w, dot_h), child, child_x, child_y)
    return Subtree(
        bbox=bbox,
        anchor_out=(0, 0),
        nodes=nodes_dict,
        root_node=node,
        anchor_in_per_slot={0: (child_x, child_y)},
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

    if node.knob(_SIDE_DOT_KNOB_NAME) is not None and len(pairs) == 1:
        return _layout_side_dot(node, ctx, pairs)

    if is_block_root and not pairs:
        # Block root with no in-filter external inputs: opaque rigid leaf.
        # Members keep their stored relative offsets; non-root external input
        # subtrees are included in this local geometry.
        nodes = {block.root: (0, 0)}
        bbox = _fold_freeze_block_geometry(
            block, ctx, nodes, _block_local_extents(block)
        )
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
            nodes={node: (0, 0)},
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
    side_margins_v = [
        int(
            node_layout._subtree_margin(
                node, slot, ctx.node_count_for(node), mode_multiplier=scheme
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
        if n > 1 or all_side:
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

    for i, inp in enumerate(inputs):
        if inp.knob(node_layout._OUTPUT_DOT_KNOB_NAME) is not None:
            y_positions[i] = (node_h - inp.screenHeight()) // 2
        elif inp.knob(_SIDE_DOT_KNOB_NAME) is not None:
            y_positions[i] = (node_h - inp.screenHeight()) // 2

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

    # ----- Merge children + place dots into this node's frame. -----
    # Translate each child by (x_positions[i], y_positions[i]) and merge.
    nodes_dict: dict[object, tuple[int, int]] = {node: (0, 0)}
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

    # If this node is a freeze block root with external inputs, fold the rigid
    # block geometry into the result: add non-root members at their stored
    # offsets and widen the bbox to include the full block extent.
    if is_block_root:
        bbox_left, bbox_top, bbox_right, bbox_bottom = _fold_freeze_block_geometry(
            block, ctx, nodes_dict, (bbox_left, bbox_top, bbox_right, bbox_bottom)
        )

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

    # Side inputs affect the horizontal footprint of each spine node. Compute
    # them before placing the spine so adjacent spine sections are spaced by
    # their whole occupied bboxes, not just the spine tiles.
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
        side_layout_mode=ctx.side_layout_mode,
        all_member_ids=ctx.all_member_ids,
        horizontal_seeds=ctx.horizontal_seeds,
        all_horizontal_ids=ctx.all_horizontal_ids,
        local_node_counts=ctx.local_node_counts,
    )
    h_gap = int(prefs.get("horizontal_subtree_gap") * scheme)
    side_layouts: list[list[tuple[int, object, Subtree]]] = []
    local_bboxes: list[tuple[int, int, int, int]] = []
    occupied_intervals: list[tuple[int, int]] = []
    for spine_node in spine_nodes:
        block = ctx.dimension_overrides.get(id(spine_node))
        if block is not None and id(spine_node) == block.root_id:
            local_bbox = _block_local_extents(block)
        else:
            local_bbox = (0, 0, spine_node.screenWidth(), spine_node.screenHeight())
        local_bboxes.append(local_bbox)
        occ_l, occ_r = local_bbox[0], local_bbox[2]

        side_entries: list[tuple[int, object, Subtree]] = []
        for slot in range(1, spine_node.inputs()):
            inp = spine_node.input(slot)
            if inp is None or not ctx.passes_filter(inp):
                continue
            child_subtree = (
                _snapshot_existing_subtree(inp, side_ctx)
                if ctx.side_layout_mode == "place_only"
                else layout(inp, side_ctx)
            )
            side_entries.append((slot, inp, child_subtree))

        if len(side_entries) == 1:
            _slot, side_root, child_subtree = side_entries[0]
            child_root_x = (
                spine_node.screenWidth() // 2 - side_root.screenWidth() // 2
            )
            occ_l = min(occ_l, child_root_x + child_subtree.bbox[0])
            occ_r = max(occ_r, child_root_x + child_subtree.bbox[2])
        elif len(side_entries) > 1:
            cur_alloc = spine_node.screenWidth()
            for _slot, _side_root, child_subtree in side_entries:
                child_w_total = child_subtree.bbox[2] - child_subtree.bbox[0]
                child_root_x = cur_alloc - child_subtree.bbox[0]
                occ_l = min(occ_l, child_root_x + child_subtree.bbox[0])
                occ_r = max(occ_r, child_root_x + child_subtree.bbox[2])
                cur_alloc += child_w_total + h_gap

        side_layouts.append(side_entries)
        occupied_intervals.append((occ_l, occ_r))

    # Place root at (0, 0). Each prior spine node sits to the left.
    nodes_dict: dict[object, tuple[int, int]] = {}
    bbox_l, bbox_t, bbox_r, bbox_b = 0, 0, 0, 0
    cur_y = 0

    # Walk spine left to right (index 0 = rightmost root).
    # We place the root first, then each upstream spine node steps left.
    spine_x_per_index: list[int] = []
    spine_left_edges: list[int] = []
    for i, spine_node in enumerate(spine_nodes):
        block = ctx.dimension_overrides.get(id(spine_node))
        local_bbox = local_bboxes[i]
        occ_l, occ_r = occupied_intervals[i]

        if i == 0:
            spine_x = 0
        else:
            target_right_edge = spine_left_edges[i - 1] - step_x
            spine_x = target_right_edge - occ_r
        spine_x_per_index.append(spine_x)
        spine_left_edges.append(spine_x + occ_l)
        if block is not None and id(spine_node) == block.root_id:
            block_nodes: dict[object, tuple[int, int]] = {spine_node: (0, 0)}
            block_bbox = _fold_freeze_block_geometry(
                block, ctx, block_nodes, _block_local_extents(block)
            )
            for member, (mx, my) in block_nodes.items():
                nodes_dict[member] = (spine_x + mx, cur_y + my)
            bbox_l = min(bbox_l, spine_x + block_bbox[0])
            bbox_t = min(bbox_t, cur_y + block_bbox[1])
            bbox_r = max(bbox_r, spine_x + block_bbox[2])
            bbox_b = max(bbox_b, cur_y + block_bbox[3])
        else:
            nodes_dict[spine_node] = (spine_x, cur_y)
            bbox_l = min(bbox_l, spine_x)
            bbox_t = min(bbox_t, cur_y)
            bbox_r = max(bbox_r, spine_x + spine_node.screenWidth())
            bbox_b = max(bbox_b, cur_y + spine_node.screenHeight())

    # Now lay out side inputs (slot >= 1) of each spine node vertically.
    # We build a vertical Subtree for each side input via layout_vertical,
    # then translate so its root sits centered above the spine node tile.
    for i, spine_node in enumerate(spine_nodes):
        spine_x = spine_x_per_index[i]
        side_entries = side_layouts[i]
        if not side_entries:
            continue

        # Lay out side inputs as vertical subtrees above the spine node.
        # Stack their bboxes rightward (cur_alloc) so multiple side inputs on
        # one spine node don't overlap each other. The first band's left edge
        # sits at the spine node's right edge; each subsequent band starts at
        # the previous band's right edge plus a horizontal gap. Single side
        # input case: it sits centered above the spine node tile.
        target_bbox_bottom = -side_v_gap
        if len(side_entries) == 1:
            _slot, side_root, child_subtree = side_entries[0]
            center_x = spine_x + spine_node.screenWidth() // 2
            child_root_x = center_x - side_root.screenWidth() // 2
            translated = _translate(
                child_subtree,
                child_root_x,
                target_bbox_bottom - child_subtree.bbox[3],
            )
            nodes_dict.update(translated.nodes)
            bbox_l = min(bbox_l, translated.bbox[0])
            bbox_t = min(bbox_t, translated.bbox[1])
            bbox_r = max(bbox_r, translated.bbox[2])
            bbox_b = max(bbox_b, translated.bbox[3])
        else:
            cur_alloc = spine_x + spine_node.screenWidth()
            for _slot, _side_root, child_subtree in side_entries:
                child_w_total = child_subtree.bbox[2] - child_subtree.bbox[0]
                child_root_x = cur_alloc - child_subtree.bbox[0]
                translated = _translate(
                    child_subtree,
                    child_root_x,
                    target_bbox_bottom - child_subtree.bbox[3],
                )
                nodes_dict.update(translated.nodes)
                bbox_l = min(bbox_l, translated.bbox[0])
                bbox_t = min(bbox_t, translated.bbox[1])
                bbox_r = max(bbox_r, translated.bbox[2])
                bbox_b = max(bbox_b, translated.bbox[3])
                cur_alloc += child_w_total + h_gap

    # Leftward extension: input(0) of the leftmost spine node, when non-spine
    # and eligible, is laid out as its own subtree (the dispatcher handles
    # mode) and placed so its bbox right edge sits step_x left of the leftmost
    # spine node, with the subtree's anchor_out vertically aligned to the
    # spine row. This realises the invariant "main input of a horizontal
    # node is directly to the left".
    if spine_nodes:
        leftmost = spine_nodes[-1]
        leftmost_x = spine_x_per_index[-1]
        zero = leftmost.input(0)
        zero_eligible = (
            zero is not None
            and (spine_set is None or id(zero) not in spine_set)
            and ctx.passes_filter(zero)
        )
        if zero_eligible:
            zero_subtree = (
                _snapshot_existing_subtree(zero, side_ctx)
                if ctx.side_layout_mode == "place_only"
                else layout(zero, side_ctx)
            )
            # Target: zero subtree's bbox right edge sits at leftmost_x - step_x.
            # Vertical align: the wire from zero's output_anchor enters
            # leftmost.input(0) at the spine row's mid-Y. We align by Y on
            # the subtree root (zero) — root sits at (anchor_out_x, 0) in its
            # local frame; we want it at the same Y as the spine row (cur_y).
            # The spine row's Y for a tile is cur_y..cur_y+spine_node.h, and
            # we vertically center against the leftmost spine tile.
            target_zero_root_y = (
                cur_y + leftmost.screenHeight() // 2 - zero.screenHeight() // 2
            )
            target_zero_bbox_right = leftmost_x - step_x
            # zero_subtree root sits at (0, 0) in local; bbox_right is
            # zero_subtree.bbox[2].  Translate so bbox right = target.
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

    ``Subtree`` stores live node objects, so applying geometry is a direct
    translation/write-back with no id lookup pass.
    """
    dx = anchor_x - subtree.anchor_out[0]
    dy = anchor_y - subtree.anchor_out[1]
    for node_obj, (lx, ly) in subtree.nodes.items():
        node_obj.setXpos(lx + dx)
        node_obj.setYpos(ly + dy)


def apply_with_lookup(
    subtree: Subtree, anchor_x: int, anchor_y: int, id_to_node: dict[int, object]
):
    """Place every node in ``subtree`` so the root sits at (anchor_x, anchor_y)."""
    dx = anchor_x - subtree.anchor_out[0]
    dy = anchor_y - subtree.anchor_out[1]
    for node_obj, (lx, ly) in subtree.nodes.items():
        node_obj.setXpos(lx + dx)
        node_obj.setYpos(ly + dy)


def collect_id_to_node(subtree: Subtree, extra_nodes=()) -> dict[int, object]:
    """Build id->node map. Walks ``root_node`` plus any extras provided.

    Kept for compatibility with older tests/helpers. The bbox engine now stores
    live node objects directly in ``subtree.nodes``.
    """
    id_map: dict[int, object] = {id(node): node for node in subtree.nodes}
    for extra in extra_nodes:
        id_map[id(extra)] = extra
    return id_map


# ---------------------------------------------------------------------------
# Mutation phase — all topology changes happen before bbox layout starts.
# ---------------------------------------------------------------------------

def _walk_mutable_graph(roots, ctx: LayoutContext) -> list:
    found = {}

    def _walk(node):
        if node is None or id(node) in found or not ctx.passes_filter(node):
            return
        found[id(node)] = node
        if node_layout._hides_inputs(node):
            return
        for slot in range(node.inputs()):
            _walk(node.input(slot))

    for root in roots:
        _walk(root)
    return list(found.values())


def _needs_side_dot(index: int, all_side: bool, is_fan: bool) -> bool:
    return all_side or is_fan or index > 0


def _ensure_side_dots(roots, ctx: LayoutContext):
    changed = True
    while changed:
        changed = False
        for node in _walk_mutable_graph(roots, ctx):
            if node.Class() == "Dot" or node_layout._hides_inputs(node):
                continue
            if node_layout_state.read_node_state(node).get("mode") == "horizontal":
                continue
            pairs, all_side, fan_active = _filtered_input_pairs(node, ctx)
            is_fan = fan_active and len(pairs) >= 3
            for index, (slot, inp) in enumerate(pairs):
                if not _needs_side_dot(index, all_side, is_fan):
                    continue
                if inp.Class() == "Dot":
                    if (
                        inp.knob(node_layout._OUTPUT_DOT_KNOB_NAME) is None
                        and inp.knob(node_layout._LEFTMOST_DOT_KNOB_NAME) is None
                        and inp.knob("node_layout_diamond_dot") is None
                    ):
                        _add_invisible_marker(
                            inp,
                            _SIDE_DOT_KNOB_NAME,
                            "BBox Side Dot Marker",
                        )
                    if inp.knob(_SIDE_DOT_KNOB_NAME) is not None:
                        _record_side_dot_gap(inp, node, slot, ctx)
                    continue
                dot = _make_side_dot(inp)
                if dot is None:
                    continue
                _record_side_dot_gap(dot, node, slot, ctx)
                node.setInput(slot, dot)
                changed = True


def _consumer_in_filter(root, ctx: LayoutContext, current_group) -> bool:
    all_nodes = current_group.nodes() if current_group is not None else nuke.allNodes()
    for node in all_nodes:
        if node.knob(node_layout._OUTPUT_DOT_KNOB_NAME) is not None:
            continue
        if not ctx.passes_filter(node):
            continue
        for slot in range(node.inputs()):
            inp = node.input(slot)
            if inp is not None and id(inp) == id(root):
                return True
            if (
                inp is not None
                and inp.knob(node_layout._OUTPUT_DOT_KNOB_NAME) is not None
                and inp.input(0) is not None
                and id(inp.input(0)) == id(root)
            ):
                return True
    return False


def _has_horizontal_consumer_in_filter(root, ctx: LayoutContext, current_group) -> bool:
    all_nodes = current_group.nodes() if current_group is not None else nuke.allNodes()
    for node in all_nodes:
        if not ctx.passes_filter(node):
            continue
        if node_layout_state.read_node_state(node).get("mode") != "horizontal":
            continue
        primary = node.input(0) if node.inputs() else None
        if primary is None:
            continue
        if id(primary) == id(root):
            return True
        if (
            primary.knob(node_layout._OUTPUT_DOT_KNOB_NAME) is not None
            and primary.input(0) is not None
            and id(primary.input(0)) == id(root)
        ):
            return True
    return False


def _ensure_leftmost_routing_dot_for_spine(root, ctx: LayoutContext, current_group):
    spine = ctx.spine_set if ctx.spine_set is not None else _spine_set_from(
        root, ctx.all_member_ids
    )
    cursor = root
    leftmost = None
    while cursor is not None and id(cursor) in spine:
        leftmost = cursor
        cursor = cursor.input(0)
    if (
        leftmost is None
        or cursor is None
        or not ctx.passes_filter(cursor)
        or cursor.Class() == "Dot"
    ):
        return
    if current_group is not None:
        node_layout._find_or_create_leftmost_dot(leftmost, current_group)
    else:
        dot = _make_side_dot(cursor)
        if dot is not None:
            _add_invisible_marker(
                dot,
                node_layout._LEFTMOST_DOT_KNOB_NAME,
                "Leftmost Dot Marker",
            )
            leftmost.setInput(0, dot)


def _ensure_horizontal_routing_dots(roots, ctx: LayoutContext, current_group):
    for node in list(_walk_mutable_graph(roots, ctx)):
        if node_layout_state.read_node_state(node).get("mode") != "horizontal":
            continue
        if (
            not _has_horizontal_consumer_in_filter(node, ctx, current_group)
            and _consumer_in_filter(node, ctx, current_group)
        ):
            node_layout._place_output_dot_for_horizontal_root(
                node,
                current_group,
                ctx.snap_threshold,
                ctx.scheme_for(node),
            )
        _ensure_leftmost_routing_dot_for_spine(node, ctx, current_group)


def _ensure_selected_horizontal_leftmost_dot(roots, ctx: LayoutContext, current_group):
    for root in roots:
        _ensure_leftmost_routing_dot_for_spine(root, ctx, current_group)


def prepare_layout_graph(roots, ctx: LayoutContext, current_group, routing_mode="full"):
    """Mutate graph topology before pure bbox composition begins."""
    for root in roots:
        node_layout.insert_dot_nodes(root, ctx.node_filter)
    if routing_mode == "selected_horizontal":
        _ensure_selected_horizontal_leftmost_dot(roots, ctx, current_group)
        return
    _ensure_horizontal_routing_dots(roots, ctx, current_group)
    _ensure_side_dots(roots, ctx)


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

        snap = node_layout.get_dag_snap_threshold()
        original_selected = root

        if all_non_root_ids:
            vertical_filter = {n for n in all_upstream
                               if id(n) not in all_non_root_ids}
        else:
            vertical_filter = None

        # Phase 1: per-node scheme/scale resolution for the pre-mutation graph.
        prefs = node_layout_prefs.prefs_singleton
        per_node_scheme = {}
        per_node_h_scale = {}
        per_node_v_scale = {}
        for n in all_upstream:
            stored = node_layout_state.read_node_state(n)
            if scheme_multiplier is not None:
                per_node_scheme[id(n)] = scheme_multiplier
            else:
                per_node_scheme[id(n)] = node_layout_state.scheme_name_to_multiplier(
                    stored["scheme"], prefs
                )
            per_node_h_scale[id(n)] = stored["h_scale"]
            per_node_v_scale[id(n)] = stored["v_scale"]

        ctx = LayoutContext(
            snap_threshold=snap,
            node_count=len(all_upstream),
            node_filter=vertical_filter,
            per_node_scheme=per_node_scheme,
            per_node_h_scale=per_node_h_scale,
            per_node_v_scale=per_node_v_scale,
            dimension_overrides=dimension_overrides,
            all_member_ids=all_member_ids,
        )

        # Phase 2: all graph mutation happens up front. After this, the bbox
        # recursion only reads topology and returns final geometry.
        prepare_layout_graph([root], ctx, current_group)
        upstream_after_mutation = node_layout.collect_subtree_nodes(root)
        ctx.node_count = len(upstream_after_mutation)
        if all_non_root_ids:
            ctx.node_filter = {n for n in upstream_after_mutation
                               if id(n) not in all_non_root_ids}
        for n in upstream_after_mutation:
            if id(n) in per_node_scheme:
                continue
            stored = node_layout_state.read_node_state(n)
            per_node_scheme[id(n)] = (
                scheme_multiplier if scheme_multiplier is not None
                else node_layout_state.scheme_name_to_multiplier(stored["scheme"], prefs)
            )
            per_node_h_scale[id(n)] = stored["h_scale"]
            per_node_v_scale[id(n)] = stored["v_scale"]

        # Phase 4: run recursion. The dispatcher picks vertical vs horizontal
        # based on each node's stored mode, so a vertical consumer with a
        # horizontal input subtree composes correctly.
        subtree = layout(root, ctx)

        # Phase 5: apply. Anchor: original_selected stays where it is.
        if root in subtree.nodes:
            local_x, local_y = subtree.nodes[root]
            dx = root.xpos() - local_x
            dy = root.ypos() - local_y
        else:
            dx = root.xpos() - subtree.anchor_out[0]
            dy = root.ypos() - subtree.anchor_out[1]

        for obj, (lx, ly) in subtree.nodes.items():
            obj.setXpos(lx + dx)
            obj.setYpos(ly + dy)

        # Phase 8: state write-back.
        final_nodes = list(subtree.nodes.keys())
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
        # for mode write-back after the loop.
        all_horizontal_ids: set = set()
        ctx = LayoutContext(
            snap_threshold=snap,
            node_count=node_count,
            node_filter=node_filter,
            per_node_scheme=per_node_scheme,
            per_node_h_scale=per_node_h_scale,
            per_node_v_scale=per_node_v_scale,
            dimension_overrides=dimension_overrides,
            all_member_ids=all_member_ids,
            all_horizontal_ids=all_horizontal_ids,
        )
        prepare_layout_graph(roots, ctx, current_group)
        mutated_selected = set()
        for root in roots:
            mutated_selected.update(node_layout.collect_subtree_nodes(root, ctx.node_filter))
        node_count = len(mutated_selected) or node_count
        ctx.node_count = node_count
        for n in mutated_selected:
            if id(n) in per_node_scheme:
                continue
            stored = node_layout_state.read_node_state(n)
            per_node_scheme[id(n)] = (
                scheme_multiplier if scheme_multiplier is not None
                else node_layout_state.scheme_name_to_multiplier(stored["scheme"], prefs)
            )
            per_node_h_scale[id(n)] = stored["h_scale"]
            per_node_v_scale[id(n)] = stored["v_scale"]

        placed_nodes = set()
        for root in roots:
            subtree = layout(root, ctx)
            placed_nodes.update(subtree.nodes.keys())
            anchor_x = root.xpos()
            anchor_y = root.ypos()
            local_root_x, local_root_y = subtree.nodes.get(
                root, subtree.anchor_out
            )
            dx = anchor_x - local_root_x
            dy = anchor_y - local_root_y
            for obj, (lx, ly) in subtree.nodes.items():
                obj.setXpos(lx + dx)
                obj.setYpos(ly + dy)

        # State write-back
        all_after_nodes = set(selected) | mutated_selected | placed_nodes
        for n in all_after_nodes:
            stored = node_layout_state.read_node_state(n)
            n_scheme = per_node_scheme.get(id(n), prefs.get("normal_multiplier"))
            stored["scheme"] = node_layout_state.multiplier_to_scheme_name(
                n_scheme, prefs
            )
            stored["mode"] = (
                "horizontal" if id(n) in all_horizontal_ids else "vertical"
            )
            node_layout_state.write_node_state(n, stored)

        # Push surrounding nodes
        for block in freeze_blocks:
            for m in block.members:
                if m not in all_after_nodes:
                    all_after_nodes.add(m)
        bbox_after = node_layout.compute_node_bounding_box(list(all_after_nodes))
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
                    side_layout_mode=side_layout_mode,
                    all_member_ids=all_member_ids,
                )

                prepare_layout_graph(
                    [root], ctx, current_group,
                    routing_mode="selected_horizontal",
                )
                mutated_nodes = set(_walk_mutable_graph([root], ctx))
                for n in mutated_nodes:
                    if id(n) in per_node_scheme:
                        continue
                    stored = node_layout_state.read_node_state(n)
                    per_node_scheme[id(n)] = (
                        scheme_multiplier if scheme_multiplier is not None
                        else node_layout_state.scheme_name_to_multiplier(
                            stored["scheme"], prefs
                        )
                    )
                    per_node_h_scale[id(n)] = stored["h_scale"]
                    per_node_v_scale[id(n)] = stored["v_scale"]

                subtree = layout_horizontal(root, ctx)
                anchor_x = root.xpos()
                anchor_y = root.ypos()
                local_root_x, local_root_y = subtree.nodes.get(
                    root, subtree.anchor_out
                )
                dx = anchor_x - local_root_x
                dy = anchor_y - local_root_y
                for obj, (lx, ly) in subtree.nodes.items():
                    obj.setXpos(lx + dx)
                    obj.setYpos(ly + dy)

                # State write-back
                all_after_nodes = set(selected) | set(subtree.nodes.keys())
                for n in all_after_nodes:
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

                bbox_after = node_layout.compute_node_bounding_box(list(all_after_nodes))
                if bbox_before is not None and bbox_after is not None:
                    node_layout.push_nodes_to_make_room(
                        {id(n) for n in all_after_nodes}, bbox_before, bbox_after,
                        current_group=current_group,
                        freeze_blocks=freeze_blocks,
                    )

        except Exception:
            nuke.Undo.cancel()
            raise
        else:
            nuke.Undo.end()

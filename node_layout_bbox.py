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
from dataclasses import dataclass, field, replace
from typing import Optional

import nuke

import node_layout
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
    # Maps id(node) -> mode name (e.g. "horizontal") for every node placed
    # by a non-default packer inside this subtree. Bubbles up through
    # merges so entry points can drive mode write-back from the layout
    # result instead of mutating the layout context during recursion.
    mode_assignments: dict = field(default_factory=dict)


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
        mode_assignments=dict(subtree.mode_assignments),
    )


# ---------------------------------------------------------------------------
# Layout context — bundles all the per-call state the recursion needs.
# ---------------------------------------------------------------------------

@dataclass
class LayoutContext:
    """Shared per-call state used by every packer.

    Discipline (see ``CLEAN_REWRITE_IMPLEMENTATION_PLAN.md``): only fields
    consumed by all packers belong here. Per-packer state (e.g. horizontal
    spine info) lives under ``packer_params`` keyed by packer name.
    """
    snap_threshold: int
    node_count: int
    node_filter: Optional[set]
    per_node_scheme: dict
    per_node_h_scale: dict
    per_node_v_scale: dict
    dimension_overrides: dict  # id(root) -> FreezeBlock
    all_member_ids: set = field(default_factory=set)
    # Vertical gap between a side routing Dot's top and the bottom of its
    # upstream subtree's bbox. Constant per layout call: derived from
    # ``base_subtree_margin`` and the resolved scheme multiplier so every
    # side Dot in a single run uses the same spacing.
    side_dot_gap: int = 0
    # Per-packer params keyed by packer name (e.g. ``HorizontalParams``
    # under ``"horizontal"``). The shared context never reads these
    # directly; each packer pulls its own params.
    packer_params: dict = field(default_factory=dict)

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

_SIDE_DOT_KNOB_NAME = "node_layout_bbox_side_dot"


def _resolve_side_dot_gap(snap_threshold: int, scheme_multiplier=None) -> int:
    """Return the vertical gap above a side routing Dot for one layout run.

    The gap is a single value per call, derived from prefs and the resolved
    scheme multiplier. Per-node font/scale variation is intentionally not
    applied here: side Dots are simple routing elements and benefit from
    consistent spacing across the run.
    """
    prefs = node_layout_prefs.prefs_singleton
    if scheme_multiplier is None:
        scheme_multiplier = prefs.get("normal_multiplier")
    gap = int(prefs.get("base_subtree_margin") * scheme_multiplier)
    return max(snap_threshold - 1, gap)


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
    from layout_contracts import PACKER_HORIZONTAL, HorizontalParams  # noqa: PLC0415

    state = node_layout_state.read_node_state(node)
    if state.get("mode") == "horizontal":
        spine_ids = frozenset(_spine_set_from(node, ctx.all_member_ids))
        existing = ctx.packer_params.get(PACKER_HORIZONTAL)
        side_layout_mode = existing.side_layout_mode if existing else "recursive"
        new_packer_params = dict(ctx.packer_params)
        new_packer_params[PACKER_HORIZONTAL] = HorizontalParams(
            spine_ids=spine_ids,
            root_id=id(node),
            side_layout_mode=side_layout_mode,
        )
        horizontal_ctx = replace(ctx, packer_params=new_packer_params)
        return layout_horizontal(node, horizontal_ctx)
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
    mode_assignments: Optional[dict] = None,
) -> tuple[int, int, int, int]:
    translated = _translate(subtree, dx, dy)
    target_nodes.update(translated.nodes)
    if mode_assignments is not None:
        mode_assignments.update(translated.mode_assignments)
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
    mode_assignments: Optional[dict] = None,
) -> tuple[int, int, int, int]:
    """Add a freeze block's rigid members and non-root external inputs.

    The returned bbox describes the whole block-local layout, so callers do
    not need a post-placement reposition or external-input pass.
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
            mode_assignments,
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
    gap = ctx.side_dot_gap
    dot_w = node.screenWidth()
    dot_h = node.screenHeight()
    child_x = node_layout._center_x(upstream.screenWidth(), 0, dot_w)
    child_y = -gap - child.bbox[3]
    nodes_dict: dict[object, tuple[int, int]] = {node: (0, 0)}
    mode_assignments: dict = {}
    bbox = _merge_translated(
        nodes_dict, (0, 0, dot_w, dot_h), child, child_x, child_y, mode_assignments,
    )
    return Subtree(
        bbox=bbox,
        anchor_out=(0, 0),
        nodes=nodes_dict,
        root_node=node,
        anchor_in_per_slot={0: (child_x, child_y)},
        mode_assignments=mode_assignments,
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
        mode_assignments: dict = {}
        bbox = _fold_freeze_block_geometry(
            block, ctx, nodes, _block_local_extents(block), mode_assignments,
        )
        return Subtree(
            bbox=bbox,
            anchor_out=(0, 0),
            nodes=nodes,
            root_node=node,
            mode_assignments=mode_assignments,
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
    # Pass ``scaling_reference_count`` so the sqrt(node_count)/sqrt(ref)
    # term inside ``_subtree_margin`` cancels to 1, making the margin
    # independent of the layout-scope size — running layout from a
    # subtree root produces the same spacing as from the full graph root.
    margin_reference_count = node_layout_prefs.prefs_singleton.get(
        "scaling_reference_count"
    )
    side_margins_v = [
        int(
            node_layout._subtree_margin(
                node, slot, margin_reference_count, mode_multiplier=scheme
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
        block_left, block_top, block_right, _block_bottom = _block_local_extents(block)
        consumer_right = max(node_w, block_right)
        consumer_left = min(0, block_left)
        consumer_top = min(0, block_top)
    else:
        block_left = block_right = 0
        block_top = 0
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
        if (
            inp.knob(node_layout._OUTPUT_DOT_KNOB_NAME) is not None
            or inp.knob(_SIDE_DOT_KNOB_NAME) is not None
        ):
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
    mode_assignments: dict = {}

    for i, child in enumerate(child_subtrees):
        translated = _translate(child, x_positions[i], y_positions[i])
        nodes_dict.update(translated.nodes)
        mode_assignments.update(translated.mode_assignments)
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
            block, ctx, nodes_dict,
            (bbox_left, bbox_top, bbox_right, bbox_bottom),
            mode_assignments,
        )

    return Subtree(
        bbox=(bbox_left, bbox_top, bbox_right, bbox_bottom),
        anchor_out=(0, 0),
        nodes=nodes_dict,
        root_node=node,
        anchor_in_per_slot=anchor_in_per_slot,
        mode_assignments=mode_assignments,
    )


# ---------------------------------------------------------------------------
# Horizontal packing — spine (input[0] chain) extends rightward from root,
# side inputs stack vertically above each spine node.
# ---------------------------------------------------------------------------

def layout_horizontal(root, ctx: LayoutContext) -> Subtree:
    """Lay out a horizontal chain rooted at ``root``.

    The spine is the chain of ``input[0]`` ancestors whose ids are in
    ``params.spine_ids`` (where ``params`` is
    ``ctx.packer_params[PACKER_HORIZONTAL]``).  ``root`` is the most-
    downstream spine node and is placed at (0, 0) in the returned Subtree's
    local frame.  Earlier spine nodes are placed leftward (more negative X).
    Each spine node's side inputs (slots >= 1) are laid out vertically above
    it.
    """
    from layout_contracts import PACKER_HORIZONTAL  # noqa: PLC0415

    params = ctx.packer_params.get(PACKER_HORIZONTAL)
    if params is not None:
        spine_set = set(params.spine_ids)
        side_layout_mode = params.side_layout_mode
    else:
        spine_set = _spine_set_from(root, ctx.all_member_ids)
        side_layout_mode = "recursive"
    prefs = node_layout_prefs.prefs_singleton
    # H-axis margins are scheme-independent everywhere else in the engine
    # (see ``node_layout._horizontal_margin``), so the spine step and the
    # side-input gap also use the raw pref value, scaled only by the
    # consumer's per-node h_scale.
    h_scale = ctx.h_scale_for(root)
    step_x = int(prefs.get("horizontal_subtree_gap") * h_scale)
    side_v_gap = prefs.get("horizontal_side_vertical_gap")

    # Build spine (rightmost first): root, root.input(0), input(0).input(0), ...
    spine_nodes = []
    cursor = root
    while cursor is not None:
        if id(cursor) not in spine_set:
            break
        spine_nodes.append(cursor)
        cursor = cursor.input(0)

    # Side inputs affect the horizontal footprint of each spine node. Compute
    # them before placing the spine so adjacent spine sections are spaced by
    # their whole occupied bboxes, not just the spine tiles. Sub-recursions
    # pop back to vertical-mode dispatch — clear the horizontal params so a
    # nested horizontal subtree below a side input rebuilds its own spine.
    from layout_contracts import PACKER_HORIZONTAL as _PACKER_HORIZONTAL  # noqa: PLC0415
    side_packer_params = {
        k: v for k, v in ctx.packer_params.items() if k != _PACKER_HORIZONTAL
    }
    side_ctx = replace(ctx, packer_params=side_packer_params)
    h_gap = step_x
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
                if side_layout_mode == "place_only"
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
    # Spine nodes themselves are the horizontal-mode set this subtree
    # contributes; side-input subtrees may add more if they contain nested
    # horizontal layouts.
    mode_assignments: dict = {
        id(spine_node): "horizontal" for spine_node in spine_nodes
    }

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
                block, ctx, block_nodes, _block_local_extents(block),
                mode_assignments,
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
            mode_assignments.update(translated.mode_assignments)
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
                mode_assignments.update(translated.mode_assignments)
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
                if side_layout_mode == "place_only"
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
            # Right edge of the leftward extension: clear the spine tile by
            # step_x, AND clear the leftmost spine's occupied interval (which
            # extends further left when its side input subtrees contain
            # horizontal nodes) by h_gap. occupied_intervals[-1][0] is the
            # leftmost spine's segment left edge in spine-local frame.
            leftmost_seg_left_world = leftmost_x + occupied_intervals[-1][0]
            target_zero_bbox_right = min(
                leftmost_x - step_x,
                leftmost_seg_left_world - h_gap,
            )
            # zero_subtree root sits at (0, 0) in local; bbox_right is
            # zero_subtree.bbox[2].  Translate so bbox right = target.
            zero_root_x = target_zero_bbox_right - zero_subtree.bbox[2]
            translated = _translate(
                zero_subtree,
                zero_root_x,
                target_zero_root_y,
            )
            nodes_dict.update(translated.nodes)
            mode_assignments.update(translated.mode_assignments)
            bbox_l = min(bbox_l, translated.bbox[0])
            bbox_t = min(bbox_t, translated.bbox[1])
            bbox_r = max(bbox_r, translated.bbox[2])
            bbox_b = max(bbox_b, translated.bbox[3])

    return Subtree(
        bbox=(bbox_l, bbox_t, bbox_r, bbox_b),
        anchor_out=(0, cur_y),
        nodes=nodes_dict,
        root_node=root,
        mode_assignments=mode_assignments,
    )


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
                if inp.Class() == "Dot":
                    # Any existing Dot — regardless of slot or origin — is
                    # treated as a side routing dot so it routes through
                    # ``_layout_side_dot`` with the same gap as engine-
                    # created side dots. Excluded: leftmost-spine boundary
                    # dots and diamond dots, which have specialised geometry
                    # handled elsewhere.
                    if (
                        inp.knob(node_layout._LEFTMOST_DOT_KNOB_NAME) is None
                        and inp.knob("node_layout_diamond_dot") is None
                    ):
                        _add_invisible_marker(
                            inp,
                            _SIDE_DOT_KNOB_NAME,
                            "BBox Side Dot Marker",
                        )
                    continue
                # Non-Dot input: only wrap in a new side dot for slots that
                # need one (slot >= 1 in normal mode, or fan/all_side modes).
                # Main inputs (slot 0 in normal mode) stay bare.
                if not _needs_side_dot(index, all_side, is_fan):
                    continue
                dot = _make_side_dot(inp)
                if dot is None:
                    continue
                node.setInput(slot, dot)
                changed = True


def _ensure_leftmost_routing_dot_for_spine(root, ctx: LayoutContext, current_group):
    from layout_contracts import PACKER_HORIZONTAL  # noqa: PLC0415

    params = ctx.packer_params.get(PACKER_HORIZONTAL)
    if params is not None and params.spine_ids is not None:
        spine = set(params.spine_ids)
    else:
        spine = _spine_set_from(root, ctx.all_member_ids)
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
        # Output Dot insertion intentionally omitted. The legacy
        # ``_place_output_dot_for_horizontal_root`` positions a Dot at
        # consumer mid-Y — appropriate when the chain is anchored to the
        # right of the consumer (legacy geometry), but in the bbox layout
        # the horizontal subtree sits naturally above its consumer, so a
        # Dot at consumer mid-Y overlaps the consumer tile. The
        # leftmost-spine boundary Dot inserted by ``layout_horizontal``
        # provides the only routing turn the chain needs.
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
# Engine — exposes the four layout entry points used by ``node_layout``.
#
# Each entry point follows the same shape:
#
#   1. clear color cache, snapshot pre-layout bbox
#   2. expand scope for freeze groups, build freeze blocks
#   3. resolve per-node scheme/scale state
#   4. mutate graph topology (insert routing dots) up front
#   5. recurse: produce a Subtree with mode_assignments carried on the result
#   6. translate the Subtree so the anchor node lands at its current xpos/ypos
#   7. write per-node state (scheme + mode) back from the recursion result
#   8. push surrounding DAG nodes to make room
#
# The shared steps (1, 6, 7, 8 and parts of 2/3) live in the helpers below.
# Each entry point composes them with its specific shape: layout_upstream
# recurses from a single anchor; layout_selected loops over multiple roots;
# layout_selected_horizontal forces a horizontal chain at the selected root.
# ---------------------------------------------------------------------------


def _resolve_per_node_state(nodes, scheme_multiplier, prefs,
                            scheme_map, h_scale_map, v_scale_map):
    """Fill ``scheme_map`` / ``h_scale_map`` / ``v_scale_map`` for ``nodes``.

    Reads each node's stored layout state via ``node_layout_state`` and
    writes one entry per node, keyed by ``id(node)``. Existing keys are
    preserved so the function is safe to call repeatedly for new nodes
    introduced by the mutation phase.
    """
    for node in nodes:
        if id(node) in scheme_map:
            continue
        stored = node_layout_state.read_node_state(node)
        if scheme_multiplier is not None:
            scheme_map[id(node)] = scheme_multiplier
        else:
            scheme_map[id(node)] = node_layout_state.scheme_name_to_multiplier(
                stored["scheme"], prefs,
            )
        h_scale_map[id(node)] = stored["h_scale"]
        v_scale_map[id(node)] = stored["v_scale"]


def _apply_subtree_anchored_at(subtree: Subtree, anchor_node):
    """Translate the subtree so ``anchor_node`` ends at its current xpos/ypos.

    Falls back to ``subtree.anchor_out`` when the anchor isn't in the node
    dict (defensive — every recursion path returns the anchor in nodes).
    """
    local_x, local_y = subtree.nodes.get(anchor_node, subtree.anchor_out)
    dx = anchor_node.xpos() - local_x
    dy = anchor_node.ypos() - local_y
    for obj, (lx, ly) in subtree.nodes.items():
        obj.setXpos(lx + dx)
        obj.setYpos(ly + dy)


def _write_state(nodes, scheme_map, prefs, mode_for_node):
    """Write scheme + mode back to each node's hidden state knob.

    ``mode_for_node`` is a callable returning either ``"horizontal"`` or
    ``None`` to leave the existing mode untouched.
    """
    for node in nodes:
        stored = node_layout_state.read_node_state(node)
        n_scheme = scheme_map.get(id(node), prefs.get("normal_multiplier"))
        stored["scheme"] = node_layout_state.multiplier_to_scheme_name(
            n_scheme, prefs,
        )
        new_mode = mode_for_node(node)
        if new_mode is not None:
            stored["mode"] = new_mode
        node_layout_state.write_node_state(node, stored)


def _push_after(all_after_nodes, bbox_before, current_group, freeze_blocks):
    """Run ``push_nodes_to_make_room`` for the post-layout bounding box.

    ``all_after_nodes`` is augmented with any freeze-block members that
    weren't part of the recursion result so the push correctly skips over
    rigid block geometry.
    """
    augmented = set(all_after_nodes)
    for block in freeze_blocks:
        augmented.update(block.members)
    bbox_after = node_layout.compute_node_bounding_box(list(augmented))
    if bbox_before is None or bbox_after is None:
        return
    node_layout.push_nodes_to_make_room(
        {id(n) for n in augmented}, bbox_before, bbox_after,
        current_group=current_group,
        freeze_blocks=freeze_blocks,
    )


@contextlib.contextmanager
def _undo_block(label):
    """Context manager that wraps a block in a Nuke undo group.

    Cancels the undo group on exception, ends it cleanly otherwise.
    """
    nuke.Undo.name(label)
    nuke.Undo.begin()
    try:
        yield
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def _setup_freeze(scope_nodes, current_group):
    """Expand the scope for freeze groups and build FreezeBlock objects.

    Returns ``(expanded, freeze_blocks, dimension_overrides,
    all_non_root_ids, all_member_ids)``.
    """
    expanded = node_layout._expand_scope_for_freeze_groups(
        list(scope_nodes), current_group,
    )
    freeze_group_map, _ = node_layout._detect_freeze_groups(expanded)
    freeze_blocks, dimension_overrides, all_non_root_ids, all_member_ids = (
        node_layout._build_freeze_blocks(freeze_group_map)
    )
    return (
        expanded, freeze_blocks, dimension_overrides,
        all_non_root_ids, all_member_ids,
    )


class BboxEngine:
    """Thin compatibility shim over ``layout_orchestrator``.

    Public commands now build a ``LayoutRequest`` and call
    ``layout_orchestrator.run_layout``. The four methods below preserve the
    pre-refactor surface so existing tests and ``node_layout`` entry points
    keep working without churn.
    """

    def layout_upstream(self, scheme_multiplier=None):
        from layout_contracts import LayoutRequest  # noqa: PLC0415
        from layout_orchestrator import run_layout  # noqa: PLC0415

        current_group = nuke.lastHitGroup()
        root = nuke.selectedNode()
        request = LayoutRequest(
            command="layout_upstream",
            scheme_multiplier=scheme_multiplier,
            undo_label="Layout Upstream (bbox)",
            scope_kind="upstream",
        )
        return run_layout(request, [root], current_group)

    def layout_selected(self, scheme_multiplier=None):
        from layout_contracts import LayoutRequest  # noqa: PLC0415
        from layout_orchestrator import run_layout  # noqa: PLC0415

        current_group = nuke.lastHitGroup()
        selected = nuke.selectedNodes()
        if len(selected) < 2:
            return None
        request = LayoutRequest(
            command="layout_selected",
            scheme_multiplier=scheme_multiplier,
            undo_label="Layout Selected (bbox)",
            scope_kind="selected",
        )
        return run_layout(request, selected, current_group)

    def layout_selected_horizontal(self, scheme_multiplier=None):
        from layout_contracts import LayoutRequest  # noqa: PLC0415
        from layout_orchestrator import run_layout  # noqa: PLC0415

        current_group = nuke.lastHitGroup()
        selected = nuke.selectedNodes()
        if not selected:
            return None
        request = LayoutRequest(
            command="layout_selected_horizontal",
            scheme_multiplier=scheme_multiplier,
            undo_label="Layout Selected Horizontal (bbox)",
            scope_kind="selected_horizontal",
            routing_mode="selected_horizontal",
            selected_horizontal_side_mode="recursive",
        )
        return run_layout(request, selected, current_group)

    def layout_selected_horizontal_place_only(self, scheme_multiplier=None):
        from layout_contracts import LayoutRequest  # noqa: PLC0415
        from layout_orchestrator import run_layout  # noqa: PLC0415

        current_group = nuke.lastHitGroup()
        selected = nuke.selectedNodes()
        if not selected:
            return None
        request = LayoutRequest(
            command="layout_selected_horizontal_place_only",
            scheme_multiplier=scheme_multiplier,
            undo_label="Layout Selected Horizontal Place-Only (bbox)",
            scope_kind="selected_horizontal",
            routing_mode="selected_horizontal",
            selected_horizontal_side_mode="place_only",
        )
        return run_layout(request, selected, current_group)

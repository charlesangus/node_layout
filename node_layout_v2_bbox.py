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

def layout_vertical(node, ctx: LayoutContext) -> Subtree:
    """Post-order DFS: build a Subtree for ``node``.

    Local frame convention: ``node``'s top-left is placed at (0, 0). The
    returned Subtree is in this frame; the parent caller translates it.
    """
    # --- Freeze block leaf (opaque rigid bbox) ---
    block = ctx.dimension_overrides.get(id(node))
    if block is not None and id(node) == block.root_id:
        # Drop the entire freeze block as an opaque leaf. The block is anchored
        # so its root sits at (0, 0).  Members keep their stored relative offsets.
        nodes = {id(block.root): (0, 0)}
        for member in block.members:
            if id(member) == block.root_id:
                continue
            dx, dy = block.offsets.get(id(member), (0, 0))
            nodes[id(member)] = (dx, dy)
        # bbox spans the full block: left_overhang to the left, right_extent to the right.
        bbox = (
            -block.left_overhang,
            0,
            block.right_extent,
            block.block_height,
        )
        return Subtree(
            bbox=bbox,
            anchor_out=(0, 0),
            nodes=nodes,
            root_node=node,
        )

    pairs, all_side, fan_active = _filtered_input_pairs(node, ctx)

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
    child_subtrees = [layout_vertical(inp, ctx) for inp in inputs]

    h_scale = ctx.h_scale_for(node)
    v_scale = ctx.v_scale_for(node)
    scheme = ctx.scheme_for(node)

    side_margins_h = [
        int(node_layout._horizontal_margin(node, slot) * h_scale)
        for slot in actual_slots
    ]
    side_margins_v = [
        int(
            node_layout._subtree_margin(node, slot, ctx.node_count, mode_multiplier=scheme)
            * v_scale
        )
        for slot in actual_slots
    ]

    node_w = node.screenWidth()
    node_h = node.screenHeight()
    snap = ctx.snap_threshold

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
        # Each non-mask child placed so its bottom sits at (-gap_to_fan).
        # Top-of-child Y = -gap_to_fan - child_height (in parent frame, where
        # parent top is 0).  In each child's local frame the root is at (0, 0)
        # and bbox top is bbox[1] (often 0).  We translate each child so that
        # ITS root sits at the chosen Y; so child_y_for_root = -gap_to_fan - child.root_h.
        y_positions = [0] * n
        for i in range(non_mask_start, n):
            y_positions[i] = -gap_to_fan - inputs[i].screenHeight()
        for i in range(mask_count):
            raw_gap_mask = node_layout.vertical_gap_between(
                inputs[i], node, snap, scheme
            )
            gap_mask = max(snap - 1, int(raw_gap_mask * v_scale))
            gap_mask = max(gap_mask, side_margins_v[i])
            y_positions[i] = -gap_mask - inputs[i].screenHeight()
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
        bottom_y = [0] * n
        bottom_y[n - 1] = -gap_closest  # bottom edge of last band sits at -gap above parent top
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

    # ----- X placement -----
    if all_side:
        x_positions = []
        cur_alloc = node_w + side_margins_h[0]
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
        cur_alloc = node_w + side_margins_h[1]
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
        # Allocation right edge after B: max(parent right, B's bbox right in parent frame).
        # B's bbox in parent frame: alloc_left = root_x_b + child.bbox[0];
        # right = alloc_left + child_w_total.
        b_alloc_left = root_x_b + child_subtrees[non_mask_start].bbox[0]
        b_alloc_right = b_alloc_left + (
            child_subtrees[non_mask_start].bbox[2]
            - child_subtrees[non_mask_start].bbox[0]
        )
        cur_alloc = max(node_w, b_alloc_right) + (
            side_margins_h[non_mask_start + 1] if non_mask_start + 1 < n else 0
        )
        for i in range(non_mask_start + 1, n):
            child_w_total = child_subtrees[i].bbox[2] - child_subtrees[i].bbox[0]
            child_root_offset = -child_subtrees[i].bbox[0]
            x_positions[i] = cur_alloc + child_root_offset
            if i + 1 < n:
                cur_alloc += child_w_total + side_margins_h[i + 1]
        # Mask(s) placed LEFT of consumer: alloc band ends at -mask_gap_h.
        for i in range(mask_count):
            mask_gap_h = side_margins_h[i]
            child_w_total = child_subtrees[i].bbox[2] - child_subtrees[i].bbox[0]
            child_root_offset = -child_subtrees[i].bbox[0]
            alloc_left = -mask_gap_h - child_w_total
            x_positions[i] = alloc_left + child_root_offset
    else:
        # n >= 3 staircase
        root_x_0 = node_layout._center_x(inputs[0].screenWidth(), 0, node_w)
        x_positions = [root_x_0]
        cur_alloc = node_w + side_margins_h[1]
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
        # Dot sits between the consumer (this node) and the child root.
        if i in new_dots:
            dot = new_dots[i]
            dot_w = dot.screenWidth()
            dot_h = dot.screenHeight()
            child_root_x_in_parent = translated.anchor_out[0]
            actual_upstream_w = inputs[i].screenWidth()
            dot_center_x = child_root_x_in_parent + actual_upstream_w // 2
            if is_fan:
                dot_y = -(snap - 1) - dot_h
            elif i == n - 1:
                # Bottom-most dot: vertically centered next to root tile
                dot_y = (node_h - dot_h) // 2
            else:
                # Staggered: just above bottom-row, using subtree margin
                dot_y = (
                    y_positions[i] + actual_upstream_w * 0  # placeholder
                )
                dot_y = (
                    translated.bbox[3]
                    + int(
                        node_layout._subtree_margin(
                            node, actual_slots[n - 1], ctx.node_count,
                            mode_multiplier=scheme,
                        ) * v_scale
                    )
                )
            dot_x = dot_center_x - dot_w // 2
            nodes_dict[id(dot)] = (dot_x, dot_y)
            bbox_left = min(bbox_left, dot_x)
            bbox_top = min(bbox_top, dot_y)
            bbox_right = max(bbox_right, dot_x + dot_w)
            bbox_bottom = max(bbox_bottom, dot_y + dot_h)

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

    # Place root at (0, 0). Each prior spine node sits to the left.
    nodes_dict: dict[int, tuple[int, int]] = {}
    bbox_l, bbox_t, bbox_r, bbox_b = 0, 0, 0, 0
    cur_y = 0

    # Walk spine left to right (index 0 = rightmost root).
    # We place the root first, then each upstream spine node steps left.
    spine_x_per_index: list[int] = []
    for i, spine_node in enumerate(spine_nodes):
        if i == 0:
            spine_x = 0
        else:
            prev_left_edge = spine_x_per_index[i - 1]
            spine_x = prev_left_edge - step_x - spine_node.screenWidth()
        spine_x_per_index.append(spine_x)
        nodes_dict[id(spine_node)] = (spine_x, cur_y)
        # Update bbox for spine node tile
        bbox_l = min(bbox_l, spine_x)
        bbox_t = min(bbox_t, cur_y)
        bbox_r = max(bbox_r, spine_x + spine_node.screenWidth())
        bbox_b = max(bbox_b, cur_y + spine_node.screenHeight())

    # Now lay out side inputs (slot >= 1) of each spine node vertically.
    # We build a vertical Subtree for each side input via layout_vertical,
    # then translate so its root sits centered above the spine node tile.
    # Use a recursive context with horizontal_root_id=None and spine_set=None.
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
    )

    for i, spine_node in enumerate(spine_nodes):
        spine_x = spine_x_per_index[i]
        slot_count = spine_node.inputs()
        # Side inputs: slots 1+ on every spine node, plus slot 0 on the
        # leftmost spine node when its input(0) is NOT in the spine.
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
        # Last spine node: include input[0] as a vertical side input if it's
        # not part of the spine and is non-None.
        if i == len(spine_nodes) - 1:
            zero = spine_node.input(0)
            zero_eligible = (
                zero is not None
                and (spine_set is None or id(zero) not in spine_set)
                and (
                    ctx.node_filter is None
                    or node_layout._passes_node_filter(zero, ctx.node_filter)
                )
            )
            if zero_eligible:
                side_slot_pairs.insert(0, (0, zero))

        if not side_slot_pairs:
            continue

        # Lay out each side input as a vertical subtree, position it above
        # the spine node tile separated by side_v_gap.
        # If multiple side inputs, stack them rightward in horizontal bands above.
        cumulative_x = spine_x
        for slot, side_root in side_slot_pairs:
            child_subtree = layout_vertical(side_root, side_ctx)
            if slot == 0 and i == len(spine_nodes) - 1:
                # Centered above leftmost spine node
                center_x = spine_x + spine_node.screenWidth() // 2
                child_root_x = center_x - side_root.screenWidth() // 2
                target_alloc_left = child_root_x + child_subtree.bbox[0]
            else:
                # Side slot: center over spine node, but if multiple, stack rightward.
                # Simplest: center this slot above spine node tile.
                center_x = spine_x + spine_node.screenWidth() // 2
                child_root_x = center_x - side_root.screenWidth() // 2
                target_alloc_left = child_root_x + child_subtree.bbox[0]

            # Place vertical bbox so its bottom is side_v_gap above the spine row.
            target_bbox_bottom = -side_v_gap
            translated = _translate(
                child_subtree,
                child_root_x - 0,  # already calculated for root
                target_bbox_bottom - child_subtree.bbox[3],
            )
            # Recompute child_root_x precisely from translated.anchor_out
            # (anchor_out is the root tile's top-left in parent frame)
            nodes_dict.update(translated.nodes)
            bbox_l = min(bbox_l, translated.bbox[0])
            bbox_t = min(bbox_t, translated.bbox[1])
            bbox_r = max(bbox_r, translated.bbox[2])
            bbox_b = max(bbox_b, translated.bbox[3])
            cumulative_x = max(cumulative_x, translated.bbox[2])
            _ = target_alloc_left  # not used after refactor

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

        # Phase 3: detect horizontal mode.
        root_state = node_layout_state.read_node_state(root)
        root_mode = root_state.get("mode", "vertical")
        original_selected = root
        spine_set: Optional[set] = None

        if root_mode != "horizontal":
            # BFS upstream to find a horizontal-mode ancestor.
            replay_root = self._find_horizontal_ancestor(root, all_member_ids)
            if replay_root is not None:
                root = replay_root
                root_mode = "horizontal"

        if root_mode == "horizontal":
            spine_set = self._build_spine_set(root, all_member_ids)

        # Phase 4: build LayoutContext.
        # Filter out non-root freeze members so the recursion treats blocks as leaves.
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
            spine_set=spine_set,
            horizontal_root_id=id(root) if root_mode == "horizontal" else None,
        )

        # Phase 5: run recursion.
        if root_mode == "horizontal":
            subtree = layout_horizontal(root, ctx)
        else:
            subtree = layout_vertical(root, ctx)

        # Phase 6: apply. Anchor: keep root at its current position
        # so the selected node stays put (invariant from spec).
        if root_mode == "horizontal" and root is not original_selected:
            anchor_root = original_selected
        else:
            anchor_root = root
        anchor_x = anchor_root.xpos()
        anchor_y = anchor_root.ypos()

        id_to_node = collect_id_to_node(
            subtree,
            extra_nodes=[m for b in freeze_blocks for m in b.members],
        )

        # Compute translation so anchor_root lands at its current position.
        if id(anchor_root) in subtree.nodes:
            local_x, local_y = subtree.nodes[id(anchor_root)]
            dx = anchor_x - local_x
            dy = anchor_y - local_y
        else:
            dx = anchor_x - subtree.anchor_out[0]
            dy = anchor_y - subtree.anchor_out[1]

        for node_id, (lx, ly) in subtree.nodes.items():
            obj = id_to_node.get(node_id)
            if obj is None:
                continue
            obj.setXpos(lx + dx)
            obj.setYpos(ly + dy)

        # Phase 7: restore freeze block member positions (their offsets are
        # baked into nodes_dict, but if any block root was a leaf, we already
        # placed them as a unit — this is a safety net for blocks the
        # recursion didn't touch via nodes_dict).
        for block in freeze_blocks:
            if id(block.root) not in subtree.nodes:
                continue
            block.restore_positions()

        # Phase 8: state write-back.
        final_nodes = node_layout.collect_subtree_nodes(original_selected)
        for n in final_nodes:
            stored = node_layout_state.read_node_state(n)
            n_scheme = per_node_scheme.get(id(n), prefs.get("normal_multiplier"))
            stored["scheme"] = node_layout_state.multiplier_to_scheme_name(
                n_scheme, prefs
            )
            if root_mode == "horizontal" and spine_set is not None:
                stored["mode"] = "horizontal" if id(n) in spine_set else "vertical"
            else:
                stored["mode"] = "vertical"
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
        freeze_blocks, dimension_overrides, all_non_root_ids, _ = (
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

        for root in roots:
            ctx = LayoutContext(
                snap_threshold=snap,
                node_count=node_count,
                node_filter=node_filter,
                per_node_scheme=per_node_scheme,
                per_node_h_scale=per_node_h_scale,
                per_node_v_scale=per_node_v_scale,
                dimension_overrides=dimension_overrides,
            )
            subtree = layout_vertical(root, ctx)
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
            n_scheme = per_node_scheme.get(id(n), prefs.get("normal_multiplier"))
            stored["scheme"] = node_layout_state.multiplier_to_scheme_name(
                n_scheme, prefs
            )
            stored["mode"] = "vertical"
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
                freeze_blocks, dim_overrides, all_non_root_ids, _ = (
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

                snap = node_layout.get_dag_snap_threshold()
                ctx = LayoutContext(
                    snap_threshold=snap,
                    node_count=len(selected),
                    node_filter=node_filter,
                    per_node_scheme=per_node_scheme,
                    per_node_h_scale=per_node_h_scale,
                    per_node_v_scale=per_node_v_scale,
                    dimension_overrides=dim_overrides,
                    spine_set=spine_set,
                    horizontal_root_id=id(root),
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

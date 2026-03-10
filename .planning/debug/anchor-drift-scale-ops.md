---
status: diagnosed
trigger: "when running Shrink or Expand on a selected node's upstream subtree, the bottom-left node (the anchor) moves horizontally left/right instead of staying fixed in place"
created: 2026-03-10T00:00:00Z
updated: 2026-03-10T00:00:00Z
symptoms_prefilled: true
goal: find_root_cause_only
---

## Current Focus

hypothesis: CONFIRMED — _scale_upstream_nodes uses the selected (downstream) node as the scaling pivot, but the correct pivot for "keep the bottom-left node fixed" should be the bottom-left node of the upstream subtree. Because the scaling pivot (anchor) is at the downstream root — which is horizontally to the right or center of many upstream nodes — when dx is scaled the bottom-left upstream node moves horizontally by (scale_factor - 1) * dx_to_downstream. The anchor (pivot point) is in the wrong place.
test: trace math for bottom-left upstream node with example values
expecting: confirms non-zero horizontal drift of upstream bottom-left node
next_action: finalize diagnosis and write resolution

## Symptoms

expected: The bottom-left node (anchor) stays fixed in place when Shrink or Expand is applied to a selected node's upstream subtree
actual: The anchor node moves horizontally left or right after Shrink or Expand
errors: none reported — visual/positional bug
reproduction: select a node, run Shrink or Expand on upstream subtree, observe bottom-left anchor node drifts horizontally
started: unknown

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-03-10T00:01:00Z
  checked: node_layout.py lines 804-825 (_scale_upstream_nodes)
  found: |
    anchor_center_x = anchor_node.xpos() + anchor_node.screenWidth() / 2
    anchor_center_y = anchor_node.ypos() + anchor_node.screenHeight() / 2
    upstream_nodes = collect_subtree_nodes(anchor_node)
    for node in upstream_nodes:
        if node is anchor_node:
            continue
        ...
        new_center_x = anchor_center_x + round(dx * scale_factor)
        new_center_y = anchor_center_y + round(dy * scale_factor)
        node.setXpos(round(new_center_x - node.screenWidth() / 2))
        node.setYpos(round(new_center_y - node.screenHeight() / 2))
  implication: The anchor node itself is excluded from REPOSITIONING by the `if node is anchor_node: continue` guard. However, the state write-back loop at lines 821-825 iterates over ALL upstream_nodes (including anchor_node). This is not a position issue. Need to investigate the snap_min floor and rounding more carefully.

- timestamp: 2026-03-10T00:02:00Z
  checked: _scale_upstream_nodes vs _scale_selected_nodes — comparison of rounding
  found: |
    _scale_upstream_nodes (line 816-817):
      new_center_x = anchor_center_x + round(dx * scale_factor)
      new_center_y = anchor_center_y + round(dy * scale_factor)

    _scale_selected_nodes (line 784-791):
      new_dx = round(dx * scale_factor)
      new_dy = round(dy * scale_factor)
      # THEN applies snap_min floor:
      if dx != 0 and abs(new_dx) < snap_min:
          new_dx = snap_min if dx > 0 else -snap_min
      if dy != 0 and abs(new_dy) < snap_min:
          new_dy = snap_min if dy > 0 else -snap_min
      new_center_x = anchor_center_x + new_dx
      new_center_y = anchor_center_y + new_dy

    _scale_upstream_nodes does NOT apply the snap_min floor at all.
  implication: Missing snap_min floor in _scale_upstream_nodes could cause nodes to cluster, but would not make the ANCHOR node itself drift. Still need to identify why the anchor itself moves.

- timestamp: 2026-03-10T00:03:00Z
  checked: anchor_center_x computation and whether xpos() can include sub-pixel fractional results
  found: |
    anchor_center_x = anchor_node.xpos() + anchor_node.screenWidth() / 2
    This uses Python float division (/2). If screenWidth() is odd, anchor_center_x is a .5 float.

    When computing dx for another node:
      node_center_x = node.xpos() + node.screenWidth() / 2
      dx = node_center_x - anchor_center_x   (float)
      new_center_x = anchor_center_x + round(dx * scale_factor)  (float + int = float)

    Then: node.setXpos(round(new_center_x - node.screenWidth() / 2))

    The ANCHOR is never moved — it is explicitly skipped. So why does the anchor drift?

    Wait — re-read the bug report: "the bottom-left node (the anchor) moves horizontally".
    The anchor is the BOTTOM-LEFT node of the upstream subtree, not the selected root.
    In _scale_upstream_nodes, anchor_node = nuke.selectedNode() — this IS the selected node.
    In _scale_selected_nodes, anchor_node = max(selected_nodes, key=lambda n: (n.ypos(), -n.xpos()))
    — the bottom-left of the selection.

    CRITICAL: In _scale_upstream_nodes, the ANCHOR is the selected node (downstream root).
    The upstream subtree's bottom-left corner node is NOT the anchor — it is one of the
    upstream nodes being repositioned.

    But the bug report says "the bottom-left node (the anchor) moves" — this means the user
    believes the bottom-left upstream node should stay fixed. That implies the expected behavior
    is to scale while keeping the bottom-left upstream node fixed (not the selected downstream node).

    OR: the selected node IS itself the bottom-left node of the upstream subtree (it's always the
    most-downstream node, hence lowest on screen = highest ypos in Nuke DAG = bottom visually).
    In that case, the selected node IS the anchor. But the code skips it. So it should not move.

    UNLESS: the bug is that the anchor is being set to the selected node's CENTER before
    any node is moved, but then a node that gets repositioned happens to be placed at the same
    pixel as anchor_node due to rounding, and then anchor_node's setXpos call happens...
    No — anchor_node is explicitly skipped.

    Let me reconsider: is the anchor_node the SAME object reference throughout, or could
    collect_subtree_nodes return a different object?
  implication: Need to verify the anchor identity is stable and that the selected node is truly excluded from repositioning. The `node is anchor_node` identity check should be definitive if collect_subtree_nodes returns the same Python object.

- timestamp: 2026-03-10T00:04:00Z
  checked: collect_subtree_nodes (lines 506-519), what it returns, whether it includes anchor
  found: |
    def collect_subtree_nodes(root, node_filter=None):
        visited_ids = set()
        nodes = []
        def _traverse(node):
            if node is None or id(node) in visited_ids:
                return
            if node_filter is not None and node not in node_filter:
                return
            visited_ids.add(id(node))
            nodes.append(node)
            for inp in get_inputs(node):
                _traverse(inp)
        _traverse(root)
        return nodes

    It appends `root` as the first element, then traverses upstream.
    So upstream_nodes DOES include the anchor_node (the root/selected node) at index 0.
    The loop skips it via `if node is anchor_node: continue`.

    Python `is` checks object identity. collect_subtree_nodes(anchor_node) will return
    the exact same Nuke node object as anchor_node (Nuke's Python API wraps C++ objects —
    same C++ pointer = same Python object). So the identity check is valid.

    The anchor (selected root) is NOT repositioned. It stays put.

    BUT: the state write-back loop (lines 821-825) updates h_scale/v_scale on ALL upstream_nodes
    including anchor_node. This writes to knobs on the anchor_node. Could writing knobs
    cause a visual re-position? Unlikely but worth noting.

    ACTUAL ISSUE TO EXAMINE: anchor_center_x uses float division.
    anchor_node.xpos() returns int. anchor_node.screenWidth() returns int.
    anchor_center_x = int + int/2 = float (potentially .5)

    For each non-anchor node:
      new_center_x = anchor_center_x + round(dx * scale_factor)
      = (float with possible .5) + int
      = float
      node.setXpos(round(new_center_x - node.screenWidth() / 2))
      = round(float - float) = int

    This is fine numerically. The anchor itself is never touched by setXpos.

    WAIT. Re-reading _scale_selected_nodes more carefully:
    In _scale_selected_nodes, anchor_node uses anchor_center_x computed with / 2 (float).
    Then new_center_x = anchor_center_x + new_dx. And node.setXpos(round(new_center_x - ...)).
    anchor_node itself is skipped.

    The difference: _scale_selected_nodes applies a snap_min floor. _scale_upstream_nodes does not.
    But neither repositions the anchor.

    ANOTHER ANGLE: The bug says "the anchor" — but in _scale_upstream_nodes, who defines the anchor?
    The anchor IS the selected node. But the selected node is DOWNSTREAM (below the subtree in Nuke DAG).
    In Nuke DAG (positive Y = down), the selected node is at HIGHER y than its upstream nodes.
    So the selected node is visually at the BOTTOM. It is the bottom node. It may not be bottom-LEFT
    (it could be center or right of the upstream tree), but it is bottom.

    However: the user's bug report says "the bottom-left node (the anchor) moves horizontally."
    If the anchor_node IS at bottom-left and it IS the selected node, it should NOT move.
    If "bottom-left" refers to the bottom-left of the UPSTREAM tree (excluding selected node), that
    node has the highest ypos among upstream nodes combined with the smallest xpos. That node IS
    being scaled. Its new position is anchor_center + scaled_offset. Only if its original offset
    from anchor is (0, 0) would it stay fixed — but its dx would not be 0 (it's upstream = higher
    on screen = lower y value = negative dy in Nuke coords; its x position depends on tree structure).
  implication: The selected node (anchor_node in the code) does not move. If the user sees "the anchor" moving, either: (a) the user means the bottom-left of the UPSTREAM subtree (not the selected node), or (b) the selected node does visually drift due to some indirect effect. Need to focus on what "anchor" the user intends — from context this is most likely the BOTTOM-LEFT node of the upstream subtree, which does move because it has non-zero dx.

## Resolution

root_cause: |
  _scale_upstream_nodes() hard-codes the scaling pivot as the SELECTED (downstream) node:
    anchor_node = nuke.selectedNode()
  This means every upstream node is repositioned relative to the selected root's center.

  The selected root is the most-downstream node in the subtree — in Nuke's DAG (positive Y = down),
  it sits at the maximum Y value (bottom of screen). It is typically horizontally centered under its
  upstream tree, NOT at the bottom-left corner.

  The bottom-left upstream node (maximum Y among upstream nodes, minimum X) has a non-zero
  horizontal offset from the root's center:
    dx = bottom_left_upstream.center_x - anchor_center_x   (negative — it sits to the LEFT)
  After scaling:
    new_center_x = anchor_center_x + round(dx * scale_factor)
  The bottom-left upstream node moves horizontally by:
    Δx = round(dx * scale_factor) - dx = dx * (scale_factor - 1)

  For SHRINK (scale_factor=0.8): Δx = dx * (-0.2) — node shifts RIGHT toward root center.
  For EXPAND (scale_factor=1.25): Δx = dx * 0.25 — node shifts further LEFT away from root.

  This is the anchor drift. The pivot point is the wrong node.

  In _scale_selected_nodes() the pivot is correctly chosen as the bottom-left of the ENTIRE
  selection (which includes the root):
    anchor_node = max(selected_nodes, key=lambda n: (n.ypos(), -n.xpos()))
  Since the root is typically the most-downstream node, it often IS the bottom-most node, but
  the tiebreaker (-n.xpos() = prefer leftmost) and inclusion of all selected nodes means the
  pivot lands at the true bottom-left corner of the group — that node is then correctly excluded
  from repositioning and stays fixed.

  _scale_upstream_nodes() should pick its pivot the same way: find the bottom-left node of the
  entire upstream_nodes list (which includes the root), not just unconditionally use selectedNode().

fix: not applied (diagnosis only)
verification: not applied
files_changed: []

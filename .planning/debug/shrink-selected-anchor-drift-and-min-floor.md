---
status: investigating
trigger: "Investigate two bugs in shrink_selected / _scale_selected_nodes in node_layout.py: Bug 1 anchor drift, Bug 2 no minimum distance floor"
created: 2026-03-05T00:00:00Z
updated: 2026-03-05T00:00:00Z
---

## Current Focus

hypothesis: Two independent bugs: (1) anchor pick uses only Y which can select wrong node when Y is tied, and int() truncation creates systematic leftward drift of the anchor itself; (2) no minimum distance clamping exists — tight gap is snap_threshold - 1 from vertical_gap_between()
test: Code trace analysis of _scale_selected_nodes and vertical_gap_between
expecting: Both bugs confirmed by reading the code path
next_action: Document findings

## Symptoms

expected: Nodes stay in place relative to anchor after shrink. Nodes never get closer than tight/snapped distance.
actual: Nodes drift rightward on shrink. Nodes can be pushed arbitrarily close together.
errors: none
reproduction: Select multiple nodes, run shrink_selected repeatedly
started: Feature was written without these constraints

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-03-05T00:00:00Z
  checked: _scale_selected_nodes lines 696-709
  found: anchor_node = max(selected_nodes, key=lambda n: n.ypos()) — uses only ypos; anchor_x/anchor_y are set from anchor_node.xpos()/ypos(); int(dx * scale_factor) truncates toward zero
  implication: If two nodes share the same maximum ypos, the last one in iteration order wins (not leftmost). The anchor's own xpos is used correctly — but int() truncation of dx means sub-pixel remainders are discarded each call, systematically biasing non-anchor nodes leftward relative to anchor.

- timestamp: 2026-03-05T00:00:00Z
  checked: vertical_gap_between lines 86-92
  found: Returns snap_threshold - 1 for same-color/same-folder pairs, otherwise int(loose_gap_multiplier * scheme_multiplier * snap_threshold). snap_threshold default is 8 (from get_dag_snap_threshold).
  implication: The "tight distance" between nodes is snap_threshold - 1 (= 7 with default snap_threshold 8). This is the minimum meaningful gap used elsewhere in the codebase.

- timestamp: 2026-03-05T00:00:00Z
  checked: DEFAULTS in node_layout_prefs.py
  found: No snap_threshold or tight_gap key in DEFAULTS. snap_threshold comes exclusively from Nuke preferences (dag_snap_threshold knob), defaulting to 8.
  implication: The floor for minimum separation should use get_dag_snap_threshold() at call time, not a hardcoded constant. The minimum edge-to-edge gap to enforce is snap_threshold - 1.

- timestamp: 2026-03-05T00:00:00Z
  checked: int() truncation mechanics for shrink direction
  found: When shrinking (scale_factor = 0.8 < 1.0), dx is negative for nodes left of anchor, positive for nodes right of anchor. int() in Python truncates toward zero. For negative dx: int(-10.4) = -10 (moves node 0.4px closer to anchor = rightward shift). For positive dx: int(8.0) = 8 (exact). Net effect: nodes LEFT of anchor shift RIGHT toward anchor on each call — a systematic rightward drift accumulating over repeated shrinks.
  implication: This is the primary cause of the rightward drift the user observes. The anchor tiebreaker bug is secondary but also real.

## Resolution

root_cause: |
  BUG 1 (anchor/drift): Two sub-causes:
    a) Anchor selection: max(selectedNodes(), key=lambda n: n.ypos()) considers only Y. When multiple nodes share the highest Y value, the tiebreaker is arbitrary (last in nuke iteration order). Should use (ypos, xpos) as a compound key so leftmost is chosen on tie.
    b) int() truncation drift: int(dx * scale_factor) truncates toward zero. For negative dx values (nodes left of anchor), this moves nodes slightly rightward on each call. Over repeated shrinks the drift accumulates visibly.

  BUG 2 (no minimum floor): _scale_selected_nodes applies the scale unconditionally. There is no check ensuring the post-scale distance between any pair of nodes meets the minimum separation the layout system expects. The "tight distance" is snap_threshold - 1 (the value returned by vertical_gap_between for same-color/same-folder pairs). The minimum edge-to-edge gap should be snap_threshold - 1; equivalently, the minimum ypos separation between two vertically adjacent nodes should be snap_threshold - 1 + the upper node's screenHeight().

fix: |
  BUG 1a — anchor tiebreaker: change key to (ypos, xpos) ascending, so when ypos ties, leftmost wins.
    anchor_node = max(selected_nodes, key=lambda n: (n.ypos(), -n.xpos()))
    # max ypos = bottommost; among ties, max -xpos = min xpos = leftmost

  BUG 1b — int() drift: replace int(dx * scale_factor) with round(dx * scale_factor).
    round() gives nearest integer on both sides, eliminating systematic bias.
    Alternatively, track positions as floats across calls, but round() per-call
    is simpler and eliminates per-call drift completely.

  BUG 2 — minimum floor: after computing new dx/dy, clamp so no node ends up
    closer than snap_threshold - 1 pixels (edge-to-edge) to the anchor node in
    each axis independently. Because _scale_selected_nodes operates on arbitrary
    selections (not just connected pairs), the floor is best expressed as:
    each node's distance from the anchor (in absolute pixels) must be at least
    snap_threshold - 1 in any direction where it is non-zero.
    Enforce inside the per-node loop, after computing new_dx/new_dy but before
    calling setXpos/setYpos.
    Minimum gap = get_dag_snap_threshold() - 1.

verification: not yet applied
files_changed: []

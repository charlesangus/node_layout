---
status: diagnosed
trigger: "after running Shrink or Expand (which stores h_scale/v_scale in node_layout_state), subsequently running Layout Upstream or Layout Selected does not respect the stored scale — nodes are laid out as if h_scale/v_scale are 1.0"
created: 2026-03-10T00:00:00Z
updated: 2026-03-10T00:00:00Z
---

## Current Focus

hypothesis: h_scale/v_scale are stored per-node by Shrink/Expand but are never read back during layout_upstream() or layout_selected() — the layout path only reads the "scheme" key from stored state, completely ignoring h_scale/v_scale
test: traced full call path from layout_upstream() through compute_dims() and place_subtree()
expecting: confirmed — h_scale/v_scale are written but never consumed
next_action: DONE — diagnosis complete

## Symptoms

expected: After Shrink/Expand stores h_scale/v_scale per-node, a subsequent Layout Upstream or Layout Selected run should apply those scale factors to node spacing so the layout respects the previously applied scale
actual: Layout Upstream and Layout Selected lay out nodes as if h_scale=1.0 and v_scale=1.0 — the stored scale is silently ignored
errors: none (silent behavior mismatch)
reproduction: 1. Select nodes, run Expand. 2. Run Layout Upstream on the same root. 3. Result is identical to running Layout Upstream with no prior scale.
started: by design gap — h_scale/v_scale were added to the state schema but the layout read-back path was never wired to use them

## Eliminated

- hypothesis: h_scale/v_scale are read and passed to compute_dims
  evidence: layout_upstream() reads stored_state["scheme"] and converts it via scheme_name_to_multiplier() but does NOT read stored_state["h_scale"] or stored_state["v_scale"] at all
  timestamp: 2026-03-10

- hypothesis: compute_dims or place_subtree apply h_scale/v_scale internally via some lookup
  evidence: both functions accept only scheme_multiplier; there is no h_scale/v_scale parameter anywhere in their signatures or bodies
  timestamp: 2026-03-10

## Evidence

- timestamp: 2026-03-10
  checked: _scale_selected_nodes() and _scale_upstream_nodes() in node_layout.py (lines 768-825)
  found: both functions accumulate h_scale and v_scale into per-node state via write_node_state() after moving nodes
  implication: h_scale/v_scale correctly record the cumulative geometric scale factor on each node

- timestamp: 2026-03-10
  checked: layout_upstream() per-node scheme resolution block (lines 601-614)
  found: reads stored_state["scheme"] only, converts it to a float multiplier via scheme_name_to_multiplier(), then passes that single float as scheme_multiplier to compute_dims() and place_subtree()
  implication: h_scale and v_scale in stored_state are never accessed during layout

- timestamp: 2026-03-10
  checked: layout_selected() per-node scheme resolution block (lines 683-692)
  found: identical pattern — reads stored_state["scheme"] only, ignores h_scale/v_scale
  implication: same gap in layout_selected as in layout_upstream

- timestamp: 2026-03-10
  checked: compute_dims() signature (line 285) and body
  found: accepts scheme_multiplier (one scalar), uses it uniformly for both horizontal and vertical spacing via _subtree_margin() and vertical_gap_between(); no separate h_scale/v_scale parameters exist
  implication: there is no mechanism to pass independent horizontal vs vertical scale into the geometry engine

- timestamp: 2026-03-10
  checked: place_subtree() signature (line 336) and body
  found: same — only scheme_multiplier; horizontal positions are computed from _horizontal_margin() (prefs-only, no scale) and vertical from _subtree_margin() (uses mode_multiplier=scheme_multiplier)
  implication: horizontal spacing (side margins) is never scaled at all even by scheme_multiplier — only vertical spacing uses the scheme multiplier

- timestamp: 2026-03-10
  checked: state write-back in layout_upstream() (lines 624-635) and layout_selected() (717-730)
  found: comment on line 634 explicitly says "h_scale and v_scale are NOT reset by re-layout — preserve existing values"; code reads stored_state, updates only scheme and mode, then writes back — so h_scale/v_scale survive the layout pass but are still never used
  implication: the code intentionally preserves the stored values but has no code path that acts on them

## Resolution

root_cause: |
  h_scale and v_scale are stored correctly by _scale_selected_nodes() and
  _scale_upstream_nodes(), but the layout functions (layout_upstream,
  layout_selected) only read stored_state["scheme"] from per-node state.
  The h_scale/v_scale fields are never read back, and neither compute_dims()
  nor place_subtree() have parameters to receive them.  The result is that
  every layout run treats every node as if h_scale=1.0 and v_scale=1.0
  regardless of how many Shrink/Expand operations preceded it.

  Secondary structural gap: compute_dims and place_subtree use a single scalar
  (scheme_multiplier) for spacing.  h_scale would need to scale horizontal
  margins and v_scale would need to scale vertical margins independently, but
  the current API has no way to express that split — both dimensions share
  the same multiplier.

fix: NOT APPLIED — diagnosis only
verification: NOT APPLIED — diagnosis only
files_changed: []

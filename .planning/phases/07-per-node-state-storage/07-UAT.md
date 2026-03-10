---
status: complete
phase: 07-per-node-state-storage
source: [07-01-SUMMARY.md, 07-02-SUMMARY.md, 07-03-SUMMARY.md, 07-04-SUMMARY.md, 07-05-SUMMARY.md]
started: 2026-03-10T11:00:00Z
updated: 2026-03-10T11:05:00Z
---

## Current Test

[testing complete]

## Tests

### 1. State knob written after layout
expected: Run Layout Upstream or Layout Selected on a node. The node_layout_state knob and its tab should both be invisible — neither should appear in the properties panel. Verify via Script Editor: nuke.selectedNode()['node_layout_state'].value() should return JSON with scheme, mode, h_scale, v_scale.
result: pass

### 2. State persists across .nk save/load
expected: After laying out nodes (so they have the node_layout_state knob), save the .nk file and reopen it. Select a node that was laid out — its node_layout_state knob should still be present with the same JSON data (check via Script Editor).
result: pass

### 3. Scheme replay on re-layout
expected: Layout a node with an explicit scheme (e.g., "Layout Upstream Compact"). The node gets node_layout_state with scheme=compact. Now run plain "Layout Upstream" (no scheme argument) on the same node. The layout should use the previously stored compact scheme — nodes should be positioned as if compact was passed explicitly.
result: pass

### 4. Scale accumulation across multiple Shrink/Expand ops
expected: Select a node and run Shrink once. Check node_layout_state — h_scale and v_scale should be < 1.0. Run Shrink again. The values should be smaller still (multiplied, not reset). Run Expand to confirm it multiplies in the opposite direction. Values should never reset to 1.0 unless you clear state.
result: issue
reported: "Works, but subsequent layouts do not respect the setting. Also, the shrink/expand is still not correctly anchoring on the bottom-left node. The bottom left node is moving right and left."
severity: major

### 5. Clear Layout State Selected removes knob
expected: Select one or more nodes that have a node_layout_state knob. Run "Clear Layout State Selected" from the menu. The node_layout_state knob should be gone from those nodes (check via Script Editor). Nodes that were NOT selected should be unaffected.
result: pass

### 6. Clear Layout State Upstream removes knob
expected: Select a root node with upstream nodes that all have node_layout_state knobs. Run "Clear Layout State Upstream" from the menu. All upstream nodes (and the root) should have their node_layout_state knob removed. Nodes outside that subtree should be unaffected.
result: pass

### 7. Clear-state commands appear in menu
expected: Open the Nuke menu where layout commands live. Both "Clear Layout State Selected" and "Clear Layout State Upstream" should appear as menu items, grouped near the Layout Selected commands.
result: pass

## Summary

total: 7
passed: 6
issues: 2
pending: 0
skipped: 0

## Gaps

- truth: "node_layout_tab Tab_Knob should be invisible (not visible in properties panel)"
  status: resolved
  reason: "User reported: The tab must be hidden as well as the knob."
  severity: minor
  test: 1
  fix: "Set INVISIBLE flag on Tab_Knob in write_node_state() — committed 3179afa"

- truth: "Subsequent layouts after Shrink/Expand should respect stored h_scale/v_scale"
  status: failed
  reason: "User reported: Works, but subsequent layouts do not respect the setting."
  severity: major
  test: 4
  artifacts: []
  missing: []

- truth: "Shrink/Expand should anchor on the bottom-left node (it should not move)"
  status: failed
  reason: "User reported: The bottom left node is moving right and left."
  severity: major
  test: 4
  artifacts: []
  missing: []

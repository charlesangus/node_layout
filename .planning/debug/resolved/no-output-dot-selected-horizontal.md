---
status: resolved
trigger: "Investigate why Layout Selected Horizontal produces no output Dot below the root (rightmost) spine node"
created: 2026-03-14T00:00:00Z
updated: 2026-03-14T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED — _find_or_create_output_dot is never called in _layout_selected_horizontal_impl
test: grep all call sites of _find_or_create_output_dot in node_layout.py
expecting: call missing in the selected-horizontal path
next_action: report findings

## Symptoms

expected: An output Dot appears below the root (rightmost) spine node after Layout Selected Horizontal
actual: No dot appears
errors: None (silent omission)
reproduction: Select a chain of nodes, run Layout Selected Horizontal
started: Always (feature gap, not regression)

## Eliminated

(none needed — root cause found in first pass)

## Evidence

- timestamp: 2026-03-14
  checked: All call sites of _find_or_create_output_dot in node_layout.py
  found: |
    Line 1213: called after place_subtree_horizontal in the layout_upstream (replay-horizontal) path
    Line 1340: called after place_subtree_horizontal in the layout_selected (multi-root replay) path
    Lines 1456-1470: _layout_selected_horizontal_impl calls place_subtree_horizontal but NEVER calls _find_or_create_output_dot
  implication: The selected-horizontal path is the only horizontal layout path that omits the output Dot call.

## Resolution

root_cause: _layout_selected_horizontal_impl (lines 1456-1470) calls place_subtree_horizontal for each root but never calls _find_or_create_output_dot(root, root, 0, current_group) afterward, unlike the two other horizontal layout paths (layout_upstream horizontal-replay at line 1213 and layout_selected multi-root replay at line 1340) which both call it immediately after place_subtree_horizontal.
fix: After the place_subtree_horizontal call inside _layout_selected_horizontal_impl (around line 1470), add _find_or_create_output_dot(root, root, 0, current_group) for each root.
verification: applied — fixed by commit 65f50f8
files_changed:
  - node_layout.py

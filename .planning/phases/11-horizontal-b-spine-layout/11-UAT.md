---
status: complete
phase: 11-horizontal-b-spine-layout
source: 11-01-SUMMARY.md, 11-02-SUMMARY.md, 11-03-SUMMARY.md + post-UAT redesign
started: 2026-03-13T01:30:00Z
updated: 2026-03-14T13:30:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

[testing complete]

## Tests

### 1. Menu entries visible
expected: Open the Nuke menu where layout commands live. You should see two new entries:
"Layout Selected Horizontal" and "Layout Selected Horizontal (Place Only)" — placed after
the "Clear Layout State" commands and before the Shrink section.
result: pass

### 2. Layout Selected Horizontal — basic left-to-right spine
expected: Create a linear chain of 4+ nodes (A → B → C → D). Select all 4. Run
"Layout Selected Horizontal". D should be rightmost. C one step left. B further left.
A furthest left. All nodes on roughly the same Y axis (horizontal spine). An output Dot
appears below D (for downstream wire routing).
result: issue
reported: "No dot."
severity: major

### 3. Leftmost Dot placement
expected: After running "Layout Selected Horizontal" on a chain (select all spine nodes)
where the leftmost spine node (A) has an unselected upstream input (E): a Dot appears
to the LEFT of A, at the same Y level as the spine (vertically centered with A). E's
subtree is placed ABOVE the Dot. The Dot is X-centered beneath E's root node.
result: pass

### 4. Side inputs placed above spine — adequate spacing
expected: Create a Merge (B + A inputs) and select it along with its B-input chain.
Run "Layout Selected Horizontal". The B-chain forms the horizontal spine. The A-input
(unselected) is placed above its spine node with its full upstream subtree laid out
vertically. Adjacent side subtrees should have adequate horizontal breathing room
(no overlapping bounding boxes between side subtrees of neighbouring spine nodes).
result: pass

### 5. Mask kink staircase
expected: Create a chain where one spine node has a mask connection (input slot "M").
Select all spine nodes. Run "Layout Selected Horizontal". The spine nodes downstream of
the masked node sit slightly lower in Y (staircase kink), making room for the mask
subtree above. The spine should not be perfectly flat through the masked node.
result: pass

### 6. Output and leftmost Dot reuse on re-layout
expected: Run "Layout Selected Horizontal" on the same selection twice. On the second
run, NO duplicate output Dot appears below the root, and NO duplicate leftmost Dot
appears to the left. Both Dots are reused and repositioned.
result: pass

### 7. HORIZ-03 mode replay — normal layout replays horizontal
expected: Run "Layout Selected Horizontal" on a chain (stores mode='horizontal' on the
selected nodes). Scramble the positions. Now run normal "Layout Upstream" or "Layout
Selected" on the same root. It should automatically replay in horizontal mode — the
result matches running "Layout Selected Horizontal" directly.
result: issue
reported: "fail - only works if you select that exact root, If you select a downstream node and run layout upstream, the horizontal mode flag is ignored."
severity: major

### 8. Place Only — translates subtrees without re-layout
expected: Build a chain with side subtrees that have complex internal layouts. Select
the spine nodes. Run "Layout Selected Horizontal (Place Only)". The spine nodes snap to
the horizontal layout. Side subtrees MOVE to above their spine nodes as rigid units
(all relative positions within each subtree are preserved — not re-laid-out). Running
normal layout afterward does NOT replay as horizontal (mode was not stored).
result: issue
reported: "fail - subsequent layout selected/upstream _should_ replay the horizontally-laid-out nodes as horizontal."
severity: major

## Summary

total: 8
passed: 5
issues: 3
pending: 0
skipped: 0

## Gaps

- truth: "An output Dot appears below the root (rightmost) spine node after Layout Selected Horizontal"
  status: failed
  reason: "User reported: No dot."
  severity: major
  test: 2
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "Running Layout Upstream on any downstream node of a horizontal chain replays the horizontal mode, not just when selecting the exact stored root"
  status: failed
  reason: "User reported: fail - only works if you select that exact root, If you select a downstream node and run layout upstream, the horizontal mode flag is ignored."
  severity: major
  test: 7
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "Running Layout Selected or Layout Upstream after Place Only should replay the spine nodes as horizontal (mode stored by Place Only)"
  status: failed
  reason: "User reported: fail - subsequent layout selected/upstream _should_ replay the horizontally-laid-out nodes as horizontal."
  severity: major
  test: 8
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

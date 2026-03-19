---
status: diagnosed
phase: 16-layout-integration
source: [16-01-SUMMARY.md, 16-02-SUMMARY.md]
started: 2026-03-19T00:00:00Z
updated: 2026-03-19T02:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Test suite passes
expected: Run `python3 -m pytest tests/test_freeze_layout.py -v`. All 18 freeze layout tests pass. Full suite (331 tests) also green.
result: pass

### 2. Frozen nodes hold positions after layout (Nuke)
expected: In Nuke — freeze a group of 2+ nodes (Freeze Selected), then run Layout Upstream or Layout Selected on a DAG that includes those nodes. The frozen nodes do not move relative to each other; non-frozen upstream nodes are repositioned normally around them.
result: issue
reported: "The frozen nodes are positioned correctly. The non-frozen nodes above them are not moved; this is incorrect, they should be laid out normally above the frozen group."
severity: major

### 3. Auto-join: node inserted between frozen nodes (Nuke)
expected: In Nuke — with a freeze group already set up, wire a new (unfrozen) node between two frozen nodes in the DAG. Run layout again. The inserted node automatically behaves as part of the frozen block (moves with it) without needing to manually freeze it.
result: pass

### 4. Partial selection expands to include full freeze group (Nuke)
expected: In Nuke — freeze 3 nodes (A, B, C) into a group. Select only node A and run Layout Selected. The layout expands scope silently to include B and C as well — all three move together as a unit, even though only A was in the selection.
result: issue
reported: "Incorrect behaviour. The frozen group layout is changed. In addition, layout selected on a bunch of nodes, some of which are frozen, produces incorrect dot locations (in addition to the same error already mentioned about layout upstream)."
severity: major

### 5. Frozen block moves as unit during push-away (Nuke)
expected: In Nuke — freeze a group of nodes into a block. Use Expand/Push-Away (e.g., Expand Selected or the push triggered by layout). The entire frozen block translates by the same delta — no individual block member is pushed independently of the others.
result: issue
reported: "NameError: name \"make_room\" is not defined"
severity: blocker

### 6. Freeze overrides horizontal mode (Nuke)
expected: In Nuke — mark some nodes as horizontal (Layout Selected Horizontal), then freeze a subset that overlaps with the horizontal spine. Run layout. The frozen nodes are treated as a freeze block, not as part of the horizontal spine. The horizontal spine walk stops at the frozen node boundaries.
result: issue
reported: "Fail. The frozen nodes are laid out normally."
severity: major

## Summary

total: 6
passed: 2
issues: 5
pending: 0
skipped: 0

## Gaps

- truth: "Non-frozen nodes upstream of a frozen block are repositioned normally by layout"
  status: failed
  reason: "User reported: The frozen nodes are positioned correctly. The non-frozen nodes above them are not moved; this is incorrect, they should be laid out normally above the frozen group."
  severity: major
  test: 2
  root_cause: "vertical_freeze_filter excludes non-root block members (freeze_excluded_ids). If a non-frozen upstream node connects through an excluded non-root member, place_subtree cannot traverse through it (_passes_node_filter returns False), so those upstream nodes are never visited and never repositioned."
  artifacts:
    - path: "node_layout.py"
      issue: "place_subtree traversal blocked by freeze_excluded_ids — non-frozen nodes above excluded block members are unreachable"
  missing:
    - "Non-frozen nodes upstream of the freeze block must be collected and positioned above the anchored block after it is placed"

- truth: "Frozen group node positions are preserved (do not change) during layout"
  status: failed
  reason: "User reported: The frozen group layout is changed."
  severity: major
  test: 4
  root_cause: "Only non-root block members are added to freeze_excluded_ids. The block root is included in node_filter and freely repositioned by place_subtree. Offset restoration then moves all members relative to the new root position — the entire block translates to wherever the layout algorithm places the root."
  artifacts:
    - path: "node_layout.py"
      issue: "freeze block root not held at its original absolute position — only relative intra-block offsets preserved, not the block's absolute location"
  missing:
    - "Capture block root's absolute position before place_subtree; restore it (and all member offsets) afterward so the entire block stays at its original location"

- truth: "Dot node positions are correct when Layout Selected is run on a mixed selection containing frozen nodes"
  status: failed
  reason: "User reported: layout selected on a bunch of nodes, some of which are frozen, produces incorrect dot locations"
  severity: major
  test: 4
  root_cause: "insert_dot_nodes is called with node_filter that already has non-root freeze members removed. Connections passing through excluded members are invisible to dot insertion, so dots at those junctions are misplaced or not created, based on incomplete graph geometry."
  artifacts:
    - path: "node_layout.py"
      issue: "insert_dot_nodes called after freeze_excluded_ids removed from node_filter — dot insertion has incomplete graph view"
  missing:
    - "Dot insertion must see full block geometry; block root should act as opaque boundary rather than leaving a traversal hole through excluded members"

- truth: "Expand/Push-Away runs without error when frozen nodes are present"
  status: failed
  reason: "User reported: NameError: name \"make_room\" is not defined"
  severity: blocker
  test: 5
  root_cause: "menu.py registers Make Room commands as string expressions (e.g. 'make_room.make_room()') evaluated by Nuke at invocation, but never imports the make_room module. The name is not in scope when Nuke evaluates the string."
  artifacts:
    - path: "menu.py"
      issue: "missing 'import make_room' — all six Make Room addCommand calls reference make_room.* but the module is never imported"
  missing:
    - "Add 'import make_room' to menu.py after existing imports"

- truth: "Frozen nodes are excluded from horizontal spine walk; freeze membership overrides stored mode=horizontal"
  status: failed
  reason: "User reported: Fail. The frozen nodes are laid out normally."
  severity: major
  test: 6
  root_cause: "The BFS that searches upstream for a horizontal replay root does not check node_freeze_uuid. It rebinds root to a frozen node if its stored mode is 'horizontal'. The spine walk's freeze guard (id(cursor) != id(root)) cannot stop the walk at the first node (which is now the rebounded frozen root), so the frozen node is added to the spine and laid out normally."
  artifacts:
    - path: "node_layout.py"
      issue: "BFS for horizontal replay root (layout_upstream ~lines 1737-1755, layout_selected ~lines 2185-2206) does not skip frozen nodes — frozen nodes with mode=horizontal become layout roots and are repositioned"
  missing:
    - "In both BFS loops, skip any candidate whose id() is in node_freeze_uuid before rebinding root"

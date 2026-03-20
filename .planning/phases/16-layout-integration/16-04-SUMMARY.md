---
phase: 16-layout-integration
plan: "04"
subsystem: freeze-layout
tags: [freeze, layout, bug-fix, regression-tests]
dependency_graph:
  requires: [16-03]
  provides: [freeze-layout-gap-closure]
  affects: [node_layout.py, tests/test_freeze_layout.py]
tech_stack:
  added: []
  patterns: [id()-based set comprehension for node filter, BFS freeze guard, upstream second-pass BFS]
key_files:
  created: [tests/test_freeze_layout.py (TestFreezeGapClosure class added)]
  modified: [node_layout.py, tests/test_freeze_layout.py]
decisions:
  - "layout_selected node_filter correction uses set comprehension with id() comparison — same pattern already used in layout_upstream vertical_freeze_filter"
  - "upstream_non_frozen second pass BFS starts from block members inputs, not from freeze block root — avoids re-traversing already-placed block"
  - "layout_selected scope restriction (scope_ids guard) prevents repositioning nodes outside user's selected subgraph in the second pass"
  - "BFS freeze guard continues traversal through frozen nodes rather than stopping — allows non-frozen horizontal nodes further upstream to still be found"
metrics:
  duration: "3m 22s"
  completed_date: "2026-03-20"
  tasks_completed: 2
  files_changed: 2
---

# Phase 16 Plan 04: Freeze Integration Bug Fixes Summary

Fix three distinct freeze-layout integration bugs with id()-based set comprehension, upstream second-pass BFS, and BFS horizontal replay root freeze guard — closing four UAT gaps.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix all three freeze integration bugs in node_layout.py | 76687a5 | node_layout.py (+181 lines) |
| 2 | Add regression tests for all three gap closure fixes | f902a80 | tests/test_freeze_layout.py (+229 lines) |

## What Was Built

Three targeted fixes to `node_layout.py` closing four UAT gaps in the freeze layout feature:

**Change A — Fix type mismatch in layout_selected (Gaps 2 and 3)**

Root cause: `node_filter -= freeze_excluded_ids` was a no-op. Python set difference between a set of node objects and a set of `int` id() values is always empty — no members were removed. Non-root freeze members remained in `node_filter`, causing `insert_dot_nodes` to traverse through them and `place_subtree` to reposition them independently. After offset restoration, any Dots placed inside the freeze group were stranded.

Fix: `node_filter = {n for n in node_filter if id(n) not in freeze_excluded_ids}` — matching the pattern already used in `layout_upstream` for `vertical_freeze_filter`.

**Change B — Post-pass for non-frozen upstream nodes (Gap 1)**

Root cause: `place_subtree` could not traverse through excluded non-root block members. Non-frozen nodes only reachable through those excluded members were never visited or repositioned.

Fix: Added a second-pass BFS after offset restoration in both `layout_upstream` and `layout_selected`. The BFS starts from each block member's inputs, collects non-frozen nodes, then calls `place_subtree` to position them above the now-anchored block. In `layout_selected`, an additional `scope_ids` guard restricts the pass to nodes within the original selection scope.

**Change C — Skip frozen nodes in BFS horizontal replay root search (Gap 5)**

Root cause: The BFS that searches upstream for a horizontal replay root did not check `node_freeze_uuid`. A frozen node with `mode=horizontal` in its stored state could become the replay root and be repositioned.

Fix: Added a freeze guard in both BFS loops (in `layout_upstream` and `layout_selected`) that skips frozen nodes as root candidates while continuing BFS traversal through their inputs.

**Regression tests (Task 2)**

Added `TestFreezeGapClosure` class with 4 tests:
- `test_layout_selected_excludes_non_root_members_from_filter` — demonstrates the broken `-=` and verifies the corrected comprehension
- `test_frozen_block_moves_as_unit_in_layout_selected` — verifies offset restoration preserves relative position
- `test_frozen_node_not_used_as_horizontal_replay_root` — replicates the BFS with freeze guard, asserts frozen node not bound as root
- `test_non_frozen_upstream_nodes_repositioned_after_freeze_block` — verifies second-pass BFS collects D and E upstream of excluded freeze block members

## Verification

- `python3 -m pytest tests/test_freeze_layout.py -x -v` — 22 tests pass (18 existing + 4 new gap closure)
- `python3 -m pytest tests/ -x -q` — 335 tests pass (full suite)
- `grep "n for n in node_filter if id(n) not in freeze_excluded_ids" node_layout.py` — fix present (1 match)
- `grep "upstream_non_frozen" node_layout.py` — second-pass logic present (10 matches, in both entry points)
- `grep "id(bfs_cursor) in node_freeze_uuid" node_layout.py` — BFS freeze guard in both loops (2 matches)

## Deviations from Plan

None — plan executed exactly as written. All three changes applied to the specified locations with the exact patterns described in the plan.

## Self-Check: PASSED

- node_layout.py modified: FOUND
- tests/test_freeze_layout.py modified: FOUND
- Commit 76687a5: FOUND
- Commit f902a80: FOUND
- 335 tests passing: CONFIRMED

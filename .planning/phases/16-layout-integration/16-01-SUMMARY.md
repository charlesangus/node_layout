---
phase: 16-layout-integration
plan: "01"
subsystem: node_layout
tags: [freeze-layout, preprocessing, auto-join, group-merge, scope-expansion, tdd]
dependency_graph:
  requires: [node_layout_state.read_freeze_group, node_layout_state.write_freeze_group]
  provides: [_detect_freeze_groups, _expand_scope_for_freeze_groups, _find_freeze_block_root]
  affects: [layout_upstream, layout_selected]
tech_stack:
  added: []
  patterns: [iterative-auto-join-loop, upstream-downstream-bfs, uuid-merge]
key_files:
  created: [tests/test_freeze_layout.py]
  modified: [node_layout.py]
decisions:
  - "_detect_freeze_groups merges groups when ancestor_uuids | descendant_uuids has 2+ entries (not intersection-based), correctly handling cross-group bridging"
  - "_expand_scope_for_freeze_groups uses current_group.nodes() when context available, falls back to nuke.allNodes()"
  - "Auto-join iterative loop re-checks all non-frozen nodes after each join/merge to handle chain reactions"
metrics:
  duration: 4min
  completed: "2026-03-19"
  tasks_completed: 2
  files_modified: 2
---

# Phase 16 Plan 01: Freeze Group Preprocessing Summary

Freeze group preprocessing for layout engine: `_detect_freeze_groups` with iterative BFS auto-join and group merge, `_expand_scope_for_freeze_groups` for partial selection expansion, and `_find_freeze_block_root` for identifying the most-downstream block member. Integrated into both `layout_upstream` and `layout_selected` inside undo groups before any positioning.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 (RED) | Create test_freeze_layout.py | 9ecdbd2 | tests/test_freeze_layout.py |
| 2 (GREEN) | Implement preprocessing functions and integration | e595576 | node_layout.py |

## What Was Built

### `_find_freeze_block_root(block_members)` (node_layout.py line 1394)
Identifies the most-downstream node in a freeze group. Checks which member is not used as input by any other member. Tiebreaks by `max(ypos())` — highest Y value is lowest on screen (positive Y is down in Nuke DAG).

### `_detect_freeze_groups(scope_nodes)` (node_layout.py line 1422)
Two-pass algorithm:
1. **Pass 1**: Scans all scope nodes, reads `node_layout_state.read_freeze_group()`, builds `freeze_group_map` (UUID → list of nodes) and `node_freeze_uuid` (id(node) → UUID).
2. **Pass 2**: Iterative loop over non-frozen nodes. For each candidate, BFS upstream for frozen ancestor UUIDs, BFS downstream via `downstream_map` for frozen descendant UUIDs. If both are non-empty: single shared group → auto-join via `write_freeze_group`; two different groups → merge with `str(uuid.uuid4())` persisted to all affected nodes.

Key design decision: merge triggers when `ancestor_uuids | descendant_uuids` has 2+ entries (not the intersection), correctly handling the case where a node bridges group-A (upstream) and group-B (downstream).

### `_expand_scope_for_freeze_groups(selected_nodes, current_group)` (node_layout.py line 1544)
Scans selected nodes for freeze UUIDs, then scans all nodes in `current_group.nodes()` (or `nuke.allNodes()` as fallback) to find additional members of those same groups. Returns the union, deduplicated by `id(node)`.

### Integration points
- **`layout_upstream`** (line 1605): calls `_expand_scope_for_freeze_groups` then `_detect_freeze_groups` inside `with current_group:` block, before `original_subtree_nodes = collect_subtree_nodes(root)`.
- **`layout_selected`** (line 2007): expands `node_filter` and `selected_nodes` via `_expand_scope_for_freeze_groups`, then calls `_detect_freeze_groups`, both before `find_selection_roots`.

## Test Coverage

10 new tests in `tests/test_freeze_layout.py` (323 total in suite):

| Class | Tests |
|-------|-------|
| TestFreezePreprocessing | detect_groups_returns_maps, no_frozen_nodes_returns_empty, multiple_groups_detected |
| TestFreezeAutoJoin | node_between_frozen_nodes_joins, node_only_downstream_does_not_join, mixed_inputs_with_frozen_descendant_joins |
| TestFreezeGroupMerge | bridging_node_merges_two_groups, merge_persists_via_write_freeze_group |
| TestFreezeScopeExpansion | partial_selection_expands_to_full_group, no_expansion_when_no_frozen_nodes |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Merge condition used intersection instead of union for detecting cross-group bridges**
- **Found during:** Task 2 GREEN phase (test `test_bridging_node_merges_two_groups` failed)
- **Issue:** Plan algorithm checked `ancestor_uuids & descendant_uuids` (intersection) for both auto-join and merge. For cross-group bridges, the intersection is empty (group-A ≠ group-B), so the merge was never triggered.
- **Fix:** Changed condition to use `ancestor_uuids | descendant_uuids` (union). Single-UUID union = auto-join; multi-UUID union = merge.
- **Files modified:** node_layout.py
- **Commit:** e595576

## Self-Check: PASSED

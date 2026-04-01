---
phase: quick-260331-otl
plan: 1
subsystem: leader-dispatch
tags: [leader-keys, context-aware, clear-state, undo]
key-files:
  modified: [node_layout_leader.py]
decisions:
  - "_dispatch_clear_state() follows same context-aware pattern as _dispatch_shrink()/_dispatch_expand()"
metrics:
  duration: ~2min
  completed: 2026-03-31
  tasks_completed: 1
  files_modified: 1
---

# Quick Task 260331-otl: Make clear-state leader command context-aware

**One-liner:** C leader key now triggers upstream-tree clear when 1 node selected, selected-only clear when >1 selected.

## What Was Done

Updated `_dispatch_clear_state()` in `node_layout_leader.py` to check `len(nuke.selectedNodes())` and route to the appropriate function:

- **1 node selected** → `node_layout.clear_layout_state_upstream()` (clears selected node + all upstream)
- **>1 nodes selected** → `node_layout.clear_layout_state_selected()` (clears only selected nodes)
- **0 nodes selected** → no-op (implicit fall-through)

This matches the context-aware pattern already established by `_dispatch_shrink()` and `_dispatch_expand()` from quick task 260331-nc2.

## Commits

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Make C dispatch context-aware | 7d46984 |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- [x] `/workspace/node_layout_leader.py` modified and committed (7d46984)
- [x] `_dispatch_clear_state()` contains `selected_count = len(nuke.selectedNodes())`
- [x] Both `clear_layout_state_upstream` and `clear_layout_state_selected` referenced
- [x] File passes `ast.parse()` syntax check

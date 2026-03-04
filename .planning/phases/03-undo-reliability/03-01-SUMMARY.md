---
phase: 03-undo-reliability
plan: "01"
subsystem: undo-wrapping
tags: [undo, reliability, tdd, ast-tests]
dependency_graph:
  requires: []
  provides: [undo-group-wrapping]
  affects: [layout_upstream, layout_selected]
tech_stack:
  added: []
  patterns: [try-except-else undo group, AST structural tests]
key_files:
  created:
    - node_layout/tests/test_undo_wrapping.py
  modified:
    - node_layout/node_layout.py
decisions:
  - "Use try/except/else (not finally) for undo group — nuke.Undo.end() strictly in else, nuke.Undo.cancel() strictly in except, matching the Nuke API contract"
  - "Early-return guard for layout_selected() placed before undo group open — no empty undo entries created when fewer than 2 nodes selected"
  - "All mutations (collect, insert_dot_nodes through push_nodes_to_make_room) inside the try block — guarantees atomic rollback on any exception"
metrics:
  duration: "2 min"
  completed_date: "2026-03-04"
  tasks_completed: 2
  files_changed: 2
requirements_addressed: [UNDO-01, UNDO-02]
---

# Phase 3 Plan 01: Undo Group Wrapping Summary

**One-liner:** Added nuke.Undo group wrapping to layout_upstream() and layout_selected() using try/except/else pattern so Ctrl+Z undoes all node movements and Dot insertions in one step.

## What Was Built

Both layout entry-point functions in `node_layout/node_layout.py` now wrap all mutating operations inside a single Nuke undo group. The wrapping follows the Nuke API contract precisely:

- `nuke.Undo.name()` sets the label before `nuke.Undo.begin()` opens the group
- All mutations (Dot insertion, dimension computation, placement, room-pushing) are inside a `try` block
- `nuke.Undo.cancel()` + bare `raise` in the `except Exception` clause rolls back and re-raises
- `nuke.Undo.end()` in the `else` clause commits — never in `finally`

For `layout_selected()`, the early-return guard (`if len(selected_nodes) < 2: return`) remains before the undo group opens, preventing empty undo entries.

## Tasks Completed

### Task 1: Write failing AST structural tests (RED)

Created `node_layout/tests/test_undo_wrapping.py` with two test classes:

- `TestUndoWrappingLayoutUpstream` — 7 structural tests for `layout_upstream()`
- `TestUndoWrappingLayoutSelected` — 7 structural tests for `layout_selected()`

Tests use AST analysis and `ast.get_source_segment()` to verify structural properties without the Nuke runtime. String-position ordering checks confirm `begin()` precedes first mutation and `push_nodes_to_make_room` precedes `end()`. All 12 substantive tests failed (RED) before implementation.

Commit: `90f9d38`

### Task 2: Add undo group wrapping to both functions (GREEN)

Modified `node_layout/node_layout.py` — the two entry-point functions only. No other functions were touched.

After modification:
- 8 Undo-related lines total (2x name, 2x begin, 2x cancel, 2x end)
- 0 `finally` blocks in either function
- All 54 tests pass (14 new + 40 existing from phases 1 and 2)

Commit: `dd48190`

## Deviations from Plan

None — plan executed exactly as written.

## Verification

```
grep -n "Undo" node_layout/node_layout.py
559:    nuke.Undo.name("Layout Upstream")
560:    nuke.Undo.begin()
580:        nuke.Undo.cancel()
583:        nuke.Undo.end()
605:    nuke.Undo.name("Layout Selected")
606:    nuke.Undo.begin()
642:        nuke.Undo.cancel()
645:        nuke.Undo.end()

grep -n "finally" node_layout/node_layout.py
(no output — no finally blocks)

pytest tests/ → 54 passed in 0.22s
```

## Self-Check: PASSED

- FOUND: node_layout/tests/test_undo_wrapping.py
- FOUND: .planning/phases/03-undo-reliability/03-01-SUMMARY.md
- FOUND: commit 90f9d38 (test RED phase)
- FOUND: commit dd48190 (feat GREEN phase)

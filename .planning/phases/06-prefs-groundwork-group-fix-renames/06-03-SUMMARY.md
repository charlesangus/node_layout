---
phase: 06-prefs-groundwork-group-fix-renames
plan: "03"
subsystem: layout
tags: [nuke, group-context, ast-tests, python]

# Dependency graph
requires:
  - phase: 06-02
    provides: _horizontal_margin() and H-axis prefs decoupled from V-axis sqrt formula

provides:
  - Group-context-safe layout_upstream() that captures nuke.thisGroup() first and wraps work in 'with current_group:'
  - Group-context-safe layout_selected() that captures nuke.thisGroup() first and wraps work in 'with current_group:'
  - push_nodes_to_make_room() scoped to current_group.nodes() when inside a Group, nuke.allNodes() at root
  - 8 AST tests in test_group_context.py verifying structural correctness of all three functions
  - CMD-01 comment in menu.py confirming scheme command naming convention

affects:
  - Phase 7 (State Storage): layout entry points now have current_group available as context
  - Any future changes to layout_upstream or layout_selected must preserve the thisGroup-first pattern

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Group context: capture nuke.thisGroup() as very first Nuke API call in entry points, before nuke.selectedNode()"
    - "with current_group: wraps the try-body (all layout work); nuke.Undo calls remain OUTSIDE the with block"
    - "push_nodes_to_make_room current_group=None default: safe no-op at root level, Group-scoped when inside a Group"

key-files:
  created:
    - tests/test_group_context.py
  modified:
    - node_layout.py
    - menu.py

key-decisions:
  - "nuke.thisGroup() is the VERY FIRST Nuke API call in layout_upstream() and layout_selected() — before nuke.selectedNode() and nuke.selectedNodes()"
  - "'with current_group:' chosen over group.begin()/group.end() — context manager is exception-safe"
  - "nuke.Undo.begin() stays OUTSIDE 'with current_group:' — Undo is script-level, not Group-level"
  - "push_nodes_to_make_room() uses current_group.nodes() when current_group is not None, falls back to nuke.allNodes() at root"

patterns-established:
  - "Entry-point Group capture: current_group = nuke.thisGroup() before any other Nuke API call"
  - "Group-safe Dot creation: any nuke.nodes.Dot() calls under place_subtree run inside 'with current_group:' implicitly"

requirements-completed:
  - LAYOUT-04
  - LAYOUT-05
  - CMD-01

# Metrics
duration: 2min
completed: "2026-03-08"
---

# Phase 6 Plan 03: Group Context Fix Summary

**Group-context-safe layout: nuke.thisGroup() captured first in both entry points, Dot creation and node push scoped to current Group via 'with current_group:'**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-08T02:48:49Z
- **Completed:** 2026-03-08T02:50:46Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Fixed LAYOUT-04: Dot nodes created by layout commands now land in the correct Group context instead of Root level
- Fixed LAYOUT-05: push_nodes_to_make_room() now uses current_group.nodes() when inside a Group, preventing root-level node displacement
- Confirmed CMD-01: all four scheme command names in menu.py end with 'Compact' or 'Loose' for tab-menu discoverability
- Added 8 AST tests in test_group_context.py that verify the structural rules will never regress

## Task Commits

Each task was committed atomically:

1. **Task 1: Add group context wrapping to layout entry points and push_nodes_to_make_room** - `e6da292` (fix + test)
2. **Task 2: Verify CMD-01 names in menu.py and run full test suite** - `412263a` (chore)

**Plan metadata:** (final docs commit — see below)

## Files Created/Modified

- `node_layout.py` - layout_upstream() and layout_selected() now call nuke.thisGroup() first and wrap layout work in 'with current_group:'; push_nodes_to_make_room() has new current_group=None parameter
- `tests/test_group_context.py` - new; 8 AST tests verifying group context structural rules
- `menu.py` - added CMD-01 comment above the four scheme addCommand calls

## Decisions Made

- Used `with current_group:` (context manager) rather than `group.begin()/group.end()` because the context manager is exception-safe — if the layout operation raises, the group context is still exited cleanly.
- `nuke.Undo.begin()` placed before `with current_group:` because Undo is script-level; the entire layout operation including the context switch is captured in one undoable action.
- `push_nodes_to_make_room(current_group=None)` uses a defaulted optional parameter so all existing call sites without the argument continue to work unchanged (backward compatible).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 6 is fully complete: prefs groundwork (Plan 01), H-axis decoupling (Plan 02), Group context fix (Plan 03).
- Phase 7 (State Storage) can proceed; layout entry points now hold `current_group` at the point where state knobs will eventually be read.
- The `with current_group:` pattern is established and documented — future entry points must follow it.

## Self-Check: PASSED

- tests/test_group_context.py: FOUND
- node_layout.py: FOUND (contains 'with current_group:' and 'current_group.nodes()')
- menu.py: FOUND (contains CMD-01 comment and all 4 scheme names)
- 06-03-SUMMARY.md: FOUND
- Commit e6da292: FOUND
- Commit 412263a: FOUND
- All 168 tests pass

---
*Phase: 06-prefs-groundwork-group-fix-renames*
*Completed: 2026-03-08*

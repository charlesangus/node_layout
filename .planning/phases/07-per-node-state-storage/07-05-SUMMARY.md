---
phase: 07-per-node-state-storage
plan: "05"
subsystem: layout
tags: [nuke, python, state-storage, undo, menu]

# Dependency graph
requires:
  - phase: 07-04
    provides: scale state write-back in _scale_selected_nodes and _scale_upstream_nodes
  - phase: 07-01
    provides: node_layout_state.clear_node_state() and write_node_state() API
provides:
  - clear_layout_state_selected() public function in node_layout.py
  - clear_layout_state_upstream() public function in node_layout.py
  - Two new menu registrations in menu.py for state-clearing commands
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "try/except/else undo group pattern extended to clear-state commands"
    - "State clear commands mirror the layout and scale command structure: _selected and _upstream variants"

key-files:
  created: []
  modified:
    - node_layout.py
    - menu.py

key-decisions:
  - "No keyboard shortcuts assigned to clear-state commands — keyboard namespace kept clean; plan CONTEXT.md locked decisions did not specify shortcuts"
  - "clear_layout_state_upstream() raises ValueError (from nuke.selectedNode()) if nothing is selected — matches existing upstream command behaviour"

patterns-established:
  - "Clear-state commands: collect nodes first, then iterate calling clear_node_state() inside a single undo group"

requirements-completed: [STATE-01, STATE-03]

# Metrics
duration: 4min
completed: 2026-03-10
---

# Phase 7 Plan 05: Clear Layout State Commands Summary

**Two clear-state public functions added to node_layout.py and registered in menu.py, completing the state lifecycle (write via layout/scale, clear via explicit user command)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-10T10:34:00Z
- **Completed:** 2026-03-10T10:34:57Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `clear_layout_state_selected()` — iterates selectedNodes(), calls `clear_node_state()` per node, wrapped in undo group
- Added `clear_layout_state_upstream()` — uses `collect_subtree_nodes()`, calls `clear_node_state()` per node, wrapped in undo group
- Registered both commands in menu.py immediately after the loose-scheme commands (no separators between them and related layout commands)
- Full test suite (193 tests) remains green after both changes

## Task Commits

Each task was committed atomically:

1. **Task 1: Add clear_layout_state_selected() and clear_layout_state_upstream() to node_layout.py** - `fab6da5` (feat)
2. **Task 2: Register clear-state commands in menu.py** - `7e87df8` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `node_layout.py` — Two new public functions at end of file (lines 888-931)
- `menu.py` — Two new addCommand registrations after Layout Selected Loose

## Decisions Made
- No keyboard shortcuts assigned to clear-state commands — CONTEXT.md locked decisions do not specify shortcuts; omitting keeps the keyboard namespace clean.
- Menu placement: immediately after `Layout Selected Loose` (before the Shrink/Expand separator), grouping all scheme-variant and clear-state commands together.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Phase 7 state system is now complete: state is written by layout and scale commands (Plans 02–04) and cleared by the two new commands (Plan 05).
- STATE-01 and STATE-03 requirements are closed.
- No blockers for subsequent phases.

---
*Phase: 07-per-node-state-storage*
*Completed: 2026-03-10*

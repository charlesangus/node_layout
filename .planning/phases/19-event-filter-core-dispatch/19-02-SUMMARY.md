---
phase: 19-event-filter-core-dispatch
plan: "02"
subsystem: testing
tags: [ast, structural-tests, pytest, unittest, leader-key, event-filter]

# Dependency graph
requires:
  - phase: 19-01
    provides: node_layout_leader.py implementation with LeaderKeyFilter, arm, _disarm
provides:
  - AST-based structural test suite for node_layout_leader.py (14 tests)
  - CI-runnable verification of LeaderKeyFilter structure without PySide6 import
affects:
  - 19-event-filter-core-dispatch (verifier plan)
  - Any future refactors of node_layout_leader.py

# Tech tracking
tech-stack:
  added: []
  patterns:
    - AST structural test pattern for PySide6 modules (no display server required)
    - Source text assertion pattern for string presence checks

key-files:
  created:
    - tests/test_node_layout_leader.py
  modified: []

key-decisions:
  - "Tests split into Task 1 (class/method AST tests) and Task 2 (source-text assertion tests) but committed together as one file"
  - "Top-level function detection uses tree.body iteration (not ast.walk) to avoid matching nested functions"
  - "Source text assertions used for dispatch keys, guards, lifecycle hooks — avoids complex AST traversal"

patterns-established:
  - "Leader test pattern: LEADER_PATH constant + _load_leader_source() + _parse_leader_ast() helpers"
  - "Class method verification: walk ClassDef body for FunctionDef nodes"
  - "Top-level function detection: iterate tree.body directly, not ast.walk"

requirements-completed: ["LEAD-02", "LEAD-03", "DISP-01", "DISP-02", "DISP-03", "DISP-04"]

# Metrics
duration: 1min
completed: 2026-03-31
---

# Phase 19 Plan 02: Structural AST tests for LeaderKeyFilter Summary

**14 AST/source-text structural tests for node_layout_leader.py covering class inheritance, dispatch table keys V/Z/F/C, auto-repeat guard, mouse cancellation, timer stop, and filter lifecycle install/remove**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-31T00:43:37Z
- **Completed:** 2026-03-31T00:44:47Z
- **Tasks:** 2 (both in one file, committed together)
- **Files modified:** 1

## Accomplishments
- Created `tests/test_node_layout_leader.py` with 14 structural tests following the overlay test canonical pattern
- Verified tests fail gracefully (FileNotFoundError) when implementation is missing, pass when 19-01 implementation is present
- All 366 pre-existing tests continue to pass — no regressions

## Task Commits

Each task was committed atomically:

1. **Tasks 1+2: Create test file with all structural tests** - `f4bc035` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `tests/test_node_layout_leader.py` - 14 AST and source-text structural tests for LeaderKeyFilter

## Decisions Made
- Tasks 1 and 2 both write to the same file; committed together as one atomic commit rather than two commits for the same file
- Used `tree.body` iteration (not `ast.walk`) for top-level function detection to correctly exclude nested functions from match set

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Structural test suite for leader key filter is complete
- Ready for integration with menu.py wiring (next phase plans)
- When node_layout_leader.py exists (from 19-01), all 14 tests pass

---
*Phase: 19-event-filter-core-dispatch*
*Completed: 2026-03-31*

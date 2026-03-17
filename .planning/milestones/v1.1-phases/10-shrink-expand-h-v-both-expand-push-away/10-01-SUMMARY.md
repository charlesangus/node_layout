---
phase: 10-shrink-expand-h-v-both-expand-push-away
plan: "01"
subsystem: testing

tags: [tdd, red-tests, unittest, ast, axis-scaling, repeat-last-scale, push-away]

requires:
  - phase: 07-per-node-state-storage
    provides: h_scale/v_scale per-node state with read_node_state/write_node_state
  - phase: 09-multi-input-fan-alignment-mask-side-swap
    provides: push_nodes_to_make_room and existing scale function signatures

provides:
  - RED test scaffold (15 failing tests) for all axis-scaling, repeat-last-scale, and push-away behaviours
  - tests/test_scale_nodes_axis.py as acceptance criteria for Plan 02 implementation

affects:
  - 10-02 (implementation plan that must turn these tests GREEN)

tech-stack:
  added: []
  patterns:
    - unittest.mock.patch.object used to verify push_nodes_to_make_room call presence/absence
    - MagicMock used to isolate repeat_last_scale call-forwarding test
    - AST inspection pattern for module-level variable assignments (ast.Assign targets)

key-files:
  created:
    - tests/test_scale_nodes_axis.py
  modified: []

key-decisions:
  - "Test file contains 15 tests (plan spec said 14 but enumerated 15 behaviors across 6 classes; all 15 fail RED correctly)"
  - "lastHitGroup stub added to nuke stub for expand wrapper tests — Rule 3 auto-fix (expand_selected_horizontal would error without it)"

patterns-established:
  - "setUp() resets _nl.nuke = sys.modules['nuke'] before each test to prevent cross-test stub pollution"
  - "patch.object(_nl, 'push_nodes_to_make_room') pattern for testing push-away presence/absence"

requirements-completed:
  - SCALE-01
  - SCALE-02
  - SCALE-03

duration: 2min
completed: 2026-03-12
---

# Phase 10 Plan 01: Axis Scale RED Test Scaffold Summary

**15-test RED scaffold covering axis-selective _scale_selected_nodes, _last_scale_fn tracking, repeat_last_scale, and expand push-away — all failing until Plan 02 implementation**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-12T12:56:39Z
- **Completed:** 2026-03-12T12:58:52Z
- **Tasks:** 1 (TDD RED phase)
- **Files modified:** 1

## Accomplishments

- 15 failing tests written in tests/test_scale_nodes_axis.py (594 lines, well above 200-line minimum)
- Tests cover axis="h" (dy unchanged), axis="v" (dx unchanged), axis="both" (regression guard), snap-floor not applied to unchanged axis
- State write-back tests verify h_scale/v_scale selective accumulation per axis
- AST tests check 8 new wrapper function names and _last_scale_fn module-level variable
- Behavioral tests verify repeat_last_scale call-forwarding, no-op on None, and _last_scale_fn set after wrapper call
- TestExpandPushAway verifies expand H/V call push_nodes_to_make_room; shrink H does not
- Existing tests/test_scale_nodes.py still passes: 17 tests, OK

## Task Commits

1. **Task 1: RED test scaffold** - `36fc1d7` (test)

## Files Created/Modified

- `/workspace/tests/test_scale_nodes_axis.py` — 15-test RED scaffold for Phase 10 behaviors

## Decisions Made

- Test count is 15, not 14 as stated in the plan spec: the plan's class-level enumeration lists 3 tests in TestExpandPushAway (test_expand_h_calls_push, test_expand_v_calls_push, test_shrink_h_no_push) which totals 15. All 15 fail correctly at RED.
- Added `lastHitGroup` to the nuke stub (auto-fix Rule 3): expand wrapper calls `nuke.lastHitGroup()` as first call; without the stub attribute the tests for expand wrappers would raise AttributeError during setup rather than during the assertion.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added lastHitGroup to nuke stub**
- **Found during:** Task 1 (writing TestExpandPushAway tests)
- **Issue:** expand_selected_horizontal/expand_selected_vertical call `nuke.lastHitGroup()` as their first line; the nuke stub built in this file lacked that attribute
- **Fix:** Added `if not hasattr(_active_nuke, "lastHitGroup"): _active_nuke.lastHitGroup = lambda: None` to the stub augmentation block
- **Files modified:** tests/test_scale_nodes_axis.py
- **Verification:** Tests execute and fail on the expected AttributeError (missing function) rather than on lastHitGroup
- **Committed in:** 36fc1d7 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (blocking)
**Impact on plan:** Necessary for test execution. No scope creep.

## Issues Encountered

None — test scaffold written cleanly following established patterns from tests/test_scale_nodes.py.

## Next Phase Readiness

- Plan 02 (implementation) has a complete RED scaffold to turn GREEN
- All 15 tests enumerate precise behavioral contracts for _scale_selected_nodes axis parameter, _last_scale_fn, repeat_last_scale, and 8 new wrapper functions
- tests/test_scale_nodes.py passes (17 tests) — no regression from this plan

---
*Phase: 10-shrink-expand-h-v-both-expand-push-away*
*Completed: 2026-03-12*

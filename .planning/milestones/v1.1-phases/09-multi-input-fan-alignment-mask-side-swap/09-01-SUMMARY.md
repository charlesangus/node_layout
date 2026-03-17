---
phase: 09-multi-input-fan-alignment-mask-side-swap
plan: "01"
subsystem: testing
tags: [tdd, unit-tests, fan-alignment, mask-side-swap, node-layout]

# Dependency graph
requires:
  - phase: 08-dot-font-size-margin-scaling
    provides: stub patterns (_StubKnob, _StubNode) and module-load pattern reused verbatim
provides:
  - RED test scaffold — 8 failing tests that define the Phase 9 acceptance criteria
affects: [09-02, 09-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_StubMergeNode subclass with inputLabel() dict for Merge2 mask-slot classification"
    - "unique module alias 'node_layout_fan_alignment' prevents sys.modules collision"
    - "consumer._inputs[slot] Dot-walk pattern to resolve xpos/ypos after place_subtree rewires"

key-files:
  created:
    - tests/test_fan_alignment.py
  modified: []

key-decisions:
  - "test_two_input_no_fan_regression and test_mask_right_when_no_fan_regression are expected to PASS RED — they are regression guards for unchanged n==2 behaviour"
  - "_StubMergeNode uses slot-index dict in inputLabel() so _is_mask_input correctly identifies slot 2 as mask without needing knob stubs"
  - "consumer._inputs array is set directly (not via setInput) to control exact slot mapping including None slots for mask"
  - "Dot-walk helper inline in test methods: consumer._inputs[slot] may be a Dot after place_subtree; walk to input(0) to get actual subtree root position"

patterns-established:
  - "TDD RED scaffold: 6 FAIL + 2 PASS (regression guards) is the correct RED state for Phase 9"
  - "Non-mask slot detection relies on _is_mask_input indirectly — tests use _StubMergeNode (Merge2 class) so slot 2 is always mask"

requirements-completed:
  - LAYOUT-01
  - LAYOUT-02

# Metrics
duration: 5min
completed: 2026-03-11
---

# Phase 9 Plan 01: Fan Alignment RED Test Scaffold Summary

**8 failing unit tests that define Phase 9 acceptance criteria: fan-mode height formula, uniform fan-root Y, uniform Dot-row Y, and mask side-swap to the left when 3+ non-mask inputs**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-11
- **Completed:** 2026-03-11
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created 8-test RED scaffold that precisely encodes every Phase 9 geometry invariant
- 6 tests fail with correct RED reasons (AttributeError on _is_fan_active, wrong height, wrong Y, wrong mask side)
- 2 regression-guard tests pass RED confirming n==2 staircase is unchanged today
- Full 222-test suite runs with zero pre-existing regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Write RED test scaffold — test_fan_alignment.py** - `27fdfbc` (test)

## Files Created/Modified
- `/workspace/tests/test_fan_alignment.py` - RED scaffold: 4 test classes, 8 test methods covering _is_fan_active, fan compute_dims height, fan place_subtree Y alignment, Dot-row uniformity, and mask side-swap

## Decisions Made
- Regression-guard tests (test_two_input_no_fan_regression, test_mask_right_when_no_fan_regression) are intentionally left to pass RED — they encode existing correct behaviour that Phase 9 must not break
- _StubMergeNode used throughout mask tests (Merge2 class) so _is_mask_input returns True for slot 2 without extra knob stubs
- Inline Dot-walk pattern in assertions avoids coupling test logic to place_subtree's internal rewiring details

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness
- RED scaffold committed; Plan 09-02 (implementation) can begin
- _is_fan_active does not exist yet — that is the correct pre-implementation state
- 6 failing tests will turn GREEN as Plans 09-02 and 09-03 implement fan geometry and mask side-swap

---
*Phase: 09-multi-input-fan-alignment-mask-side-swap*
*Completed: 2026-03-11*

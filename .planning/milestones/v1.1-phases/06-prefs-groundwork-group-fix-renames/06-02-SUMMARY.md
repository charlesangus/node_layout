---
phase: 06-prefs-groundwork-group-fix-renames
plan: 02
subsystem: layout-engine
tags: [node-layout, prefs, h-axis, tdd, ast-tests]

# Dependency graph
requires:
  - phase: 06-01
    provides: node_layout_prefs.py with horizontal_subtree_gap and horizontal_mask_gap keys in DEFAULTS
provides:
  - _horizontal_margin() function in node_layout.py that reads H-axis gaps directly from prefs
  - compute_dims() and place_subtree() use _horizontal_margin() for side_margins_h (no sqrt scaling)
  - layout_selected() horizontal_clearance is a direct prefs.get("horizontal_subtree_gap") call
  - All test files use /workspace paths (no broken /home/latuser paths)
  - Full test suite passes (160 tests, 0 errors, 0 failures)
affects:
  - Phase 07 (State Storage) — H-axis layout behavior now stable
  - Phase 08 (Dot Font Scaling) — horizontal_mask_gap pref is wired in
  - Phase 09 (Fan Alignment) — H-axis margin contract is final

# Tech tracking
tech-stack:
  added: []
  patterns:
    - _horizontal_margin() as the single H-axis margin read point (like _subtree_margin() for V-axis)
    - Direct pref.get() for absolute pixel values (no sqrt scaling on H-axis)
    - AST tests for structural verification of private function presence and call sites
    - Behavioral TDD tests using stub nodes to verify _horizontal_margin() return values

key-files:
  created:
    - tests/test_horizontal_margin.py
  modified:
    - node_layout.py
    - tests/test_prefs_integration.py
    - tests/test_node_layout_bug02.py
    - tests/test_undo_wrapping.py
    - tests/test_diamond_dot_centering.py
    - tests/test_scale_nodes.py
    - tests/test_make_room_bug01.py
    - tests/test_margin_symmetry.py

key-decisions:
  - "_horizontal_margin() is a separate function from _subtree_margin() — H-axis and V-axis are fully decoupled"
  - "horizontal_clearance in layout_selected() is a direct prefs.get() call with no scaling formula"
  - "test_margin_symmetry.py assertions updated to use horizontal_subtree_gap (150) not base_subtree_margin (300) for H-axis"
  - "TestHorizontalOnlyScheme.test_horizontal_margin_unaffected_by_compact_scheme now calls _horizontal_margin() directly"

patterns-established:
  - "_horizontal_margin(node, slot): pure pref read, routes to mask vs subtree gap via _is_mask_input()"
  - "H-axis margin: absolute px value from prefs. V-axis margin: sqrt-scaled from base_subtree_margin."
  - "Test isolation: _PREFS_DEFAULTS in test files must include all 10 DEFAULTS keys to prevent cross-test contamination"

requirements-completed: [PREFS-01, PREFS-02]

# Metrics
duration: 6min
completed: 2026-03-08
---

# Phase 6 Plan 02: H-Axis Decoupling Summary

**_horizontal_margin() wired into node_layout.py — H-axis now reads horizontal_subtree_gap/horizontal_mask_gap directly from prefs with no sqrt scaling, and all test paths fixed to /workspace**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-08T02:40:41Z
- **Completed:** 2026-03-08T02:46:00Z
- **Tasks:** 2
- **Files modified:** 9 (1 created, 8 modified)

## Accomplishments
- Added `_horizontal_margin(node, slot)` to node_layout.py — reads `horizontal_subtree_gap` or `horizontal_mask_gap` based on `_is_mask_input()`, no sqrt formula
- Replaced `side_margins_h` computation in `compute_dims()` and `place_subtree()` to use `_horizontal_margin()`, removing unused `normal_multiplier` reads from both functions
- Replaced `horizontal_clearance` formula in `layout_selected()` with a single `current_prefs.get("horizontal_subtree_gap")` call
- Fixed all broken `/home/latuser/git/nuke_layout_project/...` path constants in 6 test files, plus `MAKE_ROOM_PATH` in test_make_room_bug01.py
- Updated `test_prefs_integration.py` to reflect new DEFAULTS (base=200, loose_gap_mult=8.0, 3 new H-axis keys) and new `_horizontal_margin()` contract
- Updated `test_margin_symmetry.py` to use `_HORIZONTAL_MARGIN_AT_REFERENCE = 150` for H-axis assertions
- Full test suite: 160 tests, 0 errors, 0 failures

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _horizontal_margin() and replace side_margins_h** - `1bf9b88` (feat + test)
2. **Task 2: Fix broken /home/latuser paths and update TestHorizontalOnlyScheme** - `c1b8e44` (fix)

**Plan metadata:** (docs commit — see below)

_Note: Task 1 used TDD — failing tests written first (test_horizontal_margin.py), then implementation made them pass._

## Files Created/Modified
- `/workspace/node_layout.py` - Added `_horizontal_margin()`, updated `compute_dims()`, `place_subtree()`, `layout_selected()`
- `/workspace/tests/test_horizontal_margin.py` - New TDD test file: 12 AST + behavioral tests for `_horizontal_margin()`
- `/workspace/tests/test_prefs_integration.py` - Fixed NODE_LAYOUT_PATH, updated _PREFS_DEFAULTS (3 new keys, rebalanced values), updated TestHorizontalOnlyScheme tests
- `/workspace/tests/test_margin_symmetry.py` - Added new H-axis prefs to _PREFS_DEFAULTS, added _HORIZONTAL_MARGIN_AT_REFERENCE constant, updated 4 test assertions
- `/workspace/tests/test_node_layout_bug02.py` - Fixed NODE_LAYOUT_PATH
- `/workspace/tests/test_undo_wrapping.py` - Fixed NODE_LAYOUT_PATH
- `/workspace/tests/test_diamond_dot_centering.py` - Fixed NODE_LAYOUT_PATH
- `/workspace/tests/test_scale_nodes.py` - Fixed NODE_LAYOUT_PATH and NODE_LAYOUT_PREFS_PATH
- `/workspace/tests/test_make_room_bug01.py` - Fixed MAKE_ROOM_PATH to /workspace/make_room.py

## Decisions Made
- `_horizontal_margin()` placed after `_subtree_margin()` and before `_center_x()` — logically grouped with other per-slot margin helpers
- `normal_multiplier` variable removed from `compute_dims()` and `place_subtree()` since it was only used for the old `side_margins_h` formula
- `test_margin_symmetry.py` uses separate `_SUBTREE_MARGIN_AT_REFERENCE = 300` (V-axis, set via local _PREFS_DEFAULTS) and `_HORIZONTAL_MARGIN_AT_REFERENCE = 150` (H-axis, from DEFAULTS)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_margin_symmetry.py H-axis assertions to match new contract**
- **Found during:** Task 2 (fix broken paths)
- **Issue:** After Task 1 changed `side_margins_h` to use `_horizontal_margin()`, the test_margin_symmetry.py tests expected the old `_subtree_margin()` value (300) for horizontal margins. The new value is 150 (`horizontal_subtree_gap` default).
- **Fix:** Added `horizontal_subtree_gap: 150` to test's `_PREFS_DEFAULTS`, added `_HORIZONTAL_MARGIN_AT_REFERENCE = 150` constant, updated 4 test assertions (2 in TestMarginSymmetryN2, 2 in TestMarginSymmetryN3)
- **Files modified:** `tests/test_margin_symmetry.py`
- **Verification:** All 160 tests pass
- **Committed in:** c1b8e44 (Task 2 commit)

**2. [Rule 1 - Bug] Updated test_subtree_margin_at_reference_count_equals_base expected value**
- **Found during:** Task 2 (update test_prefs_integration.py)
- **Issue:** Test asserted `margin == 300` but `_PREFS_DEFAULTS` was updated to `base_subtree_margin: 200` matching the new DEFAULTS
- **Fix:** Updated expected value from 300 to 200 to match the rebalanced default
- **Files modified:** `tests/test_prefs_integration.py`
- **Verification:** All 160 tests pass
- **Committed in:** c1b8e44 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug: test assertions updated to reflect new implementation contract)
**Impact on plan:** Both fixes necessary for test correctness after the H-axis decoupling. No scope creep.

## Issues Encountered
None — both deviation fixes were straightforward value updates to test assertions.

## Next Phase Readiness
- H-axis decoupling complete. `_horizontal_margin()` is the canonical H-axis read point.
- Phase 6 Plan 03 (group context fix + renames) can proceed.
- No blockers introduced.

---
*Phase: 06-prefs-groundwork-group-fix-renames*
*Completed: 2026-03-08*

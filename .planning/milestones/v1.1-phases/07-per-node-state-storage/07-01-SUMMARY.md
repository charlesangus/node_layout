---
phase: 07-per-node-state-storage
plan: 01
subsystem: testing
tags: [python, json, nuke-knobs, tdd, ast-tests, state-storage]

# Dependency graph
requires:
  - phase: 06-prefs-groundwork-group-fix-renames
    provides: node_layout_prefs.py with compact/normal/loose multiplier prefs used by scheme helpers

provides:
  - node_layout_state.py with read_node_state, write_node_state, clear_node_state, scheme_name_to_multiplier, multiplier_to_scheme_name
  - tests/test_node_layout_state.py with 19 passing unit tests using a Nuke stub
  - tests/test_state_integration.py with 6 RED AST scaffold tests for Plans 02-04

affects:
  - 07-02 (write-back integration — must call write_node_state after place_subtree)
  - 07-03 (per-node scheme replay — read_node_state + memo key tuple)
  - 07-04 (scale write-back — _scale_selected_nodes/_scale_upstream_nodes)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deferred nuke import inside functions that use nuke API — keeps module importable without Nuke runtime"
    - "Nuke stub injected via sys.modules before importing module under test"
    - "setUp() restores nuke stub to prevent cross-contamination from other test files"
    - "AST scaffold tests written as RED-from-day-one acceptance criteria for future plans"

key-files:
  created:
    - node_layout_state.py
    - tests/test_node_layout_state.py
    - tests/test_state_integration.py
  modified: []

key-decisions:
  - "Deferred import nuke inside write_node_state/clear_node_state only — keeps module pure-Python importable for tests"
  - "setUp() nuke stub restore pattern required because other test files overwrite sys.modules['nuke'] with incompatible stubs"
  - "AST scaffold tests are proper failing assertions (not skipped) — they are the acceptance criteria for Plans 02-04"
  - "_DEFAULT_STATE never mutated directly — always dict(_DEFAULT_STATE) clone to prevent state bleed between calls"

patterns-established:
  - "Deferred nuke import pattern: import nuke inside function body, not at module top level"
  - "Stub restore in setUp(): any test class exercising deferred nuke imports must restore the stub in setUp()"
  - "Merge-from-defaults pattern: dict(_DEFAULT_STATE).update(stored) — absent keys always fall back to defaults"

requirements-completed: [STATE-01, STATE-02, STATE-03, STATE-04]

# Metrics
duration: 8min
completed: 2026-03-10
---

# Phase 7 Plan 01: node_layout_state.py Foundation Summary

**Pure-Python per-node state helpers (read/write/clear/scheme-resolve) with 19 passing unit tests and 6 RED AST scaffold tests for Plans 02-04 integration**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-10T10:05:00Z
- **Completed:** 2026-03-10T10:13:00Z
- **Tasks:** 2
- **Files modified:** 3 (created)

## Accomplishments

- `node_layout_state.py` created with all 5 exported functions: `read_node_state`, `write_node_state`, `clear_node_state`, `scheme_name_to_multiplier`, `multiplier_to_scheme_name`
- `tests/test_node_layout_state.py` with 19 unit tests — all pass — covering defaults, merge, malformed JSON, knob creation guard, no-duplicate, INVISIBLE flag, clear/tab removal logic, scheme resolution, and scale accumulation
- `tests/test_state_integration.py` with 6 RED AST scaffold tests — intentionally failing, serving as acceptance criteria for Plans 02-04
- Full test suite: 193 tests total; 168 original + 19 new unit tests pass; exactly 6 RED scaffold tests fail (as designed)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create node_layout_state.py helper module** - `1d01d09` (feat)
2. **Task 2: Create test_node_layout_state.py and test_state_integration.py** - `a4f9021` (test)

**Plan metadata:** committed with docs commit below

_Note: TDD tasks — tests written before implementation (RED confirmed, then GREEN)_

## Files Created/Modified

- `/workspace/node_layout_state.py` — Pure-Python state helpers; no top-level nuke import; deferred import inside write/clear functions
- `/workspace/tests/test_node_layout_state.py` — 19 unit tests; FakeNode/FakeKnob Nuke stub; setUp() stub-restore in write/clear/scale test classes
- `/workspace/tests/test_state_integration.py` — 6 RED AST scaffold tests verifying structural properties in node_layout.py for Plans 02-04

## Decisions Made

- Deferred `import nuke` inside function bodies (write_node_state, clear_node_state) to keep the module importable without a live Nuke runtime — allows pure-Python test execution.
- Added `setUp()` nuke stub restore to `TestWriteNodeState`, `TestClearNodeState`, and `TestScaleAccumulation` classes after discovering that other test files overwrite `sys.modules['nuke']` with incompatible stubs (missing `Tab_Knob`). This is a Rule 1 (bug fix) that prevented 5 tests from passing when run via `discover`.
- AST scaffold tests are written as real failing assertions rather than skipped — they serve as the acceptance criteria for Plans 02, 03, and 04.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed nuke stub cross-contamination in test discovery**
- **Found during:** Task 2 verification (full suite run)
- **Issue:** `python3.11 -m unittest discover` ran 5 tests with `AttributeError: module 'nuke' has no attribute 'Tab_Knob'` because other test files replace `sys.modules['nuke']` with minimal stubs that don't include `Tab_Knob`/`String_Knob`, and the stub injected at module-load time was not being restored for write/clear test methods
- **Fix:** Added `_restore_nuke_stub()` helper and `setUp()` method in `TestWriteNodeState`, `TestClearNodeState`, and `TestScaleAccumulation` to re-inject the correct stub before each test
- **Files modified:** `tests/test_node_layout_state.py`
- **Verification:** Full suite: 193 tests, 0 errors, 6 expected RED scaffold failures
- **Committed in:** `a4f9021` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Required fix for test isolation — no scope creep, stays within the test file.

## Issues Encountered

None beyond the cross-contamination bug documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `node_layout_state.py` is the Wave 0 foundation — all Plans 02-05 depend on it
- 6 RED scaffold tests in `test_state_integration.py` are ready as acceptance criteria:
  - Plans 02: write_node_state after place_subtree in layout_upstream/layout_selected
  - Plan 03: read_node_state in layout_upstream, tuple memo key in compute_dims
  - Plan 04: write_node_state in _scale_selected_nodes/_scale_upstream_nodes
- No blockers — proceed to Plan 02

---
*Phase: 07-per-node-state-storage*
*Completed: 2026-03-10*

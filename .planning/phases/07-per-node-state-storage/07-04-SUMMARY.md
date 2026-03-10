---
phase: 07-per-node-state-storage
plan: 04
subsystem: layout-engine
tags: [python, nuke, layout-engine, state-storage, scale, shrink, expand]

# Dependency graph
requires:
  - phase: 07-per-node-state-storage
    plan: 03
    provides: per-node scheme resolution dict; compute_dims tuple memo key

provides:
  - _scale_selected_nodes() writes accumulated h_scale/v_scale to all selected nodes after position loop
  - _scale_upstream_nodes() writes accumulated h_scale/v_scale to all upstream nodes after position loop
  - round(..., 10) used in both write-backs to prevent float drift
  - All 6 AST scaffold tests in test_state_integration.py now GREEN

affects:
  - 07-05 (clear-state commands — will read/clear these accumulated scale values)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Scale state accumulation: read_node_state then multiply h_scale/v_scale by scale_factor with round(..., 10) then write_node_state — iterates all affected nodes including anchor"
    - "_StubNode addKnob pattern: test stubs used for behavioral tests need addKnob + writable __getitem__ when production code calls write_node_state"
    - "Nuke stub knob factory fallback: ensure Tab_Knob/String_Knob/INVISIBLE present on active stub after conditional registration"

key-files:
  created: []
  modified:
    - node_layout.py
    - tests/test_scale_nodes.py

key-decisions:
  - "Scale write-back placed after the position loop in both scale functions — anchor node included even though it does not move (it participated in the scaling operation)"
  - "round(h_scale * scale_factor, 10) — 10 decimal places prevents IEEE 754 float accumulation drift across many repeated shrink/expand operations"
  - "test_scale_nodes.py _StubNode extended with addKnob() and writable __getitem__ fallback — Rule 3 fix required by new write_node_state call path"

patterns-established:
  - "Nuke stub completeness: any test stub used with functions that call write_node_state must support addKnob, Tab_Knob factory, String_Knob factory, INVISIBLE constant"

requirements-completed: [STATE-04]

# Metrics
duration: ~2min
completed: 2026-03-10
---

# Phase 7 Plan 04: Scale State Write-Back Summary

**Scale state accumulation added to _scale_selected_nodes() and _scale_upstream_nodes(): each Shrink/Expand operation multiplies stored h_scale/v_scale by scale_factor using round(..., 10), satisfying STATE-04**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-10T10:30:10Z
- **Completed:** 2026-03-10T10:32:26Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- `_scale_selected_nodes(scale_factor)` now iterates all `selected_nodes` after the position loop and writes `h_scale = round(old_h_scale * scale_factor, 10)`, `v_scale = round(old_v_scale * scale_factor, 10)` via `node_layout_state.write_node_state()`
- `_scale_upstream_nodes(scale_factor)` now iterates all `upstream_nodes` after the position loop and writes the same accumulated scale state
- Anchor node is included in the write-back loop in both functions — it does not move positionally but its scale state is updated to reflect participation in the operation
- `TestScaleWriteBackAST.test_scale_selected_writes_state_after_scaling` and `test_scale_upstream_writes_state_after_scaling` both GREEN; full suite 193 tests, all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Add scale state write-back to _scale_selected_nodes() and _scale_upstream_nodes()** - `c2bbebf` (feat)

## Files Created/Modified

- `/workspace/node_layout.py` — Added 5-line scale state write-back block after position loop in `_scale_selected_nodes()`; added 5-line scale state write-back block after position loop in `_scale_upstream_nodes()`
- `/workspace/tests/test_scale_nodes.py` — Added `_StubWritableKnob` class; extended `_StubNode` with `addKnob()` and writable `__getitem__` fallback; added `Tab_Knob`/`String_Knob`/`INVISIBLE` fallback initialization on active nuke stub (Rule 3 fix)

## Decisions Made

- Scale write-back placed after position loop — anchor node receives write-back even though it does not move positionally, since it is conceptually part of the scaling operation.
- `round(..., 10)` chosen for both axes — matches the specified pattern from RESEARCH.md and prevents IEEE 754 float accumulation drift.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Extended _StubNode and nuke stub in test_scale_nodes.py to support write_node_state call path**
- **Found during:** Task 1 (after adding scale write-back to node_layout.py)
- **Issue:** `_StubNode` lacked `addKnob()` method; nuke stub lacked `Tab_Knob`, `String_Knob`, `INVISIBLE` — `write_node_state()` calls all three, causing `AttributeError` on 10 existing behavioral tests in `test_scale_nodes.py`
- **Fix:** Added `_StubWritableKnob` class; added `addKnob()` to `_StubNode`; replaced bare `return _StubKnob(0)` in `__getitem__` with auto-registered writable knob; added `_make_stub_knob` factory and fallback initialization block for `Tab_Knob`/`String_Knob`/`INVISIBLE` on the active nuke stub
- **Files modified:** `tests/test_scale_nodes.py`
- **Verification:** `python3.11 -m unittest discover -s /workspace/tests -p "*.py" -q` — 193 tests, all pass
- **Committed in:** `c2bbebf` (part of task commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 blocking)
**Impact on plan:** Required for correctness — existing behavioral tests broke when the new `write_node_state` call path exercised APIs absent from the test stub. No scope creep.

## Issues Encountered

None — after stub fix, all tests passed first run.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- STATE-04 fully satisfied: Shrink/Expand commands update h_scale/v_scale on all affected nodes
- All 6 AST scaffold tests in `test_state_integration.py` are now GREEN (Plans 01-04 all complete)
- Full suite 193 tests passing — no regressions
- Plan 05 (clear-state commands + menu registration) is the final plan in Phase 7

## Self-Check: PASSED

- FOUND: /workspace/.planning/phases/07-per-node-state-storage/07-04-SUMMARY.md
- FOUND: commit c2bbebf (feat(07-04): add scale state write-back to _scale_selected_nodes and _scale_upstream_nodes)

---
*Phase: 07-per-node-state-storage*
*Completed: 2026-03-10*

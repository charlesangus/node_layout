---
phase: 12-fix-fan-layout-logic
plan: "02"
subsystem: layout-engine
tags: [fan-layout, geometry, tdd, green-phase, node_layout]

requires:
  - phase: 12-01
    provides: "3 RED regression tests for fan Dot Y, A1 X, compute_dims W"
provides:
  - "Fan Dot row Y formula corrected — Dot bottom clears consumer top by snap_threshold-1 px"
  - "A1 X start uses max(consumer right, B subtree right) — A1 no longer overlaps B"
  - "compute_dims W includes B right overhang — fan bbox width correctly reported"
affects: ["compute_dims callers", "place_subtree fan branch", "fan layout visual positioning"]

tech-stack:
  added: []
  patterns:
    - "b_right_overhang = max(0, (b_w - node_w) // 2) pattern for centered-above-consumer overhang calculation"
    - "max(consumer_right, subtree_right) pattern for rightward clearance starting point"

key-files:
  created: []
  modified:
    - node_layout.py

key-decisions:
  - "dot_row_y = y - (snap_threshold - 1) - inp.screenHeight(): Dot bottom clears consumer top by snap_threshold-1; subtracting moves upward in positive-down Nuke Y axis"
  - "A1 current_x uses max(x + node_w, x_positions[non_mask_start] + child_dims[non_mask_start][0]): B's subtree right edge gates A1 start when B wider than consumer"
  - "b_right_overhang uses // (integer division) to match _center_x which uses // — keeps overhang symmetric"
  - "Pre-existing 4 errors in test_scale_nodes_axis (nuke.Undo stub missing) confirmed pre-existing — no new failures introduced"

patterns-established:
  - "b_right_overhang pattern: when centering wide child above narrow consumer, account for rightward overhang in W formula"

requirements-completed: []

duration: 8min
completed: 2026-03-17
---

# Phase 12 Plan 02: Fan Layout Fix (GREEN) Summary

**3 arithmetic fixes in node_layout.py turn fan Dot row Y, A1 X clearance, and compute_dims W overhang from RED to GREEN — all 11 fan alignment tests pass.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-17T11:13:06Z
- **Completed:** 2026-03-17T11:21:00Z
- **Tasks:** 3
- **Files modified:** 1 (node_layout.py)

## Accomplishments

- Fix Site 1: fan Dot row Y formula — Dot now sits in reserved gap above consumer; bottom clears consumer top by exactly snap_threshold-1 px
- Fix Site 2: A1 X start accounts for B's subtree right edge — prevents A1 overlapping B when B is wider than consumer
- Fix Site 3: compute_dims fan W formula adds b_right_overhang in both fan paths — bbox width correctly represents rightward spread including B overhang
- All 11 fan alignment tests pass; no regressions in 280-test full suite

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix Bug 1 — fan Dot row Y formula** - `3cb3677` (fix)
2. **Task 2: Fix Bug 2 — A1 X start and compute_dims W** - `9034376` (fix)
3. **Task 3: Full regression verification** - `cdde382` (chore)

## Files Created/Modified

- `node_layout.py` — 3 fix sites applied: dot_row_y formula (line ~1145), A1 current_x (line ~1074), compute_dims W both fan paths (lines ~896-904)

## Decisions Made

- Used `//` (integer division) for `b_right_overhang` to match `_center_x` which uses `//` — ensures overhang is symmetric and the same amount is added to W as was subtracted to center B
- Pre-existing `nuke.Undo` stub failures in `test_scale_nodes_axis` (4 errors) are out of scope — confirmed pre-existing by running stash test before changes

## Deviations from Plan

None — plan executed exactly as written. All 3 fix sites matched the plan's specified before/after code exactly.

## Issues Encountered

None. All test assertions passed on first attempt after applying each fix.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 12 fan layout bug fixes complete
- All fan tests green; full suite at parity with pre-plan state (same 4 pre-existing errors, no new)
- Fan layout geometry is now correct for Dot row placement, A1 X clearance, and bbox width reporting

---
*Phase: 12-fix-fan-layout-logic*
*Completed: 2026-03-17*

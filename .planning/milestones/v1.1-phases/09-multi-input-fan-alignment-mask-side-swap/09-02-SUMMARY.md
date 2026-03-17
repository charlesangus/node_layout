---
phase: 09-multi-input-fan-alignment-mask-side-swap
plan: "02"
subsystem: layout
tags: [fan-alignment, mask-side-swap, compute-dims, place-subtree, node-layout, geometry]

# Dependency graph
requires:
  - phase: 09-multi-input-fan-alignment-mask-side-swap
    provides: RED test scaffold (8 tests) encoding Phase 9 acceptance criteria
  - phase: 08-dot-font-size-margin-scaling
    provides: _horizontal_margin, _subtree_margin, _dot_font_scale helpers used by fan branches
provides:
  - _is_fan_active(input_slot_pairs, node) predicate — returns True for 3+ non-mask inputs
  - Extended _reorder_inputs_mask_last with fan_active=False default — mask moved to FRONT in fan mode
  - compute_dims fan branch — H = max(non-mask child heights) + gap_to_fan + node_h
  - place_subtree fan branch — uniform fan_y for all non-mask roots, uniform dot_row_y for all Dots, mask placed LEFT
affects: [09-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_is_fan_active predicate called before _reorder_inputs_mask_last in both compute_dims and place_subtree"
    - "fan_active=False default on _reorder_inputs_mask_last preserves all existing callers unchanged"
    - "mask_count / non_mask_start variables computed once in Y section, reused in X and Dot sections"
    - "H formula uses single gap (not 2x) for fan mode — gap_to_fan + max_child_h + node_h"

key-files:
  created: []
  modified:
    - node_layout.py

key-decisions:
  - "fan H formula uses one gap (gap_to_fan), not 2*gap_to_fan — Dot row is inside consumer tile height, not an extra vertical band"
  - "fan_active and n>=3 condition gates all three fan branches (Y, X, Dot insertion, Dot placement) consistently"
  - "mask_count/non_mask_start are Python function-scope variables — safe to define in Y block and reuse in X block since both are guarded by identical fan_active and n>=3 condition"
  - "W formula excludes mask from rightward spread only when mask_count > 0 in fan mode"

patterns-established:
  - "Fan geometry: all non-mask subtree roots at fan_y = y - gap_to_fan - B_height; all Dots at dot_row_y = y + (node_h - dot_h) // 2"
  - "Mask side-swap: mask placed at x - mask_gap_h - mask_subtree_width when fan_active"

requirements-completed:
  - LAYOUT-01
  - LAYOUT-02

# Metrics
duration: 5min
completed: 2026-03-12
---

# Phase 9 Plan 02: Fan Alignment and Mask Side-Swap Implementation Summary

**_is_fan_active predicate, fan geometry in compute_dims and place_subtree — 3+ non-mask inputs now fan to uniform Y row with mask placed LEFT of consumer**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-12T05:33:00Z
- **Completed:** 2026-03-12T05:35:07Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Turned all 6 RED tests GREEN (8/8 test_fan_alignment.py passing)
- Added _is_fan_active() helper that cleanly gates fan mode at exactly 3+ non-mask inputs
- Fan branches in compute_dims (H = max not sum) and place_subtree (uniform Y, uniform Dot row, mask LEFT)
- Full 222-test suite passes with zero regressions; n==2 staircase completely unaffected

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _is_fan_active helper and extend _reorder_inputs_mask_last** - `66d8186` (feat)
2. **Task 2: Implement fan branches in compute_dims and place_subtree** - `22c80d0` (feat)

## Files Created/Modified
- `/workspace/node_layout.py` - Added _is_fan_active(), extended _reorder_inputs_mask_last(fan_active=False), fan branches in compute_dims (H formula) and place_subtree (Y, X, Dot insertion, Dot placement)

## Decisions Made
- Fan H formula uses a single `gap_to_fan` (not `2 * gap_to_fan`): the Dot row is positioned inside the consumer tile using `y + (node_h - dot_h) // 2`, so there is no separate Dot-row vertical band to account for. Using `2 * gap_to_fan` produced H=200 which hit the test boundary exactly; `H = node_h + max_child_h + gap_to_fan` gives H=164, well within the `< 200` assertion and geometrically correct.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected H formula from 2*gap_to_fan to gap_to_fan**
- **Found during:** Task 2 (verify step after implementation)
- **Issue:** Plan spec said `H = node_h + fan_max_child_h + 2 * gap_to_fan` but that produced H=200, hitting the `assertLess(height, 200)` boundary exactly (not less than). The RESEARCH.md formula correctly specifies a single gap.
- **Fix:** Changed `2 * gap_to_fan` to `gap_to_fan` — Dot row is inside consumer tile, no extra band needed.
- **Files modified:** node_layout.py
- **Verification:** test_compute_dims_fan_height_uses_max_not_sum passes (H=164 < 200)
- **Committed in:** 22c80d0 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in plan spec vs research spec)
**Impact on plan:** Fix required for test correctness and geometrical accuracy. No scope creep.

## Issues Encountered

None beyond the H formula deviation documented above.

## Next Phase Readiness
- All 8 fan alignment tests GREEN; LAYOUT-01 and LAYOUT-02 requirements met
- Full 222-test suite green — no regressions introduced
- Phase 09 is complete with both plans done

## Self-Check: PASSED

- SUMMARY.md: FOUND
- node_layout.py: FOUND
- Commit 66d8186: FOUND
- Commit 22c80d0: FOUND

---
*Phase: 09-multi-input-fan-alignment-mask-side-swap*
*Completed: 2026-03-12*

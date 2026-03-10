---
phase: 07-per-node-state-storage
plan: "07"
subsystem: layout-engine
tags: [node_layout, per-node-state, h_scale, v_scale, compute_dims, place_subtree, memoization]

requires:
  - phase: 07-per-node-state-storage
    provides: "Per-node state storage with h_scale/v_scale written by _scale_upstream_nodes and _scale_selected_nodes (Plans 04, 06)"

provides:
  - "compute_dims() and place_subtree() accept h_scale=1.0 and v_scale=1.0 keyword parameters"
  - "Memo key extended to (id(node), scheme_multiplier, h_scale, v_scale) to prevent cache collisions"
  - "layout_upstream() and layout_selected() read per-node h_scale/v_scale from stored state and pass root values to compute_dims/place_subtree"
  - "Subsequent Layout Upstream/Layout Selected respects spacing previously stored by Shrink/Expand"

affects:
  - future UAT for test 4 (scale-then-re-layout scenario)

tech-stack:
  added: []
  patterns:
    - "Root-level scale propagation: same pattern as root_scheme_multiplier — build per-node dict at entry point, extract single root value, pass uniformly to entire subtree"
    - "Snap floor on scaled gaps: max(snap_threshold - 1, int(gap * v_scale)) prevents same-tile-color tight gaps from being scaled below minimum"

key-files:
  created: []
  modified:
    - node_layout.py
    - tests/test_state_integration.py

key-decisions:
  - "h_scale/v_scale read at entry points only (layout_upstream, layout_selected) — never inside compute_dims or place_subtree recursion to preserve memoization"
  - "scale_state read separately from scheme stored_state for h/v scale — clear separation even when two reads per node occur"
  - "v_scale applied to vertical gaps with max(snap_threshold-1, ...) floor — same-color tight-gap minimum preserved"
  - "Per-subtree uniform scaling: root node's h_scale/v_scale applied to entire subtree for this plan; per-node variation within subtree deferred to future"

requirements-completed: [STATE-03, STATE-04]

duration: 4min
completed: 2026-03-10
---

# Phase 7 Plan 07: Scale Wiring into Layout Engine Summary

**h_scale/v_scale from per-node state wired into compute_dims/place_subtree so Layout Upstream and Layout Selected honour previously accumulated Shrink/Expand spacing**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-10T11:52:35Z
- **Completed:** 2026-03-10T11:56:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `compute_dims()` and `place_subtree()` now accept `h_scale=1.0` and `v_scale=1.0` keyword parameters; default values preserve full backward compatibility
- Memo key extended from `(id(node), scheme_multiplier)` to `(id(node), scheme_multiplier, h_scale, v_scale)` to prevent cache collisions when the same node appears with different scales
- `layout_upstream()` and `layout_selected()` build `per_node_h_scale` / `per_node_v_scale` dicts and extract root-level values passed to the geometry engine
- All 203 tests pass; 9 new AST tests added (3 for Task 1, 6 for Task 2)

## Task Commits

Each task was committed atomically:

1. **RED: Failing AST tests** - `4040589` (test)
2. **Task 1: Extend compute_dims and place_subtree** - `4877884` (feat)
3. **Task 2: Wire layout_upstream and layout_selected** - `aacb958` (feat)

_Note: TDD tasks have test commit (RED) then implementation commit (GREEN)._

## Files Created/Modified
- `/workspace/node_layout.py` - compute_dims/place_subtree signatures, memo key, scaled margins; layout_upstream/layout_selected per-node scale resolution and call sites
- `/workspace/tests/test_state_integration.py` - Added TestScaleParamsAST (3 tests) and TestScaleWiringAST (6 tests)

## Decisions Made
- State read occurs only at entry points (layout_upstream, layout_selected), not inside compute_dims or place_subtree — mid-recursion reads break memoization (per existing v1.1 decision)
- `scale_state = node_layout_state.read_node_state(subtree_node)` called separately from the scheme `stored_state` read — two reads per node is acceptable and keeps the code intent clear
- Vertical gap scaling uses `max(snap_threshold - 1, int(gap * v_scale))` floor — same-color tight-gap (snap_threshold-1) is a minimum constraint, not a spacing preference, so it must not be shrunk below that value
- Per-subtree uniform scaling: the root node's h_scale/v_scale is applied to the entire subtree; per-node variation within a subtree is a future feature

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- UAT test 4 (scale-then-re-layout) can now be retested; the gap closure is complete
- Phase 7 gap closure plans 06 and 07 both complete

## Self-Check: PASSED

- SUMMARY.md: FOUND at .planning/phases/07-per-node-state-storage/07-07-SUMMARY.md
- node_layout.py: FOUND
- test_state_integration.py: FOUND
- Commit 4040589 (RED tests): FOUND
- Commit 4877884 (Task 1 feat): FOUND
- Commit aacb958 (Task 2 feat): FOUND
- All 203 tests: PASS

---
*Phase: 07-per-node-state-storage*
*Completed: 2026-03-10*

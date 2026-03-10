---
phase: 07-per-node-state-storage
plan: "06"
subsystem: layout
tags: [nuke, dag, scaling, state, anchor-pivot, snap-min]

# Dependency graph
requires:
  - phase: 07-per-node-state-storage
    provides: _scale_upstream_nodes() with state write-back (Plan 04)
provides:
  - Fixed _scale_upstream_nodes() using bottom-left upstream node as pivot
  - snap_min floor applied in _scale_upstream_nodes() matching _scale_selected_nodes
  - AST regression test asserting max(upstream_nodes, ...) anchor selection
affects:
  - Shrink/Expand Upstream operations — anchor node no longer drifts on repeated scale

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Bottom-left anchor via max(nodes, key=lambda n: (n.ypos(), -n.xpos())) — consistent across both scale functions"
    - "snap_min = get_dag_snap_threshold() - 1 floor applied to dx/dy before position update"

key-files:
  created: []
  modified:
    - node_layout.py
    - tests/test_state_integration.py
    - tests/test_scale_nodes.py

key-decisions:
  - "_scale_upstream_nodes now matches _scale_selected_nodes pattern: same anchor selection logic and same snap_min floor"
  - "Old test_no_snap_min_in_scale_upstream replaced with test_snap_min_floor_guard_in_scale_upstream — Plan 06 supersedes the prior no-floor decision"

patterns-established:
  - "Scale functions: always select anchor via max(nodes, key=lambda n: (n.ypos(), -n.xpos())) for bottom-left corner pivot"

requirements-completed: [STATE-04]

# Metrics
duration: 2min
completed: 2026-03-10
---

# Phase 07 Plan 06: Fix _scale_upstream_nodes() Anchor Pivot Summary

**_scale_upstream_nodes() corrected to use bottom-left upstream node as pivot with snap_min floor, eliminating horizontal anchor drift on Shrink/Expand Upstream**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-10T11:49:16Z
- **Completed:** 2026-03-10T11:51:00Z
- **Tasks:** 1 (TDD: test + fix)
- **Files modified:** 3

## Accomplishments
- Fixed `_scale_upstream_nodes()` to use `max(upstream_nodes, key=lambda n: (n.ypos(), -n.xpos()))` as the pivot anchor instead of `nuke.selectedNode()` (which was the downstream root, not part of the upstream tree's bottom-left corner)
- Added `snap_min = get_dag_snap_threshold() - 1` floor guard to prevent nodes from snapping too close together, matching `_scale_selected_nodes()` behavior
- Added AST regression test in `test_state_integration.py` asserting `max(upstream_nodes` appears in `_scale_upstream_nodes()`
- Updated `test_scale_nodes.py` to reflect the corrected spec: `test_no_snap_min_in_scale_upstream` replaced with `test_snap_min_floor_guard_in_scale_upstream`

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing AST test for anchor pivot** - `730c385` (test)
2. **Task 1 GREEN: Fix _scale_upstream_nodes() + update conflicting test** - `f108966` (feat)

_Note: TDD task had RED commit then GREEN commit_

## Files Created/Modified
- `/workspace/node_layout.py` - `_scale_upstream_nodes()` rewritten with correct pivot and snap_min floor
- `/workspace/tests/test_state_integration.py` - New `TestUpstreamAnchorAST` class with anchor regression test
- `/workspace/tests/test_scale_nodes.py` - `test_no_snap_min_in_scale_upstream` replaced with `test_snap_min_floor_guard_in_scale_upstream`

## Decisions Made
- `_scale_upstream_nodes()` now uses the same bottom-left anchor selection as `_scale_selected_nodes()`. The upstream subtree (from `collect_subtree_nodes`) includes `root_node`, so the max() correctly picks from the full set including the selected node.
- The old `test_no_snap_min_in_scale_upstream` test was superseded by the Plan 06 gap closure requirement. The prior "upstream trees are self-consistent" rationale was wrong — snap_min prevents nodes from collapsing past the DAG grid threshold on repeated shrinks.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated conflicting pre-existing test in test_scale_nodes.py**
- **Found during:** Task 1 GREEN (running full test suite after fix)
- **Issue:** `test_no_snap_min_in_scale_upstream` asserted `snap_min` must NOT be in `_scale_upstream_nodes()`, directly contradicting the Plan 06 requirement to add snap_min
- **Fix:** Renamed the test to `test_snap_min_floor_guard_in_scale_upstream` and changed the assertion to `assertIn` — matching the new correct behavior
- **Files modified:** `tests/test_scale_nodes.py`
- **Verification:** Full suite of 194 tests passes
- **Committed in:** `f108966` (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - conflicting pre-existing test)
**Impact on plan:** Required to make the test suite consistent with the corrected spec. No scope creep.

## Issues Encountered
- Pre-existing test `test_no_snap_min_in_scale_upstream` directly contradicted the plan's requirement. The old test captured a design decision that was superseded by Plan 06. Updated the test to reflect the current correct spec.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Both `_scale_selected_nodes()` and `_scale_upstream_nodes()` now use identical anchor selection and snap_min logic
- UAT test 4 (anchor drift on Shrink/Expand Upstream) should now pass
- All 194 tests pass — no regressions

---
*Phase: 07-per-node-state-storage*
*Completed: 2026-03-10*

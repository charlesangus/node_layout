---
phase: 05-new-commands-scheme
plan: 04
subsystem: layout-engine
tags: [scaling, shrink-expand, center-based-offsets, rounding, tiebreaker, snap-floor, tdd]

requires:
  - phase: 05-01
    provides: shrink/expand commands with _scale_selected_nodes and _scale_upstream_nodes
provides:
  - Fixed _scale_selected_nodes: anchor tiebreaker, center-based offsets, round(), snap_min floor
  - Fixed _scale_upstream_nodes: center-based offsets, round(), no floor
affects: [node_layout.py, tests/test_scale_nodes.py]

tech-stack:
  added: []
  patterns: [center-based-scaling, round-not-int, snap-min-floor]

key-files:
  created:
    - tests/test_scale_nodes.py
  modified:
    - node_layout.py

key-decisions:
  - "Center-based offsets (node.xpos() + node.screenWidth()/2) replace top-left offsets in both scale functions — Dot nodes (width=12) move the same fractional center-to-center distance as regular nodes"
  - "round() replaces int() at all integer conversions — eliminates systematic rightward drift over repeated shrinks"
  - "Anchor tiebreaker key=(n.ypos(), -n.xpos()) ensures deterministic anchor selection when multiple nodes share the maximum ypos"
  - "snap_min floor (snap_threshold-1) applied only in _scale_selected_nodes, not _scale_upstream_nodes — upstream trees are self-consistent layouts"
  - "_set_selected_nodes helper updates _nl.nuke directly (not sys.modules['nuke']) to handle test_undo_wrapping.py replacing the stub after _nl was freshly loaded"

patterns-established:
  - "Use node.xpos() + node.screenWidth()/2 for center-x in any geometric operation on mixed node types"
  - "Minimum floor pattern: guard with original dx != 0 (not scaled), clamp new_dx to ±snap_min"

requirements-completed: [CMD-01, CMD-02]

duration: 8min
completed: "2026-03-05"
---

# Phase 05 Plan 04: Fix Shrink/Expand Scaling Summary

**Fixed four bugs in _scale_selected_nodes and one in _scale_upstream_nodes using center-based offsets, round(), a deterministic anchor tiebreaker, and a snap_min spacing floor**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-05T05:50:34Z
- **Completed:** 2026-03-05T05:58:50Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 2

## Accomplishments

- `_scale_selected_nodes`: anchor chosen via `max(selected_nodes, key=lambda n: (n.ypos(), -n.xpos()))` — deterministic on Y tie
- `_scale_selected_nodes`: all offsets computed center-to-center (xpos + screenWidth/2) — Dots no longer drift disproportionately
- `_scale_selected_nodes`: `round()` replaces `int()` — no systematic rounding bias over repeated shrinks
- `_scale_selected_nodes`: snap_min floor (snap_threshold-1) enforced center-to-center — nodes cannot overlap; zero-offset nodes exempt
- `_scale_upstream_nodes`: same center-based offsets and round() applied; no snap_min floor added (upstream trees are self-consistent)
- 17 new tests in `tests/test_scale_nodes.py` covering AST structural checks and behavioral correctness for both functions

## Task Commits

Each task was committed atomically (TDD approach):

1. **Task 1+2 RED: Failing tests for all four bugs** - `924e707` (test)
2. **Task 1+2 GREEN: Fix both scale functions + test helper fix** - `3a8bb58` (feat)

_Note: Tasks 1 and 2 share TDD commits since both functions were fixed together in one GREEN pass_

## Files Created/Modified

- `node_layout.py` — Fixed `_scale_selected_nodes` (anchor tiebreaker, center-based offsets, round(), snap_min floor) and `_scale_upstream_nodes` (center-based offsets, round())
- `tests/test_scale_nodes.py` — 17 new behavioral and AST tests covering all four bugs and both functions

## Decisions Made

- Center-based offsets chosen at both read (dx/dy computation) and write (setXpos/setYpos) sites — node.screenWidth()/2 subtracted when converting center back to top-left
- snap_min floor uses original `dx != 0` guard (not `new_dx != 0`) — ensures a node at the exact anchor column stays at dx=0 rather than being clamped to snap_min
- No floor in `_scale_upstream_nodes` — upstream tree nodes are placed by the layout engine as a coherent unit; enforcing a minimum gap on an already-correct layout would corrupt relative spacing

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test helper _set_selected_nodes to update _nl.nuke directly**
- **Found during:** Task 1 GREEN verification (combined test run)
- **Issue:** `test_undo_wrapping.py` unconditionally replaces `sys.modules["nuke"]` with a new stub object at import time. When `test_scale_nodes.py` loads BEFORE `test_undo_wrapping.py` (alphabetically), `_nl.nuke` captures the original stub. After `test_undo_wrapping.py` loads, `sys.modules["nuke"]` is a different object. `_set_selected_nodes` was updating `sys.modules["nuke"].selectedNodes` — the new stub — but `_nl.nuke.selectedNodes` still referenced the old stub.
- **Fix:** Changed `_set_selected_nodes` and `_set_selected_node` to update `_nl.nuke` directly instead of `sys.modules["nuke"]`
- **Files modified:** `tests/test_scale_nodes.py`
- **Commit:** `3a8bb58`

## Issues Encountered

None beyond the test helper stub-reference issue documented above.

## Next Phase Readiness

Phase 05-new-commands-scheme is now complete. All four scaling bugs are fixed; shrink/expand commands move Dots proportionally to regular nodes in all layouts.

## Self-Check: PASSED

- `05-04-SUMMARY.md` created: FOUND
- `node_layout.py` modified: FOUND
- `tests/test_scale_nodes.py` created: FOUND
- Commit 924e707 (RED tests) exists: FOUND
- Commit 3a8bb58 (GREEN implementation) exists: FOUND

---
*Phase: 05-new-commands-scheme*
*Completed: 2026-03-05*

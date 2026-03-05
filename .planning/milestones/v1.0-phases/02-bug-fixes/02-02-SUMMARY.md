---
phase: 02-bug-fixes
plan: "02"
subsystem: layout
tags: [geometry, positioning, x-alignment, centering, node-layout]

# Dependency graph
requires:
  - phase: 02-bug-fixes
    provides: "BUG-01 and BUG-02 fixes in node_layout.py"
provides:
  - "_center_x() helper for centering a child tile over a parent tile"
  - "Input 0 centered horizontally over consumer in place_subtree() for all n cases"
  - "compute_dims() W formula accounts for input[0] left overhang when wider than consumer"
  - "Confirmed margin symmetry for secondary inputs in both compute_dims() and place_subtree()"
  - "Regression tests for BUG-04 and BUG-05 geometry invariants"
affects: [03-features, future-layout-changes]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_center_x(child_width, parent_x, parent_width) pure helper for tile centering math"
    - "input0_overhang = max(0, (child_width - parent_width) // 2) for left-overhang bounding box"

key-files:
  created:
    - "tests/__init__.py"
    - "tests/test_center_x.py"
    - "tests/test_margin_symmetry.py"
  modified:
    - "node_layout.py"

key-decisions:
  - "Use _center_x(child_width, parent_x, parent_width) as a pure function (not taking node objects) so it is easily testable without Nuke runtime"
  - "input0_overhang accounts for bounding box expansion when input[0] is wider than the consumer; W formula adds overhang to the first max() argument covering input[0]"
  - "BUG-05 investigation found no structural asymmetry in margin application: gap before side child[i] is side_margins[i] in both compute_dims and place_subtree; apparent asymmetry was caused by BUG-04 left-edge alignment"

patterns-established:
  - "Tests stub nuke module with _StubKnob and _StubNode classes; nuke.nodes.Dot() stubbed via _StubNodesModule for place_subtree tests involving side-input dot insertion"
  - "Geometry helper tests are pure Python with no Nuke runtime dependency"

requirements-completed: [BUG-04, BUG-05]

# Metrics
duration: 10min
completed: 2026-03-04
---

# Phase 2 Plan 02: Input-0 Centering and Secondary Margin Symmetry Summary

**_center_x() helper centers input[0] over consumer tile in all non-all_side cases; compute_dims W formula updated for left overhang; BUG-05 margin application confirmed symmetric**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-04T03:35:35Z
- **Completed:** 2026-03-04T03:45:59Z
- **Tasks:** 2
- **Files modified:** 4 (node_layout.py + 3 test files created)

## Accomplishments
- Added `_center_x(child_width, parent_x, parent_width)` helper near `_subtree_margin` for clear centering semantics
- Fixed `place_subtree()` x_positions[0] in n==1, n==2, and n>=3 cases to use `_center_x` instead of bare `x`
- Updated `compute_dims()` W formula to include `input0_overhang` so bounding box correctly extends left when input[0] is wider than the consumer node
- Investigated BUG-05 margin index alignment; confirmed existing code applies side_margins[i] as the gap before side child[i] in both functions consistently
- Added 16 regression tests covering all centering and margin symmetry invariants

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for _center_x() and BUG-04** - `8b7085c` (test)
2. **Task 1 GREEN: center input 0; add _center_x() helper** - `49161e3` (fix)
3. **Task 2: secondary input margin symmetry tests and investigation** - `4b8b530` (fix)

## Files Created/Modified
- `node_layout.py` - Added `_center_x()` helper; updated `place_subtree()` x_positions[0] in all non-all_side cases; updated `compute_dims()` W formula with `input0_overhang`
- `tests/__init__.py` - New: package marker for tests directory
- `tests/test_center_x.py` - New: 11 tests for `_center_x()`, `compute_dims()` overhang, and `place_subtree()` centering
- `tests/test_margin_symmetry.py` - New: 5 tests confirming margin symmetry invariants for n==2 and n==3

## Decisions Made
- `_center_x` takes `(child_width, parent_x, parent_width)` as plain integers rather than node objects — keeps it testable without Nuke runtime and more composable
- `input0_overhang = max(0, (child_dims[0][0] - node.screenWidth()) // 2)` — computed once before the W if/elif/else block and reused in all three branches
- BUG-05 investigation conclusion: no structural asymmetry existed in margin application; the visual asymmetry was a symptom of BUG-04's left-edge alignment making input[0] appear offset relative to side inputs

## Deviations from Plan

None - plan executed exactly as written. BUG-05 investigation found the behavior was already correct; the tests document that invariant as a regression guard.

## Issues Encountered
- Test stub required iterative enhancement: `_StubNode` needed `__getitem__` for `node["tile_color"]`, `knobs()` method on preferences node, `setInput()` for dot insertion, and `nuke.nodes.Dot()` factory stub for `place_subtree` with side inputs. All resolved inline as test infrastructure issues.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- BUG-04 and BUG-05 fixed; input[0] now correctly centered over consumer in all configurations
- Test infrastructure in `tests/` directory established with nuke-runtime-free stubs
- Remaining bugs in phase (BUG-03 diamond Dot centering if planned) can follow same test pattern

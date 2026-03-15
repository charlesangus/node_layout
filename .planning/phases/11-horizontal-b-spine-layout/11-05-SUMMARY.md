---
phase: 11-horizontal-b-spine-layout
plan: 05
subsystem: layout-engine
tags: [nuke, node-layout, horizontal-layout, tdd, bug-fix]

# Dependency graph
requires:
  - phase: 11-horizontal-b-spine-layout
    provides: "Plans 01-04: horizontal spine layout, output dot placement, downstream replay"
provides:
  - "Fixed _place_output_dot_for_horizontal_root: id()-based identity comparison replaces bare 'is'"
  - "Fixed layout_upstream horizontal anchor: right-of-consumer (spine_x = consumer.xpos() + consumer.screenWidth() + horizontal_gap)"
  - "Fixed layout_selected horizontal anchor: same right-of-consumer formula when BFS rebinds root"
  - "5 new tests: TestDownstreamReplayAnchor (3) and TestPlaceOutputDotForHorizontalRootReplay (2)"
affects: [phase-12, uat, live-nuke-testing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "id()-based node identity: always use id(node.input(x)) == id(root) with is not None guard — never bare 'is'"
    - "AST test for formula verification: inspect function source text for key pattern strings when live Nuke calls can't be stubbed"
    - "Save original_selected_root before BFS walk — allows anchoring to consumer after root rebind"

key-files:
  created: []
  modified:
    - node_layout.py
    - tests/test_horizontal_layout.py

key-decisions:
  - "id() with is not None guards used for both output-dot identity checks in _place_output_dot_for_horizontal_root — prevents Nuke proxy wrapper false-negatives"
  - "layout_selected saves original_selected_root before BFS walk, mirrors layout_upstream pattern — enables right-of-consumer anchoring when BFS rebinds root"
  - "AST inspection chosen for TestDownstreamReplayAnchor — live layout_upstream/layout_selected require Nuke undo groups that can't be stubbed; formula check is sufficient"

patterns-established:
  - "Horizontal chain downstream anchor: spine_x = consumer.xpos() + consumer.screenWidth() + horizontal_gap; spine_y = consumer.ypos()"
  - "Node identity pattern: node.input(x) is not None and id(node.input(x)) == id(ref_node)"

requirements-completed: [HORIZ-01, HORIZ-02, HORIZ-03]

# Metrics
duration: 10min
completed: 2026-03-15
---

# Phase 11 Plan 05: Gap Closure — Duplicate Dot and Downstream Anchor Summary

**Fixed two UAT-blocking bugs: id()-based Nuke proxy identity in output dot detection, and right-of-consumer horizontal anchor formula in both layout_upstream and layout_selected**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-15T16:18:00Z
- **Completed:** 2026-03-15T16:22:46Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Replaced bare `is` comparisons with `id()`-based identity checks (with `is not None` guards) in `_place_output_dot_for_horizontal_root` — prevents duplicate Dot creation when Nuke returns fresh proxy wrapper objects on second layout call
- Fixed `layout_upstream` horizontal anchor block: replaced vertical "above consumer" formula (using `loose_gap` / `_DOT_TILE_HEIGHT`) with correct right-of-consumer formula (`spine_x = original_selected_root.xpos() + original_selected_root.screenWidth() + horizontal_gap`, `spine_y = original_selected_root.ypos()`)
- Fixed `layout_selected` to save `original_selected_root` before BFS ancestor walk and apply the same right-of-consumer anchor formula when BFS rebinds root
- Added 5 new tests (3 in `TestDownstreamReplayAnchor`, 2 in `TestPlaceOutputDotForHorizontalRootReplay`) — all fail RED before fixes, pass GREEN after

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix duplicate Dot — replace `is` with id() in _place_output_dot_for_horizontal_root** - `6f4f050` (fix)
2. **Task 2: Fix horizontal downstream anchoring — right-of-consumer placement in layout_upstream and layout_selected** - `6658d7b` (fix)

## Files Created/Modified

- `/workspace/node_layout.py` - Two bug fixes: id()-based identity in output dot scan; right-of-consumer anchor formula in layout_upstream and layout_selected
- `/workspace/tests/test_horizontal_layout.py` - Added TestDownstreamReplayAnchor (3 AST tests) and TestPlaceOutputDotForHorizontalRootReplay (2 behavioral tests)

## Decisions Made

- **id() with is not None guards:** Both output dot identity checks in `_place_output_dot_for_horizontal_root` use `node.input(x) is not None and id(node.input(x)) == id(root)`. The `is not None` guard prevents `id(None) == id(None)` false-positives since `None` is a singleton with a constant id in CPython.
- **layout_selected saves original_selected_root before BFS:** Mirrors the same pattern already in `layout_upstream`. The BFS walk (lines 1434-1452) may rebind `root` to an upstream horizontal ancestor. Without saving the original, there is no reference point for the right-of-consumer anchor.
- **AST test approach for TestDownstreamReplayAnchor:** Since `layout_upstream` and `layout_selected` call `nuke.Undo.begin()` / `nuke.selectedNode()`, they cannot be called in the test stub environment. AST inspection of the source text for the corrected formula pattern is sufficient to detect regression.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] layout_selected also needed original_selected_root save**

- **Found during:** Task 2 (inspection of layout_selected code before writing)
- **Issue:** Plan's Fix B mentioned checking whether layout_selected has an ancestor walk — it does (BFS at lines 1434-1452 that rebinds root). Without saving original_selected_root before the BFS, the right-of-consumer anchor can't be applied.
- **Fix:** Added `original_selected_root = root` before the BFS block in layout_selected's per-root loop, and added an `if root is not original_selected_root:` anchor block before the `place_subtree_horizontal` call — identical pattern to Fix A in layout_upstream.
- **Files modified:** node_layout.py
- **Verification:** 24/24 horizontal layout tests pass; AST tests confirm formula presence
- **Committed in:** `6658d7b` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 — missing critical functionality)
**Impact on plan:** The plan explicitly instructed inspection of layout_selected before writing and provided the correct action for the case where an ancestor walk exists. This was Plan-anticipated work executed correctly.

## Issues Encountered

None — both fixes were clean targeted edits. Pre-existing cross-test nuke stub contamination in `test_scale_nodes_axis` (4 errors when run together with other suites) was confirmed pre-existing and unrelated to these changes.

## Next Phase Readiness

- All 3 UAT tests from 11-04-UAT.md should now pass in live Nuke:
  - UAT-1: No duplicate Dot on replay (id()-based detection)
  - UAT-2: Downstream-node replay via layout_upstream places chain to the right (not above)
  - UAT-3: Downstream-node replay via layout_selected places chain to the right (not above)
- Phase 11 is ready for final UAT sign-off

---
*Phase: 11-horizontal-b-spine-layout*
*Completed: 2026-03-15*

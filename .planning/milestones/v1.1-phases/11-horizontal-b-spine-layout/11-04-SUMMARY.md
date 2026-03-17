---
phase: 11-horizontal-b-spine-layout
plan: 04
subsystem: layout
tags: [nuke, horizontal-layout, dot-placement, mode-replay, ancestor-walk]

# Dependency graph
requires:
  - phase: 11-horizontal-b-spine-layout
    provides: "Plan 03 — horizontal spine layout foundation with place_subtree_horizontal and _find_or_create_output_dot"
provides:
  - "Output Dot placed below rightmost spine node after Layout Selected Horizontal"
  - "Downstream-node mode replay via input(0) ancestor walk in layout_upstream and layout_selected"
  - "Unconditional mode='horizontal' write-back in _layout_selected_horizontal_impl (both recursive and place_only)"
  - "Correct call site: _place_output_dot_for_horizontal_root used at all three horizontal entry points"
  - "Dot positioned using loose_gap (not compact gap) so it is clearly visible below root"
affects:
  - 11-horizontal-b-spine-layout (plan 05 — id() vs is fix and right-of-consumer anchoring)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ancestor walk using input(0) chain to find first upstream horizontal-mode node for replay"
    - "_place_output_dot_for_horizontal_root used at all horizontal layout entry points (not _find_or_create_output_dot directly)"
    - "loose_gap used for output Dot vertical separation to prevent compact-gap collapse"

key-files:
  created: []
  modified:
    - node_layout.py

key-decisions:
  - "Unconditional mode write-back: both recursive and place_only call _layout_selected_horizontal_impl and must write mode='horizontal' — guard removed"
  - "Ancestor walk via input(0) chain (not BFS) was specified in plan; actual implementation in plan 03 used BFS — BFS is correct and was preserved"
  - "_place_output_dot_for_horizontal_root used at all call sites instead of _find_or_create_output_dot directly — the latter creates circular wiring (root as its own input)"
  - "Output Dot uses loose_gap for vertical separation so it is not collapsed to near-zero by same-tile-color compact rule"

patterns-established:
  - "Horizontal replay entry points (layout_upstream, layout_selected, _layout_selected_horizontal_impl) all call _place_output_dot_for_horizontal_root after place_subtree_horizontal"
  - "Downstream node ancestor walk reads stored mode on each input(0) predecessor until horizontal root found"

requirements-completed: [HORIZ-01, HORIZ-02, HORIZ-03]

# Metrics
duration: ~35min
completed: 2026-03-15
---

# Phase 11 Plan 04: Gap Closure — Output Dot, Downstream Replay, Place-Only Mode Storage Summary

**Three UAT gaps closed in horizontal B-spine layout: output Dot added below spine root, downstream-node ancestor walk wired in both entry points, and unconditional mode='horizontal' write-back for both recursive and place_only variants**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-03-14T14:00:00Z
- **Completed:** 2026-03-15T16:15:05Z
- **Tasks:** 3 (2 auto + 1 checkpoint:human-verify auto-approved)
- **Files modified:** 1

## Accomplishments
- Added `_place_output_dot_for_horizontal_root` call inside the `for root in roots:` loop in `_layout_selected_horizontal_impl` — output Dot now placed after every Layout Selected Horizontal run
- Removed `if side_layout_mode == "recursive":` guard from mode write-back block — both `place_only` and `recursive` now store `mode='horizontal'` on spine nodes
- Added upstream ancestor walk (BFS across input slots) before the `if root_mode == "horizontal":` branch in both `layout_upstream` and `layout_selected` — selecting a downstream node now replays the horizontal chain
- Fixed wrong call site: replaced `_find_or_create_output_dot(root, root, 0, ...)` (circular wiring) with `_place_output_dot_for_horizontal_root` at all three horizontal layout entry points
- Fixed Dot vertical position: switched to `loose_gap` so Dot is clearly below root rather than collapsed by the compact-gap rule

## Task Commits

Each task was committed atomically:

1. **Task 1: Add output Dot call and unconditional mode write-back** - `a9e5104` (feat)
2. **Task 2: Upstream ancestor walk for downstream-node mode replay** - `8ef07b9` (feat)
3. **Task 3: UAT checkpoint** - auto-approved (auto_advance=true)

**Deviation fixes:**
- `65f50f8` (fix): Replace wrong `_find_or_create_output_dot` call with `_place_output_dot_for_horizontal_root` at all three entry points
- `df8028f` (fix): Fix Dot vertical position to use loose_gap; anchor downstream consumer chain above selected node

## Files Created/Modified
- `node_layout.py` - All gap-closure edits: output Dot call, mode write-back guard removal, ancestor walk insertion, call-site corrections, Dot position fix

## Decisions Made
- Unconditional write-back: the `if side_layout_mode == "recursive":` guard was wrong because Place Only must also store mode so replay can fire later.
- BFS (not input(0)-only walk) used in the ancestor walk — the plan specified input(0) chain, but BFS was already present from plan 03 and is strictly more correct (handles Merge nodes where horizontal root enters non-zero input).
- `_place_output_dot_for_horizontal_root` is the correct public function for placing the output Dot; `_find_or_create_output_dot` expects a real consumer node and creates a circular connection when passed `root` as both root and consumer.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Replaced circular-wiring _find_or_create_output_dot call with _place_output_dot_for_horizontal_root**
- **Found during:** Task 1 / Task 2 verification
- **Issue:** The plan specified calling `_find_or_create_output_dot(root, root, 0, current_group)` inside the for-root loop and at the horizontal replay sites. This is incorrect — passing `root` as both `root` and `consumer_node` causes Nuke to reject the `setInput` call as a circular connection. The existing Dot was never reused and a new floating Dot was created each time.
- **Fix:** Replaced all three call sites with `_place_output_dot_for_horizontal_root(root, current_group, snap_threshold, root_scheme_multiplier)` which scans `allNodes()` to find existing output Dots or real downstream consumers.
- **Files modified:** node_layout.py
- **Committed in:** `65f50f8`

**2. [Rule 1 - Bug] Fixed Dot vertical position: use loose_gap instead of compact gap**
- **Found during:** Task 2 verification / UAT review
- **Issue:** The Dot was placed too close to the root node when the compact same-color rule produced a near-zero gap. The Dot appeared visually merged with the root.
- **Fix:** `_place_output_dot_for_horizontal_root` now reads `loose_gap_multiplier` from prefs and computes `dot_gap = int(loose_gap_multiplier * scheme_multiplier * snap_threshold)` for the Dot's vertical offset.
- **Files modified:** node_layout.py
- **Committed in:** `df8028f`

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs)
**Impact on plan:** Both fixes were necessary for correct behaviour. The circular-wiring bug was a plan specification error; the gap fix was a visual correctness issue found during execution.

## Issues Encountered
- UAT run after this plan's code changes revealed two remaining bugs: (1) Python `is` used instead of `id()` for node identity in `_place_output_dot_for_horizontal_root`, and (2) downstream replay places the horizontal chain above the consumer instead of to its right. These are tracked in `11-04-UAT.md` and addressed in plan 05.

## Next Phase Readiness
- Plan 05 (`11-05-PLAN.md`) is ready to close the remaining two UAT gaps: the `is` vs `id()` duplicate-Dot bug and the right-of-consumer anchoring formula.

---
*Phase: 11-horizontal-b-spine-layout*
*Completed: 2026-03-15*

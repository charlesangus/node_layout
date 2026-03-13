---
phase: 11-horizontal-b-spine-layout
plan: 02
subsystem: layout
tags: [horizontal-layout, b-spine, place_subtree_horizontal, output-dot, mask-kink, nuke-dag]

# Dependency graph
requires:
  - phase: 11-horizontal-b-spine-layout
    provides: RED test scaffold (11-01) with TestHorizontalSpine, TestOutputDot, TestMaskKink, TestSideInputPlacement
  - phase: 09-multi-input-fan-alignment-mask-side-swap
    provides: _is_mask_input(), vertical_gap_between(), _subtree_margin(), _center_x() used in horizontal placement
provides:
  - "place_subtree_horizontal() in node_layout.py — horizontal B-spine placement with mask kink staircase"
  - "_find_or_create_output_dot() in node_layout.py — places/reuses routing Dot below root"
  - "_OUTPUT_DOT_KNOB_NAME constant — 'node_layout_output_dot'"
affects:
  - 11-03 (entry point wiring: layout_upstream_horizontal, layout_selected_horizontal, mode dispatch)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-pass spine walk: first pass accumulates mask kink Y amounts (ancestor-first), second pass places nodes"
    - "_find_or_create_output_dot takes (root, consumer_node, consumer_slot, current_group) — consumer passed directly, not discovered via allNodes()"
    - "Output Dot reuse: check consumer.input(consumer_slot).knob(_OUTPUT_DOT_KNOB_NAME) before creating new Dot"
    - "memo dict optional in place_subtree_horizontal — created internally if not passed by caller"

key-files:
  created: []
  modified:
    - node_layout.py

key-decisions:
  - "_find_or_create_output_dot signature matches test: (root, consumer_node, consumer_slot, current_group) — plan described auto-discovery but tests pass consumer directly; tests are acceptance criteria"
  - "Two-pass spine algorithm: kink accumulation pass (ancestor-first) then placement pass — cleanest way to ensure correct cumulative Y drop at each spine node without backward reference"
  - "step_x uses only horizontal_subtree_gap * scheme_multiplier (the gap portion); node width handled separately via screenWidth() on each node — avoids assuming uniform node widths"
  - "Side input placement uses setXpos/setYpos directly (no recursion into subtree) — matches plan spec; Plan 03 can recurse via place_subtree() if needed for side subtrees"

patterns-established:
  - "Horizontal spine walk: spine_nodes = [root, anc1, anc2, ...]; reversed iteration for kink accumulation"

requirements-completed:
  - HORIZ-01

# Metrics
duration: 5min
completed: 2026-03-13
---

# Phase 11 Plan 02: Horizontal B-Spine Layout — Core Algorithm Summary

**place_subtree_horizontal() and _find_or_create_output_dot() implemented: horizontal B-spine geometry with mask-kink staircase, output Dot creation/reuse, and side-input above-spine placement**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-13T00:52:22Z
- **Completed:** 2026-03-13T00:57:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Added `_OUTPUT_DOT_KNOB_NAME = "node_layout_output_dot"` module constant
- Implemented `_find_or_create_output_dot()`: places routing Dot below root at vertical_gap_between distance; detects existing Dot via knob on replay and returns the same object (no duplicate)
- Implemented `place_subtree_horizontal()`: two-pass B-spine walk — first pass accumulates cumulative mask kink Y from ancestors, second pass places each spine node at correct X/Y with side inputs above
- TestHorizontalSpine (2), TestOutputDot (2), TestMaskKink (1), TestSideInputPlacement (1) all pass GREEN
- No regressions: 237 pre-existing tests still pass; only pre-existing RED tests for Plan 03 (layout_upstream_horizontal, mode dispatch) remain failing

## Task Commits

1. **Task 1: Implement _find_or_create_output_dot() and _OUTPUT_DOT_KNOB_NAME** — `5a67a0d` (feat)
2. **Task 2: Implement place_subtree_horizontal()** — `91d4754` (feat)

## Files Created/Modified

- `/workspace/node_layout.py` — added _OUTPUT_DOT_KNOB_NAME constant, _find_or_create_output_dot(), and place_subtree_horizontal()

## Decisions Made

- `_find_or_create_output_dot` signature uses `(root, consumer_node, consumer_slot, current_group)` — the tests pass consumer directly rather than discovering it via allNodes(); tests are the acceptance criteria
- Two-pass algorithm chosen for mask kink: first pass walks ancestor-first to accumulate cumulative kink, second pass places nodes — avoids need for backward reference during placement
- `step_x` uses only the gap portion (`horizontal_subtree_gap * scheme_multiplier`); node width is subtracted separately in the cur_x update loop — handles non-uniform node widths correctly
- `memo` parameter is optional in `place_subtree_horizontal` (created internally if None) — matches test call sites which don't pass memo

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Deviation] _find_or_create_output_dot signature differs from plan spec**
- **Found during:** Task 1 (reading test acceptance criteria)
- **Issue:** Plan spec described `_find_or_create_output_dot(root, snap_threshold, scheme_multiplier, current_group)` with internal consumer discovery, but tests call it as `_find_or_create_output_dot(root, consumer, 0, current_group)` — tests are authoritative
- **Fix:** Implemented the signature the tests expect: `(root, consumer_node, consumer_slot, current_group, snap_threshold=None, scheme_multiplier=None)` with consumer passed by caller
- **Files modified:** node_layout.py
- **Verification:** TestOutputDot 2/2 pass
- **Committed in:** 5a67a0d (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (signature alignment to test acceptance criteria)
**Impact on plan:** No scope creep; tests are the behavioral contract, so conforming to them is correct.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 02 complete: place_subtree_horizontal() and _find_or_create_output_dot() implemented and tested GREEN
- Plan 03 (entry points + menu) can now add layout_upstream_horizontal(), layout_selected_horizontal(), and mode dispatch in layout_upstream() to turn remaining RED tests GREEN
- Pre-existing RED tests in TestHorizontalAST and TestModeReplay will turn GREEN in Plan 03

---
*Phase: 11-horizontal-b-spine-layout*
*Completed: 2026-03-13*

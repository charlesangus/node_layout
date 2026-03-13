---
phase: 11-horizontal-b-spine-layout
plan: 03
subsystem: layout
tags: [horizontal-layout, entry-points, mode-dispatch, menu, state-replay]

# Dependency graph
requires:
  - phase: 11-horizontal-b-spine-layout
    provides: place_subtree_horizontal, _find_or_create_output_dot (11-02)
  - phase: 11-horizontal-b-spine-layout
    provides: RED test scaffold (11-01) with TestHorizontalAST and TestModeReplay
provides:
  - "layout_upstream_horizontal() entry point in node_layout.py"
  - "layout_selected_horizontal() entry point in node_layout.py"
  - "Mode dispatch in layout_upstream(): horizontal path when stored mode == 'horizontal'"
  - "Mode dispatch in layout_selected(): per-root horizontal dispatch"
  - "compute_dims layout_mode parameter and extended memo key"
  - "Two new menu entries in menu.py"
affects:
  - Users: normal layout_upstream/layout_selected now replays horizontal mode automatically (HORIZ-03)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mode dispatch at entry point: read root stored mode, branch to horizontal or vertical path"
    - "State write-back writes mode='horizontal' or 'vertical' conditional on which path was taken"
    - "compute_dims memo key extended to 5-tuple: (id, scheme_multiplier, h_scale, v_scale, layout_mode)"
    - "layout_upstream_horizontal/layout_selected_horizontal follow established undo pattern exactly"

key-files:
  created: []
  modified:
    - node_layout.py
    - menu.py

key-decisions:
  - "compute_dims memo key uses inline tuple syntax (not memo_key variable) — test_compute_dims_memo_key_includes_node_h_scale checks for 'node_h_scale' within 80 chars of 'memo['; variable approach broke this"
  - "layout_selected() mode dispatch is per-root — each root reads its own stored mode independently; roots in the same selection can mix horizontal and vertical"
  - "No keyboard shortcuts for horizontal layout commands — locked decision from CONTEXT.md"
  - "Horizontal commands placed after Clear Layout State commands, before Shrink separator in menu.py"

patterns-established:
  - "HORIZ-03 mode replay: layout_upstream() and layout_selected() now transparently dispatch to horizontal path when stored mode is 'horizontal'"

requirements-completed:
  - HORIZ-02
  - HORIZ-03

# Metrics
duration: 6min
completed: 2026-03-12
---

# Phase 11 Plan 03: Entry Points, Mode Dispatch, and Menu Registration Summary

**layout_upstream_horizontal and layout_selected_horizontal wired as full entry points; layout_upstream/layout_selected dispatch to horizontal path from stored mode; compute_dims memo key extended with layout_mode; two menu commands registered**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-03-12
- **Completed:** 2026-03-12
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `layout_mode="vertical"` parameter to `compute_dims()` with extended 5-tuple memo key `(id(node), scheme_multiplier, node_h_scale, node_v_scale, layout_mode)` preventing horizontal/vertical cache collisions
- Added mode dispatch to `layout_upstream()`: reads root's stored mode, calls `place_subtree_horizontal()` + `_find_or_create_output_dot()` when mode == "horizontal"; state write-back records correct mode per path taken
- Added per-root mode dispatch to `layout_selected()`: each root reads its stored mode independently, dispatches to horizontal or vertical path; state write-back records mode per root's subtree nodes
- Implemented `layout_upstream_horizontal()`: full undo pattern, subtree collection, per-node scheme/scale dict, `place_subtree_horizontal`, `_find_or_create_output_dot`, mode='horizontal' write-back, push_nodes_to_make_room
- Implemented `layout_selected_horizontal()`: same pattern for multi-root selections, 2-node guard
- Registered 'Layout Upstream Horizontal' and 'Layout Selected Horizontal' in menu.py after Clear Layout State commands
- All 10 tests in test_horizontal_layout.py pass GREEN; full suite has only 4 pre-existing errors (unchanged)

## Task Commits

1. **Task 1: Entry points, mode dispatch, compute_dims memo key** — `9d10964` (feat)
2. **Task 2: Menu registration** — `475c734` (feat)
3. **[Deviation fix]: Inline memo key to preserve AST test** — `11b9e85` (fix)

## Files Created/Modified

- `/workspace/node_layout.py` — compute_dims layout_mode param + memo key, layout_upstream/layout_selected mode dispatch, layout_upstream_horizontal, layout_selected_horizontal
- `/workspace/menu.py` — added Layout Upstream Horizontal, Layout Selected Horizontal commands

## Decisions Made

- `compute_dims` memo key uses inline tuple syntax (not a `memo_key` variable) because `test_compute_dims_memo_key_includes_node_h_scale` uses AST text search for `node_h_scale` within 80 chars of `memo[`; a named variable breaks this check
- `layout_selected()` mode dispatch is per-root — each root in a multi-root selection reads its own stored mode; roots in the same selection can use different modes
- No keyboard shortcuts for horizontal layout commands (locked decision from CONTEXT.md)
- Horizontal menu commands placed after Clear Layout State Upstream and before the Shrink separator

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] compute_dims memo_key variable broke existing AST test**
- **Found during:** Task 1 implementation + regression check
- **Issue:** Refactoring the memo key to a named `memo_key` variable caused `test_compute_dims_memo_key_includes_node_h_scale` to fail — the test searches for `node_h_scale` within 80 chars of `memo[` in the function source; with a named variable, `memo[memo_key]` has no `node_h_scale` nearby
- **Fix:** Reverted to inline tuple for both the check and the lookup; added `# noqa: E501` to the long store line
- **Files modified:** node_layout.py
- **Commit:** 11b9e85 (fix)

## Issues Encountered

None blocking.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 11 complete: all 3 plans executed, all 10 horizontal layout tests GREEN
- HORIZ-01, HORIZ-02, HORIZ-03 requirements fulfilled
- Horizontal layout is fully functional: place_subtree_horizontal, _find_or_create_output_dot, mode dispatch (HORIZ-03 replay), and menu entries all in place

---
*Phase: 11-horizontal-b-spine-layout*
*Completed: 2026-03-12*

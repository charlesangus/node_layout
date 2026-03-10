---
phase: 07-per-node-state-storage
plan: 02
subsystem: testing
tags: [python, json, nuke-knobs, state-storage, ast-tests, layout-engine]

# Dependency graph
requires:
  - phase: 07-per-node-state-storage
    plan: 01
    provides: node_layout_state.py with write_node_state, read_node_state, multiplier_to_scheme_name

provides:
  - node_layout.py imports node_layout_state
  - layout_upstream() writes scheme+mode to every layout-touched node after place_subtree()
  - layout_selected() writes scheme+mode to every layout-touched node after the roots for-loop

affects:
  - 07-03 (per-node scheme replay — will replace uniform fallback with per-node read_node_state in compute_dims)
  - 07-04 (scale write-back — _scale_selected_nodes/_scale_upstream_nodes)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Read-then-write state pattern: read_node_state() to get existing state, mutate scheme/mode, write_node_state() — preserves h_scale/v_scale across re-layouts"
    - "State write-back after place_subtree inside with current_group: and try block — undo coverage for knob creation"
    - "collect_subtree_nodes(state_root, node_filter=node_filter) to gather touched nodes in layout_selected after for-loop"

key-files:
  created: []
  modified:
    - node_layout.py

key-decisions:
  - "Write-back uses scheme_multiplier (the raw parameter) not resolved_scheme_multiplier — resolved_scheme_multiplier is only for compute_dims; write_scheme_name is a distinct local to avoid confusion"
  - "Write-back stays inside with current_group: and try block so Undo covers knob creation on newly inserted Dot nodes"
  - "Bonus: read_node_state call in layout_upstream write-back loop also satisfies TestSchemeReplayAST structural test (Plan 03 scaffold) — 3 RED tests remain instead of 4"

patterns-established:
  - "State write-back position: always after place_subtree() (and roots for-loop in layout_selected), before push_nodes_to_make_room()"
  - "final_subtree_nodes reused — no second collect_subtree_nodes call; write loop inserted between existing assignment and final_subtree_node_ids"

requirements-completed: [STATE-01, STATE-02]

# Metrics
duration: 5min
completed: 2026-03-10
---

# Phase 7 Plan 02: State Write-Back Integration Summary

**layout_upstream() and layout_selected() now write scheme+mode to every layout-touched node's node_layout_state knob immediately after place_subtree() completes**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-10T10:20:00Z
- **Completed:** 2026-03-10T10:25:36Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- `node_layout.py` now imports `node_layout_state` at the module level
- `layout_upstream()` write-back loop: resolves scheme name from multiplier, reads existing state per-node (preserving h_scale/v_scale), writes scheme+mode using `write_node_state` — covering all final_subtree_nodes including newly inserted Dot nodes
- `layout_selected()` write-back loop: collects all touched nodes across all roots via `collect_subtree_nodes(state_root, node_filter=node_filter)`, writes scheme+mode to each
- Both `TestStateWriteBackAST` tests now GREEN; full suite: 193 tests, 3 RED scaffold tests remain (Plans 03-04), no regressions
- Bonus: `TestSchemeReplayAST.test_layout_upstream_reads_per_node_state_when_scheme_is_none` also turned GREEN because the write-back loop calls `read_node_state` in `layout_upstream`

## Task Commits

Each task was committed atomically:

1. **Task 1: Add import and write-back pass to layout_upstream()** - `322d067` (feat)
2. **Task 2: Add write-back pass to layout_selected() and run full suite** - `93c27bf` (feat)

## Files Created/Modified

- `/workspace/node_layout.py` — Added `import node_layout_state`; added 13-line write-back block in `layout_upstream()` and 13-line write-back block in `layout_selected()`

## Decisions Made

- Write-back uses `scheme_multiplier` (raw parameter) for scheme name resolution, not `resolved_scheme_multiplier` (which is already consumed by `compute_dims`). New local `write_scheme_name` keeps naming unambiguous.
- `read_node_state` called before write to preserve existing `h_scale`/`v_scale` values — re-running layout does not clobber previously stored scale data.
- Write-back placed inside `with current_group:` and `try` block so knob creation on Dot nodes is covered by the undo group.

## Deviations from Plan

None - plan executed exactly as written.

Bonus outcome (not a deviation): `TestSchemeReplayAST` structural test passed as a side effect of the write-back loop calling `read_node_state` in `layout_upstream`. Plan 03 scaffold test count drops from 4 expected RED to 3 remaining RED. This is beneficial — it means Plan 03 only needs to add the per-node logic for `compute_dims` memo key tuple.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Write-back pass is complete for both layout entry points; STATE-01 and STATE-02 are satisfied
- 3 RED scaffold tests remain as acceptance criteria for Plans 03-04:
  - Plan 03: `TestMemoKeyAST.test_compute_dims_memo_key_is_tuple` — compute_dims must use tuple memo key including layout_mode
  - Plan 04: `TestScaleWriteBackAST.test_scale_selected_writes_state_after_scaling`
  - Plan 04: `TestScaleWriteBackAST.test_scale_upstream_writes_state_after_scaling`
- No blockers — proceed to Plan 03

## Self-Check: PASSED

- FOUND: /workspace/.planning/phases/07-per-node-state-storage/07-02-SUMMARY.md
- FOUND: commit 322d067 (feat(07-02): add state write-back pass to layout_upstream())
- FOUND: commit 93c27bf (feat(07-02): add state write-back pass to layout_selected())

---
*Phase: 07-per-node-state-storage*
*Completed: 2026-03-10*

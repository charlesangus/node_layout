---
phase: 07-per-node-state-storage
plan: 03
subsystem: layout-engine
tags: [python, nuke, layout-engine, state-storage, per-node-scheme, memoization]

# Dependency graph
requires:
  - phase: 07-per-node-state-storage
    plan: 02
    provides: layout_upstream/layout_selected write scheme+mode to node state after place_subtree

provides:
  - compute_dims() uses (id(node), scheme_multiplier) tuple as memo key
  - layout_upstream() builds per_node_scheme dict; scheme_multiplier=None reads stored per-node state
  - layout_selected() builds per_node_scheme dict; replaces resolved_scheme_multiplier uniform fallback
  - Write-back loops in both entry points use per-node scheme names from per_node_scheme

affects:
  - 07-04 (scale write-back — _scale_selected_nodes/_scale_upstream_nodes)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-node scheme resolution dict: built once before compute_dims(), maps id(node)->float; scheme_multiplier=None triggers read_node_state per node; explicit value fills all entries"
    - "root_scheme_multiplier: resolved from per_node_scheme for the subtree root, passed to compute_dims/place_subtree as a single float"
    - "Tuple memo key in compute_dims: (id(node), scheme_multiplier) prevents cache collision when shared node appears in subtrees called with different scheme values"

key-files:
  created: []
  modified:
    - node_layout.py

key-decisions:
  - "compute_dims memo key changed to (id(node), scheme_multiplier) tuple — prevents stale cached dimensions when a shared node appears in two subtrees with different per-node schemes"
  - "Per-node scheme resolution dict built at entry point before compute_dims; each root gets root_scheme_multiplier extracted from dict — compute_dims still receives a single float per call"
  - "Write-back loops now use per_node_scheme for per-node scheme name resolution instead of a uniform fallback — explicit scheme commands write explicit scheme; replay writes read-back scheme"
  - "resolved_scheme_multiplier block removed from layout_selected() — superseded by per_node_scheme dict"

# Metrics
duration: ~5min
completed: 2026-03-10
---

# Phase 7 Plan 03: Per-Node Scheme Resolution and Memo Key Fix Summary

**Per-node scheme replay in layout_upstream/layout_selected: scheme_multiplier=None now reads stored per-node state; compute_dims uses (id(node), scheme_multiplier) tuple memo key preventing cache collisions**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-10T10:25:36Z
- **Completed:** 2026-03-10
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- `compute_dims()` memo key changed from `id(node)` to `(id(node), scheme_multiplier)` — prevents stale cached dimensions when a shared node appears in two subtrees called with different scheme values
- `layout_upstream()` now builds `per_node_scheme` dict before `compute_dims()`: when `scheme_multiplier is None`, reads `read_node_state()` for each subtree node; when explicit, fills all entries with the override value
- `layout_selected()` replaces old `resolved_scheme_multiplier` uniform fallback with the same `per_node_scheme` pattern, iterating over `selected_nodes`
- Both entry points pass `root_scheme_multiplier` (extracted from `per_node_scheme`) to `compute_dims()` and `place_subtree()` — single float per call, per-node resolution happens at the dict-build level
- Write-back loops updated in both entry points to resolve scheme name per-node from `per_node_scheme` instead of using a single uniform value
- `TestMemoKeyAST.test_compute_dims_memo_key_is_tuple` now GREEN
- `TestSchemeReplayAST.test_layout_upstream_reads_per_node_state_when_scheme_is_none` remains GREEN (already passed from Plan 02 bonus)
- Full suite: 193 tests, only 2 RED scale write-back tests remain (Plan 04 acceptance criteria)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix compute_dims() memo key to (id(node), scheme_multiplier) tuple** - `3c540d8` (feat)
2. **Task 2: Add per-node scheme resolution block to both layout entry points** - `f530dea` (feat)

## Files Created/Modified

- `/workspace/node_layout.py` — Changed 3 memo accesses in `compute_dims()`; added 15-line per-node scheme resolution block and updated write-back loop in `layout_upstream()`; replaced `resolved_scheme_multiplier` block with per-node dict and updated write-back loop in `layout_selected()`

## Decisions Made

- Tuple memo key `(id(node), scheme_multiplier)` is the minimal fix that prevents cache collision — no other `compute_dims()` logic was changed.
- `root_scheme_multiplier` is extracted from `per_node_scheme` for each root and passed as a single float to `compute_dims`/`place_subtree` — this is correct for Phase 7 because per-node replay primarily affects write-back; compute_dims still traverses with one scheme value per call tree.
- `resolved_scheme_multiplier` variable fully removed from `layout_selected()` — it is replaced by `per_node_scheme` with no behavioral regression (uniform override path still works).

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

- STATE-03 satisfied: re-layout replays stored scheme; explicit scheme commands override and write back per-node
- 2 RED scaffold tests remain as acceptance criteria for Plan 04:
  - `TestScaleWriteBackAST.test_scale_selected_writes_state_after_scaling`
  - `TestScaleWriteBackAST.test_scale_upstream_writes_state_after_scaling`
- No blockers — proceed to Plan 04

## Self-Check: PASSED

- FOUND: /workspace/.planning/phases/07-per-node-state-storage/07-03-SUMMARY.md
- FOUND: commit 3c540d8 (feat(07-03): fix compute_dims() memo key to (id(node), scheme_multiplier) tuple)
- FOUND: commit f530dea (feat(07-03): add per-node scheme resolution to layout_upstream() and layout_selected())

---
*Phase: 07-per-node-state-storage*
*Completed: 2026-03-10*

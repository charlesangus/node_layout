---
phase: 05-new-commands-scheme
plan: 01
subsystem: layout-engine
tags: [scheme-multiplier, compact, loose, geometric-scaling, shrink, expand]
dependency_graph:
  requires: [04-03]
  provides: [CMD-01, CMD-02, SCHEME-01]
  affects: [node_layout.py, menu-wiring]
tech_stack:
  added: []
  patterns: [scheme-multiplier-threading, try-except-else-undo, geometric-offset-scaling]
key_files:
  created: []
  modified:
    - node_layout.py
    - tests/test_prefs_integration.py
decisions:
  - "scheme_multiplier defaults to None throughout call chain; each function resolves to normal_multiplier on first None check, not at every level — avoids redundant prefs reads in recursive calls"
  - "layout_selected resolves scheme_multiplier once into resolved_scheme_multiplier for use in horizontal_clearance, while still passing the original None/value scheme_multiplier downstream to compute_dims/place_subtree"
  - "SHRINK_FACTOR and EXPAND_FACTOR placed as module-level constants before the scaling helper functions — plan spec, not in prefs"
  - "_scale_upstream_nodes uses nuke.selectedNode() directly (raises ValueError on no selection); guard in public wrappers via try/except before undo group opens"
metrics:
  duration: 3 min
  completed_date: "2026-03-04"
  tasks_completed: 2
  files_modified: 2
---

# Phase 05 Plan 01: New Commands Scheme Summary

Scheme-aware layout pipeline with `scheme_multiplier` threading and geometric scaling commands (shrink/expand) completing CMD-01, CMD-02, and SCHEME-01.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Thread scheme_multiplier through layout pipeline; add compact/loose entry-points | 18e8ab5 | node_layout.py, tests/test_prefs_integration.py |
| 2 | Add shrink/expand selected and upstream geometric scaling commands | 3a9115b | node_layout.py, tests/test_prefs_integration.py |

## What Was Built

**Task 1 — Scheme-aware layout pipeline:**
- `vertical_gap_between(top_node, bottom_node, snap_threshold, scheme_multiplier=None)`: when `scheme_multiplier` is None, resolves to `normal_multiplier` from prefs; formula is `int(loose_gap_multiplier * scheme_multiplier * snap_threshold)`.
- `compute_dims` and `place_subtree` both accept `scheme_multiplier=None` and propagate it to `_subtree_margin` (as `mode_multiplier`) and `vertical_gap_between` at every call site including recursive calls.
- `layout_upstream(scheme_multiplier=None)` and `layout_selected(scheme_multiplier=None)` accept the parameter and pass it through. `layout_selected` resolves it once into `resolved_scheme_multiplier` for use in the inline `horizontal_clearance` formula, replacing the previous hardcoded `normal_multiplier` read.
- Four scheme entry-points: `layout_upstream_compact`, `layout_selected_compact`, `layout_upstream_loose`, `layout_selected_loose` — each reads the appropriate pref key and calls the base function.
- Existing `Normal` behavior numerically unchanged: `int(12.0 * 1.0 * snap_threshold)` equals the old `int(12.0 * snap_threshold)`.

**Task 2 — Geometric scaling commands:**
- `_scale_selected_nodes(scale_factor)`: anchor is `max(selectedNodes(), key=lambda n: n.ypos())` (lowest on screen in positive-Y-down DAG); multiplies `(dx, dy)` offsets by `scale_factor` using `int()`.
- `_scale_upstream_nodes(scale_factor)`: anchor is `nuke.selectedNode()`; traverses upstream via `collect_subtree_nodes(anchor)`.
- `shrink_selected`, `expand_selected`: guard for `< 2` selected nodes before opening undo group; use `try/except/else` undo pattern.
- `shrink_upstream`, `expand_upstream`: guard via `try/except ValueError` on `nuke.selectedNode()` before opening undo group.
- `SHRINK_FACTOR = 0.8`, `EXPAND_FACTOR = 1.25` at module level.

## Verification

All 93 tests pass:
```
python3 -m pytest tests/ -q
93 passed in 0.34s
```

Spot-checks:
- All five key functions (`vertical_gap_between`, `compute_dims`, `place_subtree`, `layout_upstream`, `layout_selected`) have `scheme_multiplier` in their signatures.
- `horizontal_clearance` in `layout_selected` uses `resolved_scheme_multiplier` — no hardcoded `normal_multiplier` literal.
- `SHRINK_FACTOR` and `EXPAND_FACTOR` confirmed at module level.
- 10 public entry-point functions exported: `layout_upstream`, `layout_selected`, `layout_upstream_compact`, `layout_selected_compact`, `layout_upstream_loose`, `layout_selected_loose`, `shrink_selected`, `expand_selected`, `shrink_upstream`, `expand_upstream`.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `node_layout.py` modified: FOUND
- `tests/test_prefs_integration.py` modified: FOUND
- Commit 18e8ab5 exists: FOUND
- Commit 3a9115b exists: FOUND

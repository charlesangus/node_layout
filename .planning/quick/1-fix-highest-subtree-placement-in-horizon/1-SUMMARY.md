---
phase: quick-1
plan: 1
subsystem: horizontal-layout
tags: [bugfix, geometry, tdd, place_subtree_horizontal]
key-files:
  modified:
    - node_layout.py
    - tests/test_horizontal_layout.py
decisions:
  - "Dot creation moved before recursive/place_only branch split so both modes always create a leftmost Dot"
  - "upstream_x formula changed from cur_x-step_x-upstream_w (far-left) to dot_x-centered (directly above Dot)"
  - "place_only branch simplified: single delta translate using pre-computed upstream_x, upstream_y"
  - "Test tolerance for center-X alignment is 1px (integer arithmetic off-by-one) not dot.screenWidth()"
metrics:
  duration: "~10 min"
  completed: "2026-03-14T13:13:27Z"
  tasks: 2
  files: 2
---

# Quick Task 1: Fix Highest Subtree Placement in Horizontal Layout

**One-liner:** Unified Dot creation + center-above-Dot upstream_x formula fixing diagonal-upper-left A-subtree misplacement in both recursive and place_only modes.

## What Was Done

The `is_last_spine_node` block in `place_subtree_horizontal()` had two bugs:

1. **Wrong upstream_x formula (both modes):** The old formula `upstream_x = cur_x - step_x - upstream_w` placed the A subtree diagonally upper-left of the Dot instead of directly above it.

2. **Missing Dot creation in place_only mode:** `_find_or_create_leftmost_dot()` was only called in the `recursive` branch, never in `place_only`. So replays never got a Dot.

## Changes

### `node_layout.py` — `is_last_spine_node` block (lines ~687-743)

Restructured the block to move shared logic before the `recursive`/`place_only` branch split:

1. **Dot creation (before branch split):**
   ```python
   if leftmost_dot is None:
       leftmost_dot = _find_or_create_leftmost_dot(spine_node, current_group)
   ```

2. **Dot positioning (before branch split):**
   ```python
   dot_x = cur_x - step_x - leftmost_dot.screenWidth()
   dot_y = cur_y + (spine_node.screenHeight() - leftmost_dot.screenHeight()) // 2
   ```

3. **upstream_x formula (before branch split):**
   ```python
   upstream_x = dot_x + (leftmost_dot.screenWidth() - upstream_root.screenWidth()) // 2
   ```
   Centers the upstream node above the Dot so the wire drops vertically.

4. **Recursive branch:** Kept `compute_dims` (memo warming) and `place_subtree` call using pre-computed position.

5. **place_only branch:** Simplified to a single delta-translate using pre-computed `upstream_x`, `upstream_y`. Removed the old `upstream_right_extent` extent calculation and the conditional Dot reposition.

### `tests/test_horizontal_layout.py` — `TestHighestSubtreePlacement` class

Added 9 tests covering:
- Recursive mode: creates Dot, Dot is left of spine, upstream center-X aligns with Dot center-X, upstream Y above spine, no overlap
- place_only mode: creates Dot, Dot is left of spine, upstream center-X aligns with Dot center-X, upstream Y above spine

Test tolerance for center-X alignment is `<= 1px` (accounts for integer floor division off-by-one when upstream node is wider than Dot).

## Deviations from Plan

**1. [Rule 1 - Bug] Test tolerance for center-X was too tight**

- **Found during:** Task 2 (GREEN phase)
- **Issue:** The plan specified `|upstream_root.xpos() - dot.xpos()| <= dot.screenWidth()` but with upstream width=80 and dot width=12, the formula `upstream_x = dot_x + (12-80)//2 = dot_x - 34` legitimately puts upstream_node.xpos() 34px left of dot_x — greater than dot_width=12.
- **Fix:** Changed test verification to compare center X coordinates: `|(upstream_x + upstream_w/2) - (dot_x + dot_w/2)| <= 1px`. This correctly validates center-alignment regardless of relative node widths.
- **Files modified:** `tests/test_horizontal_layout.py`
- **Commit:** c557afe (included in Task 2 commit)

## Verification

```
python3 -m unittest tests/test_horizontal_layout.py -v
# Ran 19 tests in 0.034s — OK (all TestHighestSubtreePlacement GREEN)

python3 -m unittest discover tests/ -q
# Ran 256 tests — FAILED (errors=4)
# Only the 4 pre-existing test_scale_nodes_axis nuke-stub errors. No new failures.
```

## Self-Check

### Files created/modified
- FOUND: /workspace/node_layout.py (modified)
- FOUND: /workspace/tests/test_horizontal_layout.py (modified)
- FOUND: /workspace/.planning/quick/1-fix-highest-subtree-placement-in-horizon/1-SUMMARY.md (this file)

### Commits
- 5daba9a: test(quick-1): add failing tests for corrected A/B placement geometry
- c557afe: fix(quick-1): correct A-subtree and Dot placement in is_last_spine_node block

## Self-Check: PASSED

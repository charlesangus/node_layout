---
phase: 12-fix-fan-layout-logic
plan: "01"
subsystem: tests/fan-layout
tags: [tdd, red-scaffold, fan-layout, geometry]
dependency_graph:
  requires: []
  provides: ["RED regression tests for fan geometry bugs — Bug 1 Dot Y, Bug 2 A1 X, compute_dims W"]
  affects: ["tests/test_fan_alignment.py"]
tech_stack:
  added: []
  patterns: ["small-horizontal-gap pref override to expose margin-sensitive bugs", "RED-before-fix TDD scaffold"]
key_files:
  created: []
  modified:
    - tests/test_fan_alignment.py
decisions:
  - "Set horizontal_subtree_gap=10 in Bug 2 tests — default 250px gap masks the overhang; small gap exposes A1 X collision and W undercount"
  - "test_fan_dot_row_y_in_gap_not_on_consumer asserts both ypos() < consumer_y AND dot_bottom <= consumer_y - (snap_threshold-1)"
  - "TestComputeDimsFanWidth is a new class (not added to TestPlaceSubtreeFanRoots) — separate concern from place_subtree geometry"
metrics:
  duration: "5 min"
  completed: "2026-03-17"
  tasks_completed: 2
  files_modified: 1
---

# Phase 12 Plan 01: Fan Layout RED Test Scaffold Summary

**One-liner:** 3 failing RED tests for fan Dot row Y (above consumer), A1 X (clears B right edge), and compute_dims W (B overhang) using small-gap pref override to expose margin-sensitive bugs.

## What Was Built

Added 3 RED regression tests to `tests/test_fan_alignment.py` covering two fan layout geometry bugs:

### Bug 1 — Fan Dot row Y wrong (test_fan_dot_row_y_in_gap_not_on_consumer)

The existing formula `y + (node.screenHeight() - inp.screenHeight()) // 2 = 500 + 8 = 508` places routing Dots ON or BELOW the consumer top (at ypos=500). The test asserts:
- `dot.ypos() < consumer_y` (Dot top strictly above consumer)
- `dot.ypos() + dot.screenHeight() <= consumer_y - (snap_threshold - 1)` (Dot bottom clears by snap_threshold-1)

Fails RED: 508 is not < 500.

### Bug 2 — A1 X ignores B subtree right edge (test_fan_a1_x_clears_b_subtree_right_edge)

With `horizontal_subtree_gap=10`, A1 is placed at `consumer_x + consumer_w + 10 = 590`. B (width=500) is centered above consumer (width=80) with B_left=290, B_right=790. A1 at 590 < B_right 790 — overlap. Test asserts `input_a1.xpos() >= b_right`.

Fails RED: 590 not >= 790.

### compute_dims W — understates fan bbox (test_compute_dims_fan_w_accounts_for_b_overhang)

With `horizontal_subtree_gap=10`, B=500, A1=300, A2=300: broken W = max(500, 80+10+10+300+300) = 700. Fixed W = max(500, 80+210+10+10+300+300) = 910 (includes B's 210px right overhang). Test asserts `width > 880`.

Fails RED: 700 not > 880.

## Key Design Decision

The default `horizontal_subtree_gap=250` masks Bug 2 — with 250px gaps, A1 always starts 250px past consumer right (830), which already clears B's right edge (790). Tests set `horizontal_subtree_gap=10` via `prefs_singleton.set()` in setUp to expose the gap between the correct and broken formulas. The `_reset_prefs()` call in setUp ensures isolation.

## Test Count

| State | Count |
|-------|-------|
| Existing passing tests | 8 |
| New RED tests | 3 |
| Total | 11 |
| Failures (all new) | 3 |
| Errors | 0 |

## Deviations from Plan

### Auto-adjusted Test Assertions

**1. [Rule 1 - Bug] Corrected W threshold from 880 to still 880, but with correct pref setup**
- **Found during:** Task 2 verification
- **Issue:** Plan assumed ~7px horizontal margins; actual default is 250px, which makes broken formula also produce W=1180 (above 880 threshold). Bug 2 tests would pass on broken code.
- **Fix:** Set `horizontal_subtree_gap=10` in both Bug 2 tests to expose the overhang gap. Broken W=700 (fails > 880); fixed W=910 (passes).
- **Files modified:** tests/test_fan_alignment.py
- **Commits:** 3d705b4

**2. [Rule 1 - Bug] Same pref override needed for test_fan_a1_x_clears_b_subtree_right_edge**
- **Found during:** Task 2 verification
- **Issue:** With default 250px gap, A1 at 830 already clears B_right=790. Bug only appears with small gap.
- **Fix:** Added `prefs_singleton.set("horizontal_subtree_gap", 10)` at top of test method.
- **Files modified:** tests/test_fan_alignment.py
- **Commits:** 3d705b4

## Self-Check

Checking created files and commits exist.

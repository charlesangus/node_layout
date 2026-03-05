---
phase: 04-preferences-system
plan: 03
subsystem: layout-engine
tags: [python, prefs, sqrt-scaling, tdd]

# Dependency graph
requires:
  - phase: 04-01
    provides: "node_layout_prefs.py with NodeLayoutPrefs class and prefs_singleton"
provides:
  - "node_layout.py reading all spacing values from prefs at call time"
  - "_subtree_margin() with sqrt-scaled dynamic margin based on node_count"
  - "compute_dims() and place_subtree() accepting node_count parameter"
  - "vertical_gap_between() reading loose_gap_multiplier from prefs"
affects: [04-04, future-layout-features]

# Tech tracking
tech-stack:
  added: ["import math (standard library)"]
  patterns: ["call-time prefs reads (no import-time binding)", "sqrt scaling for size-proportional margins", "node_count propagation through layout call chain"]

key-files:
  created:
    - "node_layout/tests/test_prefs_integration.py"
  modified:
    - "node_layout/node_layout.py"
    - "node_layout/tests/test_center_x.py"
    - "node_layout/tests/test_diamond_dot_centering.py"
    - "node_layout/tests/test_margin_symmetry.py"

key-decisions:
  - "node_count counted once per top-level entry point (layout_upstream/layout_selected) and propagated down, not re-counted per recursion"
  - "At scaling_reference_count=150, sqrt formula produces same margin as old constant (300) — backward-compatible default behavior"
  - "Staggered dot margin uses _subtree_margin(node, actual_slots[n-1], node_count) for consistency with other margin calls"
  - "Existing test files updated to pass node_count=150 (reference count) — preserves identical geometry assertions"
  - "Bare SUBTREE_MARGIN variable in test_margin_symmetry.py replaced with _SUBTREE_MARGIN_AT_REFERENCE=300 module constant"

patterns-established:
  - "Pattern: all prefs reads use node_layout_prefs.prefs_singleton.get() at call time, never at import time"
  - "Pattern: local alias current_prefs = node_layout_prefs.prefs_singleton inside functions to avoid shadowing module name"

requirements-completed: [PREFS-03, PREFS-07]

# Metrics
duration: 6min
completed: 2026-03-04
---

# Phase 4 Plan 3: Prefs Integration — Spacing Constants Summary

**node_layout.py spacing fully driven by node_layout_prefs singleton at call time, with sqrt-scaled dynamic margins proportional to subtree size**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-03-04T12:24:47Z
- **Completed:** 2026-03-04T12:31:04Z
- **Tasks:** 2 (TDD: RED + GREEN; no refactor needed)
- **Files modified:** 5

## Accomplishments

- Deleted SUBTREE_MARGIN and MASK_INPUT_MARGIN module-level constants from node_layout.py
- Replaced all 5 constant usage sites with prefs reads: `_subtree_margin()`, `vertical_gap_between()`, `compute_dims()` side margins, staggered dot margin, layout_selected() horizontal clearance
- `_subtree_margin(node, slot, node_count, mode_multiplier=None)` uses locked sqrt formula: `int(base * multiplier * sqrt(node_count) / sqrt(reference_count))` — small subtrees get proportionally smaller margins
- `node_count` propagated through `compute_dims()` and `place_subtree()` signatures; counted once at entry point
- 86 tests pass (68 pre-existing + 12 new integration tests + 6 from other test files)

## Task Commits

Each task was committed atomically:

1. **RED: Failing prefs integration tests** - `fd1316c` (test)
2. **GREEN: node_layout.py implementation + test API updates** - `fd40217` (feat)

**Plan metadata:** (pending docs commit)

_Note: TDD tasks — test commit then implementation commit_

## Files Created/Modified

- `node_layout/tests/test_prefs_integration.py` — New: 12 behavioral tests for TestPrefsIntegration class; verifies sqrt scaling, mask ratio, loose_gap_multiplier override, constant absence, signature inspection
- `node_layout/node_layout.py` — Modified: removed constants, added `import math` + `import node_layout_prefs`, rewrote `_subtree_margin()`, updated `vertical_gap_between()`, `compute_dims()`, `place_subtree()`, `layout_upstream()`, `layout_selected()`
- `node_layout/tests/test_center_x.py` — Modified: added node_layout_prefs stub loading; added `node_count=150` to all `compute_dims`/`place_subtree` calls
- `node_layout/tests/test_diamond_dot_centering.py` — Modified: added node_layout_prefs stub loading; added `node_count=150` to all calls
- `node_layout/tests/test_margin_symmetry.py` — Modified: added node_layout_prefs stub loading; added `node_count=150` to all calls; replaced `_nl.SUBTREE_MARGIN` with `_SUBTREE_MARGIN_AT_REFERENCE=300`

## Decisions Made

- **node_count counted once at entry point, not per recursion** — layout_upstream counts subtree nodes before insert_dot_nodes; layout_selected uses len(selected_nodes). This avoids recounting on every recursive call and ensures consistent margin size throughout one layout run.
- **Backward-compatible default** — at node_count=150 (scaling_reference_count) with normal_multiplier=1.0, sqrt formula returns exactly 300, matching old SUBTREE_MARGIN constant. No visual change at default settings.
- **Existing tests updated to pass node_count=150** — rather than making node_count optional with a default, the tests are updated to use the reference count. This keeps the required-parameter discipline and documents the explicit contract.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated 3 existing test files broken by API signature change**
- **Found during:** GREEN phase (running full test suite)
- **Issue:** test_center_x.py, test_margin_symmetry.py, and test_diamond_dot_centering.py all called `compute_dims()` and `place_subtree()` without the new required `node_count` parameter. Also, test_margin_symmetry.py referenced `_nl.SUBTREE_MARGIN` which was deleted. Additionally, none of the pre-existing test files loaded `node_layout_prefs` into `sys.modules` before loading `node_layout.py`, causing ImportError.
- **Fix:** Added `node_layout_prefs` stub loading in each affected test file; added `node_count=150` to all `compute_dims`/`place_subtree` calls; replaced `_nl.SUBTREE_MARGIN` with module-level constant `_SUBTREE_MARGIN_AT_REFERENCE = 300`
- **Files modified:** tests/test_center_x.py, tests/test_diamond_dot_centering.py, tests/test_margin_symmetry.py
- **Verification:** 86 tests pass
- **Committed in:** fd40217 (GREEN phase commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug: broken tests from API change)
**Impact on plan:** Necessary consequence of the planned API change. No scope creep.

## Issues Encountered

None beyond the test API updates documented above.

## Next Phase Readiness

- All spacing in node_layout.py is now prefs-driven and testable
- prefs_singleton.set() can be used in tests to verify layout behavior changes at runtime
- Ready for Phase 04-04 (if any) or Phase 05

---
*Phase: 04-preferences-system*
*Completed: 2026-03-04*

## Self-Check: PASSED

- FOUND: .planning/phases/04-preferences-system/04-03-SUMMARY.md
- FOUND: tests/test_prefs_integration.py
- FOUND: commit fd1316c (test RED phase)
- FOUND: commit fd40217 (feat GREEN phase)
- 86 tests pass

---
phase: 05-new-commands-scheme
plan: 03
subsystem: layout-engine
tags: [scheme-multiplier, side-margins, horizontal-spacing, vertical-spacing, compact, loose, tdd]

requires:
  - phase: 05-02
    provides: scheme_multiplier threading through layout pipeline and compact/loose entry-points
provides:
  - side_margins_h (horizontal X/W, always normal_multiplier) in compute_dims and place_subtree
  - side_margins_v (vertical staircase, uses scheme_multiplier) in compute_dims and place_subtree
  - horizontal_clearance in layout_selected uses normal_multiplier exclusively
affects: [node_layout.py, tests/test_prefs_integration.py]

tech-stack:
  added: []
  patterns: [h-v-margin-split, scheme-vertical-only]

key-files:
  created: []
  modified:
    - node_layout.py
    - tests/test_prefs_integration.py

key-decisions:
  - "Split side_margins into side_margins_h (normal_multiplier) and side_margins_v (scheme_multiplier) at both compute_dims and place_subtree call sites — horizontal X/W formulas are decoupled from scheme changes"
  - "horizontal_clearance in layout_selected uses current_prefs.get(normal_multiplier) directly — resolved_scheme_multiplier is still passed to place_subtree but must not affect horizontal inter-tree spacing"
  - "dot_y stagger in place_subtree left unchanged — it is a vertical gap and correctly uses scheme_multiplier"

patterns-established:
  - "Margin split pattern: side_margins_h for X/W placement, side_margins_v for Y staircase — always compute both at each call site"

requirements-completed: [SCHEME-01]

duration: 2min
completed: "2026-03-05"
---

# Phase 05 Plan 03: New Commands Scheme Summary

**Split side_margins into horizontal (normal_multiplier) and vertical (scheme_multiplier) at all layout call sites so compact/loose schemes only alter vertical inter-band gaps, not horizontal X positions**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-05T05:46:29Z
- **Completed:** 2026-03-05T05:48:13Z
- **Tasks:** 1 (TDD: RED + GREEN commits)
- **Files modified:** 2

## Accomplishments
- compute_dims: side_margins_h (normal_multiplier) used for W formulas; side_margins_v (scheme_multiplier) used for inter_band_gaps and gap_closest floor
- place_subtree: side_margins_h used for all X positions; side_margins_v used for Y staircase (bottom_y) and gap_closest floor
- layout_selected: horizontal_clearance now computed with current_prefs.get("normal_multiplier") — no longer scales with scheme
- 6 new tests in TestHorizontalOnlyScheme verify structural (side_margins_h/v present in source) and behavioral (horizontal unaffected, vertical affected) contracts

## Task Commits

Each task was committed atomically (TDD approach):

1. **Task 1 RED: Failing tests for h/v margin split** - `0e6de98` (test)
2. **Task 1 GREEN: Split side_margins and fix horizontal_clearance** - `d8a8809` (feat)

**Plan metadata:** (docs commit — see below)

_Note: TDD task has two commits: test (RED) then feat (GREEN)_

## Files Created/Modified
- `node_layout.py` - Split side_margins into side_margins_h/side_margins_v in compute_dims and place_subtree; horizontal_clearance uses normal_multiplier
- `tests/test_prefs_integration.py` - Added TestHorizontalOnlyScheme class with 6 behavioral/structural tests

## Decisions Made
- Split side_margins into side_margins_h and side_margins_v at each call site rather than passing two multipliers to _subtree_margin — clearer intent at the call site, no change to _subtree_margin signature
- horizontal_clearance uses current_prefs.get("normal_multiplier") directly rather than introducing a local variable — avoids ambiguity with resolved_scheme_multiplier which remains needed for place_subtree

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness
- Phase 05-new-commands-scheme is now complete: scheme_multiplier threading, compact/loose entry-points, menu wiring, and horizontal/vertical margin separation are all done
- Compact/Loose layout commands now correctly change only vertical inter-band gaps — horizontal gaps between side inputs remain identical to Normal layout

## Self-Check: PASSED

- `05-03-SUMMARY.md` created: FOUND
- `node_layout.py` modified: FOUND
- `tests/test_prefs_integration.py` modified: FOUND
- Commit 0e6de98 (RED tests) exists: FOUND
- Commit d8a8809 (GREEN implementation) exists: FOUND

---
*Phase: 05-new-commands-scheme*
*Completed: 2026-03-05*

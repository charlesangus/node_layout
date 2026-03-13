---
phase: 11-horizontal-b-spine-layout
plan: 01
subsystem: testing
tags: [unittest, tdd, red-scaffold, horizontal-layout, b-spine, nuke-stub]

# Dependency graph
requires:
  - phase: 09-multi-input-fan-alignment-mask-side-swap
    provides: stub pattern (test_fan_alignment.py) and fan alignment logic used as reference
  - phase: 10-shrink-expand-h-v-both-expand-push-away
    provides: extended test scaffold patterns, _StubNode with setInput/input
provides:
  - "RED test scaffold for HORIZ-01, HORIZ-02, HORIZ-03 in tests/test_horizontal_layout.py"
  - "Behavioral contract for place_subtree_horizontal() spine geometry"
  - "Behavioral contract for _find_or_create_output_dot() creation and reuse"
  - "Behavioral contract for mask kink downstream Y drop"
  - "Behavioral contract for side-input above-spine placement"
  - "Behavioral contract for layout_upstream() horizontal dispatch"
affects:
  - 11-02 (implementation plan uses these tests as acceptance criteria)
  - 11-03 (entry point wiring + menu plan)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "spec_from_file_location with unique alias 'node_layout_horizontal' to avoid sys.modules collisions"
    - "_StubDotNode subclass extends _StubNode with optional node_layout_output_dot knob for reuse tests"
    - "_StubKnob.setValue() added (required for output Dot knob value assignment)"
    - "nuke.lastHitGroup stub returns None (root context — established Phase 6 pattern)"

key-files:
  created:
    - tests/test_horizontal_layout.py
  modified: []

key-decisions:
  - "test_output_dot_reused_on_replay uses assertIs() (identity check) not assertEqual() — ensures exact same object, not a new Dot with matching attributes"
  - "TestMaskKink uses a _SpineNodeWithMask inner class with inputLabel() returning 'M' for slot 2 — mirrors real Merge2 stub pattern to trigger _is_mask_input() correctly"
  - "TestModeReplay verifies both 'horizontal' string presence AND 'place_subtree_horizontal' string presence in layout_upstream() body — two-condition AST check prevents false passes"

patterns-established:
  - "_StubDotNode: subclass pattern for Dot-specific stubs with optional custom knob flags"
  - "Inner class stub for mask-input simulation in TestMaskKink"

requirements-completed:
  - HORIZ-01
  - HORIZ-02
  - HORIZ-03

# Metrics
duration: 3min
completed: 2026-03-13
---

# Phase 11 Plan 01: Horizontal B-Spine Layout RED Scaffold Summary

**10-test RED scaffold in tests/test_horizontal_layout.py covering all HORIZ-01/02/03 behaviors — spine X placement, output Dot creation/reuse, mask kink Y drop, side-input above-spine, and layout_upstream() dispatch**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-13T00:47:19Z
- **Completed:** 2026-03-13T00:49:49Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created tests/test_horizontal_layout.py with 6 test classes and 10 test methods, all failing RED
- Established stub pattern with _StubDotNode (Dot-specific) and _StubKnob.setValue() extension
- Added nuke.Tab_Knob, nuke.Int_Knob, and nuke.lastHitGroup stubs required for horizontal layout entry points
- Verified full suite unchanged: 237 pre-existing tests pass; 4 pre-existing test_scale_nodes_axis errors remain (known nuke stub issue, documented in RESEARCH.md)

## Task Commits

1. **Task 1: RED test scaffold for horizontal B-spine layout** — `3f85bd6` (test)

## Files Created/Modified

- `/workspace/tests/test_horizontal_layout.py` — 569-line RED test scaffold covering all Phase 11 behavioral contracts

## Decisions Made

- Used `assertIs()` for the output Dot reuse test (identity check, not equality) — prevents a false pass if the implementation creates a new Dot with matching position values
- TestMaskKink inner class `_SpineNodeWithMask` uses `inputLabel("M")` for slot 2 — mirrors the real Merge2 pattern that `_is_mask_input()` reads, so the test drives the correct code path without requiring a fully-wired Merge2 stub
- TestModeReplay checks for both `"horizontal"` string AND `"place_subtree_horizontal"` in `layout_upstream()` body — prevents a false pass from a comment-only mention of the word

## Deviations from Plan

None — plan executed exactly as written. The test file structure, class names, and test count match the plan specification precisely.

## Issues Encountered

None. The stub pattern from test_fan_alignment.py transferred cleanly. The only additions needed were `_StubKnob.setValue()` (for Dot knob assignment), `_StubDotNode` subclass, and three new stub entries (`Tab_Knob`, `Int_Knob`, `lastHitGroup`).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- RED scaffold complete; Plan 02 can begin implementing `place_subtree_horizontal()` and `_find_or_create_output_dot()` against these acceptance criteria
- All 10 tests must pass GREEN after Plan 02 implementation
- Pre-condition for GREEN: `nuke.nodes.Dot()` in stub must return a `_StubDotNode` with `setXpos`/`setYpos` already working — confirmed stub supports this

---
*Phase: 11-horizontal-b-spine-layout*
*Completed: 2026-03-13*

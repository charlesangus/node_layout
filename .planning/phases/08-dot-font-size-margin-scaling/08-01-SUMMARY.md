---
phase: 08-dot-font-size-margin-scaling
plan: "01"
subsystem: testing
tags: [unittest, tdd, red-phase, node-layout, dot-font-scale]

# Dependency graph
requires:
  - phase: 06-horizontal-layout
    provides: _horizontal_margin and _subtree_margin helpers under test
  - phase: 07-per-node-state-storage
    provides: stable test infrastructure patterns (nuke stub, prefs reset)
provides:
  - RED test scaffold: 11 failing tests for _dot_font_scale LAYOUT-03 contract
  - TestDotFontScaleUnit (8 unit tests), TestSubtreeMarginFontScale (1), TestHorizontalMarginFontScale (1), TestNoRegression (1)
affects:
  - 08-02 (GREEN implementation — all tests in this file must pass after that plan)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_StubDotNode subclass pattern: stores upstream node; input(0) returns _upstream attribute"
    - "_StubDotNodeMissingFontKnob: overrides __getitem__ to raise KeyError for specific knob name"
    - "TDD RED scaffold: tests assert on AttributeError from missing symbol (8 tests) and AssertionError from unimplemented behaviour (2 tests)"

key-files:
  created:
    - tests/test_dot_font_scale.py
  modified: []

key-decisions:
  - "test_default_font_no_change passes at RED by design: regression guard verifying no change when font=reference is trivially true before implementation; this is the correct and expected RED state for that test"
  - "_StubDotNode uses _upstream attribute + input(0) override rather than _inputs list to express explicit upstream chaining semantics"

patterns-established:
  - "Keyed-KeyError stub pattern: _StubDotNodeMissingFontKnob raises KeyError only for 'note_font_size' while allowing 'label' through — tests the fallback path without hiding other knob reads"

requirements-completed:
  - LAYOUT-03

# Metrics
duration: ~8min
completed: 2026-03-11
---

# Phase 08 Plan 01: Dot Font Scale RED Test Scaffold Summary

**11-test RED scaffold for _dot_font_scale: walker + formula unit tests, margin integration tests, and reference-size regression guard — all backed by AttributeError/AssertionError before any production code**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-11T12:37:00Z
- **Completed:** 2026-03-11T12:45:47Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Wrote `tests/test_dot_font_scale.py` with 11 tests covering the full LAYOUT-03 contract
- 8 unit tests fail with AttributeError (missing `_dot_font_scale` symbol) — genuine RED
- 2 integration tests fail with AssertionError (margins not scaled yet) — genuine RED
- 1 regression guard (`test_default_font_no_change`) passes at RED by design — trivially true before implementation, will remain true after
- Full suite grows from 203 to 214 tests; existing 203 tests still pass (no regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write RED test scaffold (test_dot_font_scale.py)** - `fd486d9` (test)

**Plan metadata:** (docs commit follows)

_Note: This is a TDD RED-phase plan; no production code was written._

## Files Created/Modified

- `/workspace/tests/test_dot_font_scale.py` - 11-test RED scaffold for _dot_font_scale LAYOUT-03 contract

## Decisions Made

- `test_default_font_no_change` passes at RED by design: the test is a regression guard (checks that font=reference produces no change). Before implementation, no scaling occurs anywhere, so both baseline and ref-dot margins are equal. This is correct behavior at RED state; the test will continue to pass after GREEN implementation as long as the formula is correct (floor at 1.0 when font/reference=1.0).
- `_StubDotNode` uses an explicit `_upstream` attribute with `input(0)` override rather than the `_inputs` list pattern from `_StubNode`. This makes the upstream chain semantics explicit in the stub and avoids coupling to index-based list setup.

## Deviations from Plan

None - plan executed exactly as written. The one test that passes at RED (`test_default_font_no_change`) is consistent with the plan's implementation note: "TestSubtreeMarginFontScale and TestHorizontalMarginFontScale tests will pass or fail depending on whether the margin helpers incorporate font scaling." The regression test by its nature passes when no scaling is implemented.

## Issues Encountered

None.

## Next Phase Readiness

- RED scaffold complete; ready for 08-02 GREEN implementation of `_dot_font_scale` and its integration into `_subtree_margin` / `_horizontal_margin`
- All 10 failing tests provide a precise, unambiguous contract for the implementation

## Self-Check: PASSED

- `/workspace/tests/test_dot_font_scale.py` — FOUND
- commit `fd486d9` — FOUND

---
*Phase: 08-dot-font-size-margin-scaling*
*Completed: 2026-03-11*

---
phase: 08-dot-font-size-margin-scaling
plan: "02"
subsystem: layout
tags: [node_layout, dot, font-size, margin-scaling, nuke]

# Dependency graph
requires:
  - phase: 08-01
    provides: RED test scaffold (11 tests in test_dot_font_scale.py) for _dot_font_scale()
provides:
  - _dot_font_scale(node, slot) helper in node_layout.py
  - _subtree_margin() modified to multiply font_mult into effective_margin
  - _horizontal_margin() modified to multiply font_mult into gap value
affects:
  - 08-03
  - 09-fan-alignment

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "str() guard before .strip() when reading Nuke knob label values — knob stubs may return int 0"
    - "font multiplier applied multiplicatively before int() cast to preserve fractional precision"
    - "Dot walk uses candidate.input(0) not node.input(slot) — only input 0 of Dot is a logical chain"

key-files:
  created: []
  modified:
    - node_layout.py

key-decisions:
  - "str() wraps candidate['label'].value() to guard against non-string knob fallback values (int 0 from stub)"
  - "font_mult applied before the final int() cast in both margin helpers to avoid premature rounding"
  - "Walk uses candidate.input(0) for upstream traversal — Dots have a single logical upstream input"

patterns-established:
  - "str() guard on knob values: always coerce label values to str before calling .strip() — Nuke stubs may return int 0 for missing knobs"

requirements-completed:
  - LAYOUT-03

# Metrics
duration: 5min
completed: 2026-03-11
---

# Phase 8 Plan 02: Dot Font-Size Margin Scaling Summary

**_dot_font_scale() helper implemented in node_layout.py with min/max clamping formula, wired into both _subtree_margin() and _horizontal_margin() so labeled Dots with large fonts produce proportionally wider margins**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-11T12:47:00Z
- **Completed:** 2026-03-11T12:48:43Z
- **Tasks:** 2 (+ 1 auto-fix deviation)
- **Files modified:** 1

## Accomplishments

- Implemented `_dot_font_scale(node, slot)` with the locked formula `min(max(font_size / reference_size, 1.0), 4.0)`, floor at 1.0, cap at 4.0
- Modified `_subtree_margin()` to call `_dot_font_scale()` and multiply `font_mult` into `effective_margin` before `int()` cast
- Modified `_horizontal_margin()` to call `_dot_font_scale()` and multiply `font_mult` into gap values before `int()` cast
- All 11 new tests pass GREEN; full suite 214 tests, 0 failures

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement _dot_font_scale() and modify margin helpers** - `823204d` (feat)
2. **Auto-fix: guard label.strip() against non-string knob values** - `e63e9a7` (fix)

_Note: Task 2 (regression check) surfaced a bug fixed inline before final commit._

## Files Created/Modified

- `/workspace/node_layout.py` - Added `_dot_font_scale()` helper; modified `_subtree_margin()` and `_horizontal_margin()` to call it

## Decisions Made

- `str()` wraps the label knob value before `.strip()` — stubs return `int 0` for missing knobs; `str(0)` produces `'0'` which `.strip()` handles correctly, and `'0'.strip()` is falsy for the label check
- `font_mult` applied before the final `int()` in both margin helpers — applying `int()` early would discard fractional precision from intermediate calculations
- Walk uses `candidate.input(0)` for upstream traversal — Dot nodes have a single logical upstream connection on input 0

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Guard `label.strip()` against non-string knob fallback values**
- **Found during:** Task 2 (Full test suite regression check)
- **Issue:** `_StubKnob(0).value()` returns `int` `0`, not `str` `''`. Calling `0.strip()` raises `AttributeError`, causing 4 test failures in unrelated test files.
- **Fix:** Wrapped `candidate['label'].value()` in `str()` before calling `.strip()`
- **Files modified:** `node_layout.py`
- **Verification:** Full suite 214 tests pass after fix
- **Committed in:** `e63e9a7`

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix was necessary for correctness with real Nuke stubs. No scope creep.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- LAYOUT-03 complete: font-size-driven margin scaling is live
- node_layout.py exports `_dot_font_scale`, `_subtree_margin`, `_horizontal_margin` with updated contracts
- Phase 8 complete if no further plans; Phase 9 (Fan Alignment) can proceed

---
*Phase: 08-dot-font-size-margin-scaling*
*Completed: 2026-03-11*

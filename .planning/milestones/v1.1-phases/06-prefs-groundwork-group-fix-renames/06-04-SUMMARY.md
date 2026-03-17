---
phase: 06-prefs-groundwork-group-fix-renames
plan: "04"
subsystem: layout
tags: [nuke, group-context, lastHitGroup, ast-tests, python]

# Dependency graph
requires:
  - phase: 06-03
    provides: group context wrapping with nuke.thisGroup() at entry points and 'with current_group:' pattern
provides:
  - layout_upstream() and layout_selected() using nuke.lastHitGroup() for Group View compatibility
  - AST tests asserting lastHitGroup() at both entry points
affects: [phase-07, phase-08, phase-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "nuke.lastHitGroup() as the canonical group-context capture API — works for both Ctrl-Enter and Group View panels"

key-files:
  created: []
  modified:
    - node_layout.py
    - tests/test_group_context.py

key-decisions:
  - "nuke.lastHitGroup() replaces nuke.thisGroup() — lastHitGroup() resolves the last-clicked Group View panel context (correct for both Ctrl-Enter and Group View); thisGroup() only resolves Python call-stack context (Ctrl-Enter only)"

patterns-established:
  - "Group context capture: current_group = nuke.lastHitGroup() as FIRST Nuke API call at every layout entry point"

requirements-completed: [LAYOUT-04]

# Metrics
duration: 4min
completed: 2026-03-08
---

# Phase 6 Plan 04: Group View Context Fix (lastHitGroup) Summary

**Two-line production fix: nuke.lastHitGroup() replaces nuke.thisGroup() in both layout entry points, closing the Group View panel context bug**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-08T03:20:16Z
- **Completed:** 2026-03-08T03:24:00Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Replaced `nuke.thisGroup()` with `nuke.lastHitGroup()` in `layout_upstream()` and `layout_selected()` so commands work correctly when the user has a Group open in a Group View panel (not just via Ctrl-Enter)
- Updated both AST test docstrings and the two `capture_text` assertions in `test_group_context.py` to match the new API call
- All 168 tests pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace nuke.thisGroup() with nuke.lastHitGroup() in layout entry points and update AST tests** - `3b6df2c` (fix)

## Files Created/Modified

- `node_layout.py` - Lines 583 and 633: `nuke.thisGroup()` → `nuke.lastHitGroup()` in `layout_upstream()` and `layout_selected()`
- `tests/test_group_context.py` - Docstring (lines 5, 8) and `capture_text` strings (lines 43, 99) updated to assert `lastHitGroup()`

## Decisions Made

- `nuke.lastHitGroup()` is the canonical Nuke API for this use case: it returns the group associated with the last-clicked Group View panel, making it correct for both Ctrl-Enter navigation and explicit Group View panels. At root (no Group View active), it returns `nuke.root()` — the same safe fallback as `thisGroup()`. Foundry documents this explicitly; `nukescripts.createNodeLocal` uses it internally.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

`pytest` was not available in this environment (`python3-pytest` not installed and no pip). Tests were run via `/usr/bin/python3.11 -m unittest discover` instead. All 168 tests passed identically.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Group View context gap (UAT test 4) is now closed: `layout_upstream()` and `layout_selected()` will correctly scope Dot node creation and `push_nodes_to_make_room()` inside the active Group View panel
- Phase 7 (State Storage) can proceed — no layout entry point concerns remain

## Self-Check: PASSED

- node_layout.py: FOUND (contains 2x `nuke.lastHitGroup()`, zero `nuke.thisGroup()`)
- tests/test_group_context.py: FOUND (asserts `lastHitGroup()` in both capture_text strings)
- 06-04-SUMMARY.md: FOUND
- Commit 3b6df2c: FOUND
- All 168 tests pass

---
*Phase: 06-prefs-groundwork-group-fix-renames*
*Completed: 2026-03-08*

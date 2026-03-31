---
phase: 20-wasd-chaining-c-command
plan: "01"
subsystem: ui
tags: [pyside6, event-filter, leader-key, make_room, chaining]

# Dependency graph
requires:
  - phase: 19-event-filter-core-dispatch
    provides: LeaderKeyFilter with _DISPATCH_TABLE, arm(), _disarm(), auto-repeat guard
  - phase: 18-overlay-widget
    provides: LeaderKeyOverlay.hide() API
provides:
  - "_CHAINING_DISPATCH_TABLE mapping W/A/S/D/Q/E to dispatch callables in node_layout_leader.py"
  - "Six chaining dispatch helpers: _dispatch_move_up/down/left/right, _dispatch_shrink, _dispatch_expand"
  - "eventFilter two-step dispatch: single-shot table first, chaining table second"
  - "Overlay hides on first chaining keypress; leader mode stays active for chaining"
affects: [21-menu-binding, phase-21, tests, leader-key]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-table event dispatch: _DISPATCH_TABLE (disarms after dispatch) + _CHAINING_DISPATCH_TABLE (stays armed)"
    - "Inline imports in dispatch helpers to avoid circular imports at startup (established in Phase 19, extended here)"
    - "TDD RED/GREEN with AST structural tests for source-level verification without PySide6 instantiation"

key-files:
  created: []
  modified:
    - node_layout_leader.py
    - tests/test_node_layout_leader.py

key-decisions:
  - "Two separate dispatch tables rather than a unified table with flags — keeps single-shot vs chaining semantics explicit"
  - "Chaining branch calls _overlay.hide() directly, never _disarm() — leader mode stays active for session-length chaining"
  - "WASD amounts match existing bracket shortcuts exactly: up/down=1600, left/right=800 (D-01, D-02)"
  - "Per-step undo (no session-level undo group) — each WASD/Q/E press independently undoable (D-12, D-13)"

patterns-established:
  - "Two-table dispatch pattern: _DISPATCH_TABLE for disarming commands, _CHAINING_DISPATCH_TABLE for non-disarming commands"

requirements-completed: [DISP-05, DISP-06, DISP-07, DISP-08]

# Metrics
duration: 3min
completed: 2026-03-31
---

# Phase 20 Plan 01: WASD Chaining + C Command Summary

**WASD/Q/E chaining dispatch in LeaderKeyFilter — six helpers delegating to make_room() and shrink/expand_selected(), with two-table eventFilter keeping leader mode active for chained input**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-31T03:56:43Z
- **Completed:** 2026-03-31T03:58:51Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `_CHAINING_DISPATCH_TABLE` mapping W/A/S/D/Q/E to their respective dispatch callables
- Added six private dispatch helpers (`_dispatch_move_up/down/left/right`, `_dispatch_shrink`, `_dispatch_expand`) using inline import pattern from Phase 19
- Modified `eventFilter()` with two-step lookup: single-shot table first (disarms), chaining table second (stays armed, hides overlay)
- Extended AST structural tests with 13 new test methods across three new test classes; all 27 tests pass

## Task Commits

Each task was committed atomically:

1. **TDD RED: Structural tests for chaining dispatch** - `9ff741b` (test)
2. **TDD GREEN: WASD/Q/E chaining implementation** - `669d5d3` (feat)
3. **Task 2: Test module docstring update** - `289fc88` (feat)

_Note: TDD tasks have multiple commits (test RED → feat GREEN)_

## Files Created/Modified

- `/workspace/node_layout_leader.py` — Added six chaining dispatch helpers, `_CHAINING_DISPATCH_TABLE`, two-step eventFilter lookup, updated module docstring
- `/workspace/tests/test_node_layout_leader.py` — Added `TestChainingDispatchTableKeys`, `TestChainingDispatchHelpers`, `TestChainingDispatchTable` classes (13 new test methods); updated module docstring

## Decisions Made

- Kept two separate dispatch tables rather than a unified table with a `chains: bool` flag — the disarm/no-disarm distinction is the semantic core and reads more clearly as two named dicts
- `_overlay.hide()` called directly in chaining branch (not via `_disarm()`) — preserves `_leader_active = True` state while still cleaning up UI
- Amount values (up/down=1600, left/right=800) taken verbatim from existing bracket shortcuts — no new movement parameters introduced
- Per-step undo retained as designed in context D-12/D-13 — no session-level undo group

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None — all dispatch helpers wire directly to existing `make_room.make_room()`, `node_layout.shrink_selected()`, and `node_layout.expand_selected()`.

## Next Phase Readiness

- `node_layout_leader.py` chaining dispatch complete — Phase 21 (menu.py Shift+E binding) can wire `arm()` as the Shift+E handler
- All 27 structural AST tests pass; CI will validate on push
- C command (DISP-04) remains implemented from Phase 19 as planned — no changes needed

## Self-Check: PASSED

- node_layout_leader.py: FOUND
- tests/test_node_layout_leader.py: FOUND
- .planning/phases/20-wasd-chaining-c-command/20-01-SUMMARY.md: FOUND
- Commit 9ff741b (TDD RED tests): FOUND
- Commit 669d5d3 (feat GREEN implementation): FOUND
- Commit 289fc88 (Task 2 docstring): FOUND

---
*Phase: 20-wasd-chaining-c-command*
*Completed: 2026-03-31*

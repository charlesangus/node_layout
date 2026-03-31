---
phase: 21-menu-wiring
plan: 01
subsystem: ui
tags: [menu, nuke, leader-mode, ast-testing, keyboard-shortcut]

# Dependency graph
requires:
  - phase: 19-event-filter-core-dispatch
    provides: node_layout_leader module with arm() function
  - phase: 20-wasd-chaining-c-command
    provides: complete leader key dispatch logic
provides:
  - Shift+E wired to leader mode entry via menu.py
  - Layout Upstream accessible without keyboard shortcut
  - 6 AST structural tests verifying LEAD-01 wiring
affects: [phase-21-menu-wiring, ci-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Inline import pattern for addCommand callbacks (no top-level imports)
    - AST structural testing for menu wiring verification

key-files:
  created:
    - tests/test_menu_leader_wiring.py
  modified:
    - menu.py

key-decisions:
  - "Layout (Leader Mode) placed before Layout Upstream — preserves D-02 ordering decision"
  - "Inline import callback pattern used: no top-level import node_layout_leader added to menu.py"
  - "Layout Upstream retains no shortcut — Shift+E exclusively owned by leader mode"

patterns-established:
  - "Leader mode entry via Shift+E: import node_layout_leader; node_layout_leader.arm()"
  - "AST tests for menu wiring: parse menu.py source to verify structural properties without Nuke"

requirements-completed: [LEAD-01]

# Metrics
duration: 2min
completed: 2026-03-31
---

# Phase 21 Plan 01: Menu Wiring Summary

**Shift+E wired to leader mode arm() via inline import callback in menu.py, Layout Upstream shortcut removed, 6 AST structural tests verify LEAD-01**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-31T04:17:15Z
- **Completed:** 2026-03-31T04:19:16Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `Layout (Leader Mode)` command with `shift+e` shortcut and inline import callback to menu.py
- Removed `shift+e` and `shortcutContext=2` from `Layout Upstream` (command retained, shortcut cleared)
- Created 6 AST structural tests in `tests/test_menu_leader_wiring.py` verifying LEAD-01 wiring — all pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add leader mode command and remove Layout Upstream shortcut** - `69a6cc3` (feat)
2. **Task 2: AST structural test for menu wiring** - `5bd35c8` (feat)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified

- `/workspace/menu.py` - Added Layout (Leader Mode) addCommand before Layout Upstream; Layout Upstream no longer has shift+e
- `/workspace/tests/test_menu_leader_wiring.py` - 6 AST tests in TestMenuLeaderWiring verifying LEAD-01 wiring

## Decisions Made

- Layout (Leader Mode) placed before Layout Upstream in menu.py (preserves D-02 ordering)
- Inline import pattern used — no top-level `import node_layout_leader` in menu.py (preserves D-04)
- Layout Upstream retains no shortcut — Shift+E exclusively owned by leader mode going forward

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 21 Plan 01 complete: Shift+E leader mode wiring is live
- The v1.4 Leader Key feature is fully connected: Phases 18-20 built the event filter and dispatch; Phase 21-01 connects it to the Nuke menu system
- Ready for UAT: user should verify Shift+E arms leader mode in a live Nuke session

---
*Phase: 21-menu-wiring*
*Completed: 2026-03-31*

---
phase: quick-260325-k1f
plan: 01
subsystem: ui
tags: [nuke, menu, reload-safety]

provides:
  - "All addCommand calls in menu.py use inline import string form"
affects: [menu-registration]

key-files:
  modified: [menu.py]

key-decisions:
  - "freeze_selected/unfreeze_selected commands not in current menu.py -- skipped (plan listed them but they do not exist yet)"

requirements-completed: [QUICK-K1F]

duration: 1min
completed: 2026-03-25
---

# Quick Task 260325-k1f: Fix menu.py Command Strings Summary

**Converted all 26 addCommand calls to inline import string form and removed unused top-level imports of node_layout, node_layout_prefs_dialog**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-25T18:28:25Z
- **Completed:** 2026-03-25T18:29:29Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Converted 24 callable-reference addCommand calls to `"import X; X.func()"` string form
- Added inline `import` prefix to 8 existing string commands (make_room, util)
- Removed top-level `import node_layout` and `import node_layout_prefs_dialog`
- Only `import nuke` remains as top-level import

## Task Commits

Each task was committed atomically:

1. **Task 1: Convert all addCommand calls to inline import strings and remove unused imports** - `55b7610` (feat)

## Files Created/Modified
- `menu.py` - All addCommand calls now use inline import string form for reload safety

## Decisions Made
- freeze_selected and unfreeze_selected were listed in the plan's conversion table but do not exist in the current menu.py -- skipped without error (they will be added when freeze commands land in the menu)

## Deviations from Plan

None - plan executed exactly as written (minus two conversions for commands not yet present in the file).

## Issues Encountered
None

## Known Stubs
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- menu.py is now fully reload-safe with inline imports
- Future menu additions should follow the same `"import X; X.func()"` pattern

## Self-Check: PASSED

- FOUND: menu.py
- FOUND: 55b7610

---
*Quick Task: 260325-k1f*
*Completed: 2026-03-25*

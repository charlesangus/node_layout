---
phase: 04-preferences-system
plan: "02"
subsystem: ui
tags: [pyside6, qdialog, qformlayout, qlineedit, nuke-menu, preferences]

# Dependency graph
requires:
  - phase: 04-01
    provides: NodeLayoutPrefs singleton with get/set/save interface for 7 layout keys
provides:
  - PySide6 QDialog (NodeLayoutPrefsDialog) exposing 7 QLineEdit fields for spacing preferences
  - show_prefs_dialog() module-level function callable from Nuke menu
  - Node Layout menu Preferences entry with separator
affects:
  - 04-03
  - 05-preset-commands

# Tech tracking
tech-stack:
  added: [PySide6.QtWidgets (QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QVBoxLayout)]
  patterns:
    - QLineEdit (not QSpinBox) for numeric input — validates via try/except ValueError in _on_accept()
    - prefs_instance local alias to module singleton avoids shadowing module name
    - show_prefs_dialog() module-level wrapper calls dialog.exec() for Nuke menu wiring

key-files:
  created:
    - node_layout/node_layout_prefs_dialog.py
  modified:
    - node_layout/menu.py

key-decisions:
  - "Use QLineEdit not QSpinBox/QDoubleSpinBox — matches Labelmaker dialog pattern for sibling consistency"
  - "Validate base_subtree_margin > 0 and scaling_reference_count >= 1 to prevent ZeroDivisionError in sqrt formula"
  - "Import node_layout_prefs_dialog in menu.py only; dialog imports prefs internally — menu.py has no direct dependency on prefs singleton"
  - "Preferences unicode ellipsis (\\u2026) in menu command label matches Nuke menu convention"

patterns-established:
  - "Dialog pattern: _build_ui() + _populate_from_prefs() on __init__, _on_accept() validates + saves + self.accept()"
  - "No tight gap field in dialog — snap_threshold * 1 is not user-configurable (locked decision)"
  - "No preset selector widget in dialog — Compact/Normal/Loose are Phase 5 menu commands"

requirements-completed: [PREFS-05, PREFS-06]

# Metrics
duration: 1min
completed: "2026-03-04"
---

# Phase 4 Plan 02: Preferences Dialog Summary

**PySide6 QDialog with 7 QLineEdit fields for spacing preferences, wired into the Node Layout menu via show_prefs_dialog()**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-04T12:21:22Z
- **Completed:** 2026-03-04T12:22:27Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- NodeLayoutPrefsDialog QDialog with QFormLayout exposing all 7 configurable parameters as QLineEdit fields
- _on_accept() validates int/float conversion, enforces base_subtree_margin > 0 and scaling_reference_count >= 1, then saves to prefs_singleton
- Preferences command added to Node Layout menu with separator, import correctly placed before nuke.menu() call

## Task Commits

Each task was committed atomically:

1. **Task 1: Create node_layout_prefs_dialog.py** - `628901b` (feat)
2. **Task 2: Wire Preferences entry into menu.py** - `e6361ea` (feat)

## Files Created/Modified

- `node_layout/node_layout_prefs_dialog.py` - PySide6 QDialog class with 7 QLineEdit fields, validation, prefs save, and show_prefs_dialog() function
- `node_layout/menu.py` - Added import node_layout_prefs_dialog and Preferences command with separator at end of Node Layout menu

## Decisions Made

- Used QLineEdit (not QSpinBox/QDoubleSpinBox) to match Labelmaker dialog pattern for sibling plugin consistency
- Validate base_subtree_margin > 0 and scaling_reference_count >= 1 in _on_accept() to prevent downstream ZeroDivisionError in sqrt formula
- menu.py imports only node_layout_prefs_dialog (not node_layout_prefs directly) — dialog handles prefs internally
- Unicode ellipsis (\u2026) in "Preferences..." label matches Nuke menu convention

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Preferences dialog is complete and accessible from Node Layout menu
- Ready for Plan 04-03 (integration with layout operations reading from prefs_singleton at call time)
- Phase 5 preset commands (Compact/Normal/Loose) can call prefs_singleton.set() + layout operations without needing dialog changes

---
*Phase: 04-preferences-system*
*Completed: 2026-03-04*

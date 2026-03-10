---
phase: 06-prefs-groundwork-group-fix-renames
plan: 01
subsystem: ui
tags: [pyside6, preferences, dialog, qformlayout, qlabel, tdd, ast-tests]

# Dependency graph
requires: []
provides:
  - "node_layout_prefs.DEFAULTS with 10 keys including horizontal_subtree_gap=150, horizontal_mask_gap=50, dot_font_reference_size=20"
  - "Rebalanced defaults: base_subtree_margin=200 (was 300), loose_gap_multiplier=8.0 (was 12.0)"
  - "NodeLayoutPrefsDialog reorganized into 3 sections (Spacing, Scheme Multipliers, Advanced) with bold QLabel headers"
  - "AST structural tests for dialog (tests/test_node_layout_prefs_dialog.py)"
affects:
  - "06-02 (engine changes will consume horizontal_subtree_gap and horizontal_mask_gap from prefs)"
  - "Phase 8 (font-margin engine will use dot_font_reference_size)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AST-based structural tests for PySide6 dialogs (avoids display server requirement)"
    - "Bold QLabel section headers in QFormLayout (no QGroupBox borders)"
    - "_make_section_header() module-level helper for reuse"

key-files:
  created:
    - "tests/test_node_layout_prefs_dialog.py"
  modified:
    - "node_layout_prefs.py"
    - "node_layout_prefs_dialog.py"
    - "tests/test_node_layout_prefs.py"

key-decisions:
  - "QGroupBox not used for sections — bold QLabel headers preserve flat form appearance without borders"
  - "horizontal_mask_gap validated as >= 0 (not > 0) — a mask gap of zero is architecturally valid"
  - "No migration logic added — users with existing ~/.nuke/node_layout_prefs.json must delete it to see rebalanced defaults"
  - "AST structural tests chosen over mock-instantiation — avoids PySide6 display server dependency in CI"

patterns-established:
  - "Dialog sections: _make_section_header('Section Name') + QLabel('') spacer before each non-first section"
  - "New int pref fields: parse as int(), validate bounds, call prefs_singleton.set() + .save()"

requirements-completed: [PREFS-01, PREFS-02, PREFS-03, PREFS-04]

# Metrics
duration: 3min
completed: 2026-03-07
---

# Phase 6 Plan 01: Prefs Groundwork Summary

**10-key DEFAULTS with 3 new H-axis and font-reference prefs, prefs dialog reorganized into Spacing/Scheme Multipliers/Advanced sections using bold QLabel headers**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-07T06:35:47Z
- **Completed:** 2026-03-07T06:38:57Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Extended node_layout_prefs.DEFAULTS from 7 to 10 keys with horizontal_subtree_gap (150), horizontal_mask_gap (50), and dot_font_reference_size (20)
- Rebalanced base_subtree_margin from 300 to 200 and loose_gap_multiplier from 12.0 to 8.0 for less-tall, wider layouts by default
- Reorganized NodeLayoutPrefsDialog into three visually distinct sections (Spacing, Scheme Multipliers, Advanced) using bold QLabel section headers without QGroupBox borders
- All 10 prefs now parse, validate, and save in _on_accept() including the 3 new int fields
- Added 26 prefs tests (including new round-trip and partial-fallback tests) and 21 AST structural dialog tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Add 3 new keys to DEFAULTS and rebalance existing defaults** - `2fc06d8` (feat)
2. **Task 2: Reorganize prefs dialog into three sections with 3 new fields** - `af52d83` (feat)

_Note: Both tasks executed as TDD (RED failing tests first, then GREEN implementation)._

## Files Created/Modified
- `/workspace/node_layout_prefs.py` - DEFAULTS expanded from 7 to 10 keys with rebalanced values
- `/workspace/node_layout_prefs_dialog.py` - _make_section_header() added; _build_ui() reorganized into 3 sections; _populate_from_prefs() and _on_accept() updated for all 10 keys
- `/workspace/tests/test_node_layout_prefs.py` - Updated for 10-key assertions, new default/round-trip/fallback tests, /workspace path fix
- `/workspace/tests/test_node_layout_prefs_dialog.py` - New file: 21 AST structural tests for dialog

## Decisions Made
- **QGroupBox not used:** Section headers are bold QLabel rows — keeps the form flat without borders, as specified by plan anti-patterns
- **horizontal_mask_gap validated as >= 0 (not > 0):** A mask gap of zero is a valid architectural choice (tightly-packed mask input); only negative values are invalid
- **No migration logic:** Existing users must delete ~/.nuke/node_layout_prefs.json to see rebalanced defaults — documented in test file
- **AST tests over PySide6 instantiation:** Structural tests use ast.parse() rather than creating real QDialog widgets, making them runnable without a display server

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] QGroupBox check in AST test was a false positive**
- **Found during:** Task 2 (dialog structural tests, RED phase)
- **Issue:** Test `assertNotIn("QGroupBox", source)` failed because "QGroupBox" appeared in a docstring comment "(no QGroupBox borders)" — this is not actual usage
- **Fix:** Changed test to scan only import lines rather than full source text
- **Files modified:** tests/test_node_layout_prefs_dialog.py
- **Verification:** All 21 dialog tests pass
- **Committed in:** af52d83 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in test assertion logic)
**Impact on plan:** Minimal — test precision improvement only, no scope change.

## Issues Encountered
None beyond the false-positive QGroupBox test noted above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 02 can now consume `horizontal_subtree_gap` and `horizontal_mask_gap` from prefs_singleton for H-axis engine logic
- `dot_font_reference_size` key is stubbed and ready for Phase 8 font-margin scaling engine
- No blockers

---
*Phase: 06-prefs-groundwork-group-fix-renames*
*Completed: 2026-03-07*

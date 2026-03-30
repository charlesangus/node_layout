---
phase: 17-prefs-dialog-foundation
plan: 01
subsystem: prefs
tags: [prefs, dialog, leader-key, tdd]
dependency_graph:
  requires: []
  provides: [hint_popup_delay_ms pref key, Leader Key dialog section]
  affects: [node_layout_prefs.py, node_layout_prefs_dialog.py]
tech_stack:
  added: []
  patterns: [TDD red-green, JSON prefs singleton, QLineEdit form section]
key_files:
  created: []
  modified:
    - node_layout_prefs.py
    - node_layout_prefs_dialog.py
    - tests/test_node_layout_prefs.py
    - tests/test_node_layout_prefs_dialog.py
decisions:
  - hint_popup_delay_ms stored with default 0 as 12th DEFAULTS key
  - Leader Key section placed between Scheme Multipliers and Advanced
  - hint_popup_delay_ms_value < 0 rejected silently (returns from _on_accept)
metrics:
  duration: 130s
  completed: "2026-03-30"
  tasks_completed: 2
  files_modified: 4
---

# Phase 17 Plan 01: Prefs Dialog Foundation Summary

**One-liner:** Added `hint_popup_delay_ms` pref (default 0) to DEFAULTS dict and exposed it in the preferences dialog under a new "Leader Key" section with int parse, non-negative validation, and persist-on-accept.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add hint_popup_delay_ms to DEFAULTS and update tests | 2c7f1a3 | node_layout_prefs.py, tests/test_node_layout_prefs.py |
| 2 | Add Leader Key section to preferences dialog and update dialog tests | 86a7b5d | node_layout_prefs_dialog.py, tests/test_node_layout_prefs_dialog.py |

## What Was Built

- `node_layout_prefs.py`: Added `"hint_popup_delay_ms": 0` as the 12th key in DEFAULTS, with comment `# Leader key hint popup delay in milliseconds (0 = immediate)`
- `node_layout_prefs_dialog.py`: Inserted a "Leader Key" section between "Scheme Multipliers" and "Advanced" containing a `hint_popup_delay_ms_edit` QLineEdit. Updated `_populate_from_prefs`, `_on_accept` (parse + `< 0` guard + `prefs_instance.set`), and class docstring.
- `tests/test_node_layout_prefs.py`: Added `test_default_hint_popup_delay_ms`, renamed eleven-key test to `test_defaults_contains_all_twelve_keys`, added `test_round_trip_hint_popup_delay_ms`, and extended partial-file fallback assertion.
- `tests/test_node_layout_prefs_dialog.py`: Added `TestDialogLeaderKeySection` class with 5 structural tests covering section header, field presence, populate, on_accept parse, and section ordering.

## Verification Results

- All 28 prefs tests pass (0 failures)
- All 26 dialog tests pass (0 failures)
- Full suite (prefs + dialog + integration): 84 tests pass (0 failures)
- Structural checks:
  - `grep -c "hint_popup_delay_ms" node_layout_prefs.py` = 1
  - `grep -c "hint_popup_delay_ms_edit" node_layout_prefs_dialog.py` = 4 (>= 3)
  - `grep -c "hint_popup_delay_ms_value" node_layout_prefs_dialog.py` = 3 (>= 2)
  - `grep '"Leader Key"' node_layout_prefs_dialog.py` matches
  - `grep "four sections" node_layout_prefs_dialog.py` matches

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — `hint_popup_delay_ms` is stored and retrievable from prefs; dialog reads/writes it correctly. The runtime Qt behavior consuming this value is deferred to Phase 18 (Overlay Widget) by design.

## Self-Check: PASSED

- `/workspace/node_layout_prefs.py` — FOUND
- `/workspace/node_layout_prefs_dialog.py` — FOUND
- `/workspace/tests/test_node_layout_prefs.py` — FOUND
- `/workspace/tests/test_node_layout_prefs_dialog.py` — FOUND
- Commit 2c7f1a3 — FOUND
- Commit 86a7b5d — FOUND

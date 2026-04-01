---
phase: quick
plan: 260331-ozs
subsystem: leader-key
tags: [leader-key, overlay, selection, hidden-outputs]
key-files:
  modified:
    - node_layout_leader.py
    - node_layout_overlay.py
decisions:
  - X is a single-shot key (disarms leader mode after dispatch), consistent with V/Z/F/C
  - Inline import pattern used for node_layout_util in _dispatch_select_hidden_downstream
  - Removed setColumnMinimumWidth(1, 64) from overlay — X fills col 1 row 2 naturally
metrics:
  duration: "~3min"
  completed: "2026-04-01T01:02:39Z"
  tasks: 1
  files: 2
---

# Quick Task 260331-ozs: Add X Key to Leader Mode

**One-liner:** X key in leader mode selects downstream hidden-input nodes via `node_layout_util.select_hidden_outputs()` and exits leader mode.

## What Was Done

Added X as a single-shot leader key command that invokes the existing
`select_hidden_outputs` function — completing the QWERTY grid row 2 and
giving the command keyboard-accessible leader mode parity with the menu entry.

## Task 1: Wire X key dispatch and overlay entry

**Commit:** f66b787

**Changes in `node_layout_leader.py`:**
- Added `_dispatch_select_hidden_downstream()` after `_dispatch_clear_state` — calls `node_layout_util.select_hidden_outputs()` via inline import
- Added `Qt.Key.Key_X: _dispatch_select_hidden_downstream` to `_DISPATCH_TABLE`
- Added `"X": Qt.Key.Key_X` to `_LETTER_TO_QT_KEY`
- Updated module docstring and `dispatch_key` docstring: single-shot list now reads `(V, Z, F, C, X)`

**Changes in `node_layout_overlay.py`:**
- Replaced empty-slot comment in `_KEY_LAYOUT` with `("X", "Sel Hidden", 2, 1)`
- Removed `key_grid.setColumnMinimumWidth(1, 64)` — no longer needed since the slot is occupied

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- `/workspace/node_layout_leader.py` — FOUND
- `/workspace/node_layout_overlay.py` — FOUND
- Commit f66b787 — FOUND (`git log --oneline -1` confirms)
- AST verification: `_dispatch_select_hidden_downstream` present as top-level function
- `Key_X` in dispatch table and letter mapping
- `"X"` entry in overlay `_KEY_LAYOUT` at row 2, col 1

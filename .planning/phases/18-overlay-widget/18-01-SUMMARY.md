---
phase: 18-overlay-widget
plan: "01"
subsystem: overlay-widget
tags: [pyside6, widget, hud, leader-key, structural-tests]
dependency_graph:
  requires: []
  provides: [node_layout_overlay.LeaderKeyOverlay]
  affects: []
tech_stack:
  added: [node_layout_overlay.py]
  patterns: [AST-structural-tests, focus-safe-floating-window, QPainter-transparency]
key_files:
  created:
    - node_layout_overlay.py
    - tests/test_node_layout_overlay.py
  modified: []
decisions:
  - "show() calls super().show() before move() — native window must exist before geometry can be set (Pitfall 4 guard)"
  - "Module-level _CHAINING_KEY_COLOR and _SINGLE_SHOT_KEY_COLOR constants named so AST tests can verify two distinct badge colors without importing PySide6"
  - "WA_TranslucentBackground + paintEvent with QPainter used instead of stylesheet background — stylesheet transparency unreliable in Nuke embedded hierarchy"
metrics:
  duration: "2m9s"
  completed_date: "2026-03-30"
  tasks_completed: 2
  files_changed: 2
---

# Phase 18 Plan 01: Overlay Widget Summary

**One-liner:** LeaderKeyOverlay QWidget with focus-safe Qt attributes, QWERTY grid of 10 command keys, semi-transparent QPainter background, and 19 structural tests — all passing without PySide6 in CI.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create stub test file with failing assertions | daf1fbf | tests/test_node_layout_overlay.py |
| 2 | Implement LeaderKeyOverlay widget | b4b368c | node_layout_overlay.py |

## What Was Built

### `node_layout_overlay.py` — LeaderKeyOverlay class

A PySide6 `QWidget` subclass that floats over the active DAG panel displaying the 10 active leader-mode command keys in true QWERTY keyboard geometry. Key implementation details:

- **Focus safety (OVRL-03):** `Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint` in `setWindowFlags`, plus `setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)` — set in `__init__` before any `show()` call.
- **Semi-transparent background (D-01):** `WA_TranslucentBackground` + `paintEvent` drawing a `QColor(20, 20, 20, 180)` rounded-rect via `QPainter`. Self-contained — not dependent on parent chain transparency.
- **QWERTY grid (D-04/D-05):** `QGridLayout` with cells at exact keyboard positions. Empty `X` position at row 2 col 1 left unpopulated; `setColumnMinimumWidth(1, 64)` maintains column width.
- **Two-color badge system (D-09/D-10):** `_CHAINING_KEY_COLOR` (teal `QColor(40, 120, 160)`) for WASD/QE, `_SINGLE_SHOT_KEY_COLOR` (neutral `QColor(220, 220, 220)`) for VZFC. `CHAINING_KEYS` set drives per-cell color selection.
- **Centering (D-08):** `show()` override calls `super().show()` first (native window exists), then `parent.mapToGlobal(parent.rect().center()) - self.rect().center()` for pixel-accurate centering.
- **`adjustSize()` in `__init__`:** Ensures `rect()` has real dimensions when `show()` runs centering math.

### `tests/test_node_layout_overlay.py` — 19 structural tests

AST/string-based tests following the established `test_node_layout_prefs_dialog.py` pattern. Six test classes covering OVRL-01 through OVRL-04:

| Class | Tests | Coverage |
|-------|-------|----------|
| TestOverlayClassExists | 2 | Class definition + QWidget inheritance |
| TestOverlayQtProperties | 4 | WA_ShowWithoutActivating, WindowType.Tool, WA_TranslucentBackground, FramelessWindowHint |
| TestOverlayKeyLayout | 3 | All 10 key labels, LEADER KEY title, QGridLayout |
| TestOverlayColorConstants | 4 | _CHAINING_KEY_COLOR, _SINGLE_SHOT_KEY_COLOR, CHAINING_KEYS |
| TestOverlayShowCentering | 3 | show() defined, self.move() called, adjustSize present |
| TestOverlayPaintEvent | 3 | paintEvent defined, QPainter, drawRoundedRect |

No `from PySide6` imports in test file — fully runnable in CI without a display server.

## Verification Results

- `python3 -m pytest tests/test_node_layout_overlay.py -v` — 19/19 passed
- `python3 -m pytest tests/ --ignore=tests/test_freeze_integration.py -q` — 366 passed (no regressions; 19 new tests added to prior 347)

## Deviations from Plan

None — plan executed exactly as written.

One design clarification applied per research (not a deviation): `show()` calls `super().show()` *before* `self.move()`, matching Pitfall 4 guidance in 18-RESEARCH.md. The plan's action code listed the same order; the research note made the rationale explicit.

## Known Stubs

None. The `LeaderKeyOverlay` widget is fully implemented. Phase 19 will wire it into the event filter and manage `show()`/`hide()` calls.

## Self-Check: PASSED

---
phase: quick
plan: 260331-3nb
subsystem: leader-key-event-filter
tags: [event-filter, shortcut-override, qt, pyside6, leader-mode]
dependency_graph:
  requires: [node_layout_leader.py]
  provides: [ShortcutOverride consumption in LeaderKeyFilter.eventFilter]
  affects: [node_layout_leader.py, tests/test_node_layout_leader.py]
tech_stack:
  added: []
  patterns: [Qt ShortcutOverride interception, AST-based structural tests]
key_files:
  created: []
  modified:
    - node_layout_leader.py
    - tests/test_node_layout_leader.py
decisions:
  - ShortcutOverride handled before KeyPress in eventFilter — only active when _leader_active is True
  - event.accept() + return True both required: accept() informs Qt, return True suppresses propagation
  - New tests follow existing AST structural pattern (no PySide6 instantiation) for CI compatibility
metrics:
  duration: ~5min
  completed: "2026-03-31"
  tasks_completed: 2
  files_modified: 2
---

# Quick Task 260331-3nb: Fix ShortcutOverride Consumption in Leader Key Filter

**One-liner:** Added `QEvent.Type.ShortcutOverride` interception to `LeaderKeyFilter.eventFilter()` so Nuke's built-in shortcuts (e.g., C -> ColorCorrect) cannot fire while leader mode is active.

## Problem

Qt dispatches `QEvent.Type.ShortcutOverride` **before** `QEvent.Type.KeyPress`. If `eventFilter()` only handled `KeyPress`, Nuke's shortcut system would match the key against registered menu shortcuts during the `ShortcutOverride` phase — before the `KeyPress` handler ran. The result: pressing C during leader mode would both dispatch `_dispatch_clear_freeze()` AND create a ColorCorrect node in Nuke.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Consume ShortcutOverride during leader mode | 2172024 | node_layout_leader.py |
| 2 | Add structural tests for ShortcutOverride | 80b1b8b | tests/test_node_layout_leader.py |

## Changes Made

### node_layout_leader.py

Added `ShortcutOverride` handling inside `LeaderKeyFilter.eventFilter()`, immediately after `event_type = event.type()` and before the `KeyPress` block:

```python
# Qt sends ShortcutOverride before KeyPress; if not consumed, Nuke's shortcut
# system matches the key (e.g., C -> ColorCorrect) before our KeyPress handler runs.
if event_type == QEvent.Type.ShortcutOverride:
    # Accept the shortcut override to prevent Nuke's shortcut system
    # from matching this key while leader mode is active.
    event.accept()
    return True
```

This fires only when `_leader_active is True` (guarded by the early-return at the top of `eventFilter`).

### tests/test_node_layout_leader.py

Added `TestShortcutOverrideConsumption` class (4 structural tests):
- `test_shortcut_override_type_referenced` — `ShortcutOverride` string present in source
- `test_shortcut_override_consumed_with_accept` — `event.accept()` present in source
- `test_shortcut_override_inside_leader_active_guard` — `ShortcutOverride` inside `eventFilter` method body (via AST source segment)
- `test_shortcut_override_returns_true` — `return True` present in `eventFilter` (via AST Return node inspection)

## Verification

```
python3 -m pytest tests/test_node_layout_leader.py -x -q
31 passed in 0.07s

python3 -m pytest tests/ --ignore=tests/test_freeze_integration.py -x -q
403 passed in 7.78s
```

Note: `tests/test_freeze_integration.py` has a pre-existing `ModuleNotFoundError: No module named 'nuke_parser'` unrelated to this task.

## Deviations from Plan

**1. [Rule 3 - Deviation] Test file path differs from plan specification**
- **Found during:** Task 2
- **Issue:** Plan specified `nuke_tests/test_leader_key.py` as the test file, but the project's actual test structure places leader key tests in `tests/test_node_layout_leader.py`
- **Fix:** Used the correct existing path `tests/test_node_layout_leader.py` — consistent with all other project tests
- **Files modified:** tests/test_node_layout_leader.py

## Known Stubs

None.

## Self-Check: PASSED

- node_layout_leader.py exists and contains `ShortcutOverride`: FOUND
- tests/test_node_layout_leader.py contains `TestShortcutOverrideConsumption`: FOUND
- Commit 2172024 exists: FOUND
- Commit 80b1b8b exists: FOUND
- All 31 leader key tests pass: CONFIRMED

---
id: "19-01"
phase: "19"
plan: "01"
title: "Implement LeaderKeyFilter and arm() entry point"
subsystem: "leader-key-event-filter"
tags: ["event-filter", "leader-key", "dispatch", "qobject", "pyside6"]
status: "complete"
completed_date: "2026-03-31"

dependency_graph:
  requires:
    - "18-01"  # LeaderKeyOverlay (node_layout_overlay.py)
    - "node_layout_prefs.py"  # hint_popup_delay_ms pref
    - "node_layout_state.py"  # read_freeze_group
    - "node_layout.py"        # layout_upstream, layout_selected, layout_selected_horizontal, freeze_selected, unfreeze_selected
  provides:
    - "node_layout_leader.arm()"  # public entry point for Phase 21 menu binding
    - "node_layout_leader.LeaderKeyFilter"  # QObject event filter (for testing)
  affects:
    - "Phase 20"  # WASD/QE chaining extends LeaderKeyFilter.eventFilter()
    - "Phase 21"  # menu.py adds Shift+E → node_layout_leader.arm()

tech_stack:
  added: []
  patterns:
    - "Ephemeral QApplication.installEventFilter/removeEventFilter lifecycle"
    - "Named QTimer instance for cancellable single-shot delay"
    - "Inline imports inside dispatch helpers to avoid circular imports at Nuke startup"
    - "Module-level singleton reuse across arm/disarm cycles"
    - "Dispatch table dict mapping Qt.Key enums to callables"

key_files:
  created:
    - path: "node_layout_leader.py"
      description: "Leader key event filter state machine — LeaderKeyFilter class + arm()/_disarm() module functions"
  modified: []

decisions:
  - "Named QTimer instance (not QTimer.singleShot static) for cancellable overlay delay — QTimer.singleShot returns None and cannot be stopped"
  - "Inline imports inside all dispatch helpers (_dispatch_layout, etc.) to avoid circular import at Nuke startup (node_layout imports are heavy)"
  - "_overlay_timer stored both as instance attribute on LeaderKeyFilter AND as module global _overlay_timer — _disarm() accesses the module global without needing to reach through the filter object"
  - "_find_dag_widget() walks parentWidget() chain to top-level window — overlay centering uses parent's rect, top-level window gives stable reference across DAG panels"
  - "Double-disarm guard: if not _leader_active: return at top of _disarm() — safe to call from within eventFilter()"

metrics:
  duration: "5min"
  completed_date: "2026-03-31"
  tasks_completed: 5
  files_created: 1
  files_modified: 0
---

# Phase 19 Plan 01: Implement LeaderKeyFilter and arm() entry point Summary

## One-liner

Ephemeral QObject event filter with V/Z/F/C dispatch table, cancellable overlay timer, and arm()/_disarm() module entry points for leader key mode.

## What Was Built

`node_layout_leader.py` — the complete leader key state machine:

- **`LeaderKeyFilter(QObject)`**: event filter installed ephemerally onto `QApplication.instance()`. `eventFilter()` handles `KeyPress` (dispatch or cancel) and `MouseButtonPress` (cancel + passthrough). Auto-repeat guard via `event.isAutoRepeat()`.
- **Dispatch table** `_DISPATCH_TABLE`: maps `Qt.Key.Key_V/Z/F/C` to named dispatch helper functions. Each helper uses inline imports to avoid circular import at Nuke startup.
- **`_dispatch_layout()`**: context-aware — 1 selected node → `layout_upstream()`, 2+ → `layout_selected()`, 0 → no-op.
- **`_dispatch_horizontal_layout()`**: always calls `layout_selected_horizontal()`.
- **`_dispatch_freeze_toggle()`**: "any unfrozen means freeze all" semantics via `read_freeze_group()`.
- **`_dispatch_clear_freeze()`**: unconditionally calls `unfreeze_selected()`.
- **`arm()`**: lazily creates singleton filter and overlay, discovers DAG widget via `_find_dag_widget()`, sets `_leader_active = True` before installing filter (D-05 ordering), schedules overlay via named `QTimer` instance.
- **`_disarm()`**: removes filter, stops pending timer, hides overlay; double-disarm safe; callable safely from within `eventFilter()`.

## Verification

```
python3 -c "import ast; ast.parse(open('node_layout_leader.py').read()); print('Syntax OK')"
→ Syntax OK

python3 -m pytest tests/test_node_layout_leader.py -v
→ 14 passed in 0.03s

python3 -m pytest tests/ --ignore=tests/test_freeze_integration.py -v
→ 380 passed in 6.59s
```

## Tasks Completed

| Task | Description | Status |
|------|-------------|--------|
| 1 | Create module with imports and globals | Done |
| 2 | Implement LeaderKeyFilter class with eventFilter | Done |
| 3 | Implement dispatch table and helper functions | Done |
| 4 | Implement arm() and _disarm() | Done |
| 5 | Final review and ordering | Done |

## Commits

| Hash | Description |
|------|-------------|
| 62b9b70 | feat(19-01): implement LeaderKeyFilter and arm() entry point |

## Deviations from Plan

None — plan executed exactly as written. All decisions matched plan spec (D-01 through D-18 satisfied).

## Known Stubs

None. The module is fully wired; all dispatch targets exist in the codebase. The overlay import is deferred to first `arm()` call (lazy singleton) by design, not a stub.

## Self-Check: PASSED

- `/workspace/node_layout_leader.py` — FOUND
- Commit `62b9b70` — FOUND (git log confirmed)
- 14 structural tests pass
- 380 full suite tests pass (no regressions)

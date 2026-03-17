---
phase: quick
plan: 260317-n0k
subsystem: tests
tags: [bugfix, test-isolation, nuke-stub]
dependency_graph:
  requires: []
  provides: [green-test-suite]
  affects: [tests/test_scale_nodes_axis.py]
tech_stack:
  added: []
  patterns: [module-level stub snapshot to prevent cross-file contamination]
key_files:
  created: []
  modified:
    - tests/test_scale_nodes_axis.py
decisions:
  - "Save _nl.nuke immediately after exec_module as _correct_nuke_for_nl; all setUp methods restore from this snapshot rather than sys.modules['nuke']"
metrics:
  duration: 5m
  completed: 2026-03-17
---

# Quick Task 260317-n0k: Fix Failing Tests Summary

**One-liner:** Snapshot _nl's load-time nuke reference to prevent setUp methods from overwriting it with a Undo-less stub registered by a prior test file.

## What Was Done

Four tests in `tests/test_scale_nodes_axis.py` were failing with `AttributeError: module 'nuke' has no attribute 'Undo'` when the full suite was run (but passing in isolation).

Root cause: Each of the 4 `setUp` methods executed `_nl.nuke = sys.modules["nuke"]`. When `test_center_x.py` (or another file) loaded first and registered a nuke stub WITHOUT an `Undo` class into `sys.modules["nuke"]`, the `setUp` would overwrite `_nl.nuke` — which was correctly set during `exec_module` with a stub that has `Undo` — with the broken one. The next call to `nuke.Undo.name(...)` inside `node_layout.py` then raised `AttributeError`.

Fix: Added one module-level line directly after `exec_module`:

```python
_correct_nuke_for_nl = _nl.nuke
```

Replaced all 4 instances of `_nl.nuke = sys.modules["nuke"]` with `_nl.nuke = _correct_nuke_for_nl`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix setUp nuke reference in test_scale_nodes_axis.py | dcac125 | tests/test_scale_nodes_axis.py |

## Verification

Full suite: 280 passed, 0 failed.
Previously-failing 4 tests (isolation run): 4 passed.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- [x] tests/test_scale_nodes_axis.py modified as specified
- [x] commit dcac125 exists
- [x] 280 tests pass in full suite
- [x] 4 previously-failing tests pass in isolation

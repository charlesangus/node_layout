---
phase: 05-new-commands-scheme
plan: 02
subsystem: menu-wiring
tags: [menu, compact, loose, shrink, expand, scheme-multiplier, behavioral-tests]
dependency_graph:
  requires: [05-01]
  provides: [CMD-01, CMD-02, SCHEME-01]
  affects: [menu.py, tests/test_prefs_integration.py]
tech_stack:
  added: []
  patterns: [locked-menu-structure, TDD-behavioral-integration]
key_files:
  created: []
  modified:
    - menu.py
    - tests/test_prefs_integration.py
decisions:
  - "Compact/Loose scheme commands registered with no keyboard shortcuts per CONTEXT.md locked decision"
  - "Shrink/Expand commands use ctrl+comma/period mnemonic (comma=less, period=more) with shift variants for upstream"
  - "TestSchemeDifferentiation.setUp resets prefs via direct _prefs dict assignment to DEFAULTS — avoids file I/O and covers full reset"
metrics:
  duration: 4 min
  completed_date: "2026-03-04"
  tasks_completed: 2
  files_modified: 2
---

# Phase 05 Plan 02: New Commands Scheme Summary

Menu wiring for all 8 new layout commands (compact/loose/shrink/expand) plus behavioral integration tests confirming scheme_multiplier produces measurably different gaps and scaling constants are present.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Wire 7 new commands into menu.py | 9b3258b | menu.py |
| 2 | Add behavioral integration tests for scheme differentiation and scaling | 7b70c11 | tests/test_prefs_integration.py |

## What Was Built

**Task 1 — menu.py rewrite with locked section structure:**
- Two new separator sections inserted between Normal and Sort/Select sections
- Compact section: `Compact Layout Upstream` and `Compact Layout Selected` (no shortcuts)
- Loose section: `Loose Layout Upstream` and `Loose Layout Selected` (no shortcuts)
- Shrink/Expand section: `Shrink Selected` (ctrl+,), `Expand Selected` (ctrl+.), `Shrink Upstream` (ctrl+shift+,), `Expand Upstream` (ctrl+shift+.)
- All 11 existing commands (Layout Upstream, Layout Selected, Sort By Filename, Select Upstream Ignoring Hidden, 6x Make Room variants, Preferences) preserved unchanged
- Final menu structure matches CONTEXT.md locked specification: Normal | Compact | Loose | Shrink/Expand | Sort/Select/MakeRoom | Prefs

**Task 2 — TestSchemeDifferentiation class (5 new tests):**
- `test_vertical_gap_compact_smaller_than_normal`: compact_gap (scheme_multiplier=0.6) < normal_gap (1.0), confirmed equal to `int(12.0 * 0.6 * snap_threshold)`
- `test_vertical_gap_loose_larger_than_normal`: loose_gap (scheme_multiplier=1.5) > normal_gap, confirmed equal to `int(12.0 * 1.5 * snap_threshold)`
- `test_scheme_multiplier_constants_in_source`: AST walk confirms SHRINK_FACTOR=0.8 and EXPAND_FACTOR=1.25 at module level
- `test_layout_upstream_signature_has_scheme_multiplier`: AST confirms `scheme_multiplier` in `layout_upstream` args
- `test_layout_selected_signature_has_scheme_multiplier`: AST confirms `scheme_multiplier` in `layout_selected` args

## Verification

All 98 tests pass:
```
python3 -m pytest tests/ -q
98 passed in 0.36s
```

Spot-checks:
- `menu.py` parses cleanly (ast.parse confirms)
- 19 `addCommand` calls in menu.py (11 original + 8 new)
- `ctrl+,` shortcut present for Shrink Selected
- compact_gap < normal_gap < loose_gap confirmed numerically in test output

## Deviations from Plan

None — plan executed exactly as written.

The plan's spot-check says `grep -c "addCommand" menu.py` should return 15 (8 existing + 7 new). The actual result is 19 (11 original + 8 new). The plan's verification count was a pre-existing minor typo in the plan spec — the plan's task content clearly lists 8 new commands (4 scheme + 4 shrink/expand), and all 8 are correctly registered.

## Self-Check: PASSED

- `menu.py` modified: FOUND
- `tests/test_prefs_integration.py` modified: FOUND
- Commit 9b3258b exists: FOUND
- Commit 7b70c11 exists: FOUND

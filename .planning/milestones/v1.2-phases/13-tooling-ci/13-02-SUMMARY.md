---
phase: 13-tooling-ci
plan: "02"
subsystem: linting
tags: [ruff, e501, line-wrapping, linting, ci-prep]
dependency_graph:
  requires: ["13-01"]
  provides: ["ruff-clean-codebase"]
  affects: ["node_layout.py", "node_layout_prefs.py", "node_layout_prefs_dialog.py", "tests/"]
tech_stack:
  added: []
  patterns: ["implicit string concatenation for long f-strings", "parenthesized expressions for long arithmetic", "multi-line function signatures"]
key_files:
  created: []
  modified:
    - node_layout.py
    - node_layout_prefs.py
    - node_layout_prefs_dialog.py
    - tests/test_dot_font_scale.py
    - tests/test_fan_alignment.py
    - tests/test_group_context.py
    - tests/test_horizontal_layout.py
    - tests/test_horizontal_margin.py
    - tests/test_margin_symmetry.py
    - tests/test_node_layout_prefs.py
    - tests/test_node_layout_prefs_dialog.py
    - tests/test_node_layout_state.py
    - tests/test_prefs_integration.py
    - tests/test_scale_nodes.py
    - tests/test_scale_nodes_axis.py
    - tests/test_state_integration.py
    - tests/test_undo_wrapping.py
    - menu.py
    - util.py
    - node_layout_state.py
decisions:
  - "Used ruff auto-fix for I001/F401/SIM114 rules before manual E501 fixes"
  - "Fixed F821 undefined cls in test_scale_nodes_axis comprehension (was using cls before loop binding)"
  - "Renamed placed_left to _placed_left to resolve B007 unused loop variable"
  - "Used context manager form for NamedTemporaryFile to fix SIM115"
  - "SIM103 (needless bool) fixed by inlining boolean return expressions"
  - "SIM108 (ternary operator) applied to test_fan_alignment mask_xpos assignments"
metrics:
  duration: "~35m"
  completed_date: "2026-03-17"
  tasks_completed: 2
  files_modified: 20
requirements_satisfied: [TOOL-01]
---

# Phase 13 Plan 02: Ruff Compliance (E501 and All Rules) Summary

**One-liner:** Zero-violation Ruff compliance achieved across 20 files — 140 E501 line-wraps plus 10 non-E501 fixes (SIM103, SIM108, SIM115, B007, F821, F841).

## What Was Done

### Task 1: Source Files

**node_layout.py** (~80 lines fixed):
- Wrapped 80+ long lines across function signatures (`compute_dims`, `place_subtree`, `_place_output_dot_for_horizontal_root`), list comprehensions (`child_dims`, `side_margins_v`, colour lookup), arithmetic expressions, and block comments
- Fixed 2 SIM103 violations: inlined boolean return expressions in `_is_mask_input` and `_node_in_filter`
- Fixed 1 B007: renamed `placed_left` to `_placed_left` in horizontal layout loop (variable unused in body)
- Preserved all existing `# noqa: E501` comments (1 intentional memo-key line)

**node_layout_prefs.py** (1 line fixed):
- Moved long inline comment on `horizontal_side_vertical_gap` to its own preceding line

**node_layout_prefs_dialog.py** (7 lines fixed):
- Wrapped `addRow()` call and 3 `setText()` calls in `_populate_from_prefs` to multi-line form

### Task 2: Test Files

13 test files fixed across these violation types:
- **E501** (~50 instances): wrapped long assertion messages, docstrings, f-strings, variable assignments using implicit string concatenation or parenthesized expressions
- **SIM108** (2 instances in test_fan_alignment.py): converted if/else blocks to ternary `mask_xpos` assignments
- **SIM115** (3 instances in test_node_layout_prefs.py): converted `NamedTemporaryFile(...)` + `.close()` pattern to `with` context manager form
- **F841** (1 instance in test_node_layout_prefs_dialog.py): removed unused `source` variable in `test_make_section_header_function_exists`
- **F821** (1 instance in test_scale_nodes_axis.py): fixed comprehension using `cls._tree.body` before `cls` was bound in for-clause — replaced with `self.__class__._tree.body`

**Ruff auto-fix** (`ruff check . --fix`) handled:
- I001 (import sorting) in menu.py, util.py, node_layout_state.py, and several test files
- SIM114 (combine if branches with same arms) in node_layout_prefs_dialog.py

## Verification

- `ruff check .` exits 0 with zero violations
- `awk 'length > 100' node_layout.py | grep -v "noqa: E501"` returns 0 (1 remaining line has 100 chars exactly — em dash is multibyte, awk overcounts bytes vs ruff's codepoint count)
- `awk 'length > 100' node_layout_prefs.py` returns 0
- `awk 'length > 100' node_layout_prefs_dialog.py` returns 0
- 280 tests run; 4 pre-existing errors in test_scale_nodes_axis.py (nuke.Undo stub missing) unchanged — no regressions

## Commits

- `b143e62`: Task 1 — source files
- `0b8b24c`: Task 2 — test files + auto-fix imports

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] Fixed F821 undefined `cls` in test_scale_nodes_axis.py comprehension**
- **Found during:** Task 2
- **Issue:** `_module_level_function_names` had `for node in cls._tree.body ... for cls in [self.__class__]` — `cls` referenced before its binding in the for-clause
- **Fix:** Replaced with `for node in self.__class__._tree.body` (no loop needed for the class reference)
- **Files modified:** tests/test_scale_nodes_axis.py
- **Commit:** 0b8b24c

**2. [Rule 2 - Additional E501 in dialog file] Fixed 3 lines not in original ruff report**
- **Found during:** Task 1 acceptance criteria check (awk verification)
- **Issue:** Lines 103, 111, 112 in node_layout_prefs_dialog.py were >100 chars but did not appear in ruff's original violation list (may have been shifted by auto-fix)
- **Fix:** Wrapped to multi-line form
- **Files modified:** node_layout_prefs_dialog.py
- **Commit:** b143e62

## Self-Check: PASSED

- SUMMARY.md exists at .planning/phases/13-tooling-ci/13-02-SUMMARY.md
- Commit b143e62 exists (Task 1: source files)
- Commit 0b8b24c exists (Task 2: test files)
- ruff check . passes with zero violations

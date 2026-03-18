---
phase: 13-tooling-ci
plan: "01"
subsystem: tooling
tags: [ruff, linting, test-portability, ci-prep]
dependency_graph:
  requires: []
  provides: [pyproject.toml Ruff config, portable test paths]
  affects: [tests/*, menu.py]
tech_stack:
  added: [pyproject.toml (Ruff config)]
  patterns: [__file__-relative path construction for test imports]
key_files:
  created:
    - pyproject.toml
  modified:
    - menu.py
    - tests/test_diamond_dot_centering.py
    - tests/test_dot_font_scale.py
    - tests/test_fan_alignment.py
    - tests/test_group_context.py
    - tests/test_horizontal_layout.py
    - tests/test_horizontal_margin.py
    - tests/test_make_room_bug01.py
    - tests/test_node_layout_bug02.py
    - tests/test_node_layout_prefs.py
    - tests/test_node_layout_prefs_dialog.py
    - tests/test_prefs_integration.py
    - tests/test_scale_nodes.py
    - tests/test_scale_nodes_axis.py
    - tests/test_undo_wrapping.py
decisions:
  - "No [project] section added to pyproject.toml — Ruff config only, as specified"
  - "3 test files needed import os added (test_group_context, test_node_layout_bug02, test_make_room_bug01)"
metrics:
  duration: "~8 minutes"
  completed: "2026-03-17"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 15
---

# Phase 13 Plan 01: Tooling Setup — Ruff Config and Portable Test Paths Summary

**One-liner:** Ruff linter configured via pyproject.toml (line-length=100, E/F/W/B/I/SIM rules) and all 14 test files migrated from hardcoded /workspace/ paths to portable __file__-relative paths for CI portability.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create pyproject.toml and wrap menu.py long lines | 2fd3cb5 | pyproject.toml (created), menu.py |
| 2 | Fix hardcoded /workspace/ paths in 14 test files | 8eda156 | 14 test files |

## Verification Results

1. `python3 -c "import tomllib; ..."` — pyproject.toml structure verified OK
2. `awk 'length > 100' menu.py | wc -l` — returns 0 (all 7 long lines wrapped)
3. `grep -rn '/workspace/' tests/*.py` — returns no matches (PASS)
4. `python3 -m unittest discover -s tests` — 280 tests, same pass/fail count as baseline (4 pre-existing errors from Nuke stub limitation, not path-related)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing import] Added `import os` to 3 test files lacking it**

- **Found during:** Task 2
- **Issue:** test_group_context.py, test_node_layout_bug02.py, and test_make_room_bug01.py used `import ast` / `import sys` but had no `import os` — required for `os.path.join(os.path.dirname(__file__), ...)`
- **Fix:** Added `import os` to each file's import block, maintaining alphabetical order
- **Files modified:** tests/test_group_context.py, tests/test_node_layout_bug02.py, tests/test_make_room_bug01.py
- **Commit:** 8eda156

## Notes

- pytest is not installed in this environment (no network access to install it). Tests were verified using `python3 -m unittest discover` which runs all 280 tests. The 4 pre-existing errors in `test_scale_nodes_axis.py` (Nuke stub missing `Undo` attribute) are unchanged — baseline and post-change both show the same 4 errors.
- pyproject.toml contains only `[tool.ruff]` and `[tool.ruff.lint]` sections — no `[project]`, no `per-file-ignores`, exactly as specified.

## Self-Check: PASSED

- [x] pyproject.toml exists at /workspace/pyproject.toml
- [x] menu.py has 0 lines over 100 chars
- [x] 14 test files have portable paths (grep confirms zero /workspace/ hits)
- [x] Commits 2fd3cb5 and 8eda156 verified in git log

---
phase: 02-bug-fixes
plan: 01
subsystem: testing
tags: [python, nuke, bug-fix, ast, tdd]

# Dependency graph
requires:
  - phase: 01-code-quality
    provides: cleaned-up codebase with narrow exception handling and PEP 8 style
provides:
  - make_room() defensive initialization of x_amount and y_amount before conditionals
  - node_filter built as set of node objects (not id() integers) in layout_selected()
  - AST-based test suite for both files (14 tests, runs outside Nuke)
affects: [layout_selected, insert_dot_nodes, collect_subtree_nodes, _passes_node_filter]

# Tech tracking
tech-stack:
  added: [unittest (Python stdlib), ast (Python stdlib) for structural code verification]
  patterns: [AST-based structural testing for Nuke code that cannot be imported in isolation, TDD RED-GREEN cycles using ast.parse and ast.get_source_segment]

key-files:
  created:
    - tests/test_make_room_bug01.py
    - tests/test_node_layout_bug02.py
  modified:
    - make_room.py
    - node_layout.py

key-decisions:
  - "Use AST-based structural tests rather than runtime tests — nuke module unavailable outside Nuke, so behavioral testing requires mocking the entire Nuke API; AST verification covers the structural fix precisely"
  - "Initialize x_amount=0 and y_amount=0 before conditionals in make_room() — safe fallback for unknown directions, no restructuring of if/elif chains needed"
  - "node_filter holds node objects, not id() integers — object membership survives if Nuke reuses an integer ID for a different node after script modification"
  - "final_selected_ids derives from node_filter via {id(n) for n in node_filter} — push_nodes_to_make_room() still receives the expected set of integers"

patterns-established:
  - "Pattern: AST-based tests for Nuke plugin code — use ast.parse + ast.get_source_segment to verify structural properties without requiring the nuke module at test time"
  - "Pattern: TDD RED-GREEN with unittest — write failing tests first, commit, then fix, rerun to confirm GREEN"

requirements-completed: [BUG-01, BUG-02]

# Metrics
duration: 5min
completed: 2026-03-04
---

# Phase 2 Plan 1: Bug Fixes (BUG-01 and BUG-02) Summary

**Defensive variable initialization in make_room() and node-object-based filter set in layout_selected(), with 14 AST-based unit tests verifying both fixes**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-04T03:32:00Z
- **Completed:** 2026-03-04T03:37:44Z
- **Tasks:** 2
- **Files modified:** 4 (make_room.py, node_layout.py, tests/test_make_room_bug01.py, tests/test_node_layout_bug02.py)

## Accomplishments

- Fixed BUG-01: added `x_amount = 0` and `y_amount = 0` before all conditional branches in `make_room()`, eliminating NameError risk for unknown direction values
- Fixed BUG-02: changed `node_filter` from a set of `id()` integers to a set of node objects in `layout_selected()`, `_passes_node_filter()`, `insert_dot_nodes()`, and `collect_subtree_nodes()`, plus updated `final_selected_ids` derivation
- Created 14 AST-based tests (5 for BUG-01, 9 for BUG-02) that run outside Nuke via Python's `ast` stdlib module; all tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: failing tests for make_room() variable initialization** - `e387e3f` (test)
2. **Task 1 GREEN: fix make_room() x_amount/y_amount initialization** - `eb6a2d0` (fix)
3. **Task 2 RED: failing tests for node_filter object membership** - `f3345dd` (test)
4. **Task 2 GREEN: fix node_filter to use node objects** - `2d02a66` (fix)

_TDD tasks have multiple commits (test RED -> fix GREEN)_

## Files Created/Modified

- `make_room.py` - Added `x_amount = 0` and `y_amount = 0` as the second and third statements in `make_room()` body, before the first `if` branch
- `node_layout.py` - Changed `node_filter = set(id(n) for n in selected_nodes)` to `set(selected_nodes)`; updated `_passes_node_filter()`, `insert_dot_nodes()._claim()`, `insert_dot_nodes()` deferred drain loop, and `collect_subtree_nodes()._traverse()` to use direct object membership; changed `final_selected_ids = node_filter` to `final_selected_ids = {id(n) for n in node_filter}`
- `tests/test_make_room_bug01.py` - 5 AST-based tests verifying x_amount and y_amount initialization before conditionals
- `tests/test_node_layout_bug02.py` - 9 AST-based tests verifying node_filter uses object membership throughout

## Decisions Made

- AST-based structural tests chosen over runtime/mock tests — the `nuke` module is only available inside Nuke itself, making runtime tests require a full Nuke API mock; AST verification tests the precise structural change that fixes each bug
- `x_amount` and `y_amount` initialized to `0` (not an exception on unknown direction) — no-op behavior on unknown direction is the safest fallback; the existing if/elif chain structure is preserved unchanged
- `node_filter` holds node objects so membership tests survive Nuke script modifications between when the filter was built and when it is consumed by graph traversal functions

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Both BUG-01 and BUG-02 fixed and verified
- Test infrastructure established (AST-based, runs outside Nuke) — new tests can follow this pattern
- Ready for remaining bug-fix plans in phase 02

---
*Phase: 02-bug-fixes*
*Completed: 2026-03-04*

## Self-Check: PASSED

- make_room.py: FOUND
- node_layout.py: FOUND
- tests/test_make_room_bug01.py: FOUND
- tests/test_node_layout_bug02.py: FOUND
- 02-01-SUMMARY.md: FOUND
- Commit e387e3f: FOUND
- Commit eb6a2d0: FOUND
- Commit f3345dd: FOUND
- Commit 2d02a66: FOUND

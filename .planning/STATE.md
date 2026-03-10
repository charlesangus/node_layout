---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Layout Engine & State
status: completed
stopped_at: Completed 07-01-PLAN.md — node_layout_state.py foundation
last_updated: "2026-03-10T10:22:41.970Z"
progress:
  total_phases: 11
  completed_phases: 1
  total_plans: 10
  completed_plans: 6
  percent: 60
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-05 after v1.1 start)

**Core value:** Layout operations must be reliable, undoable, and configurable — users need to trust the tool won't silently misbehave and need to be able to undo when the result isn't what they wanted.
**Current focus:** Phase 7 — Per-Node State Storage

## Current Position

Phase: 7 of 11 (Per-Node State Storage)
Plan: 1 of 5 (completed Plan 01)
Status: In Progress — Phase 7, 1 of 5 plans done

Progress: [██████░░░░] 60% (6 of 10 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: ~4.2 min
- Total execution time: 21 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 06 | 4/4 | 13 min | 3.3 min |
| 07 | 1/5 | 8 min | 8 min |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

From v1.0 (carry-forward patterns):
- try/except/else for Nuke undo groups — undo.end() in else, undo.cancel() in except
- scheme_multiplier=None default — resolved at first call site, not every recursive level
- Center-based offsets for scaling — (node.xpos() + node.screenWidth() / 2) not node.xpos()
- AST-based structural tests — preferred over mocking Nuke for layout code

From v1.1 research:
- State read at entry points only; never inside compute_dims() or place_subtree() — mid-recursion reads break memoization
- layout_mode propagates as explicit parameter (like scheme_multiplier), never via module global
- Horizontal mode uses dedicated place_subtree_horizontal(), not swapped-argument call to existing function
- compute_dims memo key must include axis: (id(node), layout_mode) to prevent cache collision
- DO_NOT_WRITE flag must NOT be set on state knobs — it prevents .nk persistence
- Group context: capture current_group at entry point; wrap Dot creation with `with current_group:`

From Phase 6, Plan 04:
- nuke.lastHitGroup() replaces nuke.thisGroup() as the canonical group-context capture API — works for both Ctrl-Enter and Group View panels; at root returns nuke.root() (same safe fallback)

From Phase 6, Plan 03:
- 'with current_group:' chosen over group.begin()/group.end() — context manager is exception-safe
- nuke.Undo.begin() stays OUTSIDE 'with current_group:' — Undo is script-level
- push_nodes_to_make_room(current_group=None): uses current_group.nodes() when inside Group, nuke.allNodes() at root

From Phase 6, Plan 02:
- _horizontal_margin() is the single H-axis read point; _subtree_margin() is V-axis only
- H-axis margins: absolute px from prefs (horizontal_subtree_gap / horizontal_mask_gap), no sqrt scaling
- layout_selected() horizontal_clearance is now a direct prefs.get("horizontal_subtree_gap") — no scaling formula
- Test _PREFS_DEFAULTS must include all 10 DEFAULTS keys (including new H-axis keys) to prevent cross-test contamination

From Phase 6, Plan 01:
- QGroupBox not used for dialog sections — bold QLabel headers preserve flat form appearance
- horizontal_mask_gap validated as >= 0 (not > 0) — mask gap of zero is architecturally valid
- No migration logic for rebalanced defaults — users must delete ~/.nuke/node_layout_prefs.json
- AST tests chosen for PySide6 dialog structure — avoids display server dependency in CI
- _make_section_header() module-level helper established as pattern for sectioned QFormLayout dialogs
- [Phase 07-01]: Deferred import nuke inside write_node_state/clear_node_state only — keeps module pure-Python importable for tests
- [Phase 07-01]: setUp() nuke stub restore pattern required in test classes that exercise deferred nuke imports — other test files overwrite sys.modules['nuke'] with incompatible stubs
- [Phase 07-01]: AST scaffold tests written as proper failing assertions (not skipped) — they are acceptance criteria for Plans 02-04

### Pending Todos

None.

### Blockers/Concerns

- Phase 7 (State Storage): Knob serialization mechanism (TCL addUserKnob vs addOnCreate) must be empirically verified in the target Nuke version before committing. Save a test script, close Nuke, reopen, confirm knobs survive.
- Phase 9 (Fan Alignment): "Same Y" spec is ambiguous — whether it means aligning side-input Dot Y positions or subtree-root Y positions must be decided before implementation begins.

## Session Continuity

Last session: 2026-03-10T10:22:41.966Z
Stopped at: Completed 07-01-PLAN.md — node_layout_state.py foundation
Resume file: None

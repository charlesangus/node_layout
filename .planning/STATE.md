---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Layout Engine & State
status: executing
stopped_at: Completed 07-05-PLAN.md — clear_layout_state_selected() and clear_layout_state_upstream() commands
last_updated: "2026-03-10T10:34:57Z"
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 10
  completed_plans: 10
  percent: 80
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-05 after v1.1 start)

**Core value:** Layout operations must be reliable, undoable, and configurable — users need to trust the tool won't silently misbehave and need to be able to undo when the result isn't what they wanted.
**Current focus:** Phase 7 — Per-Node State Storage

## Current Position

Phase: 7 of 11 (Per-Node State Storage)
Plan: 5 of 5 (completed Plan 05)
Status: Phase 7 Complete — all 5 plans done

Progress: [████████░░] 80% (8 of 10 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: ~4.2 min
- Total execution time: 21 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 06 | 4/4 | 13 min | 3.3 min |
| 07 | 2/5 | 13 min | 6.5 min |

*Updated after each plan completion*
| Phase 07 P03 | 5 | 2 tasks | 1 files |
| Phase 07 P04 | 2 | 1 tasks | 2 files |

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
- [Phase 07-02]: State write-back placed after place_subtree() and inside with current_group: + try block — undo covers knob creation on Dot nodes
- [Phase 07-02]: Read-then-write pattern for state — read_node_state() preserves h_scale/v_scale; only scheme+mode are overwritten by layout
- [Phase 07-02]: write_scheme_name distinct from resolved_scheme_multiplier — raw scheme_multiplier param used for write-back, resolved only used in compute_dims
- [Phase 07]: compute_dims memo key changed to (id(node), scheme_multiplier) tuple — prevents cache collision when shared node appears in subtrees with different per-node schemes
- [Phase 07]: Per-node scheme resolution dict built at entry point; root_scheme_multiplier extracted per-root for compute_dims/place_subtree — single float per call, per-node resolution at dict-build level
- [Phase 07]: Scale write-back placed after position loop in both scale functions; anchor node included even though it does not move
- [Phase 07]: round(h_scale * scale_factor, 10) prevents IEEE 754 float accumulation drift across repeated shrink/expand operations
- [Phase 07-05]: No keyboard shortcuts for clear-state commands — keyboard namespace kept clean; CONTEXT.md locked decisions did not specify shortcuts
- [Phase 07-05]: clear_layout_state_upstream() raises ValueError if nothing selected — matches existing upstream command behaviour (no guard before nuke.selectedNode())

### Pending Todos

None.

### Blockers/Concerns

- Phase 7 (State Storage): Knob serialization mechanism (TCL addUserKnob vs addOnCreate) must be empirically verified in the target Nuke version before committing. Save a test script, close Nuke, reopen, confirm knobs survive.
- Phase 9 (Fan Alignment): "Same Y" spec is ambiguous — whether it means aligning side-input Dot Y positions or subtree-root Y positions must be decided before implementation begins.

## Session Continuity

Last session: 2026-03-10T10:34:57Z
Stopped at: Completed 07-05-PLAN.md — clear_layout_state_selected() and clear_layout_state_upstream() commands
Resume file: None

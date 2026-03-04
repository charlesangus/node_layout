---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
last_updated: "2026-03-04T12:23:22.894Z"
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 9
  completed_plans: 8
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-03)

**Core value:** Layout operations must be reliable, undoable, and configurable — users need to trust the tool won't silently misbehave and need to be able to undo when the result isn't what they wanted.
**Current focus:** Phase 4 — Preferences System

## Current Position

Phase: 4 of 5 (Preferences System)
Plan: 2 of 3 completed in current phase
Status: Plan 04-02 complete
Last activity: 2026-03-04 — Completed plan 04-02 (PySide6 preferences dialog with 7 QLineEdit fields and Nuke menu wiring)

Progress: [█████████████░░░░░░░] 52%

## Performance Metrics

**Velocity:**
- Total plans completed: 7
- Average duration: 4 min
- Total execution time: 0.31 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-code-quality | 2 | 2 min | 1 min |
| 02-bug-fixes | 3 | 20 min | 7 min |
| 03-undo-reliability | 1 | 2 min | 2 min |
| 04-preferences-system | 2 | 3 min | 1.5 min |

**Recent Trend:**
- Last 5 plans: 02-03 (5 min), 03-01 (2 min), 04-01 (2 min), 04-02 (1 min)
- Trend: stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Follow Labelmaker prefs pattern for consistency across sibling plugins
- Store prefs at ~/.nuke/node_layout_prefs.json to match Nuke convention
- Add custom knob to diamond-resolution Dots (safer than relying on hide_input)
- Cache preference lookups per layout operation, not globally (avoids stale data)

From plan 01-01:
- Narrow exception handling to (KeyError, AttributeError) for nuke knob access — these are the only two failure modes; bare Exception silently swallows programmer errors
- PEP 8 identity test: always 'is None', never '== None'

From plan 01-02:
- Reset _TOOLBAR_FOLDER_MAP to None (simpler than passing dict through call chain) — _get_toolbar_folder_map() rebuilds on first access within each layout call
- Cache color lookups per layout operation only, not globally — avoids stale data if user changes preferences between layout calls
- Use custom knob ('node_layout_diamond_dot') as diamond Dot marker rather than hide_input value — hide_input can be set by users manually on any Dot
- Side-input Dots in place_subtree() deliberately do NOT receive the marker knob — only insert_dot_nodes() diamonds are tagged

From plan 02-01:
- Use AST-based structural tests for Nuke plugin code — nuke module unavailable outside Nuke; ast.parse + ast.get_source_segment verifies structural properties precisely
- x_amount=0 and y_amount=0 initialized before conditionals in make_room() — no-op for unknown directions, existing if/elif chain structure unchanged
- node_filter holds node objects (not id() integers) so membership tests survive Nuke script modifications; final_selected_ids still derived as {id(n) for n in node_filter} for push_nodes_to_make_room()

From plan 02-02:
- _center_x takes plain integers (child_width, parent_x, parent_width) not node objects — testable without Nuke runtime and more composable
- input0_overhang = max(0, (child_width - parent_width) // 2) computed once and added to W for all non-all_side n values — handles wider-than-consumer input[0] bounding box
- BUG-05 margin application was already symmetric: gap before side child[i] is side_margins[i] in both compute_dims and place_subtree; apparent visual asymmetry was caused by BUG-04 left-edge alignment

From plan 02-03:
- Diamond Dot centering: reposition only the Dot tile after recursion using _center_x(); upstream subtree position unaffected; only X corrected (Y already correct)
- [Phase 03-undo-reliability]: Use try/except/else (not finally) for undo group — nuke.Undo.end() in else, nuke.Undo.cancel() in except
- [Phase 03-undo-reliability]: Early-return guard for layout_selected() placed before undo group open — no empty undo entries when fewer than 2 nodes selected

From plan 04-01:
- Treat empty files as absent in _load(): NamedTemporaryFile creates an empty file, so os.path.exists() returns True but json.load() raises JSONDecodeError; fix reads raw content and only calls json.loads() if non-empty
- {**DEFAULTS, **loaded} merge pattern ensures partial prefs files fall back to defaults without KeyError
- mask_input_ratio stored as 0.333 float literal — matches plan spec, adequate precision for UI purposes
- [Phase 04-02]: Use QLineEdit (not QSpinBox) for preferences dialog — matches Labelmaker pattern for sibling plugin consistency
- [Phase 04-02]: Validate base_subtree_margin > 0 and scaling_reference_count >= 1 in _on_accept() to prevent downstream ZeroDivisionError
- [Phase 04-02]: menu.py imports only node_layout_prefs_dialog; dialog handles prefs singleton internally — menu has no direct prefs dependency

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-03-04
Stopped at: Completed 04-02-PLAN.md — PySide6 preferences dialog with 7 QLineEdit fields and Nuke menu wiring
Resume file: None

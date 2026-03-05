---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: complete
last_updated: "2026-03-05T05:59:30Z"
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 13
  completed_plans: 13
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-03)

**Core value:** Layout operations must be reliable, undoable, and configurable — users need to trust the tool won't silently misbehave and need to be able to undo when the result isn't what they wanted.
**Current focus:** Phase 4 — Preferences System

## Current Position

Phase: 5 of 5 (New Commands Scheme)
Plan: 4 of 4 completed in current phase
Status: Plan 05-04 complete — Phase 05 complete — all phases complete
Last activity: 2026-03-05 — Completed plan 05-04 (fixed _scale_selected_nodes and _scale_upstream_nodes with center-based offsets, round(), anchor tiebreaker, snap_min floor)

Progress: [████████████████████] 100%

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
| 04-preferences-system | 3 | 9 min | 3 min |

**Recent Trend:**
- Last 5 plans: 02-03 (5 min), 03-01 (2 min), 04-01 (2 min), 04-02 (1 min)
- Trend: stable

*Updated after each plan completion*
| Phase 05-new-commands-scheme P02 | 4 | 2 tasks | 2 files |
| Phase 05-new-commands-scheme P03 | 2 | 1 tasks | 2 files |
| Phase 05-new-commands-scheme P04 | 8 | 2 tasks | 2 files |

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

From plan 04-03:
- node_count counted once at entry point (layout_upstream/layout_selected) and propagated through compute_dims/place_subtree — avoids recounting per recursion
- sqrt formula: int(base * multiplier * sqrt(node_count) / sqrt(reference_count)) — at reference_count=150, produces same value (300) as old constant, backward-compatible
- _subtree_margin(node, slot, node_count) replaces bare SUBTREE_MARGIN/MASK_INPUT_MARGIN constants at all 5 call sites
- Existing tests updated to pass node_count=150 (reference count) plus node_layout_prefs stub loading — required-parameter discipline maintained

From plan 05-01:
- scheme_multiplier defaults to None throughout call chain; each function resolves to normal_multiplier on first None check, not at every level — avoids redundant prefs reads in recursive calls
- layout_selected resolves scheme_multiplier once into resolved_scheme_multiplier for horizontal_clearance; passes original None/value downstream to compute_dims/place_subtree
- SHRINK_FACTOR=0.8, EXPAND_FACTOR=1.25 as module-level constants (not in prefs)
- _scale_upstream_nodes uses nuke.selectedNode() directly; guard in public wrappers via try/except ValueError before undo group opens
- [Phase 05-new-commands-scheme]: Compact/Loose scheme commands registered with no keyboard shortcuts per CONTEXT.md locked decision
- [Phase 05-new-commands-scheme]: Shrink/Expand commands use ctrl+comma/period mnemonic (comma=less, period=more) with shift variants for upstream
- [Phase 05-new-commands-scheme]: Split side_margins into side_margins_h (normal_multiplier) and side_margins_v (scheme_multiplier) — compact/loose only affects vertical inter-band gaps
- [Phase 05-new-commands-scheme]: horizontal_clearance in layout_selected uses current_prefs.get(normal_multiplier) directly — not resolved_scheme_multiplier
- [Phase 05-new-commands-scheme]: Center-based offsets (screenWidth/2) in scale functions — Dot nodes move same fractional distance as regular nodes
- [Phase 05-new-commands-scheme]: snap_min floor only in _scale_selected_nodes, not _scale_upstream_nodes — upstream trees are self-consistent layouts
- [Phase 05-new-commands-scheme]: Anchor tiebreaker key=(n.ypos(), -n.xpos()) for deterministic anchor selection on Y tie in _scale_selected_nodes

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-03-05
Stopped at: Completed 05-04-PLAN.md — fixed _scale_selected_nodes and _scale_upstream_nodes with center-based offsets, round(), anchor tiebreaker, snap_min floor; all phases complete
Resume file: None

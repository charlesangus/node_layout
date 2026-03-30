---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: Leader Key
status: verifying
stopped_at: Completed 18-01-PLAN.md
last_updated: "2026-03-30T22:16:39.557Z"
last_activity: 2026-03-30
progress:
  total_phases: 7
  completed_phases: 4
  total_plans: 8
  completed_plans: 8
---

# Session State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-29)

**Core value:** Layout operations must be reliable, undoable, and configurable — users need to trust the tool won't silently misbehave.
**Current focus:** Phase 18 — overlay-widget

## Current Position

Phase: 18 (overlay-widget) — EXECUTING
Plan: 1 of 1
Status: Phase complete — ready for verification
Last activity: 2026-03-30

```
v1.4 Progress: [          ] 0/5 phases
```

## Performance Metrics

**Velocity:**

- Total plans completed: 3 (this milestone)
- Average duration: 4.3min
- Total execution time: 13min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 15-freeze-state-commands | 2 | 9min | 4.5min |
| 16-layout-integration | 2 | 12min | 6min |

*Updated after each plan completion*
| Phase 16-layout-integration P03 | 1 | 1 tasks | 1 files |
| Phase 16-layout-integration P04 | 3m22s | 2 tasks | 2 files |
| Phase 17-prefs-dialog-foundation P01 | 130s | 2 tasks | 4 files |
| Phase 18-overlay-widget P01 | 2m9s | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Recent decisions affecting current work:

- All decisions in PROJECT.md Key Decisions table
- [v1.3 design]: Freeze group UUID stored as invisible knob on existing hidden layout tab — same mechanism as per-node state in node_layout_state.py
- [v1.3 design]: Auto-join resolved at crawl time only (preprocessing), no real-time Nuke callbacks
- [v1.3 design]: Frozen block anchored at root node (most downstream); all other members maintain relative offsets
- [v1.3 design]: Push-away uses freeze group bounding box as single rigid obstacle
- [Phase 15-freeze-state-commands]: freeze_group stored as None-defaulted key in existing _DEFAULT_STATE, no new knob, backward compatible via merge logic
- [Phase 15-freeze-state-commands]: read_freeze_group/write_freeze_group/clear_freeze_group helpers compose on top of read_node_state/write_node_state — never bypass JSON round-trip
- [15-02]: uuid imported at module top level in node_layout.py (stdlib, no Nuke dependency — no deferred import needed)
- [15-02]: Freeze/Unfreeze shortcuts ctrl+shift+f and ctrl+shift+u chosen — verified no conflict with existing menu shortcuts
- [16-01]: _detect_freeze_groups merge condition uses ancestor_uuids | descendant_uuids (union) not intersection — correctly triggers merge for cross-group bridges
- [16-01]: _expand_scope_for_freeze_groups uses current_group.nodes() when available, falls back to nuke.allNodes()
- [16-02]: already_translated_blocks set guards against double-translation when two block members both independently qualify for push
- [16-02]: Block bbox overlap check: if ANY part of freeze block overlaps before-bbox, entire block is skipped from push
- [16-02]: Freeze overrides horizontal mode in spine walk — freeze membership in node_freeze_uuid stops spine collection
- [16-02]: Group View Dot creation already correctly scoped via with current_group: — no nuke.thisGroup() calls needed
- [Phase 16-layout-integration]: No structural decision needed — import make_room was simply missing; added after import node_layout_prefs_dialog
- [Phase 16-layout-integration]: layout_selected node_filter correction uses id()-based set comprehension matching layout_upstream pattern
- [Phase 16-layout-integration]: upstream_non_frozen second pass BFS in both layout_upstream and layout_selected with scope restriction in layout_selected
- [Phase 16-layout-integration]: BFS freeze guard skips frozen nodes as horizontal replay root candidates but continues traversal through their inputs
- [v1.4 roadmap]: Phase build order driven by dependency: prefs must exist before overlay reads delay; overlay must exist before filter references it; menu wiring is the final one-way activation step
- [v1.4 roadmap]: LEAD-01 (Shift+E binds) assigned to Phase 21 (menu wiring) — the user-facing entry point requires all prior phases to be validated before the shortcut is live
- [v1.4 roadmap]: Q/E (shrink/expand) are sticky/chaining keys per PROJECT.md spec — stay in leader mode after dispatch; their undo grouped with WASD session in Phase 20
- [v1.4 roadmap]: Two new files: node_layout_leader.py (event filter + dispatch) and node_layout_overlay.py (HUD widget); four existing files receive minor additions
- [Phase 17-prefs-dialog-foundation]: hint_popup_delay_ms stored as 12th DEFAULTS key with value 0; Leader Key section placed between Scheme Multipliers and Advanced in prefs dialog
- [Phase 18-overlay-widget]: show() calls super().show() before move() — native window must exist before geometry can be set (Pitfall 4 guard)
- [Phase 18-overlay-widget]: Module-level _CHAINING_KEY_COLOR and _SINGLE_SHOT_KEY_COLOR constants named so AST tests can verify two distinct badge colors without importing PySide6
- [Phase 18-overlay-widget]: WA_TranslucentBackground + paintEvent with QPainter used instead of stylesheet background — stylesheet transparency unreliable in Nuke embedded hierarchy

### Pending Todos

None.

### Blockers/Concerns

Open question to resolve at Phase 20 planning: confirm Q/E undo group scope — does the single leader session undo group encompass Q/E presses alongside WASD, or are Q/E separately undoable? PROJECT.md implies Q/E stay in leader mode, suggesting they belong in the same undo session.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260317-n0k | fix the failing tests | 2026-03-17 | 29a0e26 | [260317-n0k-fix-the-failing-tests](./quick/260317-n0k-fix-the-failing-tests/) |
| 260324-an9 | build 5 freeze test scenarios in live Nuke | 2026-03-24 | d481d96 | [260324-an9-use-the-nuke-mcp-to-generate-some-live-n](./quick/260324-an9-use-the-nuke-mcp-to-generate-some-live-n/) |
| 260325-k1f | Fix menu.py command strings to use inline import form | 2026-03-25 | 51150be | [260325-k1f-fix-menu-py-command-strings-to-use-inlin](./quick/260325-k1f-fix-menu-py-command-strings-to-use-inlin/) |
| 260328-5o4 | Add select_hidden_outputs function and menu entry | 2026-03-28 | abc0b27 | [260328-5o4-add-a-select-hidden-outputs-function-tha](./quick/260328-5o4-add-a-select-hidden-outputs-function-tha/) |

## Session Continuity

Last activity: 2026-03-29 - Roadmap created for v1.4 Leader Key (Phases 17-21)
Last session: 2026-03-30T22:16:39.553Z
Stopped at: Completed 18-01-PLAN.md

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-03)

**Core value:** Layout operations must be reliable, undoable, and configurable — users need to trust the tool won't silently misbehave and need to be able to undo when the result isn't what they wanted.
**Current focus:** Phase 1 — Code Quality

## Current Position

Phase: 1 of 5 (Code Quality)
Plan: 2 of 2 completed in current phase
Status: Phase 1 complete
Last activity: 2026-03-04 — Completed plan 01-02 (per-operation cache management and custom diamond Dot marker)

Progress: [██░░░░░░░░] 10%

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: 1 min
- Total execution time: 0.03 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-code-quality | 2 | 2 min | 1 min |

**Recent Trend:**
- Last 5 plans: 01-01 (1 min), 01-02 (1 min)
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

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-03-04
Stopped at: Completed 01-02-PLAN.md — per-operation cache reset, color lookup cache, custom knob on diamond Dots
Resume file: None

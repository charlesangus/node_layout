---
phase: 01-code-quality
plan: 02
subsystem: layout-engine
tags: [nuke, python, caching, knobs, dot-nodes, toolbar]

# Dependency graph
requires:
  - phase: 01-code-quality/01-01
    provides: "Narrowed exception handling, PEP8 None comparisons fixed in node_layout.py and util.py"
provides:
  - Per-operation toolbar folder map reset (_TOOLBAR_FOLDER_MAP = None) in both layout entry points
  - Per-operation color lookup cache (_COLOR_LOOKUP_CACHE) with _clear_color_cache() helper
  - Custom 'node_layout_diamond_dot' Int_Knob marker on all diamond-resolution Dots
  - Reliable diamond Dot detection in _passes_node_filter() via knob presence instead of hide_input value
affects:
  - Future plans that add new layout entry points (must reset both caches)
  - Any code reading hide_input on Dots to identify diamond-resolution nodes

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-operation cache reset: module-level globals set to sentinel at start of each public entry point"
    - "Custom knob tagging: add Tab_Knob + Int_Knob to programmatically-created nodes for reliable identification"
    - "Cache-aside pattern: check dict first, compute and store only on miss"

key-files:
  created: []
  modified:
    - node_layout.py

key-decisions:
  - "Reset _TOOLBAR_FOLDER_MAP to None (simpler than passing dict through call chain) — _get_toolbar_folder_map() rebuilds on first access within each layout call"
  - "Cache color lookups per layout operation only, not globally — avoids stale data if user changes preferences between layout calls"
  - "Use custom knob ('node_layout_diamond_dot') as diamond Dot marker rather than hide_input value — hide_input can be set by users manually on any Dot, making it an unreliable identifier"
  - "Side-input Dots in place_subtree() deliberately do NOT receive the marker knob — only insert_dot_nodes() diamonds are tagged"

patterns-established:
  - "Cache scoping: caches that hold user-changeable data (toolbar map, node colors) are cleared at the start of each public operation, not lazily"
  - "Node identity: programmatically-created nodes get a distinct custom knob so they can be identified without relying on user-editable properties"

requirements-completed: [DEBT-01, FRAG-01, PERF-01]

# Metrics
duration: 1min
completed: 2026-03-04
---

# Phase 1 Plan 2: Per-operation cache management and custom diamond Dot marker

**Per-operation toolbar/color cache reset plus custom 'node_layout_diamond_dot' knob on all diamond Dots for robust identification**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-04T02:38:52Z
- **Completed:** 2026-03-04T02:40:32Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Both layout entry points now reset _TOOLBAR_FOLDER_MAP to None and clear the color cache before any layout work, preventing stale data from prior layout calls
- Color preference lookups are memoized for the duration of each layout operation via _COLOR_LOOKUP_CACHE — repeated calls for the same node class hit the dict rather than rescanning Nuke preferences
- Every Dot created by insert_dot_nodes() receives a Tab_Knob and Int_Knob ('node_layout_diamond_dot') so it can be identified precisely as a diamond-resolution Dot regardless of user-set properties
- _passes_node_filter() now detects diamond Dots by checking for the 'node_layout_diamond_dot' knob rather than querying hide_input.getValue(), eliminating false-positive matches on user-created hidden Dots

## Task Commits

Each task was committed atomically:

1. **Task 1: Per-operation toolbar cache reset and color lookup cache** - `bf2819b` (feat)
2. **Task 2: Tag diamond-resolution Dots with custom knob; update node filter** - `20a57b8` (feat)

**Plan metadata:** committed with docs commit below

## Files Created/Modified
- `node_layout.py` - Added _COLOR_LOOKUP_CACHE, _clear_color_cache(), updated find_node_default_color(), added cache resets and custom knob insertion

## Three Structural Changes Made

### 1. Toolbar cache reset per operation
The existing `_TOOLBAR_FOLDER_MAP` module-level global is reset to `None` at the start of both `layout_upstream()` and `layout_selected()`. The existing `_get_toolbar_folder_map()` lazy-init chain is left intact — resetting to None means it rebuilds fresh on first access within each call, with no signature changes required anywhere.

### 2. Color lookup cache per operation
A new `_COLOR_LOOKUP_CACHE = {}` module-level dict is added alongside `_clear_color_cache()` which reassigns the global to a new empty dict. `find_node_default_color()` checks the cache first (keyed by `node.Class()`) and returns immediately on a hit. On a miss it performs the full Nuke preferences scan, stores the result, then returns it. Both entry points call `_clear_color_cache()` before layout begins, so the cache is scoped to a single operation and never holds stale data across calls.

### Module-level variables and their lifetimes
- `_TOOLBAR_FOLDER_MAP`: `None` between operations; populated on first access via `_get_toolbar_folder_map()`, cleared to `None` at the start of each layout call
- `_COLOR_LOOKUP_CACHE`: `{}` between operations; populated on cache misses during layout, cleared by `_clear_color_cache()` at the start of each layout call

### 3. Custom knob on diamond-resolution Dots
`insert_dot_nodes()` has two Dot creation sites (one inside `_claim()` for the `elif id(inp) in visited:` branch, one inside the deferred mask-edge drain loop). Both sites now immediately add a `nuke.Tab_Knob('node_layout_tab', 'Node Layout')` and a `nuke.Int_Knob('node_layout_diamond_dot', 'Diamond Dot Marker')` set to 1 after `nuke.nodes.Dot()`.

`_passes_node_filter()` was updated to check `node.knob('node_layout_diamond_dot') is not None` instead of the old multi-condition block that tested `node.knob('hide_input').getValue()`.

### Why the custom knob is a more reliable marker than hide_input
`hide_input` is a standard Nuke knob that any user can set on any Dot node in the UI. Checking its value would cause user-created hidden Dots to be incorrectly identified as diamond-resolution Dots created by this codebase, potentially pulling them into layout traversal when they should be ignored. The custom `node_layout_diamond_dot` knob exists only on Dots created by `insert_dot_nodes()` — its presence is an unambiguous indicator of codebase origin.

### Side-input Dots in place_subtree() deliberately do NOT receive the marker knob
`place_subtree()` also creates Dot nodes for side inputs (those with `hide_input` left False), but these are routing aids for display purposes, not diamond-resolution connectors. They are identified by their `hide_input` state (`_hides_inputs()`) returning False and are handled via a different code path (`is_side_dot` logic). Adding the marker knob to them would corrupt the diamond-Dot detection logic.

## Decisions Made
- Reset strategy for toolbar map: set to None (simpler than passing the dict as a parameter through the entire call chain — no signature changes required)
- Color cache scoped per operation, not globally, to handle users changing node color preferences between layout calls
- Custom knob approach for diamond Dot identification (see rationale above)
- Side-input Dots in place_subtree() are intentionally left without the marker knob

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All three Phase 1 code quality requirements (DEBT-01, FRAG-01, PERF-01) are addressed across plans 01-01 and 01-02
- node_layout.py is clean, well-typed with narrowed exceptions, and has reliable per-operation caching and robust node identification
- Ready for Phase 2 planning

---
*Phase: 01-code-quality*
*Completed: 2026-03-04*

## Self-Check: PASSED

- node_layout.py: FOUND
- 01-02-SUMMARY.md: FOUND
- Commit bf2819b (Task 1): FOUND
- Commit 20a57b8 (Task 2): FOUND

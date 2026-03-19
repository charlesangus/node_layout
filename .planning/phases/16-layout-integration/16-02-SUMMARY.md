---
phase: 16-layout-integration
plan: "02"
subsystem: node_layout
tags: [freeze-layout, rigid-block, push-away, tdd]
dependency_graph:
  requires:
    - phase: 16-01
      provides: _detect_freeze_groups, _find_freeze_block_root, node_freeze_uuid, freeze_group_map
  provides:
    - push_nodes_to_make_room freeze-aware block translation (freeze_block_map, freeze_groups params)
    - Rigid block positioning in layout_upstream (freeze_relative_offsets, freeze_excluded_ids)
    - Rigid block positioning in layout_selected (freeze_relative_offsets, freeze_excluded_ids)
    - Freeze overrides horizontal mode in both spine walks
  affects: [layout_upstream, layout_selected, push_nodes_to_make_room]
tech-stack:
  added: []
  patterns: [tdd-red-green, rigid-block-offset-restoration, freeze-aware-push-unit-translation]
key-files:
  created: []
  modified: [node_layout.py, tests/test_freeze_layout.py]
key-decisions:
  - "already_translated_blocks set in push_nodes_to_make_room guards against double-translation when two block members both independently qualify for push"
  - "Block bbox overlap check in push: if ANY part of block overlaps before-bbox, entire block is skipped (not just the individual node)"
  - "Non-root freeze block members removed from node_filter in layout_selected before find_selection_roots so they are not treated as layout roots"
  - "Freeze overrides horizontal mode in spine walk: if cursor is in node_freeze_uuid (and is not the root), spine walk stops — freeze membership takes precedence over stored mode"
  - "Group View Dot creation already correctly scoped via with current_group: context inherited from callers; no changes needed (confirmed by AST tests)"
  - "In layout_selected, bbox_after computation includes freeze-excluded members so full footprint is captured for push_nodes_to_make_room"
patterns-established:
  - "Rigid block pattern: capture relative_offsets before place_subtree, exclude non-root from node_filter, apply offsets after place_subtree"
  - "Block-aware push: use compute_node_bounding_box on all block members for overlap check and delta qualification; translate all members atomically"
requirements-completed: [FRZE-06, FRZE-07]
duration: 8min
completed: "2026-03-19"
---

# Phase 16 Plan 02: Rigid Block Positioning and Freeze-Aware Push Summary

**Freeze blocks treated as rigid units during layout: non-root members maintain relative offsets via pre/post-placement offset restoration, and push_nodes_to_make_room translates entire blocks atomically using block bounding box for obstacle detection**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-19T12:57:00Z
- **Completed:** 2026-03-19T13:03:22Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments
- `push_nodes_to_make_room` extended with `freeze_block_map`/`freeze_groups` params for atomic block translation with `already_translated_blocks` double-translation guard
- Rigid block positioning in both `layout_upstream` and `layout_selected`: `freeze_relative_offsets` captured before `place_subtree`, non-root members excluded via `freeze_excluded_ids`, offsets restored after placement
- Horizontal spine walk in both entry points stops at frozen nodes (freeze membership overrides stored `mode="horizontal"`)
- Group View Dot creation confirmed correctly scoped via `with current_group:` context (AST tests confirm no `nuke.thisGroup()` calls)
- 8 new tests (18 total freeze tests), full suite 331/331 pass

## Task Commits

1. **Task 1 (RED): Add failing tests for rigid block positioning, push, Group View** - `f137654` (test)
2. **Task 2 (GREEN): Implement rigid positioning and freeze-aware push** - `feb5bb2` (feat)

## Files Created/Modified
- `/workspace/tests/test_freeze_layout.py` - Added TestFreezeBlockPositioning (3 tests), TestFreezeBlockPush (3 tests), TestGroupViewDotCreation (2 tests)
- `/workspace/node_layout.py` - push_nodes_to_make_room freeze params, rigid positioning in layout_upstream and layout_selected, freeze-overrides-horizontal in spine walks

## Decisions Made
- `already_translated_blocks` uses `block_uuid` as key (not `id(node)`) so first-encountered member marks the entire block as handled — subsequent iterations `continue` immediately
- Non-root members removed from `node_filter` in `layout_selected` before `find_selection_roots` — prevents them from being treated as selection roots during layout
- `layout_selected` bbox_after includes freeze-excluded members (computed from `freeze_group_map`) so push detection has full footprint
- Group View Dot creation unchanged: `insert_dot_nodes` and `_place_output_dot_for_horizontal_root` are called inside `with current_group:` blocks; the context is inherited, so `nuke.nodes.Dot()` creates in the correct group

## Deviations from Plan

None — plan executed exactly as written. Change 6 (Group View fix) was confirmed as a no-op by inspection: all Dot creation call sites are already inside `with current_group:` blocks.

## Issues Encountered
None.

## Next Phase Readiness
- FRZE-06 (rigid block positioning) and FRZE-07 (freeze-aware push) are complete
- v1.3 Freeze Layout milestone feature set is fully implemented across Phases 15 and 16
- Phase 15 delivered freeze/unfreeze commands and state storage; Phase 16 delivered preprocessing (Plan 01) and layout engine integration (Plan 02)

---
*Phase: 16-layout-integration*
*Completed: 2026-03-19*

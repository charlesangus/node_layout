---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Layout Engine & State
status: "Phase 11.2 open — horizontal layout still broken: spine_x clearance mismatch + Phase 2 overlap"
last_updated: "2026-03-17T10:59:31.901Z"
last_activity: "2026-03-16 - Opened Phase 11.2: fix horizontal layout bbox clearance. Root causes identified: spine_x mismatch vs effective_widths, Phase 2 ignores horizontal chain bbox."
progress:
  total_phases: 9
  completed_phases: 9
  total_plans: 30
  completed_plans: 30
  percent: 93
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-05 after v1.1 start)

**Core value:** Layout operations must be reliable, undoable, and configurable — users need to trust the tool won't silently misbehave and need to be able to undo when the result isn't what they wanted.
**Current focus:** Phase 7 — Per-Node State Storage

## Current Position

Phase: 11.2 of 11.2 (Fix Horizontal Layout BBox)
Plan: 0 of ? (CONTEXT.md written, ready to plan)
Status: Phase 11.2 open — horizontal layout still broken: spine_x clearance mismatch + Phase 2 overlap

Progress: [█████████░] 93% (26 of 26 plans complete, phase 11.2 unplanned)

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
| Phase 07 P06 | 2 | 1 tasks | 3 files |
| Phase 07 P07 | 4 | 2 tasks | 2 files |
| Phase 08 P01 | 8 | 1 tasks | 1 files |
| Phase 08 P02 | 5 | 2 tasks | 1 files |
| Phase 09-multi-input-fan-alignment-mask-side-swap P01 | 5 | 1 tasks | 1 files |
| Phase 09-multi-input-fan-alignment-mask-side-swap P02 | 5 | 2 tasks | 1 files |
| Phase 10-shrink-expand-h-v-both-expand-push-away P01 | 2 | 1 tasks | 1 files |
| Phase 10-shrink-expand-h-v-both-expand-push-away P02 | 6 | 2 tasks | 3 files |
| Phase 11-horizontal-b-spine-layout P01 | 3 | 1 tasks | 1 files |
| Phase 11-horizontal-b-spine-layout P02 | 3 | 2 tasks | 1 files |
| Phase 11-horizontal-b-spine-layout P03 | 6 | 2 tasks | 2 files |
| Phase 11-horizontal-b-spine-layout P04 | 2 | 3 tasks | 1 files |
| Phase 11-horizontal-b-spine-layout P05 | 10 | 2 tasks | 2 files |
| Phase 11.1-fix-horizontal-layout-functionality P01 | 8 | 2 tasks | 1 files |
| Phase 11.1-fix-horizontal-layout-functionality P02 | 6 | 2 tasks | 2 files |
| Phase 11.1-fix-horizontal-layout-functionality P03 | 3 | 1 tasks | 4 files |
| Phase 11.2 P01 | 526652 | 2 tasks | 1 files |
| Phase 11.2-fix-horizontal-layout-bbox P02 | 14 | 2 tasks | 1 files |
| Phase 12-fix-fan-layout-logic P01 | 5 | 2 tasks | 1 files |
| Phase 12-fix-fan-layout-logic P02 | 8 | 3 tasks | 1 files |

## Accumulated Context

### Roadmap Evolution

- Phase 11.1 inserted after Phase 11: fix horizontal layout functionality (URGENT)
- Phase 11.2 inserted after Phase 11.1: horizontal layout STILL broken — spine_x clearance mismatch + Phase 2 vertical subtrees overlapping horizontal chain bbox
- Phase 12 added: fix fan layout logic

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
- [Phase 07]: _scale_upstream_nodes now uses max(upstream_nodes) for bottom-left anchor pivot, matching _scale_selected_nodes — snap_min floor applied consistently in both scale functions
- [Phase 07-07]: h_scale/v_scale read at entry points only (layout_upstream, layout_selected) — mid-recursion reads break memoization; same pattern as per_node_scheme → root_scheme_multiplier
- [Phase 07-07]: Vertical gap scaling uses max(snap_threshold-1, int(gap * v_scale)) floor — same-color tight-gap is a minimum constraint not a spacing preference
- [Phase 07-07]: compute_dims memo key extended to (id(node), scheme_multiplier, h_scale, v_scale) — prevents cache collisions when h_scale/v_scale differ across calls
- [Phase 08]: test_default_font_no_change passes at RED by design — regression guard is trivially true before implementation; correct expected RED state for that test
- [Phase 08-02]: str() wraps label knob value before .strip() to guard against int 0 fallback from Nuke stubs
- [Phase 08-02]: font_mult applied before final int() cast in margin helpers to preserve fractional precision
- [Phase 09]: test_two_input_no_fan_regression and test_mask_right_when_no_fan_regression are expected to PASS RED — regression guards for unchanged n==2 behaviour
- [Phase 09-multi-input-fan-alignment-mask-side-swap]: fan H formula uses single gap_to_fan (not 2x) — Dot row is inside consumer tile, no extra vertical band needed
- [Phase 09-multi-input-fan-alignment-mask-side-swap]: mask side-swap: mask placed at x - mask_gap_h - mask_subtree_width when fan_active (3+ non-mask inputs)
- [Phase 10-shrink-expand-h-v-both-expand-push-away]: Test count is 15 not 14 — plan's class enumeration yields 15 behaviors across 6 classes; all fail RED correctly
- [Phase 10-shrink-expand-h-v-both-expand-push-away]: lastHitGroup stub added to nuke stub in test file — expand wrappers call nuke.lastHitGroup() as first line, stub must expose it
- [Phase 10]: axis parameter uses string 'both'/'h'/'v' — readable and unambiguous, gates both position changes and state write-back on the same axis conditions
- [Phase 10]: repeat_last_scale is a no-op when _last_scale_fn is None — avoids surprising user with unexpected scale direction on first invocation
- [Phase 11-01]: test_output_dot_reused_on_replay uses assertIs() (identity check) — prevents false pass from new Dot with matching position values
- [Phase 11-01]: TestMaskKink uses inner class _SpineNodeWithMask with inputLabel("M") for slot 2 — triggers _is_mask_input() correctly without full Merge2 stub
- [Phase 11-01]: TestModeReplay checks both "horizontal" string AND "place_subtree_horizontal" in layout_upstream() body — two-condition AST prevents comment-only false pass
- [Phase 11-02]: _find_or_create_output_dot takes (root, consumer_node, consumer_slot, current_group) — consumer passed directly; tests are acceptance criteria
- [Phase 11-02]: Two-pass spine walk: first pass accumulates mask kink Y (ancestor-first), second pass places spine nodes — clean cumulative kink without backward reference
- [Phase 11]: compute_dims memo key uses inline tuple syntax (not memo_key variable) — AST test checks for 'node_h_scale' within 80 chars of 'memo['; named variable breaks test
- [Phase 11]: layout_selected() mode dispatch is per-root — each root reads its own stored mode independently; roots in same selection can mix horizontal and vertical
- [Phase 11-horizontal-b-spine-layout]: Unconditional mode write-back in _layout_selected_horizontal_impl: guard on side_layout_mode=='recursive' removed; both recursive and place_only write mode='horizontal' to spine nodes
- [Phase 11-horizontal-b-spine-layout]: _place_output_dot_for_horizontal_root used at all horizontal layout entry points; _find_or_create_output_dot(root, root, ...) would create circular wiring and was removed
- [Phase 11]: id() with is not None guards used for Nuke node identity in _place_output_dot_for_horizontal_root — prevents proxy wrapper false-negatives
- [Phase 11]: layout_selected saves original_selected_root before BFS walk; right-of-consumer anchor applied when BFS rebinds root — mirrors layout_upstream pattern
- [Phase 11]: Horizontal chain downstream anchor formula: spine_x = consumer.xpos() + consumer.screenWidth() + horizontal_gap; spine_y = consumer.ypos()
- [Phase 11.1-01]: TestLeftExtentOverlap calls place_subtree_horizontal directly with broken spine_x to avoid full-stack call complexity while exercising the actual geometry bug
- [Phase 11.1-01]: test_no_consumer_returns_none PASSES RED by design — regression guard for the consumer=None early-return path that must not change after Bug 2 fix
- [Phase 11.1-fix-horizontal-layout-functionality]: [Phase 11.1-02]: Bug 1 spine_x uses leftward_extent = sum(step_x + node.screenWidth()) for each spine node except root — ensures leftmost node clears consumer regardless of node widths
- [Phase 11.1-fix-horizontal-layout-functionality]: [Phase 11.1-02]: Bug 2 dot_y conditional: consumer_node.ypos() + (consumer_node.screenHeight() - dot.screenHeight()) // 2 when consumer_node is not None; else keep below-root formula for standalone chains
- [Phase 11.1-fix-horizontal-layout-functionality]: [Phase 11.1-02]: RED scaffold tests rewritten as GREEN regression tests — fixed spine_x value passed to place_subtree_horizontal; AST pattern strings updated to match new code
- [Phase 11.2-01]: BUG-A test needs wide side-input (a, width=500) on spine node n to trigger effective_widths mismatch — simple chain satisfies clearance constraint before Fix A
- [Phase 11.2-01]: Use _node_layout_prefs_module.DEFAULTS not nl._PREFS_DEFAULTS for pref access in test_horizontal_layout.py — nl alias lacks _PREFS_DEFAULTS attribute
- [Phase 11.2]: Fix B rightmost formula: phase2_anchor_x + phase2_w (not centering formula) — place_subtree all_side places root at anchor; side inputs step rightward; total width = phase2_w
- [Phase 11.2]: Fix B clamp uses >= + subtract 1px from anchor to satisfy assertLess (strict <) in BUG-B test
- [Phase 11.2]: Fix A + Fix B applied symmetrically to layout_upstream and layout_selected replay branches
- [Phase 12-fix-fan-layout-logic]: Set horizontal_subtree_gap=10 in Bug 2 tests to expose margin-sensitive overlap — default 250px gap masks the bug
- [Phase 12-fix-fan-layout-logic]: TestComputeDimsFanWidth is a separate class from TestPlaceSubtreeFanRoots — compute_dims W is a distinct concern
- [Phase 12-fix-fan-layout-logic]: dot_row_y = y - (snap_threshold - 1) - inp.screenHeight(): Dot bottom clears consumer top by snap_threshold-1; subtracting moves upward in positive-down Nuke Y axis
- [Phase 12-fix-fan-layout-logic]: A1 current_x uses max(consumer right, B subtree right) so A1 clears B when B is wider than consumer
- [Phase 12-fix-fan-layout-logic]: b_right_overhang uses // to match _center_x integer division — keeps overhang symmetric and consistent in compute_dims W

### Pending Todos

None.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | Fix highest-subtree placement in horizontal layout: B left, A up, no overlaps, add Dot to B input if missing | 2026-03-14 | c557afe | [1-fix-highest-subtree-placement-in-horizon](.planning/quick/1-fix-highest-subtree-placement-in-horizon/) |

### Blockers/Concerns

- Phase 7 (State Storage): Knob serialization mechanism (TCL addUserKnob vs addOnCreate) must be empirically verified in the target Nuke version before committing. Save a test script, close Nuke, reopen, confirm knobs survive.
- Phase 9 (Fan Alignment): "Same Y" spec is ambiguous — whether it means aligning side-input Dot Y positions or subtree-root Y positions must be decided before implementation begins.

## Session Continuity

Last session: 2026-03-17T10:55:41.498Z
Last activity: 2026-03-16 - Opened Phase 11.2: fix horizontal layout bbox clearance. Root causes identified: spine_x mismatch vs effective_widths, Phase 2 ignores horizontal chain bbox.
Resume file: None

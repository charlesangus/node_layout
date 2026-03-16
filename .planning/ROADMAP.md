# Roadmap: node_layout

## Milestones

- ✅ **v1.0 Quality & Preferences** — Phases 1-5 (shipped 2026-03-05)
- 🚧 **v1.1 Layout Engine & State** — Phases 6-11 (in progress)

## Phases

<details>
<summary>✅ v1.0 Quality & Preferences (Phases 1-5) — SHIPPED 2026-03-05</summary>

- [x] Phase 1: Code Quality (2/2 plans) — completed 2026-03-04
- [x] Phase 2: Bug Fixes (3/3 plans) — completed 2026-03-04
- [x] Phase 3: Undo & Reliability (1/1 plan) — completed 2026-03-04
- [x] Phase 4: Preferences System (3/3 plans) — completed 2026-03-04
- [x] Phase 5: New Commands & Scheme (4/4 plans) — completed 2026-03-05

Full archive: `.planning/milestones/v1.0-ROADMAP.md`

</details>

### 🚧 v1.1 Layout Engine & State (In Progress)

**Milestone Goal:** Improve layout quality through spacing rebalance, multi-input fan alignment, horizontal B-spine mode, and per-node state memory for least-surprise re-layout.

- [x] **Phase 6: Prefs Groundwork + Group Fix + Renames** - Add horizontal gap prefs, fix Group context bug, rename scheme commands (completed 2026-03-08)
- [x] **Phase 7: Per-Node State Storage** - Store layout mode/scheme/scale on each node; survive script save/reload (completed 2026-03-10)
- [x] **Phase 8: Dot Font-Size Margin Scaling** - Scale subtree margin by Dot font size as section-boundary signal (completed 2026-03-11)
- [x] **Phase 9: Multi-Input Fan Alignment + Mask Side-Swap** - Align fan inputs at same Y; move mask input left when non-mask inputs fill right (completed 2026-03-12)
- [x] **Phase 10: Shrink/Expand H/V/Both + Expand Push-Away** - Axis-specific scale commands; expand pushes surrounding nodes (completed 2026-03-12)
- [x] **Phase 11: Horizontal B-Spine Layout** - Left-to-right B-spine layout command; stored in state and replayed by normal layout (completed 2026-03-13)

## Phase Details

### Phase 6: Prefs Groundwork + Group Fix + Renames
**Goal**: Users can configure horizontal spacing and the Dot font reference size via the prefs dialog; layout commands run correctly inside Group nodes; scheme commands are discoverable in the tab menu
**Depends on**: Phase 5 (v1.0 complete)
**Requirements**: PREFS-01, PREFS-02, PREFS-03, PREFS-04, CMD-01, LAYOUT-04, LAYOUT-05
**Success Criteria** (what must be TRUE):
  1. User can open the preferences dialog and set a horizontal gap between subtrees that takes effect on the next layout operation
  2. User can open the preferences dialog and set a separate (smaller) horizontal gap for mask inputs
  3. User can open the preferences dialog and set the Dot font reference size used for margin scaling
  4. Default spacing produces layouts that are visibly less tall and cramped than v1.0 defaults
  5. Running any layout command while inside a Nuke Group creates Dot nodes inside that Group, not at root level
  6. Scheme commands appear as "Layout Upstream Compact" / "Layout Upstream Loose" (scheme name at end) in the tab menu
**Plans**: 4 plans

Plans:
- [ ] 06-01-PLAN.md — Add 3 new prefs keys to DEFAULTS, rebalance defaults, reorganize prefs dialog into 3 sections
- [ ] 06-02-PLAN.md — Wire horizontal_subtree_gap/horizontal_mask_gap into engine; fix broken /home/latuser test paths
- [ ] 06-03-PLAN.md — Group context fix (with current_group: wrapping) + CMD-01 name verification
- [ ] 06-04-PLAN.md — Gap closure: replace nuke.thisGroup() with nuke.lastHitGroup() to fix Group View context

### Phase 7: Per-Node State Storage
**Goal**: Every node touched by a layout operation carries hidden knobs recording the layout mode, scheme, and scale factor; this state survives a save/close/reopen cycle and is replayed on re-layout
**Depends on**: Phase 6
**Requirements**: STATE-01, STATE-02, STATE-03, STATE-04
**Success Criteria** (what must be TRUE):
  1. After running any layout command, each affected node has a hidden `node_layout_tab` with knobs for layout mode, scheme, and scale factor (inspectable via Nuke's script editor)
  2. Saving the .nk script, closing Nuke, and reopening it preserves the hidden state knobs and their values on all previously laid-out nodes
  3. Re-running "Layout Upstream" or "Layout Selected" on a node laid out with Compact scheme replays Compact without the user specifying it again
  4. Running "Layout Upstream Compact" on a node previously stored as Loose overrides the stored scheme to Compact for that re-layout
  5. After a Shrink or Expand operation, the scale factor knob on each affected node reflects the new accumulated scale
**Plans**: 7 plans

Plans:
- [ ] 07-01-PLAN.md — Create node_layout_state.py helper module + both test files (unit tests + AST scaffold)
- [ ] 07-02-PLAN.md — Add state write-back pass to layout_upstream() and layout_selected()
- [ ] 07-03-PLAN.md — Per-node scheme replay at entry points + compute_dims() memo key fix
- [ ] 07-04-PLAN.md — Scale state accumulation in _scale_selected_nodes() and _scale_upstream_nodes()
- [ ] 07-05-PLAN.md — Clear-state commands in node_layout.py + menu.py registration
- [ ] 07-06-PLAN.md — Gap closure: fix _scale_upstream_nodes() anchor drift (wrong pivot node)
- [ ] 07-07-PLAN.md — Gap closure: wire h_scale/v_scale from stored state into layout re-run

### Phase 8: Dot Font-Size Margin Scaling
**Goal**: Subtree margins automatically grow when the Dot at a subtree root has a large font size, letting the compositor use visual font size as a section-boundary signal without any extra config
**Depends on**: Phase 6
**Requirements**: LAYOUT-03
**Success Criteria** (what must be TRUE):
  1. A Dot with a large font size (e.g. 40) at a subtree root produces a noticeably wider margin around that subtree than a Dot with the default font size
  2. The margin scaling uses the `dot_font_reference_size` pref value as the baseline, so changing the pref shifts the scaling curve
  3. Dot nodes without a custom font size (at the factory default) produce the same margin as before this phase (no regression for existing layouts)
**Plans**: 2 plans

Plans:
- [ ] 08-01-PLAN.md — Write RED test scaffold for _dot_font_scale (11 failing tests)
- [ ] 08-02-PLAN.md — Implement _dot_font_scale() and wire into _subtree_margin() and _horizontal_margin()

### Phase 9: Multi-Input Fan Alignment + Mask Side-Swap
**Goal**: When a node has 3 or more non-mask inputs, all immediate input nodes sit at the same Y position and extend their subtrees upward in parallel; the mask input is placed to the left of all non-mask inputs rather than to the right
**Depends on**: Phase 7
**Requirements**: LAYOUT-01, LAYOUT-02
**Success Criteria** (what must be TRUE):
  1. A node with 3+ non-mask inputs produces all immediate input nodes at the same Y position after layout, with their subtrees fanning upward from that shared Y
  2. A node with 3+ non-mask inputs and a mask input places the mask input to the left of all non-mask inputs after layout
  3. A node with only 1 or 2 non-mask inputs (plus optional mask) is unaffected — existing stacking behavior is preserved
**Plans**: 2 plans

Plans:
- [ ] 09-01-PLAN.md — Write RED test scaffold for fan alignment (8 failing tests)
- [ ] 09-02-PLAN.md — Implement _is_fan_active, fan branches in compute_dims and place_subtree, mask-left placement

### Phase 10: Shrink/Expand H/V/Both + Expand Push-Away
**Goal**: Users can compress or expand node trees along a specific axis (horizontal, vertical, or both); expanding a tree pushes surrounding nodes aside using the same push logic as a full layout operation
**Depends on**: Phase 7
**Requirements**: SCALE-01, SCALE-02, SCALE-03
**Success Criteria** (what must be TRUE):
  1. Running "Shrink Selected Horizontal" compresses only the horizontal spacing between selected nodes, leaving vertical positions unchanged
  2. Running "Expand Selected Vertical" increases only the vertical spacing between selected nodes, leaving horizontal positions unchanged
  3. All four axis-mode variants (Shrink/Expand x Selected/Upstream, each in H/V modes) appear as distinct menu commands and respond to modifier keys on existing shortcuts
  4. After running any Expand command, nodes outside the selection that would overlap the expanded tree are pushed away
**Plans**: 2 plans

Plans:
- [ ] 10-01-PLAN.md — Write RED test scaffold for axis scaling, state write-back, repeat-last-scale, and expand push-away (14 failing tests)
- [ ] 10-02-PLAN.md — Implement axis parameter in scale helpers, 8 new H/V wrappers, repeat_last_scale, and menu registration

### Phase 11: Horizontal B-Spine Layout
**Goal**: Users can lay out a B-spine chain left-to-right, with the root node rightmost and each successive input(0) ancestor stepping left; this mode is stored in node state and replayed automatically by subsequent normal layout commands
**Depends on**: Phase 7, Phase 9
**Requirements**: HORIZ-01, HORIZ-02, HORIZ-03
**Success Criteria** (what must be TRUE):
  1. Running "Layout Upstream Horizontal" on a linear chain places the root node rightmost and each upstream input(0) node one step to the left, producing a horizontal left-to-right spine
  2. Running "Layout Selected Horizontal" applies horizontal B-spine layout to the selected nodes
  3. After a horizontal layout, running the standard "Layout Upstream" or "Layout Selected" command on any node in that chain re-lays it out horizontally (replaying the stored mode) without the user specifying horizontal again
**Plans**: 3 plans

Plans:
- [ ] 11-01-PLAN.md — Write RED test scaffold for horizontal spine, output Dot, mask kink, side input placement, AST checks, mode replay (10 failing tests)
- [ ] 11-02-PLAN.md — Implement place_subtree_horizontal() core geometry and _find_or_create_output_dot()
- [ ] 11-03-PLAN.md — Wire layout_upstream/selected horizontal entry points, mode dispatch, state write-back, compute_dims memo key, menu registration

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Code Quality | v1.0 | 2/2 | Complete | 2026-03-04 |
| 2. Bug Fixes | v1.0 | 3/3 | Complete | 2026-03-04 |
| 3. Undo & Reliability | v1.0 | 1/1 | Complete | 2026-03-04 |
| 4. Preferences System | v1.0 | 3/3 | Complete | 2026-03-04 |
| 5. New Commands & Scheme | v1.0 | 4/4 | Complete | 2026-03-05 |
| 6. Prefs Groundwork + Group Fix + Renames | 4/4 | Complete   | 2026-03-08 | - |
| 7. Per-Node State Storage | 7/7 | Complete   | 2026-03-10 | - |
| 8. Dot Font-Size Margin Scaling | 2/2 | Complete   | 2026-03-11 | - |
| 9. Multi-Input Fan Alignment + Mask Side-Swap | 2/2 | Complete   | 2026-03-12 | - |
| 10. Shrink/Expand H/V/Both + Expand Push-Away | 2/2 | Complete    | 2026-03-12 | - |
| 11. Horizontal B-Spine Layout | 5/5 | Complete    | 2026-03-15 | - |

### Phase 11.1: fix horizontal layout functionality (INSERTED)

**Goal:** Fix two geometry bugs when a horizontal B-spine chain is embedded in a vertical tree: leftmost spine node overlaps the consumer (Bug 1) and output dot Y is misaligned causing a diagonal wire (Bug 2); also close 4 stale debug documents.
**Requirements**: none (bug-fix insertion)
**Depends on:** Phase 11
**Plans:** 3 plans

Plans:
- [ ] 11.1-01-PLAN.md — Add RED regression tests: TestLeftExtentOverlap and TestDotYAlignment
- [ ] 11.1-02-PLAN.md — Fix Bug 1 (spine_x left-extent) and Bug 2 (dot Y consumer alignment) in node_layout.py
- [ ] 11.1-03-PLAN.md — Close 4 stale debug documents (status: resolved + fix commit)

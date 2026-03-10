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
- [ ] **Phase 7: Per-Node State Storage** - Store layout mode/scheme/scale on each node; survive script save/reload
- [ ] **Phase 8: Dot Font-Size Margin Scaling** - Scale subtree margin by Dot font size as section-boundary signal
- [ ] **Phase 9: Multi-Input Fan Alignment + Mask Side-Swap** - Align fan inputs at same Y; move mask input left when non-mask inputs fill right
- [ ] **Phase 10: Shrink/Expand H/V/Both + Expand Push-Away** - Axis-specific scale commands; expand pushes surrounding nodes
- [ ] **Phase 11: Horizontal B-Spine Layout** - Left-to-right B-spine layout command; stored in state and replayed by normal layout

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
**Plans**: 5 plans

Plans:
- [ ] 07-01-PLAN.md — Create node_layout_state.py helper module + both test files (unit tests + AST scaffold)
- [ ] 07-02-PLAN.md — Add state write-back pass to layout_upstream() and layout_selected()
- [ ] 07-03-PLAN.md — Per-node scheme replay at entry points + compute_dims() memo key fix
- [ ] 07-04-PLAN.md — Scale state accumulation in _scale_selected_nodes() and _scale_upstream_nodes()
- [ ] 07-05-PLAN.md — Clear-state commands in node_layout.py + menu.py registration

### Phase 8: Dot Font-Size Margin Scaling
**Goal**: Subtree margins automatically grow when the Dot at a subtree root has a large font size, letting the compositor use visual font size as a section-boundary signal without any extra config
**Depends on**: Phase 6
**Requirements**: LAYOUT-03
**Success Criteria** (what must be TRUE):
  1. A Dot with a large font size (e.g. 40) at a subtree root produces a noticeably wider margin around that subtree than a Dot with the default font size
  2. The margin scaling uses the `dot_font_reference_size` pref value as the baseline, so changing the pref shifts the scaling curve
  3. Dot nodes without a custom font size (at the factory default) produce the same margin as before this phase (no regression for existing layouts)
**Plans**: TBD

### Phase 9: Multi-Input Fan Alignment + Mask Side-Swap
**Goal**: When a node has two or more non-mask inputs, all immediate input nodes sit at the same Y position and extend their subtrees upward in parallel; the mask input is placed to the left of all non-mask inputs rather than to the right
**Depends on**: Phase 7
**Requirements**: LAYOUT-01, LAYOUT-02
**Success Criteria** (what must be TRUE):
  1. A Merge node with two non-mask inputs (A and B) produces both immediate input nodes at the same Y position after layout, with their subtrees fanning upward from that shared Y
  2. A Merge node with a mask input and two or more non-mask inputs places the mask input to the left of all non-mask inputs after layout
  3. A node with only one non-mask input (plus optional mask) is unaffected — existing stacking behavior is preserved
**Plans**: TBD

### Phase 10: Shrink/Expand H/V/Both + Expand Push-Away
**Goal**: Users can compress or expand node trees along a specific axis (horizontal, vertical, or both); expanding a tree pushes surrounding nodes aside using the same push logic as a full layout operation
**Depends on**: Phase 7
**Requirements**: SCALE-01, SCALE-02, SCALE-03
**Success Criteria** (what must be TRUE):
  1. Running "Shrink Selected Horizontal" compresses only the horizontal spacing between selected nodes, leaving vertical positions unchanged
  2. Running "Expand Selected Vertical" increases only the vertical spacing between selected nodes, leaving horizontal positions unchanged
  3. All four axis-mode variants (Shrink/Expand x Selected/Upstream, each in H/V modes) appear as distinct menu commands and respond to modifier keys on existing shortcuts
  4. After running any Expand command, nodes outside the selection that would overlap the expanded tree are pushed away
**Plans**: TBD

### Phase 11: Horizontal B-Spine Layout
**Goal**: Users can lay out a B-spine chain left-to-right, with the root node rightmost and each successive input(0) ancestor stepping left; this mode is stored in node state and replayed automatically by subsequent normal layout commands
**Depends on**: Phase 7, Phase 9
**Requirements**: HORIZ-01, HORIZ-02, HORIZ-03
**Success Criteria** (what must be TRUE):
  1. Running "Layout Upstream Horizontal" on a linear chain places the root node rightmost and each upstream input(0) node one step to the left, producing a horizontal left-to-right spine
  2. Running "Layout Selected Horizontal" applies horizontal B-spine layout to the selected nodes
  3. After a horizontal layout, running the standard "Layout Upstream" or "Layout Selected" command on any node in that chain re-lays it out horizontally (replaying the stored mode) without the user specifying horizontal again
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Code Quality | v1.0 | 2/2 | Complete | 2026-03-04 |
| 2. Bug Fixes | v1.0 | 3/3 | Complete | 2026-03-04 |
| 3. Undo & Reliability | v1.0 | 1/1 | Complete | 2026-03-04 |
| 4. Preferences System | v1.0 | 3/3 | Complete | 2026-03-04 |
| 5. New Commands & Scheme | v1.0 | 4/4 | Complete | 2026-03-05 |
| 6. Prefs Groundwork + Group Fix + Renames | 4/4 | Complete   | 2026-03-08 | - |
| 7. Per-Node State Storage | 4/5 | In Progress|  | - |
| 8. Dot Font-Size Margin Scaling | v1.1 | 0/? | Not started | - |
| 9. Multi-Input Fan Alignment + Mask Side-Swap | v1.1 | 0/? | Not started | - |
| 10. Shrink/Expand H/V/Both + Expand Push-Away | v1.1 | 0/? | Not started | - |
| 11. Horizontal B-Spine Layout | v1.1 | 0/? | Not started | - |

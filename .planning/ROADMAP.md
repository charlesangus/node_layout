# Roadmap: node_layout

## Milestones

- ✅ **v1.0 Quality & Preferences** — Phases 1-5 (shipped 2026-03-05)
- ✅ **v1.1 Layout Engine & State** — Phases 6-12 (shipped 2026-03-17)
- ✅ **v1.2 CI/CD** — Phases 13-14 (shipped 2026-03-18)
- 🚧 **v1.3 Freeze Layout** — Phases 15-16 (in progress)

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

<details>
<summary>✅ v1.1 Layout Engine & State (Phases 6-12) — SHIPPED 2026-03-17</summary>

- [x] Phase 6: Prefs Groundwork + Group Fix + Renames (5/5 plans) — completed 2026-03-08
- [x] Phase 7: Per-Node State Storage (7/7 plans) — completed 2026-03-10
- [x] Phase 8: Dot Font-Size Margin Scaling (2/2 plans) — completed 2026-03-11
- [x] Phase 9: Multi-Input Fan Alignment + Mask Side-Swap (2/2 plans) — completed 2026-03-12
- [x] Phase 10: Shrink/Expand H/V/Both + Expand Push-Away (2/2 plans) — completed 2026-03-12
- [x] Phase 11: Horizontal B-Spine Layout (5/5 plans) — completed 2026-03-13
- [x] Phase 11.1: Fix Horizontal Layout Functionality (3/3 plans) — completed 2026-03-15 (INSERTED)
- [x] Phase 11.2: Fix Horizontal Layout Bbox (2/2 plans) — completed 2026-03-16 (INSERTED)
- [x] Phase 12: Fix Fan Layout Logic (2/2 plans) — completed 2026-03-17 (INSERTED)

Full archive: `.planning/milestones/v1.1-ROADMAP.md`

</details>

<details>
<summary>✅ v1.2 CI/CD (Phases 13-14) — SHIPPED 2026-03-18</summary>

- [x] Phase 13: Tooling + CI (3/3 plans) — completed 2026-03-17
- [x] Phase 14: Release Workflow (1/1 plan) — completed 2026-03-18

Full archive: `.planning/milestones/v1.2-ROADMAP.md`

</details>

### 🚧 v1.3 Freeze Layout (In Progress)

**Milestone Goal:** Add a freeze command that locks the relative positions of a group of nodes into a rigid block that the layout engine treats as a single unit.

- [x] **Phase 15: Freeze State & Commands** — Freeze/unfreeze menu commands and UUID state storage (completed 2026-03-19)
- [x] **Phase 16: Layout Integration** — Freeze group detection, auto-join, rigid positioning, and push-away (gap closure in progress) (completed 2026-03-20)

## Phase Details

### Phase 15: Freeze State & Commands
**Goal**: Users can freeze and unfreeze node groups, with group membership persisted invisibly in node state
**Depends on**: Phase 14 (v1.2 complete)
**Requirements**: FRZE-01, FRZE-02, FRZE-03
**Success Criteria** (what must be TRUE):
  1. User can select nodes and run "Freeze Selected" — the nodes are marked as a freeze group with no visible change in the DAG
  2. User can select frozen nodes and run "Unfreeze Selected" — the nodes lose their freeze group membership
  3. Freeze group identity (UUID) survives a .nk script save and reload — frozen nodes re-load as members of their group
  4. Both commands are accessible from the Node Layout menu with keyboard shortcuts
**Plans:** 2/2 plans complete
Plans:
- [x] 15-01-PLAN.md — Wave 0 test scaffolds + freeze_group state helpers in node_layout_state.py
- [x] 15-02-PLAN.md — freeze_selected/unfreeze_selected commands + menu registration

### Phase 16: Layout Integration
**Goal**: The layout engine treats each freeze group as a rigid block — detecting groups before positioning, auto-joining inserted nodes, anchoring via the root node, and moving the block as a unit during push-away
**Depends on**: Phase 15
**Requirements**: FRZE-04, FRZE-05, FRZE-06, FRZE-07
**Success Criteria** (what must be TRUE):
  1. Running layout on a DAG containing frozen nodes repositions non-frozen nodes while frozen nodes hold their relative positions to each other
  2. A node inserted (wired) between two frozen nodes in the DAG is automatically treated as part of the freeze group when layout next runs — no manual re-freeze required
  3. The frozen block as a whole moves when its root node is repositioned by the layout algorithm; all other block members shift by the same delta
  4. Expand/push-away moves a frozen block rigidly as a unit — no individual block nodes are pushed independently
**Plans:** 4/4 plans complete
Plans:
- [x] 16-01-PLAN.md — Freeze group preprocessing: detection, auto-join, group merge, scope expansion
- [x] 16-02-PLAN.md — Rigid block positioning, freeze-aware push-away, Group View Dot fix
- [ ] 16-03-PLAN.md — Gap closure: add missing make_room import to menu.py
- [ ] 16-04-PLAN.md — Gap closure: fix freeze block anchoring, upstream node positioning, dot filter, horizontal BFS guard

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Code Quality | v1.0 | 2/2 | Complete | 2026-03-04 |
| 2. Bug Fixes | v1.0 | 3/3 | Complete | 2026-03-04 |
| 3. Undo & Reliability | v1.0 | 1/1 | Complete | 2026-03-04 |
| 4. Preferences System | v1.0 | 3/3 | Complete | 2026-03-04 |
| 5. New Commands & Scheme | v1.0 | 4/4 | Complete | 2026-03-05 |
| 6. Prefs Groundwork + Group Fix + Renames | v1.1 | 5/5 | Complete | 2026-03-08 |
| 7. Per-Node State Storage | v1.1 | 7/7 | Complete | 2026-03-10 |
| 8. Dot Font-Size Margin Scaling | v1.1 | 2/2 | Complete | 2026-03-11 |
| 9. Multi-Input Fan Alignment + Mask Side-Swap | v1.1 | 2/2 | Complete | 2026-03-12 |
| 10. Shrink/Expand H/V/Both + Expand Push-Away | v1.1 | 2/2 | Complete | 2026-03-12 |
| 11. Horizontal B-Spine Layout | v1.1 | 5/5 | Complete | 2026-03-13 |
| 11.1. Fix Horizontal Layout Functionality (INSERTED) | v1.1 | 3/3 | Complete | 2026-03-15 |
| 11.2. Fix Horizontal Layout Bbox (INSERTED) | v1.1 | 2/2 | Complete | 2026-03-16 |
| 12. Fix Fan Layout Logic (INSERTED) | v1.1 | 2/2 | Complete | 2026-03-17 |
| 13. Tooling + CI | v1.2 | 3/3 | Complete | 2026-03-17 |
| 14. Release Workflow | v1.2 | 1/1 | Complete | 2026-03-18 |
| 15. Freeze State & Commands | v1.3 | 2/2 | Complete | 2026-03-19 |
| 16. Layout Integration | 4/4 | Complete   | 2026-03-20 | - |

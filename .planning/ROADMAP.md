# Roadmap: node_layout

## Milestones

- ✅ **v1.0 Quality & Preferences** — Phases 1-5 (shipped 2026-03-05)
- ✅ **v1.1 Layout Engine & State** — Phases 6-12 (shipped 2026-03-17)
- ✅ **v1.2 CI/CD** — Phases 13-14 (shipped 2026-03-18)
- ✅ **v1.3 Freeze Layout** — Phases 15-16 (shipped 2026-03-20)
- ✅ **v1.4 Leader Key** — Phases 17-21 (shipped 2026-04-01)
- 🔜 **v1.5 Automated Documentation** — Phases 22-26

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

<details>
<summary>✅ v1.3 Freeze Layout (Phases 15-16) — SHIPPED 2026-03-20</summary>

- [x] Phase 15: Freeze State & Commands (2/2 plans) — completed 2026-03-19
- [x] Phase 16: Layout Integration (4/4 plans) — completed 2026-03-20

Full archive: `.planning/milestones/v1.3-ROADMAP.md`

</details>

<details>
<summary>✅ v1.4 Leader Key (Phases 17-21) — SHIPPED 2026-04-01</summary>

- [x] Phase 17: Prefs + Dialog Foundation (1/1 plan) — completed 2026-03-30
- [x] Phase 18: Overlay Widget (1/1 plan) — completed 2026-03-30
- [x] Phase 19: Event Filter + Core Dispatch (2/2 plans) — completed 2026-03-31
- [x] Phase 20: WASD Chaining + C Command (1/1 plan) — completed 2026-03-31
- [x] Phase 21: Menu Wiring (1/1 plan) — completed 2026-04-01

Full archive: `.planning/milestones/v1.4-ROADMAP.md`

</details>

### 🔜 v1.5 Automated Documentation (Phases 22-26)

**Milestone Goal:** A local, single-command pipeline that programmatically generates demo DAG scenes from node_layout, captures them via `nuke-docs-screenshotter`, and assembles a hierarchical tutorial + reference manual covering all functionality — output as markdown (committed PNGs) and PDF (pandoc/LaTeX build artifact).

- [ ] **Phase 22: Build Harness Skeleton** - Scaffold the Makefile up front with one target per pipeline stage, each a testable no-op placeholder
- [ ] **Phase 23: Demo Scene Generation** - A node_layout routine programmatically builds a demo `.nk` with one `screenshot:`-labelled backdrop per feature, wired into the `scenes` Makefile target
- [ ] **Phase 24: Screenshot Capture** - The `capture` Makefile target runs `nuke_dag_capture_auto` on the demo `.nk` to emit committed PNGs
- [ ] **Phase 25: Documentation Content** - The `docs` Makefile target assembles the tutorial + reference markdown embedding the captured PNGs
- [ ] **Phase 26: PDF Build & Finalization** - The `pdf` Makefile target builds the PDF via pandoc + LaTeX; independent stage invocation and prerequisites are documented

## Phase Details

(v1.0–v1.3 phase details archived to their respective `.planning/milestones/vX.Y-ROADMAP.md` files)

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
- [x] 16-03-PLAN.md — Gap closure: add missing make_room import to menu.py
- [x] 16-04-PLAN.md — Gap closure: fix freeze block anchoring, upstream node positioning, dot filter, horizontal BFS guard

(Phase details for v1.4 archived to `.planning/milestones/v1.4-ROADMAP.md`)

### Phase 22: Build Harness Skeleton
**Goal**: A Makefile exists at the repo root with one target per pipeline stage (`scenes`, `capture`, `docs`, `pdf`) plus an `all` target chaining them in dependency order. Each stage target is initially a testable placeholder, establishing the harness that later phases wire real work into.
**Depends on**: Phase 21 (v1.4 complete)
**Requirements**: BUILD-01
**Success Criteria** (what must be TRUE):
  1. Running `make` (or `make all`) from the repo root succeeds and visibly invokes each stage target in order: `scenes` → `capture` → `docs` → `pdf`
  2. Each stage can be run independently by name (e.g. `make scenes`, `make pdf`) and reports which stage it is running
  3. `make help` (or `make` with no real work) lists every available target so a contributor can discover the pipeline stages
  4. The Makefile declares inter-stage dependencies so that a downstream target triggers its upstream prerequisites rather than running them all unconditionally
**Plans**: TBD

Plans:
- [ ] 22-01: Author Makefile skeleton with stage targets, `all` chain, dependency wiring, and a `help` target

### Phase 23: Demo Scene Generation
**Goal**: A node_layout routine programmatically builds a demo `.nk` script containing one `screenshot:`-labelled backdrop per documented feature, with deterministic per-feature slugs and before/after framing where a command transforms the DAG. The `scenes` Makefile target invokes this routine so demo scenes regenerate from code and never drift.
**Depends on**: Phase 22
**Requirements**: SCENE-01, SCENE-02, SCENE-03, SCENE-04, CAP-01
**Success Criteria** (what must be TRUE):
  1. Running `make scenes` produces a demo `.nk` file on disk containing one `screenshot:`-labelled backdrop per documented feature
  2. `nuke_dag_capture_auto --list` (or equivalent) on the generated `.nk` enumerates a stable, deterministic slug for every feature, and re-running `make scenes` reproduces the identical slug set (no drift)
  3. The generated backdrops collectively cover all documented functionality — vertical / horizontal / selected layout, multi-input fan alignment, mask placement, shrink/expand axis modes, freeze/unfreeze, every leader-key command, and prefs schemes
  4. For commands that transform a DAG, the scene presents distinct before-state and after-state backdrops so the eventual screenshot illustrates the effect
  5. The documented setup step installs `nuke-docs-screenshotter` (providing the `nuke_dag_capture_auto` CLI) as a build-time dependency
**Plans**: TBD
**UI hint**: yes

Plans:
- [ ] 23-01: Demo-scene builder routine in node_layout — backdrop-per-feature with deterministic slugs and before/after states
- [ ] 23-02: Feature-coverage map + `nuke-docs-screenshotter` setup step; wire the routine into the `scenes` Makefile target

### Phase 24: Screenshot Capture
**Goal**: The `capture` Makefile target runs `nuke_dag_capture_auto` against the generated demo `.nk`, emitting one PNG per backdrop into a docs image directory, and those PNGs are committed so docs and the PDF rebuild without a Nuke license.
**Depends on**: Phase 23
**Requirements**: CAP-02, CAP-03
**Success Criteria** (what must be TRUE):
  1. Running `make capture` invokes `nuke_dag_capture_auto` on the demo `.nk` and writes one PNG per `screenshot:` backdrop into the docs image directory
  2. Each captured PNG filename matches its backdrop slug, so the image set is predictable and stable across regenerations
  3. The captured PNGs are committed to the repo, allowing later stages to run on a machine without a Nuke license
**Plans**: TBD
**UI hint**: yes

Plans:
- [ ] 24-01: Wire `nuke_dag_capture_auto` invocation into the `capture` Makefile target; commit the generated PNG set into the docs image directory

### Phase 25: Documentation Content
**Goal**: The `docs` Makefile target assembles the hierarchical tutorial + reference manual in markdown — overview of main functions, guided walkthrough, and a complete reference for every menu command, leader-key binding, and preference — embedding the committed PNGs so the docs render correctly on GitHub.
**Depends on**: Phase 24
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06
**Success Criteria** (what must be TRUE):
  1. Running `make docs` produces the markdown documentation source, opening with a hierarchical overview of node_layout's main functions
  2. The markdown contains a tutorial/walkthrough guiding a new user through install → first layout → leader key → prefs
  3. The reference section documents every menu command, every leader-key binding (Shift+E entry plus V/Z/F/C/W/A/S/D/Q/E), and every preference (with its default and effect) — each with a description and screenshot
  4. The markdown embeds the committed PNGs and renders correctly when viewed on GitHub (relative image paths resolve, no broken images)
**Plans**: TBD
**UI hint**: yes

Plans:
- [ ] 25-01: Overview + tutorial/walkthrough markdown; embed captured PNGs with GitHub-relative paths
- [ ] 25-02: Complete reference (menu commands, leader-key bindings, prefs); wire assembly into the `docs` Makefile target

### Phase 26: PDF Build & Finalization
**Goal**: The `pdf` Makefile target converts the markdown source into a single PDF via pandoc + LaTeX, preserving document hierarchy (table of contents, nested sections) and embedded screenshots, produced as an uncommitted build artifact. The build's prerequisites are documented and stages can run independently — including rebuilding the PDF from committed PNGs without Nuke — so the no-Nuke case works end to end.
**Depends on**: Phase 25
**Requirements**: PDF-01, PDF-02, PDF-03, BUILD-02, BUILD-03
**Success Criteria** (what must be TRUE):
  1. Running `make pdf` invokes pandoc + LaTeX and produces a single PDF from the markdown source
  2. The PDF contains a table of contents and nested sections matching the markdown hierarchy, with the captured screenshots embedded inline
  3. The PDF is produced as a build artifact that is not committed to the repo (suitable for attaching to a GitHub Release)
  4. On a machine without Nuke, running the doc/PDF stages independently (skipping `scenes`/`capture`) rebuilds the PDF from the committed PNGs — `make pdf` succeeds without re-capturing
  5. The build command and all its prerequisites (Nuke, `nuke-docs-screenshotter`, pandoc, LaTeX) are documented
**Plans**: TBD

Plans:
- [ ] 26-01: Wire pandoc + LaTeX conversion into the `pdf` Makefile target with TOC, section hierarchy, and embedded images; keep the PDF uncommitted
- [ ] 26-02: Document prerequisites + the build command; verify independent/no-Nuke stage invocation (rebuild PDF from committed PNGs)

## Progress

**Execution Order:**
Phases execute in numeric order: 22 → 23 → 24 → 25 → 26

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
| 16. Layout Integration | v1.3 | 4/4 | Complete | 2026-03-20 |
| 17. Prefs + Dialog Foundation | v1.4 | 1/1 | Complete | 2026-03-30 |
| 18. Overlay Widget | v1.4 | 1/1 | Complete | 2026-03-30 |
| 19. Event Filter + Core Dispatch | v1.4 | 2/2 | Complete | 2026-03-31 |
| 20. WASD Chaining + C Command | v1.4 | 1/1 | Complete | 2026-03-31 |
| 21. Menu Wiring | v1.4 | 1/1 | Complete | 2026-04-01 |
| 22. Build Harness Skeleton | v1.5 | 0/1 | Not started | - |
| 23. Demo Scene Generation | v1.5 | 0/2 | Not started | - |
| 24. Screenshot Capture | v1.5 | 0/1 | Not started | - |
| 25. Documentation Content | v1.5 | 0/2 | Not started | - |
| 26. PDF Build & Finalization | v1.5 | 0/2 | Not started | - |

# Roadmap: node_layout

## Milestones

- ✅ **v1.0 Quality & Preferences** — Phases 1-5 (shipped 2026-03-05)
- ✅ **v1.1 Layout Engine & State** — Phases 6-12 (shipped 2026-03-17)
- ✅ **v1.2 CI/CD** — Phases 13-14 (shipped 2026-03-18)
- ✅ **v1.3 Freeze Layout** — Phases 15-16 (shipped 2026-03-20)
- 🚧 **v1.4 Leader Key** — Phases 17-21 (in progress)

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

### 🚧 v1.4 Leader Key (In Progress)

**Milestone Goal:** Replace the Shift+E Layout Upstream shortcut with a modal leader key system that dispatches to existing commands via a mnemonic keymap and displays an icon-style keyboard overlay over the DAG during the modal window.

- [x] **Phase 17: Prefs + Dialog Foundation** — Add hint popup delay preference and expose it in the dialog (completed 2026-03-30)
- [x] **Phase 18: Overlay Widget** — Build the floating keyboard HUD widget with focus-safe display (completed 2026-03-30)
- [x] **Phase 19: Event Filter + Core Dispatch** — Leader mode state machine with single-shot command dispatch (completed 2026-03-31)
- [x] **Phase 20: WASD Chaining + C Command** — Sticky movement dispatch with key-repeat guard and clear freeze command (completed 2026-03-31)
- [ ] **Phase 21: Menu Wiring** — Bind Shift+E to leader mode entry and activate the event filter at startup

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
- [x] 16-03-PLAN.md — Gap closure: add missing make_room import to menu.py
- [x] 16-04-PLAN.md — Gap closure: fix freeze block anchoring, upstream node positioning, dot filter, horizontal BFS guard

### Phase 17: Prefs + Dialog Foundation
**Goal**: The hint popup delay preference exists in the prefs system and is configurable via the preferences dialog
**Depends on**: Phase 16
**Requirements**: PREF-01, PREF-02
**Success Criteria** (what must be TRUE):
  1. `NodeLayoutPrefs` returns a default value of 0 for `hint_popup_delay_ms` on a clean install with no existing prefs file
  2. The preferences dialog contains a "Leader Key" section with a "Hint popup delay (ms)" field
  3. Entering a value in the dialog field and clicking OK persists the value to `~/.nuke/node_layout_prefs.json` and the next call to `NodeLayoutPrefs` returns the updated value
  4. Entering a negative value in the dialog field is rejected with a validation error
**Plans:** 1/1 plans complete
Plans:
- [x] 17-01-PLAN.md — Add hint_popup_delay_ms pref default + Leader Key dialog section

### Phase 18: Overlay Widget
**Goal**: A floating keyboard HUD is displayable over the DAG without stealing keyboard focus
**Depends on**: Phase 17
**Requirements**: OVRL-01, OVRL-02, OVRL-03, OVRL-04
**Success Criteria** (what must be TRUE):
  1. The overlay appears over the active DAG displaying all active command keys with their action labels
  2. Keypresses in the DAG remain functional immediately after the overlay becomes visible — the overlay does not capture keyboard input
  3. The overlay disappears when `hide()` is called, leaving no residual widget on screen
  4. `LeaderKeyOverlay` has `WA_ShowWithoutActivating` set and window type `Qt.WindowType.Tool` — verifiable via structural test without a running Nuke session
**Plans:** 1/1 plans complete
Plans:
- [x] 18-01-PLAN.md — LeaderKeyOverlay widget + AST structural tests

### Phase 19: Event Filter + Core Dispatch
**Goal**: The leader mode state machine intercepts keypresses, routes single-shot commands, and cancels on unrecognized input — all without consuming events outside leader mode
**Depends on**: Phase 18
**Requirements**: LEAD-02, LEAD-03, LEAD-04, DISP-01, DISP-02, DISP-03, DISP-04
**Success Criteria** (what must be TRUE):
  1. Pressing V while in leader mode calls `layout_upstream()` when exactly one node is selected, and `layout_selected()` when two or more nodes are selected, then exits leader mode
  2. Pressing Z while in leader mode dispatches horizontal layout then exits leader mode
  3. Pressing F while in leader mode freezes selected nodes if they are unfrozen, or unfreezes them if they are frozen, then exits leader mode
  4. Pressing any key not in the dispatch table while in leader mode cancels leader mode and consumes the event (it does not propagate to Nuke)
  5. A mouse click while in leader mode cancels leader mode and the click event propagates normally
  6. The event filter returns `False` unconditionally for all events when leader mode is not active — no Nuke built-in shortcuts are affected
  7. Leader mode does not arm when a dialog, text field, or non-DAG widget has keyboard focus at the time of the arm attempt
**Plans:** 2/2 plans complete
Plans:
- [x] 19-01-PLAN.md — Implement LeaderKeyFilter and arm() entry point
- [x] 19-02-PLAN.md — Structural AST tests for LeaderKeyFilter

### Phase 20: WASD Chaining + C Command
**Goal**: Movement keys keep leader mode alive for chained input; a complete WASD session is undoable in a single Ctrl+Z; the C key clears freeze group membership
**Depends on**: Phase 19
**Requirements**: DISP-05, DISP-06, DISP-07, DISP-08
**Success Criteria** (what must be TRUE):
  1. Pressing W, A, S, or D while in leader mode moves selected nodes one step in the corresponding direction and leader mode remains active for the next keypress
  2. Pressing Q or E while in leader mode shrinks or expands selected nodes and leader mode remains active for the next keypress
  3. Holding a WASD key down moves nodes exactly once — the OS key-repeat events are discarded; additional steps require deliberate individual keypresses
  4. All node movements made during a single leader session (from arm to exit) are undone by a single Ctrl+Z
  5. Pressing C while in leader mode removes the selected nodes from their freeze group then exits leader mode
**Plans:** 1/1 plans complete
Plans:
- [x] 20-01-PLAN.md — Add WASD/Q/E chaining dispatch helpers, _CHAINING_DISPATCH_TABLE, eventFilter chaining branch, and AST structural tests

### Phase 21: Menu Wiring
**Goal**: Shift+E arms leader mode in a live Nuke session and the old Layout Upstream shortcut no longer fires on Shift+E
**Depends on**: Phase 20
**Requirements**: LEAD-01
**Success Criteria** (what must be TRUE):
  1. Pressing Shift+E in the Nuke DAG enters leader mode — the overlay appears and the next keypress dispatches a command
  2. The Layout Upstream command is still accessible from the Node Layout menu but no longer has a keyboard shortcut assigned to it
  3. The `LeaderKeyFilter` event filter is active from Nuke startup — no manual initialization step is required after plugin load
**Plans**: TBD

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
| 16. Layout Integration | v1.3 | 4/4 | Complete | 2026-03-20 |
| 17. Prefs + Dialog Foundation | v1.4 | 1/1 | Complete    | 2026-03-30 |
| 18. Overlay Widget | v1.4 | 1/1 | Complete    | 2026-03-30 |
| 19. Event Filter + Core Dispatch | v1.4 | 2/2 | Complete   | 2026-03-31 |
| 20. WASD Chaining + C Command | v1.4 | 1/1 | Complete    | 2026-03-31 |
| 21. Menu Wiring | v1.4 | 0/? | Not started | - |

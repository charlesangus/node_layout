# Requirements: node_layout

**Defined:** 2026-03-18
**Core Value:** Layout operations must be reliable, undoable, and configurable — users need to trust the tool won't silently misbehave.

## v1.4 Requirements

Requirements for the Leader Key milestone. Phases continue from v1.3 (starting at Phase 17).

### Leader Mode

- [ ] **LEAD-01**: Shift+E arms leader mode (replaces the existing Layout Upstream shortcut)
- [x] **LEAD-02**: Pressing an unrecognized key cancels leader mode; the key event is consumed, not forwarded to Nuke
- [x] **LEAD-03**: Any mouse click cancels leader mode
- [x] **LEAD-04**: Leader mode is not armed if a dialog, text field, or non-DAG widget has keyboard focus at the time of Shift+E

### Command Dispatch

- [x] **DISP-01**: V dispatches vertical layout — context-aware: 1 node selected → layout upstream; 2+ nodes → layout selection — then exits leader mode
- [x] **DISP-02**: Z dispatches horizontal layout then exits leader mode
- [x] **DISP-03**: F toggles freeze/unfreeze for selected nodes based on their current freeze state, then exits leader mode
- [x] **DISP-04**: C removes selected nodes from their freeze group then exits leader mode
- [x] **DISP-05**: W/A/S/D dispatch node movement in the corresponding direction and keep leader mode active for chained input
- [x] **DISP-06**: Q dispatches scale down (shrink) and keeps leader mode active
- [x] **DISP-07**: E dispatches scale up (expand) and keeps leader mode active
- [x] **DISP-08**: Auto-repeat key events (OS key-hold) are discarded — each step requires a deliberate keypress

### Overlay

- [x] **OVRL-01**: An icon-style keyboard overlay is displayed over the active DAG on leader arm, after the hint popup delay
- [x] **OVRL-02**: The overlay shows only the active command keys with their action labels
- [x] **OVRL-03**: The overlay does not steal keyboard focus from the DAG
- [x] **OVRL-04**: The overlay is dismissed when leader mode exits

### Preferences

- [x] **PREF-01**: A "hint popup delay (ms)" preference is added with default 0
- [x] **PREF-02**: The hint popup delay preference is exposed in the preferences dialog

## v1.3 Requirements (Complete)

Requirements for the Freeze Layout milestone.

### Freeze Commands

- [x] **FRZE-01**: User can freeze selected nodes into a named group via "Freeze Selected" menu command (with keyboard shortcut)
- [x] **FRZE-02**: User can unfreeze selected nodes via "Unfreeze Selected" menu command (with keyboard shortcut)
- [x] **FRZE-03**: Freeze group UUID is stored as an invisible knob on the existing hidden layout tab; no visual indicator appears in the DAG

### Layout Integration

- [x] **FRZE-04**: Layout crawl runs a preprocessing step that detects all freeze groups before any node positioning begins (analogous to existing horizontal block detection)
- [x] **FRZE-05**: During preprocessing, nodes topologically inserted between frozen nodes in the DAG auto-join the freeze group (no real-time callbacks; resolved at crawl time only)
- [x] **FRZE-06**: Layout positions a frozen block as a unit — the root node (most downstream node in the block) is placed by the layout algorithm and all other block nodes are repositioned to maintain their original relative offsets
- [x] **FRZE-07**: Push-away (expand) treats a frozen block's bounding box as a single rigid obstacle; the entire block shifts as a unit when pushed

## Future Requirements

### Potential v1.5+

- Freeze group visualization (e.g. overlay or node tint) — explicitly deferred; no DAG clutter in v1.3
- Per-group freeze label / name — UUID is sufficient for v1.3 identity
- Freeze membership query command ("which group is this node in?") — defer until user need is established
- Configurable leader key — first-class keymap config is a larger UX system; hardcoded Shift+E sufficient for v1.4
- Multi-character leader sequences (e.g. Shift+E, L, 1 for "layout scheme compact")

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time auto-join callbacks | Nuke callback overhead and complexity; preprocessing at crawl time is sufficient |
| Visual freeze indicator in DAG | User prefers no DAG clutter; state is in hidden knobs |
| Nested freeze groups | Not needed; single-level grouping covers all intended use cases |
| Cross-script freeze state | Freeze groups are per-session layout artifacts; not intended to persist across script loads differently from other state |
| Timeout-based leader cancellation | User explicitly rejected this — cancellation is key/click only |
| Custom keybindings via prefs dialog | Out of scope for v1.4; hardcoded keymap is sufficient |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FRZE-01 | Phase 15 | Complete |
| FRZE-02 | Phase 15 | Complete |
| FRZE-03 | Phase 15 | Complete |
| FRZE-04 | Phase 16 | Complete |
| FRZE-05 | Phase 16 | Complete |
| FRZE-06 | Phase 16 | Complete |
| FRZE-07 | Phase 16 | Complete |
| PREF-01 | Phase 17 | Complete |
| PREF-02 | Phase 17 | Complete |
| OVRL-01 | Phase 18 | Complete |
| OVRL-02 | Phase 18 | Complete |
| OVRL-03 | Phase 18 | Complete |
| OVRL-04 | Phase 18 | Complete |
| LEAD-02 | Phase 19 | Complete |
| LEAD-03 | Phase 19 | Complete |
| LEAD-04 | Phase 19 | Complete |
| DISP-01 | Phase 19 | Complete |
| DISP-02 | Phase 19 | Complete |
| DISP-03 | Phase 19 | Complete |
| DISP-04 | Phase 19 | Complete |
| DISP-05 | Phase 20 | Complete |
| DISP-06 | Phase 20 | Complete |
| DISP-07 | Phase 20 | Complete |
| DISP-08 | Phase 20 | Complete |
| LEAD-01 | Phase 21 | Pending |

**Coverage:**
- v1.4 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-18*
*Last updated: 2026-03-29 after v1.4 roadmap creation*

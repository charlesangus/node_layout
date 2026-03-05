# Requirements: node_layout

**Defined:** 2026-03-05
**Core Value:** Layout operations must be reliable, undoable, and configurable — users need to trust the tool won't silently misbehave and need to be able to undo when the result isn't what they wanted.

## v1.1 Requirements

Requirements for the Layout Engine & State milestone. Each maps to roadmap phases.

### Prefs & Spacing

- [ ] **PREFS-01**: User can configure horizontal gap between subtrees via the preferences dialog
- [ ] **PREFS-02**: User can configure a separate (smaller) horizontal gap for mask inputs via the preferences dialog
- [ ] **PREFS-03**: User can configure the Dot font reference size used to scale subtree margins via the preferences dialog
- [ ] **PREFS-04**: Default spacing constants are rebalanced (less vertical gap, more horizontal gap) so layouts feel less tall and cramped

### Layout Quality

- [ ] **LAYOUT-01**: When a node has 2+ non-mask inputs, all immediate input nodes are placed at the same Y position (fan alignment), with their subtrees extending upward
- [ ] **LAYOUT-02**: When a node has 2+ non-mask inputs, the mask input is placed to the left of all non-mask inputs
- [ ] **LAYOUT-03**: Subtree margin scales with the font size of the Dot node at the subtree root — a larger font signals a section boundary and produces more breathing room
- [ ] **LAYOUT-04**: When running layout commands inside a Nuke Group, Dot nodes are created inside that Group (not at Root level)
- [ ] **LAYOUT-05**: When running layout commands inside a Nuke Group, push-away logic considers only nodes within that Group

### Node State Storage

- [ ] **STATE-01**: Every node touched by a layout operation receives a hidden tab with knobs storing: layout mode, scheme (compact/normal/loose), and scale factor
- [ ] **STATE-02**: Hidden state knobs persist across .nk script save/close/reopen cycles
- [ ] **STATE-03**: Re-running a layout command replays the stored scheme unless the command explicitly specifies one (e.g. running "Layout Upstream Compact" overrides stored scheme)
- [ ] **STATE-04**: Shrink/Expand commands update the scale factor knob on affected nodes

### Horizontal Layout

- [ ] **HORIZ-01**: User can run "Layout Upstream Horizontal" to lay out the B spine right-to-left — root node is rightmost, each successive input(0) ancestor steps left; output pipe from root extends downward to parent tree
- [ ] **HORIZ-02**: User can run "Layout Selected Horizontal" to lay out selected nodes in horizontal B-spine mode
- [ ] **HORIZ-03**: Horizontal layout mode is stored in each node's state knob; normal "Layout Upstream/Selected" commands replay horizontal mode automatically

### Scale Commands

- [ ] **SCALE-01**: Shrink/Expand Selected and Upstream commands support Horizontal, Vertical, and Both axis modes
- [ ] **SCALE-02**: Axis mode is selectable via separate menu commands (e.g. "Shrink Selected Horizontal") and via modifier keys on existing shortcuts
- [ ] **SCALE-03**: Expand Selected and Expand Upstream push surrounding nodes away after expanding (same push logic as regular layout)

### Command Renames

- [ ] **CMD-01**: Compact and Loose layout scheme commands are renamed so the scheme name appears at the end (e.g. "Layout Upstream Compact") for tab-menu discoverability

## Future Requirements

### v2.0

- Layout for entire DAG without selection (unpredictable on complex scripts; defer)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Keyboard shortcut customization via prefs | Conflict probability low; document in README only |
| Unit test suite for core algorithms | Requires Nuke license; not feasible in CI |
| Spatial indexing / quadtree for large DAGs | Performance acceptable up to ~500 nodes; over-engineering |
| Nuke version compatibility layer | Nuke 11+ assumed; no version guards needed |
| Error dialogs for empty selection | Fail silently; no dialog noise |
| Visible GUI toggles on node parameter panels | Hidden knobs are the correct UX; no clutter |
| Physics-based or force-directed layout | Non-deterministic; incompatible with undo expectations |
| Full Sugiyama/layered-graph layout | NP-hard general DAG; no benefit for tree-shaped Nuke DAGs |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PREFS-01 | Phase 6 | Pending |
| PREFS-02 | Phase 6 | Pending |
| PREFS-03 | Phase 6 | Pending |
| PREFS-04 | Phase 6 | Pending |
| CMD-01 | Phase 6 | Pending |
| LAYOUT-04 | Phase 6 | Pending |
| LAYOUT-05 | Phase 6 | Pending |
| STATE-01 | Phase 7 | Pending |
| STATE-02 | Phase 7 | Pending |
| STATE-03 | Phase 7 | Pending |
| STATE-04 | Phase 7 | Pending |
| LAYOUT-03 | Phase 8 | Pending |
| LAYOUT-01 | Phase 9 | Pending |
| LAYOUT-02 | Phase 9 | Pending |
| SCALE-01 | Phase 10 | Pending |
| SCALE-02 | Phase 10 | Pending |
| SCALE-03 | Phase 10 | Pending |
| HORIZ-01 | Phase 11 | Pending |
| HORIZ-02 | Phase 11 | Pending |
| HORIZ-03 | Phase 11 | Pending |

**Coverage:**
- v1.1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0

---
*Requirements defined: 2026-03-05*
*Last updated: 2026-03-05 after v1.1 roadmap creation*

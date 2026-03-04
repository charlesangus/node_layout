# Requirements: node_layout — Quality & Preferences Milestone

**Defined:** 2026-03-03
**Core Value:** Layout operations must be reliable, undoable, and configurable — users need to trust the tool won't silently misbehave and need to be able to undo when the result isn't what they wanted.

## v1 Requirements

### Tech Debt

- [x] **DEBT-01**: Toolbar folder cache is invalidated and rebuilt on each layout operation rather than persisting globally across the session
- [x] **DEBT-02**: Exception handling in `find_node_default_color()` catches `KeyError` and `AttributeError` specifically, not bare `Exception`
- [x] **DEBT-03**: Exception handling in `get_dag_snap_threshold()` catches `KeyError` and `AttributeError` specifically, not bare `Exception`
- [x] **DEBT-04**: Debug `print(start_location)` statement removed from `util.py`
- [x] **DEBT-05**: `nodes_so_far == None` comparison replaced with `nodes_so_far is None` in `util.py`

### Bug Fixes

- [x] **BUG-01**: `make_room()` initializes `x_amount = 0` and `y_amount = 0` before conditional branches so variables are always defined
- [x] **BUG-02**: `layout_selected()` node filter stores node objects directly rather than node IDs to avoid stale references
- [x] **BUG-03**: Inline Dot nodes are positioned centered under their output node, accounting for the Dot's smaller screen size
- [x] **BUG-04**: In standard layout, input 0 (main/B input) always goes directly above the consumer node — never offset to a side
- [x] **BUG-05**: A/B/mask input slot spacing is consistent; right-side input placement follows the same rules as left-side

### Undo Support

- [x] **UNDO-01**: `layout_upstream()` wraps all node position changes in a single Nuke undo group so Ctrl+Z undoes the entire operation at once
- [x] **UNDO-02**: `layout_selected()` wraps all node position changes in a single Nuke undo group so Ctrl+Z undoes the entire operation at once

### Fragile Area Fixes

- [x] **FRAG-01**: Diamond-resolution Dot nodes are tagged with a custom knob marker; `_passes_node_filter()` checks that knob instead of relying on the `hide_input` flag

### Performance

- [x] **PERF-01**: `find_node_default_color()` results are memoized for the duration of a single layout operation and cleared between operations

### Preferences & Spacing

- [ ] **PREFS-01**: `node_layout_prefs.py` module provides a JSON-backed singleton storing prefs at `~/.nuke/node_layout_prefs.json`
- [ ] **PREFS-02**: Default values reflect tighter spacing than current hardcoded constants (SUBTREE_MARGIN significantly reduced from 300)
- [ ] **PREFS-03**: Spacing constants (`SUBTREE_MARGIN`, tight gap multiplier, loose gap multiplier, mask input ratio) are read from prefs at layout-operation time rather than hardcoded
- [ ] **PREFS-04**: Three presets available: Compact, Normal (default), Loose — each sets all spacing values at once
- [ ] **PREFS-05**: PySide6 preferences dialog (`node_layout_prefs_dialog.py`) is accessible from the node_layout menu
- [ ] **PREFS-06**: Dialog exposes a preset selector and numeric fields for SUBTREE_MARGIN, tight gap multiplier, loose gap multiplier, and mask input ratio
- [ ] **PREFS-07**: Subtree margin scales proportionally to the number of nodes in the subtree (dynamic spacing) rather than using a single static value

### New Commands

- [ ] **CMD-01**: Shrink/expand selected nodes command scales the spacing between selected nodes up or down, centered on the root node
- [ ] **CMD-02**: Scale upstream command applies the same shrink/expand scaling to all upstream nodes from the selected node

### Layout Schemes

- [ ] **SCHEME-01**: Compact layout scheme produces the same structure as standard layout but applies tight spacing throughout regardless of node color or category

## v2 Requirements

### Layout Schemes (deferred)

- **SCHEME-02**: Horizontal scheme — main input (input 0) goes left instead of up; secondary inputs go up
- **SCHEME-03**: Fan scheme — all inputs laid out in one row above the root node, normal layout applied above the fan
- **SCHEME-04**: Nodes can be tagged with a layout scheme via custom knob; future layout calls respect the tag automatically
- **SCHEME-05**: Clear tag command removes layout scheme tag from selected nodes

## Out of Scope

| Feature | Reason |
|---------|--------|
| Error dialogs for empty selection | Annoying; fail silently instead |
| Keyboard shortcut customization | Low conflict probability; document in README only |
| Unit test suite for core algorithms | Requires Nuke license; not feasible in CI |
| Spatial indexing / quadtree | Acceptable performance up to ~500 nodes; over-engineering now |
| Nuke version compatibility layer | Users are on Nuke 11+; no abstraction needed |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DEBT-01 | Phase 1 | Complete |
| DEBT-02 | Phase 1 | Complete |
| DEBT-03 | Phase 1 | Complete |
| DEBT-04 | Phase 1 | Complete |
| DEBT-05 | Phase 1 | Complete |
| FRAG-01 | Phase 1 | Complete |
| PERF-01 | Phase 1 | Complete |
| BUG-01 | Phase 2 | Complete |
| BUG-02 | Phase 2 | Complete |
| BUG-03 | Phase 2 | Complete |
| BUG-04 | Phase 2 | Complete |
| BUG-05 | Phase 2 | Complete |
| UNDO-01 | Phase 3 | Complete |
| UNDO-02 | Phase 3 | Complete |
| PREFS-01 | Phase 4 | Pending |
| PREFS-02 | Phase 4 | Pending |
| PREFS-03 | Phase 4 | Pending |
| PREFS-04 | Phase 4 | Pending |
| PREFS-05 | Phase 4 | Pending |
| PREFS-06 | Phase 4 | Pending |
| PREFS-07 | Phase 4 | Pending |
| CMD-01 | Phase 5 | Pending |
| CMD-02 | Phase 5 | Pending |
| SCHEME-01 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0

---
*Requirements defined: 2026-03-03*
*Last updated: 2026-03-03 after roadmap creation*

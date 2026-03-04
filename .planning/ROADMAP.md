# Roadmap: node_layout — Quality & Preferences Milestone

## Overview

This milestone transforms node_layout from a working-but-fragile tool into a reliable, undoable, and configurable plugin. Work proceeds from internal code health inward to outward, starting with code quality and bug fixes that make the foundation trustworthy, then adding undo support to make layout operations reversible, then building the preferences system that lets users control spacing, and finally delivering new commands and layout schemes that extend capability.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Code Quality** - Clean up tech debt, fragile areas, and performance inefficiencies in the existing codebase
- [ ] **Phase 2: Bug Fixes** - Correct user-visible layout positioning errors
- [ ] **Phase 3: Undo & Reliability** - Wrap layout operations in undo groups so Ctrl+Z restores prior state
- [ ] **Phase 4: Preferences System** - Add a JSON-backed prefs module and PySide6 dialog for spacing configuration
- [ ] **Phase 5: New Commands & Scheme** - Deliver shrink/expand scaling commands and a compact layout scheme

## Phase Details

### Phase 1: Code Quality
**Goal**: The codebase is internally clean — no debug artifacts, no broad exception swallowing, no stale global state, and no expensive repeated Nuke API calls during layout
**Depends on**: Nothing (first phase)
**Requirements**: DEBT-01, DEBT-02, DEBT-03, DEBT-04, DEBT-05, FRAG-01, PERF-01
**Success Criteria** (what must be TRUE):
  1. Running a layout operation does not print any output to the Nuke script editor or terminal
  2. The toolbar folder map is rebuilt fresh on each layout call rather than persisting stale data from a prior session
  3. Exception handling in color and snap-threshold lookups catches only the specific exceptions that can occur, not bare `Exception`
  4. Diamond-resolution Dot nodes carry a custom knob marker so the node filter can identify them without relying on the user-settable `hide_input` flag
  5. Repeated calls to `find_node_default_color()` within a single layout operation do not trigger redundant Nuke preference lookups
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — Simple cleanup: remove debug print, fix None comparison, narrow exception handlers
- [ ] 01-02-PLAN.md — Structural improvements: per-operation toolbar refresh, diamond Dot custom knob, color lookup cache

### Phase 2: Bug Fixes
**Goal**: Layout placement is correct — main inputs go directly above their consumer, side inputs are placed consistently, and inline Dot nodes are centered properly
**Depends on**: Phase 1
**Requirements**: BUG-01, BUG-02, BUG-03, BUG-04, BUG-05
**Success Criteria** (what must be TRUE):
  1. After `layout_upstream()` or `layout_selected()`, input 0 (main/B input) of a node always lands directly above that node, never offset to a side
  2. Inline Dot nodes introduced during diamond resolution appear visually centered under their downstream output node
  3. A/B/mask inputs on the right side of a node are placed using the same spacing rules as inputs on the left side — no asymmetric gaps
  4. `make_room()` does not reference undefined variables; displacement works correctly in all branch combinations
  5. `layout_selected()` correctly excludes deselected nodes even after the Nuke script has been modified between selection and layout execution
**Plans**: TBD

### Phase 3: Undo & Reliability
**Goal**: Both layout commands are fully undoable — a single Ctrl+Z after any layout operation restores every node to its pre-layout position
**Depends on**: Phase 2
**Requirements**: UNDO-01, UNDO-02
**Success Criteria** (what must be TRUE):
  1. After running "Layout Upstream" (Shift+E), pressing Ctrl+Z once moves all repositioned nodes back to exactly where they were before the command ran
  2. After running "Layout Selected", pressing Ctrl+Z once restores all repositioned nodes to their pre-layout positions in a single step
  3. Ctrl+Z does not leave nodes in a partially-restored intermediate state
**Plans**: TBD

### Phase 4: Preferences System
**Goal**: Users can configure spacing values via a persistent preferences file and a dedicated dialog, and layout operations read those values at runtime
**Depends on**: Phase 3
**Requirements**: PREFS-01, PREFS-02, PREFS-03, PREFS-04, PREFS-05, PREFS-06, PREFS-07
**Success Criteria** (what must be TRUE):
  1. A `node_layout_prefs.py` module exists and provides spacing values that persist to `~/.nuke/node_layout_prefs.json` across Nuke sessions
  2. Running a layout operation after changing a preference immediately reflects the new spacing — no Nuke restart required
  3. Selecting the Compact preset produces noticeably tighter node spacing; selecting Loose produces noticeably wider spacing compared to Normal
  4. The preferences dialog is reachable from the node_layout menu and exposes numeric fields for SUBTREE_MARGIN, tight gap multiplier, loose gap multiplier, and mask input ratio
  5. Subtree margin scales with the number of nodes in the subtree, so a single-node subtree does not receive the same large clearance as a twenty-node subtree
**Plans**: TBD

### Phase 5: New Commands & Scheme
**Goal**: Users have two new scaling commands and a compact-scheme layout option that apply the existing layout engine with different spacing policies
**Depends on**: Phase 4
**Requirements**: CMD-01, CMD-02, SCHEME-01
**Success Criteria** (what must be TRUE):
  1. Selecting nodes and invoking "Shrink/Expand Selected" scales the spacing between those nodes up or down, centered on the root node, without affecting unselected nodes
  2. Invoking "Scale Upstream" from a selected node applies the same shrink/expand scaling to all upstream nodes in the tree
  3. Invoking "Compact Layout" runs the full layout algorithm but applies tight spacing throughout regardless of node color or category — the result is visually denser than a Normal layout of the same graph
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Code Quality | 1/2 | In Progress|  |
| 2. Bug Fixes | 0/? | Not started | - |
| 3. Undo & Reliability | 0/? | Not started | - |
| 4. Preferences System | 0/? | Not started | - |
| 5. New Commands & Scheme | 0/? | Not started | - |

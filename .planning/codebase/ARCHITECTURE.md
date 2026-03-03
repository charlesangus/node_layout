# Architecture

**Analysis Date:** 2026-03-03

## Pattern Overview

**Overall:** Tree layout engine with hierarchical graph traversal and spatial placement algorithm

**Key Characteristics:**
- Recursive depth-first traversal with deferred processing for complex graph topology (diamond patterns)
- Two-phase dimensional computation: bottom-up subtree measurement followed by top-down positioning
- Coordinate-space aware positioning with vertical banding and horizontal staircase placement
- Non-destructive collision avoidance that displaces surrounding nodes only when necessary

## Layers

**Menu & Command Interface:**
- Purpose: Expose layout operations to Nuke's UI
- Location: `menu.py`
- Contains: Command registration, keyboard shortcuts, menu structure
- Depends on: `node_layout`, `make_room`, `util` modules
- Used by: Nuke initialization system

**Core Layout Engine:**
- Purpose: Calculate and apply node positioning for DAG trees
- Location: `node_layout.py` (primary 600+ lines)
- Contains: Dimension computation, subtree traversal, placement algorithms, dot insertion logic
- Depends on: Nuke Python API (`nuke` module)
- Used by: `menu.py` for `layout_upstream` and `layout_selected` commands

**Utility Functions:**
- Purpose: Provide helper operations for node selection, filtering, and analysis
- Location: `util.py` (42 lines) and `make_room.py` (42 lines)
- Contains: Upstream traversal, filename sorting, node displacement
- Depends on: Nuke Python API (`nuke`, `nukescripts`)
- Used by: `menu.py` for auxiliary commands

## Data Flow

**Layout Upstream (Root-Based):**

1. User selects a node → `layout_upstream()` called via keyboard shortcut or menu
2. Snapshot original subtree nodes and bounding box via `collect_subtree_nodes(root)`
3. Call `insert_dot_nodes(root)` — DFS with mask-edge deferral to resolve diamond patterns
4. Call `compute_dims(root, memo, snap_threshold)` — recursive bottom-up measurement of each subtree
5. Call `place_subtree(root, x, y, memo, snap_threshold)` — recursive top-down positioning with dot insertion
6. Snapshot final subtree and bounding box
7. Call `push_nodes_to_make_room()` — if footprint grew, displace non-subtree nodes that would overlap

**Layout Selected (Multi-Root):**

1. User selects 2+ nodes → `layout_selected()` called via menu
2. Call `find_selection_roots()` — identify most-downstream nodes (those not used as inputs by other selections)
3. For each root (sorted left-to-right):
   - Snapshot original bounding box
   - Apply dot insertion filtered to selected node set
   - Compute dimensions with node_filter active
   - Determine starting X position: if Y-range overlaps with prior roots' subtrees, push rightward
   - Place subtree with adjusted X offset
   - Track placed bounding boxes to avoid overlap
4. Apply collision avoidance if overall footprint grew

**State Management:**
- Nodes store X/Y position via Nuke API (`setXpos()`, `setYpos()`)
- Memoization dict maps node ID to computed subtree dimensions — reused across recursive calls
- Node filters (when provided) are Python sets of node object IDs for fast membership testing
- Dot insertion is performed in-place: new Dot nodes created and wired inline

## Key Abstractions

**Dimension Memoization:**
- Purpose: Cache computed (width, height) for each subtree to avoid exponential recalculation
- Files: `node_layout.py` lines 238–283
- Pattern: `memo[id(node)]` keyed by Python object ID; checked at start of `compute_dims()`, stored at end

**Input Slot Pairs:**
- Purpose: Preserve actual input slot indices (0, 1, 2, …) while filtering and reordering inputs
- Files: `node_layout.py` lines 107–126, 128–139
- Pattern: `(slot_index, input_node)` tuples flow through `_get_input_slot_pairs()`, `_reorder_inputs_mask_last()`, and placement to correctly wire nodes even after reordering

**Node Filtering:**
- Purpose: Enable layout of a subset of selected nodes while stopping graph traversal at filter boundaries
- Files: `node_layout.py` lines 148–168, 170–181
- Pattern: `node_filter` is a set of `id(node)` values; `_passes_node_filter()` checks membership and handles special case of hidden Dot nodes (diamond resolution dots)

**Dot Node Insertion:**
- Purpose: Resolve multi-path (diamond) connections to enable tree-like placement of DAG graphs
- Files: `node_layout.py` lines 184–235
- Pattern: Two-pass DFS — non-mask edges first (claimed immediately), mask edges deferred to second pass; only create Dot if target node already visited

**Vertical Banding:**
- Purpose: Allocate exclusive Y-space to each input subtree to prevent overlap
- Files: `node_layout.py` lines 286–445, especially lines 363–372 (Y staircase)
- Pattern: Each input occupies a vertical band from `bottom_y[i] - child_dims[i][1]` to `bottom_y[i]`; bands stack downward (toward root) with gaps between them

**Collision Avoidance:**
- Purpose: Displace surrounding nodes when subtree layout grows
- Files: `node_layout.py` lines 474–518
- Pattern: Compute bounding box before and after layout; only move nodes that don't overlap original footprint; apply separate push amounts for up and right growth

## Entry Points

**layout_upstream():**
- Location: `node_layout.py` lines 521–540
- Triggers: `Shift+E` keyboard shortcut or "Layout Upstream" menu command
- Responsibilities:
  - Retrieves selected node as root
  - Captures pre-layout state
  - Orchestrates dot insertion, dimension computation, and placement
  - Applies collision avoidance if subtree grows
  - Main entry point for single-tree layout

**layout_selected():**
- Location: `node_layout.py` lines 554–591
- Triggers: "Layout Selected" menu command (no keyboard shortcut)
- Responsibilities:
  - Identifies multi-root forest from selected nodes
  - Iterates roots left-to-right with horizontal overlap detection
  - Applies node filter to scope layout to selection only
  - Applies collision avoidance to final positioned forest
  - Entry point for multi-selection layout

**Menu Registration:**
- Location: `menu.py` lines 6–33
- Triggers: Nuke initialization
- Responsibilities: Registers all menu items and keyboard shortcuts in "Edit → Node Layout"

## Error Handling

**Strategy:** Graceful degradation; missing data treated as neutral/default

**Patterns:**
- `find_node_default_color()` (lines 52–60): Attempts to find user-set colors via preferences; falls back to `NodeColor` if not found
- `get_dag_snap_threshold()` (lines 45–49): Tries to read from preferences; returns 8 px if read fails
- `_is_mask_input()` (lines 88–100): Multiple detection strategies (input label contains "mask"/"matte", specific node types like Merge, `maskChannelInput`/`maskChannel` knobs) with fallback to False
- `find_selection_roots()` (lines 543–551): Works with empty selection (returns empty list)
- `compute_node_bounding_box()` (lines 464–471): Returns None if node list is empty; callers check for None before using

No try-catch blocks in core layout logic; Nuke API calls assumed to succeed or raise exceptions that propagate.

## Cross-Cutting Concerns

**Logging:** None — no print statements or debug logging in core layout code; only `print()` in `util.py` line 13

**Validation:**
- `_hides_inputs()` (lines 80–82) checks for existence of `hide_input` knob before querying
- `_is_mask_input()` wrapped in try-except for nodes that may not have expected knobs
- No parameter validation; assumes Nuke API provides valid node objects

**Authentication:** Not applicable (single-user desktop application)

**Coordinate System:**
- Nuke DAG: positive Y points down; Y=0 is top of screen
- Inputs (upstream) placed at smaller Y values than consumers (higher on screen)
- `setXpos()`/`setYpos()` set top-left corner of node tile
- All arithmetic treats Y as-is (negative deltas move nodes up visually)

---

*Architecture analysis: 2026-03-03*

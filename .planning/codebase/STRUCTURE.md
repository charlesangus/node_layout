# Codebase Structure

**Analysis Date:** 2026-03-03

## Directory Layout

```
node_layout/
├── node_layout.py          # Core layout engine
├── menu.py                 # Menu and keyboard shortcut registration
├── make_room.py            # Node displacement utilities
├── util.py                 # Selection and sorting utilities
├── README.md               # User documentation and feature overview
├── CLAUDE.md               # Project-specific instructions
├── LICENSE                 # License file
├── .gitignore              # Git ignore patterns
├── .git/                   # Git repository metadata
├── __pycache__/            # Python bytecode cache (generated)
└── .planning/
    └── codebase/           # Architecture documentation (this directory)
```

## Directory Purposes

**Root Level:**
- Purpose: Four Python modules + documentation for Nuke plugin
- Contains: Executable code and user-facing docs
- Key files: `node_layout.py` (primary implementation), `menu.py` (integration point)

**.planning/codebase/:**
- Purpose: Internal analysis and design documentation
- Contains: ARCHITECTURE.md, STRUCTURE.md (this file)
- Generated: Yes
- Committed: Yes

**__pycache__/:**
- Purpose: Python compiled bytecode cache
- Generated: Yes
- Committed: No (listed in .gitignore)

## Key File Locations

**Entry Points:**

- `menu.py`: Nuke calls this automatically on startup via plugin path; registers all menu items and shortcuts. Lines 6–33 register four commands under "Edit → Node Layout"

- `node_layout.py`: Contains two main entry points called from menu:
  - `layout_upstream()` (lines 521–540) — `Shift+E` keyboard shortcut
  - `layout_selected()` (lines 554–591) — menu command (no shortcut)

**Configuration:**

- `.nuke/init.py` (external to this repo): User must add `nuke.pluginAddPath('/path/to/node_layout')` to expose this plugin to Nuke

**Core Logic:**

- `node_layout.py` (592 lines): Implements all layout algorithms:
  - Toolbar folder mapping (lines 1–38)
  - Color and spacing logic (lines 40–77)
  - Node classification (lines 80–104)
  - Input filtering and reordering (lines 107–181)
  - Diamond resolution (lines 184–235)
  - Dimension computation (lines 238–283)
  - Subtree placement (lines 286–445)
  - Subtree collection (lines 448–461)
  - Bounding box computation (lines 464–471)
  - Collision avoidance (lines 474–518)

**Utilities:**

- `util.py` (42 lines):
  - `sort_by_filename()` (lines 4–18) — sorts Read nodes horizontally by file path
  - `upstream_ignoring_hidden()` (lines 21–32) — recursive upstream traversal
  - `select_upstream_ignoring_hidden()` (lines 35–41) — selects all visible upstream nodes

- `make_room.py` (42 lines):
  - `make_room()` (lines 5–40) — bulk node displacement in cardinal directions

**Testing:**

- No test files present in codebase
- Manual testing expected via Nuke UI

## Naming Conventions

**Files:**
- Snake case: `node_layout.py`, `make_room.py`, `util.py`
- Single underscore prefix for "private" helper modules (none here; all four modules are public)

**Functions:**

- Public API (exposed in menu): `layout_upstream`, `layout_selected`, `sort_by_filename`, `select_upstream_ignoring_hidden`, `make_room`
- Private helpers (internal to module): `_collect_toolbar_items`, `_build_toolbar_folder_map`, `_get_toolbar_folder_map`, `_hides_inputs`, `_is_mask_input`, `_subtree_margin`, `_reorder_inputs_mask_last`, `_get_input_slot_pairs`, `_passes_node_filter`, `_primary_slot_externally_occupied`, `_claim` (nested in `insert_dot_nodes`)

**Variables:**

- Global constants: UPPERCASE — `_TOOLBAR_FOLDER_MAP`, `_MERGE_LIKE_CLASSES`, `SUBTREE_MARGIN`, `MASK_INPUT_MARGIN`
- Loop indices: Single lowercase letter (i, n, x, y) — standard Python convention
- Descriptive names: `input_slot_pairs`, `memo`, `node_filter`, `subtree_node_ids`, `bbox_before`, `bbox_after`, `selected_nodes`, `placement_roots`
- Prefixed with underscore: Private module-level variables (`_TOOLBAR_FOLDER_MAP`), private functions (`_claim`, `_hides_inputs`)

**Node-related Variables:**
- `node`, `root`, `inp` (short for input), `parent` — common in graph traversal
- `selected_nodes`, `input_slot_pairs` — descriptive plural forms
- Specific roles: `top_node`, `bottom_node` (in vertical comparisons), `actual_upstream` (in Dot handling)

## Where to Add New Code

**New Feature (e.g., different layout strategy):**
- Primary code: `node_layout.py` — add new layout function following pattern of `layout_upstream()` / `layout_selected()`
- Registration: `menu.py` lines 6–33 — add `layout_menu.addCommand()` call
- Tests: None currently; would create `test_node_layout.py` if testing framework added

**New Utility Command (e.g., node analysis):**
- Implementation: `util.py` — add function following pattern of `sort_by_filename()` or `select_upstream_ignoring_hidden()`
- Registration: `menu.py` — add command entry in layout_menu

**New Collision Avoidance Strategy:**
- Implementation: `node_layout.py` — extend or replace `push_nodes_to_make_room()` (lines 474–518)
- Consider: Called from `layout_upstream()` (line 540) and `layout_selected()` (line 591)

**New Spacing Rule (e.g., based on node type):**
- Implementation: `node_layout.py` — modify `vertical_gap_between()` (lines 74–77) or `_subtree_margin()` (lines 103–104)
- Propagates through: `compute_dims()`, `place_subtree()` (both use side_margins list)

## Special Directories

**__pycache__/:**
- Purpose: Python 3 compiled bytecode cache (`.pyc` files)
- Generated: Yes (automatic when Python imports modules)
- Committed: No

**.planning/codebase/:**
- Purpose: Architecture and structure documentation for GSD planner/executor
- Generated: Yes (by GSD map-codebase command)
- Committed: Yes (results checked into version control)

**.git/:**
- Purpose: Git repository metadata and history
- Generated: Yes
- Committed: N/A (is the repository itself)

## Import Organization

**node_layout.py:**
```python
import nuke
```
Only external import; no relative imports (no package structure).

**menu.py:**
```python
import nuke
import node_layout
import make_room
import util
```
Nuke import first, then local modules in order of feature area.

**make_room.py:**
```python
import nuke
import nukescripts
```
Standard library imports first, then Nuke API.

**util.py:**
```python
import nuke
import nukescripts
```
Same pattern as make_room.py.

**No Path Aliases:**
No `import` aliases or absolute path imports. All imports are module names (flat plugin structure).

## Module Relationships

```
menu.py (orchestrator)
  ├─→ node_layout.py
  │    └─→ nuke (API)
  ├─→ make_room.py
  │    └─→ nuke (API)
  └─→ util.py
       └─→ nuke (API)
```

`menu.py` is the integration layer; it's the only file that imports the other three modules. This allows those modules to be independently testable and reusable.

---

*Structure analysis: 2026-03-03*

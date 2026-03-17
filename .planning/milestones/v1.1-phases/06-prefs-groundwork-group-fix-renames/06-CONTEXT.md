# Phase 6: Prefs Groundwork + Group Fix + Renames - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Three workstreams in one phase:
1. **New prefs + dialog**: Add `horizontal_subtree_gap`, `horizontal_mask_gap`, and `dot_font_reference_size` prefs; expose all three in the prefs dialog; rebalance existing default values so layouts are less tall and cramped (PREFS-01 through PREFS-04)
2. **Group context fix**: When layout commands run inside a Nuke Group, Dot node creation and push-away logic must operate within that Group's context, not at Root level (LAYOUT-04, LAYOUT-05)
3. **CMD-01 verification**: Scheme command names in menu.py already match requirement ("Layout Upstream Compact" etc.); verify and mark complete — no code change expected

</domain>

<decisions>
## Implementation Decisions

### Horizontal gap prefs (PREFS-01, PREFS-02)
- Two new explicit pref keys: `horizontal_subtree_gap` (px, subtree-to-subtree) and `horizontal_mask_gap` (px, for mask inputs)
- Both are absolute pixel values, independent of each other and of `base_subtree_margin`
- `base_subtree_margin` becomes specifically the vertical baseline; H-axis driven by the new prefs
- `mask_input_ratio` still applies to the vertical mask gap (unchanged); `horizontal_mask_gap` is the H-axis equivalent

### Dot font reference size pref (PREFS-03)
- New pref key: `dot_font_reference_size`
- Exposed and editable in the prefs dialog now, even though the engine doesn't use it until Phase 8
- User can pre-configure before Phase 8 lands

### Default rebalancing (PREFS-04)
- Goal: layouts visibly less tall AND wider — both V reduction and H increase
- Claude proposes new default values based on engine analysis; will tune at UAT
- **Existing prefs files are discarded / ignored** — we're in a testing phase; no migration needed, start fresh with new defaults
- The `_load()` method in NodeLayoutPrefs already merges DEFAULTS over loaded values, so simply updating DEFAULTS handles fresh installs; we may want to add a version-bump mechanism or just clear the prefs file in test instructions

### Dialog UX
- Reorganize from flat list into three sections with **bold QLabel separators** (not QGroupBox frames):
  - **Spacing**: `horizontal_subtree_gap`, `horizontal_mask_gap`, `base_subtree_margin`, `mask_input_ratio`
  - **Scheme Multipliers**: `compact_multiplier`, `normal_multiplier`, `loose_multiplier`, `loose_gap_multiplier`
  - **Advanced**: `dot_font_reference_size`, `scaling_reference_count`
- Section headers are bold QLabel rows inserted into the QFormLayout (or above it as QLabel widgets in the outer QVBoxLayout)

### CMD-01 (command rename verification)
- Current menu.py already has correct names: "Layout Upstream Compact", "Layout Selected Compact", "Layout Upstream Loose", "Layout Selected Loose"
- Phase 6 task: verify this matches the requirement, mark CMD-01 complete — no code change expected

### Group context fix (LAYOUT-04, LAYOUT-05)
- Bug: `nuke.nodes.Dot()` inside `insert_dot_nodes()` and `place_subtree()` creates nodes at Root level when called from within a Group DAG
- Fix approach: detect `nuke.thisGroup()` at the entry points (`layout_upstream`, `layout_selected`) and wrap the entire layout operation with `group.begin()` / `group.end()` (or `with group:` context manager if available in the Nuke Python API)
- Push-away logic (`push_nodes_to_make_room` / `nuke.allNodes()`) must be scoped to the current group: use `group.nodes()` instead of `nuke.allNodes()` when inside a Group

### Claude's Discretion
- Specific default pixel values for `horizontal_subtree_gap`, `horizontal_mask_gap`, `base_subtree_margin` (will propose and adjust at UAT)
- Whether to use `with group:` or `group.begin()`/`group.end()` (depends on Nuke API availability — check during implementation)
- Exact QLabel styling for section headers (bold weight, spacing)

</decisions>

<specifics>
## Specific Ideas

- "Blast old prefs" — no migration; test environment starts fresh with new defaults
- The dialog reorganization should feel like three natural sections without heavy chrome (no QGroupBox borders)
- Group fix is a correctness bug, not a new feature — silent wrong behavior (Dot at root while wired inside group)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `NodeLayoutPrefs.get()` / `NodeLayoutPrefs.set()` / `NodeLayoutPrefs.save()`: already handles JSON persistence; adding new keys to `DEFAULTS` dict is sufficient
- `NodeLayoutPrefsDialog._build_ui()` / `_populate_from_prefs()` / `_on_accept()`: all three methods need updating for new fields and sectioned layout
- `_subtree_margin()` in `node_layout.py`: currently uses `SUBTREE_MARGIN` constant and `mask_input_ratio` pref; H-axis usage (`side_margins_h`) needs to read `horizontal_subtree_gap` / `horizontal_mask_gap` instead
- `push_nodes_to_make_room()` in `node_layout.py`: calls `nuke.allNodes()` — needs scoping to group nodes when inside a Group

### Established Patterns
- All prefs accessed via `node_layout_prefs.prefs_singleton.get(key)` throughout `node_layout.py`
- Menu commands registered in `menu.py` via `layout_menu.addCommand()`
- Try/except with silent fallback for invalid input in `_on_accept()`
- `side_margins_h` and `side_margins_v` already computed separately in `compute_dims()` and `place_subtree()` — the split between H and V pref values maps naturally

### Integration Points
- `DEFAULTS` dict in `node_layout_prefs.py`: add 3 new keys
- `NodeLayoutPrefsDialog._build_ui()`: add section labels + 3 new QLineEdit rows
- `NodeLayoutPrefsDialog._populate_from_prefs()`: add 3 new `.setText()` calls
- `NodeLayoutPrefsDialog._on_accept()`: add 3 new parse + validate + set calls
- `_subtree_margin()` or its callers in `node_layout.py`: read H-axis from `horizontal_subtree_gap` / `horizontal_mask_gap`
- `layout_upstream()` and `layout_selected()` entry points: add Group context detection and wrapping

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-prefs-groundwork-group-fix-renames*
*Context gathered: 2026-03-07*

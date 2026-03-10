# Phase 6: Prefs Groundwork + Group Fix + Renames - Research

**Researched:** 2026-03-07
**Domain:** Nuke Python API (Group context, node creation), PySide6 QFormLayout, JSON prefs extension
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Horizontal gap prefs (PREFS-01, PREFS-02)**
- Two new explicit pref keys: `horizontal_subtree_gap` (px, subtree-to-subtree) and `horizontal_mask_gap` (px, for mask inputs)
- Both are absolute pixel values, independent of each other and of `base_subtree_margin`
- `base_subtree_margin` becomes specifically the vertical baseline; H-axis driven by the new prefs
- `mask_input_ratio` still applies to the vertical mask gap (unchanged); `horizontal_mask_gap` is the H-axis equivalent

**Dot font reference size pref (PREFS-03)**
- New pref key: `dot_font_reference_size`
- Exposed and editable in the prefs dialog now, even though the engine doesn't use it until Phase 8
- User can pre-configure before Phase 8 lands

**Default rebalancing (PREFS-04)**
- Goal: layouts visibly less tall AND wider — both V reduction and H increase
- Claude proposes new default values based on engine analysis; will tune at UAT
- Existing prefs files are discarded / ignored — we're in a testing phase; no migration needed, start fresh with new defaults
- The `_load()` method in NodeLayoutPrefs already merges DEFAULTS over loaded values, so simply updating DEFAULTS handles fresh installs; we may want to add a version-bump mechanism or just clear the prefs file in test instructions

**Dialog UX**
- Reorganize from flat list into three sections with bold QLabel separators (not QGroupBox frames):
  - **Spacing**: `horizontal_subtree_gap`, `horizontal_mask_gap`, `base_subtree_margin`, `mask_input_ratio`
  - **Scheme Multipliers**: `compact_multiplier`, `normal_multiplier`, `loose_multiplier`, `loose_gap_multiplier`
  - **Advanced**: `dot_font_reference_size`, `scaling_reference_count`
- Section headers are bold QLabel rows inserted into the QFormLayout (or above it as QLabel widgets in the outer QVBoxLayout)

**CMD-01 (command rename verification)**
- Current menu.py already has correct names: "Layout Upstream Compact", "Layout Selected Compact", "Layout Upstream Loose", "Layout Selected Loose"
- Phase 6 task: verify this matches the requirement, mark CMD-01 complete — no code change expected

**Group context fix (LAYOUT-04, LAYOUT-05)**
- Bug: `nuke.nodes.Dot()` inside `insert_dot_nodes()` and `place_subtree()` creates nodes at Root level when called from within a Group DAG
- Fix approach: detect `nuke.thisGroup()` at the entry points (`layout_upstream`, `layout_selected`) and wrap the entire layout operation with `group.begin()` / `group.end()` (or `with group:` context manager if available in the Nuke Python API)
- Push-away logic (`push_nodes_to_make_room` / `nuke.allNodes()`) must be scoped to the current group: use `group.nodes()` instead of `nuke.allNodes()` when inside a Group

### Claude's Discretion

- Specific default pixel values for `horizontal_subtree_gap`, `horizontal_mask_gap`, `base_subtree_margin` (will propose and adjust at UAT)
- Whether to use `with group:` or `group.begin()`/`group.end()` (depends on Nuke API availability — check during implementation)
- Exact QLabel styling for section headers (bold weight, spacing)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PREFS-01 | User can configure horizontal gap between subtrees via the preferences dialog | DEFAULTS dict extension + dialog UI update — pattern fully understood from existing code |
| PREFS-02 | User can configure a separate (smaller) horizontal gap for mask inputs via the preferences dialog | Same pattern as PREFS-01; `_is_mask_input()` already available for routing the H-axis read |
| PREFS-03 | User can configure the Dot font reference size used to scale subtree margins via the preferences dialog | Stub pref — add to DEFAULTS and dialog; engine use deferred to Phase 8 |
| PREFS-04 | Default spacing constants are rebalanced (less vertical gap, more horizontal gap) so layouts feel less tall and cramped | DEFAULTS dict values changed; `_load()` merge-on-top pattern means existing file wins unless cleared |
| CMD-01 | Compact and Loose layout scheme commands are renamed so the scheme name appears at the end | menu.py already shows correct names; verification-only task |
| LAYOUT-04 | When running layout commands inside a Nuke Group, Dot nodes are created inside that Group (not at Root level) | Verified: `group.begin()`/`group.end()` and `with group:` both work; wrap full operation at entry points |
| LAYOUT-05 | When running layout commands inside a Nuke Group, push-away logic considers only nodes within that Group | Verified: `nuke.allNodes()` is context-aware (uses current group when no arg given); explicit `group.nodes()` is the safe, readable alternative |
</phase_requirements>

## Summary

Phase 6 has three workstreams, each technically independent but sharing the same codebase files. The prefs workstream (PREFS-01 through PREFS-04) is a straightforward extension of an established pattern: add keys to `DEFAULTS`, wire them through the dialog's three methods, and update the H-axis reads in `_subtree_margin()`'s callers. The Group context fix (LAYOUT-04, LAYOUT-05) addresses a real Nuke API behavior: `nuke.nodes.Dot()` and similar node-creation calls always create in the current Python context, which defaults to Root unless explicitly set. The CMD-01 task is a verification-only item — menu.py already has the correct names.

The key architectural insight for the Group fix is that both `group.begin()`/`group.end()` and `with group:` are verified to work as context-switching mechanisms in the Nuke Python API. The `with group:` pattern is supported (Nuke Group's `__enter__`/`__exit__` call `begin()`/`end()`). For `push_nodes_to_make_room()`, `nuke.allNodes()` documentation states it uses the "current group" when no argument is provided, making it theoretically context-aware — but explicit `group.nodes()` is clearer and safer. The STATE.md already documents the correct pattern: "Group context: capture current_group at entry point; wrap Dot creation with `with current_group:`".

The test infrastructure uses unittest (no pytest installed) with hardcoded absolute paths that are currently broken (`/home/latuser/git/nuke_layout_project/...` vs `/workspace/`). The prefs-focused tests in `test_node_layout_prefs.py` use a portable `_import_prefs_module()` approach and pass. New tests for Phase 6 should follow the AST-inspection and stub-nuke patterns already established in `test_prefs_integration.py`.

**Primary recommendation:** Follow the established code patterns exactly — DEFAULTS extension for prefs, AST-verified tests for structural changes, and `with current_group:` wrapping at both `layout_upstream()` and `layout_selected()` entry points.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Nuke Python API | Nuke 11+ | Node creation, Group context management | Runtime environment; no alternative |
| PySide6 | Nuke-bundled | Dialog UI | Already used by `node_layout_prefs_dialog.py` |
| json (stdlib) | Python 3 stdlib | Prefs persistence | Already used by `node_layout_prefs.py` |
| unittest (stdlib) | Python 3 stdlib | Test framework | Already used; pytest not installed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ast (stdlib) | Python 3 stdlib | Source inspection for tests | When behavioral testing requires Nuke runtime not available in CI |
| importlib.util (stdlib) | Python 3 stdlib | Load modules from absolute paths | When test file uses hardcoded paths different from sys.path |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `with current_group:` | `group.begin()` / `group.end()` | Both verified to work; `with` is preferred for exception safety — `end()` called even on exception |
| `group.nodes()` | `nuke.allNodes()` | `allNodes()` is documented as context-aware but can misbehave when invoked from non-DAG contexts (e.g., script editor); `group.nodes()` is explicit and unambiguous |

## Architecture Patterns

### Recommended Project Structure
```
node_layout/
├── node_layout_prefs.py      # DEFAULTS dict — add 3 new keys here
├── node_layout_prefs_dialog.py  # _build_ui, _populate_from_prefs, _on_accept — update all three
├── node_layout.py            # _subtree_margin callers + entry points — update H-axis reads + group wrap
├── menu.py                   # Verify CMD-01 names (read-only this phase)
└── tests/
    ├── test_node_layout_prefs.py     # Add tests for 3 new default keys
    ├── test_prefs_integration.py     # Add H-axis pref integration tests
    └── test_group_context.py         # New: AST tests for group context wrapping
```

### Pattern 1: Extending DEFAULTS with New Pref Keys

**What:** Add three keys to the `DEFAULTS` dict in `node_layout_prefs.py`. The `_load()` method already uses `{**DEFAULTS, **loaded}`, so new keys appear automatically for fresh installs and for users whose existing file lacks the new keys.

**When to use:** Any time a new configurable value is added.

```python
# Source: /workspace/node_layout_prefs.py (existing pattern)
DEFAULTS = {
    "base_subtree_margin": 300,       # vertical baseline (unchanged role)
    "horizontal_subtree_gap": 150,    # NEW: H-axis subtree-to-subtree gap (proposed default)
    "horizontal_mask_gap": 50,        # NEW: H-axis mask input gap (proposed default)
    "dot_font_reference_size": 20,    # NEW: stub for Phase 8 use (proposed default)
    "compact_multiplier": 0.6,
    "normal_multiplier": 1.0,
    "loose_multiplier": 1.5,
    "loose_gap_multiplier": 8.0,      # PREFS-04 rebalancing — reduce from 12.0 for less height
    "mask_input_ratio": 0.333,
    "scaling_reference_count": 150,
}
```

Note: exact default values for new keys and for `loose_gap_multiplier` rebalancing are Claude's discretion per CONTEXT.md. The values above are proposals to be validated at UAT.

### Pattern 2: Dialog Section Headers with Bold QLabel

**What:** Insert a bold `QLabel` as a full-span row in a `QFormLayout` to create a section header. Use `addRow(label_widget)` with no field widget, or insert the label into the outer `QVBoxLayout` above `addLayout(form_layout)`.

**When to use:** Grouping form rows visually without the heavy chrome of `QGroupBox`.

```python
# Source: PySide6 QFormLayout docs (qt.io/qtforpython-6)
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QFont

def _make_section_header(text):
    label = QLabel(text)
    font = label.font()
    font.setBold(True)
    label.setFont(font)
    return label

# In _build_ui():
form_layout.addRow(_make_section_header("Spacing"))
form_layout.addRow("Horizontal Subtree Gap (px):", self.horizontal_subtree_gap_edit)
form_layout.addRow("Horizontal Mask Gap (px):", self.horizontal_mask_gap_edit)
form_layout.addRow("Base Subtree Margin (px):", self.base_subtree_margin_edit)
form_layout.addRow("Mask Input Ratio:", self.mask_input_ratio_edit)

form_layout.addRow(_make_section_header("Scheme Multipliers"))
# ... multiplier fields ...

form_layout.addRow(_make_section_header("Advanced"))
form_layout.addRow("Dot Font Reference Size (px):", self.dot_font_reference_size_edit)
form_layout.addRow("Scaling Reference Count:", self.scaling_reference_count_edit)
```

The single-argument `addRow(widget)` form spans both label and field columns, making it suitable for section dividers.

### Pattern 3: Group Context Detection and Wrapping

**What:** At layout entry points, capture `nuke.thisGroup()` before any operations. If it differs from `nuke.root()`, use it as a context manager to ensure all node creation happens inside the Group.

**When to use:** Any time `nuke.nodes.*()` or `nuke.createNode()` must be scoped to the active DAG context.

```python
# Source: Foundry Nuke 14.0 Python API Reference + STATE.md confirmed pattern
# In layout_upstream() and layout_selected():

import nuke

def layout_upstream(scheme_multiplier=None):
    global _TOOLBAR_FOLDER_MAP
    _TOOLBAR_FOLDER_MAP = None
    _clear_color_cache()

    current_group = nuke.thisGroup()  # capture before any operations
    root = nuke.selectedNode()        # selectedNode() in context of current_group

    nuke.Undo.name("Layout Upstream")
    nuke.Undo.begin()
    try:
        with current_group:
            # All nuke.nodes.Dot() calls inside this block go into current_group
            original_subtree_nodes = collect_subtree_nodes(root)
            bbox_before = compute_node_bounding_box(original_subtree_nodes)
            node_count = len(collect_subtree_nodes(root))
            insert_dot_nodes(root)
            memo = {}
            snap_threshold = get_dag_snap_threshold()
            compute_dims(root, memo, snap_threshold, node_count, scheme_multiplier=scheme_multiplier)
            place_subtree(root, root.xpos(), root.ypos(), memo, snap_threshold, node_count, scheme_multiplier=scheme_multiplier)
            final_subtree_nodes = collect_subtree_nodes(root)
            final_subtree_node_ids = {id(n) for n in final_subtree_nodes}
            bbox_after = compute_node_bounding_box(final_subtree_nodes)
            if bbox_before is not None and bbox_after is not None:
                push_nodes_to_make_room(final_subtree_node_ids, bbox_before, bbox_after, current_group)
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()
```

Note that `nuke.thisGroup()` returns the root node when called at top-level (not inside a Group DAG), so `with current_group:` is safe to use unconditionally — it is a no-op when already at root context.

### Pattern 4: Scoping push_nodes_to_make_room to Group

**What:** Pass the current group into `push_nodes_to_make_room()` so it can call `current_group.nodes()` instead of `nuke.allNodes()`.

```python
# Current signature (needs update):
def push_nodes_to_make_room(subtree_node_ids, bbox_before, bbox_after):
    ...
    for node in nuke.allNodes():   # BUG: may return root-level nodes when inside group

# Updated signature:
def push_nodes_to_make_room(subtree_node_ids, bbox_before, bbox_after, current_group=None):
    ...
    all_dag_nodes = current_group.nodes() if current_group is not None else nuke.allNodes()
    for node in all_dag_nodes:
        ...
```

Alternatively, since `nuke.allNodes()` is documented as context-aware (uses "current group"), wrapping the call inside `with current_group:` at the entry point may be sufficient. The explicit `group.nodes()` approach is preferred for clarity and to avoid reliance on implicit context state.

### Pattern 5: Reading New H-axis Prefs in the Engine

**What:** Replace the `normal_multiplier`-based `_subtree_margin()` call for horizontal margins with a direct pref read of `horizontal_subtree_gap` or `horizontal_mask_gap`.

**Current code (in `compute_dims` and `place_subtree`):**
```python
# Both compute_dims() and place_subtree() do this for horizontal margins:
normal_multiplier = node_layout_prefs.prefs_singleton.get("normal_multiplier")
side_margins_h = [_subtree_margin(node, slot, node_count, mode_multiplier=normal_multiplier) for slot, _ in input_slot_pairs]
```

**Updated approach:**
```python
# Direct pref read for H-axis — no scaling formula, just the raw pref value
def _horizontal_margin(node, slot):
    """Return the horizontal gap (px) for the given input slot."""
    current_prefs = node_layout_prefs.prefs_singleton
    if _is_mask_input(node, slot):
        return current_prefs.get("horizontal_mask_gap")
    return current_prefs.get("horizontal_subtree_gap")

# In compute_dims() and place_subtree():
side_margins_h = [_horizontal_margin(node, slot) for slot, _ in input_slot_pairs]
```

This removes the sqrt-scaling from the H-axis (H-axis is now an absolute pixel value), which matches the user decision that `horizontal_subtree_gap` and `horizontal_mask_gap` are "absolute pixel values, independent of each other".

Also affects `layout_selected()`'s `horizontal_clearance` calculation — it currently uses `base_subtree_margin * normal_multiplier * sqrt(...)`. This should be updated to use `horizontal_subtree_gap` directly (no scaling formula).

### Anti-Patterns to Avoid

- **Adding QGroupBox frames:** Decided against; use bold QLabel separators only.
- **Migration logic for old prefs:** Decided against; no migration — test environment starts fresh. Do not add version bumps.
- **Calling `_subtree_margin()` for H-axis:** The new H-axis values are absolute, not scaled by `_subtree_margin()`'s sqrt formula. Create `_horizontal_margin()` or read prefs directly.
- **Checking `nuke.thisGroup() != nuke.root()` to conditionally wrap:** Unnecessary. `with current_group:` is safe to call at root level (it is a no-op). Always wrap.
- **Using `nuke.allNodes()` without explicit group scoping:** Even if context-aware by documentation, it is unreliable when code is called from non-DAG contexts (e.g., script editor). Pass and use `group.nodes()` explicitly.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Group context switching | Custom nuke context stack | `with group:` (calls `group.begin()`/`group.end()`) | Nuke API provides this; custom stacks won't handle exceptions correctly |
| Bold section labels | Custom paint or stylesheet hack | `QLabel` + `font.setBold(True)` | Standard Qt pattern; lightweight |
| Prefs migration | Version-key detection + migration logic | Update DEFAULTS; advise clearing file in test instructions | Decided out of scope for testing phase |

**Key insight:** The Nuke Group context mechanism is simple and well-documented. There is no need for custom context-tracking state.

## Common Pitfalls

### Pitfall 1: `_load()` Merge Direction — Existing File Wins Over DEFAULTS

**What goes wrong:** The existing `_load()` method does `{**DEFAULTS, **loaded}`, which means keys from the saved file **override** DEFAULTS. If a user's existing prefs file has old values, the new DEFAULTS for `base_subtree_margin` or `loose_gap_multiplier` will not take effect — the old saved value wins.

**Why it happens:** Standard merge-over pattern is correct for forward compatibility but wrong for rebalancing purposes when you want everyone on the new defaults.

**How to avoid:** CONTEXT.md decision is explicit: "Existing prefs files are discarded / ignored — we're in a testing phase." Document in test instructions that testers must delete `~/.nuke/node_layout_prefs.json` before testing PREFS-04. No code change needed.

**Warning signs:** PREFS-04 UAT reports no visible spacing change — likely caused by stale prefs file.

### Pitfall 2: `nuke.thisGroup()` Called After Operations

**What goes wrong:** If `nuke.thisGroup()` is called after `nuke.selectedNode()` or other calls that may change context, you may get the wrong group.

**Why it happens:** Order sensitivity of Nuke's Python context tracking.

**How to avoid:** Call `current_group = nuke.thisGroup()` as the very first line of `layout_upstream()` and `layout_selected()`, before any other Nuke API calls. STATE.md already documents this: "capture current_group at entry point".

**Warning signs:** Dots appear at root level despite the fix; or wrong group's nodes are pushed.

### Pitfall 3: `with group:` Exception Safety vs `group.begin()`/`group.end()`

**What goes wrong:** If `group.begin()` is used without a corresponding `group.end()` in an exception handler, Nuke's group context is left in a bad state.

**Why it happens:** The explicit `begin()`/`end()` pattern requires manual cleanup; `with group:` handles it automatically via `__exit__`.

**How to avoid:** Use `with current_group:` rather than `group.begin()`/`group.end()`. The `with` form's `__exit__` calls `end()` even when an exception is raised.

**Warning signs:** Subsequent node operations after a layout error all go into the wrong context.

### Pitfall 4: `nuke.Undo` Scope Relative to Group Context

**What goes wrong:** `nuke.Undo.begin()` / `nuke.Undo.end()` may need to be inside or outside the `with current_group:` block. Wrapping undo outside the group context is correct — undo applies to the script-level operation regardless of which Group is active.

**Why it happens:** Undo is script-level, not group-level.

**How to avoid:** Keep the undo begin/end outside (or at the same level as) the `with current_group:` block — same structure as current code. Wrap only the node-creation and placement calls inside `with current_group:`.

### Pitfall 5: `side_margins_h` Tests Will Break

**What goes wrong:** The existing `TestHorizontalOnlyScheme` tests in `test_prefs_integration.py` verify that `side_margins_h` uses `normal_multiplier`. After Phase 6, `side_margins_h` reads `horizontal_subtree_gap`/`horizontal_mask_gap` directly. Tests will fail if not updated.

**Why it happens:** Tests were written against the current H-axis implementation.

**How to avoid:** Update `test_prefs_integration.py` — specifically `TestHorizontalOnlyScheme` — to reflect the new H-axis pref reads. The behavioral contract changes: H-axis margins are now absolute pixel values, not scaled by multipliers.

**Warning signs:** Test suite shows failures in `TestHorizontalOnlyScheme` after the engine change.

### Pitfall 6: `horizontal_clearance` in `layout_selected()` Uses Old Formula

**What goes wrong:** `layout_selected()` computes `horizontal_clearance` using `base_subtree_margin * normal_multiplier * sqrt(node_count) / sqrt(scaling_reference_count)`. After Phase 6, this should use `horizontal_subtree_gap` directly (no scaling).

**Why it happens:** This calculation was separate from `side_margins_h` and may be missed during the H-axis migration.

**How to avoid:** Search for `horizontal_clearance` in `node_layout.py` and update it to read `horizontal_subtree_gap` directly. Add an AST test that verifies `horizontal_clearance` does not reference `base_subtree_margin`.

## Code Examples

### Adding a New Pref Key (Minimal Change Pattern)

```python
# Source: /workspace/node_layout_prefs.py — extend DEFAULTS only
DEFAULTS = {
    "base_subtree_margin": 300,
    "horizontal_subtree_gap": 150,    # new
    "horizontal_mask_gap": 50,        # new
    "dot_font_reference_size": 20,    # new stub
    # ... existing keys unchanged ...
}
# No change to _load(), get(), set(), or save() — they handle new keys automatically.
```

### Dialog: Adding a Row for a New Int Pref (Full Pattern)

```python
# Source: /workspace/node_layout_prefs_dialog.py — three-method update

# In _build_ui():
self.horizontal_subtree_gap_edit = QLineEdit()
form_layout.addRow("Horizontal Subtree Gap (px):", self.horizontal_subtree_gap_edit)

# In _populate_from_prefs():
self.horizontal_subtree_gap_edit.setText(str(prefs_instance.get("horizontal_subtree_gap")))

# In _on_accept():
horizontal_subtree_gap_value = int(self.horizontal_subtree_gap_edit.text())
# ... validate > 0 ...
prefs_instance.set("horizontal_subtree_gap", horizontal_subtree_gap_value)
```

### AST Test for Group Context (New Test File Pattern)

```python
# Source: established pattern in /workspace/tests/test_node_layout_bug02.py
import ast

def _get_function_source(source, function_name):
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return ast.get_source_segment(source, node)
    return None

def test_layout_upstream_captures_current_group():
    """layout_upstream() must call nuke.thisGroup() and use it as context."""
    with open(NODE_LAYOUT_PATH) as f:
        source = f.read()
    func_source = _get_function_source(source, "layout_upstream")
    assert "nuke.thisGroup()" in func_source
    assert "with current_group:" in func_source or "current_group.begin()" in func_source
```

### Nuke Group Nodes Query for Push Logic

```python
# Source: Foundry Nuke 14.0 Python API Reference (nuke.Group.nodes())
# Updated push_nodes_to_make_room signature:
def push_nodes_to_make_room(subtree_node_ids, bbox_before, bbox_after, current_group=None):
    all_dag_nodes = current_group.nodes() if current_group is not None else nuke.allNodes()
    for node in all_dag_nodes:
        ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Horizontal margin from `_subtree_margin()` (sqrt-scaled) | Direct pref read: `horizontal_subtree_gap` or `horizontal_mask_gap` (absolute px) | Phase 6 | H-axis and V-axis are now fully decoupled; H never scales with node count |
| Flat prefs dialog (7 fields, no sections) | Sectioned dialog with 3 bold-label groups (10 fields total) | Phase 6 | Easier UX for configuring the separate H/V/Advanced prefs |
| `nuke.allNodes()` in push logic (root-leaking) | `group.nodes()` scoped to current DAG context | Phase 6 | Group-safety fix for LAYOUT-05 |
| No group context wrapping at entry points | `with current_group:` wrapping all node creation | Phase 6 | Fixes LAYOUT-04 silent root-level Dot creation |

**Deprecated/outdated:**
- `_subtree_margin()` used for H-axis: still present but callers for H now use direct pref reads. The function itself stays (still used for V-axis).

## Open Questions

1. **Does `nuke.thisGroup()` return `nuke.root()` or something else at top level?**
   - What we know: Foundry docs confirm `thisGroup()` returns "the current context Group node". Community usage shows it is used to switch on Group context.
   - What's unclear: Whether calling `with nuke.root():` (the return value at top level) is a true no-op or silently changes something.
   - Recommendation: During implementation, verify empirically in Nuke. If `thisGroup()` at root returns the root node and `with root:` is a no-op, use unconditional wrapping. If it causes issues, add `if current_group is not nuke.root():` guard.

2. **`nuke.Undo` and `with group:` interaction**
   - What we know: Undo is script-level; the `with group:` is Python-level context switching.
   - What's unclear: Whether Nuke's undo mechanism tracks which group context a node was created in, and whether begin/end must be called in a specific order relative to the context manager.
   - Recommendation: Keep `nuke.Undo.begin()` before the `with current_group:` block, and `nuke.Undo.end()` after, matching the current structure.

3. **Exact default values for PREFS-04 rebalancing**
   - What we know: Goal is "less tall AND wider". Current `loose_gap_multiplier=12.0` and `base_subtree_margin=300` produce tall layouts.
   - What's unclear: What pixel values feel right without UAT.
   - Recommendation: Proposed starting values (tune at UAT): `base_subtree_margin=200`, `loose_gap_multiplier=8.0`, `horizontal_subtree_gap=150`, `horizontal_mask_gap=50`. These are Claude's discretion per CONTEXT.md.

## Sources

### Primary (HIGH confidence)
- Foundry Nuke 14.0 Python API Reference - `nuke.Group` - verified `begin()`, `end()`, `nodes()`, `with` statement support via `__enter__`/`__exit__`
- Foundry Nuke 14.0 Python API Reference - `nuke.allNodes` - verified "current group is used when group parameter omitted"
- `/workspace/node_layout_prefs.py` - DEFAULTS dict structure and `_load()` merge pattern
- `/workspace/node_layout_prefs_dialog.py` - three-method update pattern for dialog
- `/workspace/node_layout.py` - `_subtree_margin()`, `side_margins_h`/`side_margins_v` split, `push_nodes_to_make_room()`, entry point structure
- `/workspace/menu.py` - CMD-01 verification: names already correct
- `/workspace/.planning/STATE.md` - accumulated decision: "Group context: capture current_group at entry point; wrap Dot creation with `with current_group:`"

### Secondary (MEDIUM confidence)
- Qt for Python (PySide6) QFormLayout docs (`doc.qt.io`) - `addRow(widget)` single-argument form for full-span section headers
- Foundry Nuke Python mailing list discussions - confirmed `with group:` pattern for context management
- Search result summary of `nuke.thisGroup()` Nuke 14.0 docs - returns current context Group

### Tertiary (LOW confidence)
- Inferred from nuke.allNodes() documentation: behavior inside group context is "context-aware" but reliability varies by invocation context. Using explicit `group.nodes()` is safer — this is LOW confidence on the implied reliability of the implicit behavior.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use; no new dependencies
- Architecture patterns (prefs, dialog): HIGH — established pattern in existing codebase, verified by reading all three files
- Architecture patterns (Group fix): HIGH — `with group:` confirmed by official Foundry docs and STATE.md decision
- `_horizontal_margin()` approach for H-axis: HIGH — directly from CONTEXT.md decisions (absolute px, no scaling)
- Pitfalls: HIGH for prefs-file merge direction and test breakage; MEDIUM for Nuke undo/group interaction (not empirically verified)
- Default values for PREFS-04: LOW — proposals only, UAT required

**Research date:** 2026-03-07
**Valid until:** 2026-04-07 (stable codebase; Nuke API does not change between minor versions)

# Architecture Patterns

**Project:** node_layout v1.1 — Layout Engine & State
**Researched:** 2026-03-05

---

## Existing Architecture Summary

The codebase is organized as a single module (`node_layout.py`) containing all layout logic, a utility module (`util.py`) for DAG helpers, a prefs singleton (`node_layout_prefs.py`), a PySide6 dialog (`node_layout_prefs_dialog.py`), and menu registration (`menu.py`).

Core call chain for a layout operation:

```
layout_upstream() / layout_selected()
  → insert_dot_nodes()
  → compute_dims()           (recursive, memoized)
  → place_subtree()          (recursive, uses memo)
  → push_nodes_to_make_room()
```

Scale operations are a separate, simpler call chain:

```
shrink_selected() / expand_selected()
  → _scale_selected_nodes(scale_factor)

shrink_upstream() / expand_upstream()
  → _scale_upstream_nodes(scale_factor)
```

The `scheme_multiplier=None` sentinel propagates through the entire layout call chain and is resolved at the first point of use. `_TOOLBAR_FOLDER_MAP` and `_COLOR_LOOKUP_CACHE` are module-level globals cleared at the start of every layout operation.

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `node_layout.py` | Layout algorithm, scale operations, public entry points | `node_layout_prefs`, Nuke API |
| `node_layout_prefs.py` | JSON-backed singleton prefs, defaults | Nothing (pure data) |
| `node_layout_prefs_dialog.py` | PySide6 dialog for editing prefs | `node_layout_prefs` singleton |
| `menu.py` | Nuke menu wiring; maps commands to entry points | `node_layout`, `node_layout_prefs_dialog`, `make_room`, `util` |
| `util.py` | Standalone DAG helpers (`sort_by_filename`, `select_upstream_ignoring_hidden`) | Nuke API |
| `make_room.py` | Manual push-room utility (not the layout push logic) | Nuke API |

---

## New Feature Integration Analysis

### Feature 1: Per-Node State Storage

**What it is:** A hidden "Node Layout" tab with knobs `layout_mode`, `scheme`, and `scale_factor` written to every node touched by a layout operation; read back at the next layout to replay prior decisions.

**Integration points:**

- **New helper: `_write_node_state(node, layout_mode, scheme, scale_factor)`** — adds the hidden tab if absent, then sets the three knob values. Called at the end of `place_subtree()` for every positioned node. The tab (`node_layout_tab`) already exists on diamond-resolution Dot nodes; the helper must be idempotent (check `node.knob('node_layout_tab')` before adding).
- **New helper: `_read_node_state(node)`** — returns a dict or namedtuple with `layout_mode`, `scheme`, `scale_factor`, or `None` if knobs are absent. Called at layout entry points to check if a node has prior state.
- **Modified: `layout_upstream()` and `layout_selected()`** — after resolving `scheme_multiplier`, check the selected root node's state via `_read_node_state()`. If prior state is found, it overrides the caller-supplied defaults before the layout operation runs. Write state to subtree nodes after placement.
- **No changes to `compute_dims()` or `place_subtree()` signatures** — state is read/written at entry-point level, not propagated recursively.

**Knob names:** `node_layout_tab` (Tab_Knob), `node_layout_mode` (String_Knob or Enumeration_Knob), `node_layout_scheme` (String_Knob), `node_layout_scale_factor` (Double_Knob).

**Dependency:** Knob naming must be consistent with the existing `node_layout_diamond_dot` marker pattern. Tab name `node_layout_tab` already exists for Dot markers — the helper must tolerate the tab already being present.

---

### Feature 2: Horizontal B-Spine Layout

**What it is:** An alternative traversal mode where the primary B-input spine runs left-to-right (increasing X), and side-input subtrees continue to grow upward (decreasing Y). This is fundamentally a different axis orientation for the primary input chain.

**Integration points:**

- **New entry points: `layout_upstream_horizontal()` and `layout_selected_horizontal()`** — mirror the normal entry points but pass `layout_mode="horizontal"` (which triggers horizontal compute/place logic).
- **Modified: `compute_dims()`** — needs a `layout_mode` parameter (default `"vertical"`, existing behavior). In `"horizontal"` mode the primary input (slot 0) sits to the left of the consumer rather than above it; side inputs still grow upward. Width and height formulas invert their role for the primary chain:
  - Primary chain W accumulates horizontally (each step adds width + horizontal gap).
  - Primary chain H is the maximum height of any node in the spine.
  - Side inputs (slot 1+) continue to extend upward, adding to H.
- **Modified: `place_subtree()`** — same `layout_mode` parameter. In horizontal mode, slot 0 is positioned to the left (x decreases), while slots 1+ still staircase upward. The X centering logic for side-input Dots needs adjustment because the primary axis is no longer vertical.
- **New prefs key: `horizontal_gap`** (int, pixels) — the gap between primary-spine nodes in horizontal mode. Added to `DEFAULTS` in `node_layout_prefs.py` and exposed in the prefs dialog.
- **Node state:** `layout_mode` stored per-node (see Feature 1) allows a subsequent plain `layout_upstream()` call to detect and replay horizontal mode automatically.

**Key constraint:** Horizontal mode does not change how `insert_dot_nodes()` works — diamond resolution is topology-based, not orientation-based. No changes needed there.

**`compute_dims()` / `place_subtree()` signature change:**
```python
# Before
compute_dims(node, memo, snap_threshold, node_count, node_filter=None, scheme_multiplier=None)

# After
compute_dims(node, memo, snap_threshold, node_count, node_filter=None,
             scheme_multiplier=None, layout_mode="vertical")
```
The new parameter propagates through all recursive calls exactly as `scheme_multiplier` does.

---

### Feature 3: Multi-Input Fan Alignment

**What it is:** When a node has 2+ non-mask side inputs, all side-input subtree roots are placed at the same Y coordinate (fanned horizontally). Mask inputs flip to the left of the consumer when 2+ non-mask side inputs are present.

**Integration points:**

- **Modified: `place_subtree()`** — the Y staircase logic for side inputs is conditionally replaced with a flat-Y fan when `non_mask_side_count >= 2`. Instead of staircase `bottom_y[i]` assignment, all non-mask side roots share `y_for_fan = y - max(gap_closest, side_margins_v[last_non_mask])`. The existing staircase continues to apply to the mask inputs.
- **Modified: `compute_dims()`** — when fan mode activates (non-mask side count >= 2), the H formula changes: the total height contributed by side inputs is the maximum single side-subtree height (not the sum), because they share the same Y band. The W formula grows to accommodate all side subtrees spread rightward.
- **Modified: `_reorder_inputs_mask_last()` → also handles left-flip:** When 2+ non-mask side inputs are present, mask inputs are placed to the *left* of the consumer rather than the right. This is an X-axis placement change in `place_subtree()`, not a reordering change — `_reorder_inputs_mask_last()` itself stays logically the same (non-mask before mask), but the X assignment in `place_subtree()` sends mask inputs leftward.
- **New helper: `_count_non_mask_side_inputs(input_slot_pairs, node)`** — counts slots > 0 (or all slots in `all_side` mode) that are not mask inputs. Used by both `compute_dims()` and `place_subtree()` to branch into fan mode.

**Interdependency with Feature 2 (Horizontal mode):** Fan alignment only applies in vertical mode. In horizontal mode the primary spine goes left and side inputs continue to staircase upward — fan alignment is not meaningful there.

---

### Feature 4: Shrink/Expand H/V/Both Axis Modes

**What it is:** The existing shrink/expand operations currently scale both X and Y offsets uniformly. New axis-specific modes scale only the horizontal (`H`) component, only the vertical (`V`) component, or both (`Both`, existing behavior).

**Integration points:**

- **Modified: `_scale_selected_nodes(scale_factor)`** — add `axis="both"` parameter. When `axis="h"`, `new_dy = dy` (no Y change); when `axis="v"`, `new_dx = dx` (no X change); when `axis="both"`, existing behavior. The snap_min floor guard applies only to the axis being scaled.
- **Modified: `_scale_upstream_nodes(scale_factor)`** — same `axis="both"` parameter and same conditional logic (no snap_min floor for upstream, unchanged).
- **New public entry points (6 new functions):**
  - `shrink_selected_h()`, `expand_selected_h()`
  - `shrink_selected_v()`, `expand_selected_v()`
  - `shrink_upstream_h()`, `expand_upstream_h()`
  - `shrink_upstream_v()`, `expand_upstream_v()`
  Each wraps the corresponding `_scale_*` call with the axis argument. The existing `shrink_selected()` / `expand_selected()` / `shrink_upstream()` / `expand_upstream()` remain unchanged as the `Both` default.
- **Modified: `menu.py`** — add 8 new menu entries for the H/V variants. Modifier-key variants (e.g., `Ctrl+Alt+,`) are recommended for discovery without cluttering the menu with extra separators.

---

### Feature 5: Expand Push-Away

**What it is:** After a shrink/expand operation on selected or upstream nodes, call `push_nodes_to_make_room()` to push non-selected surrounding nodes out of the way if the scaled group grew.

**Integration points:**

- **Modified: `expand_selected()`** — capture `bbox_before` from `compute_node_bounding_box(selected_nodes)` before scaling, then `bbox_after` after scaling. Call `push_nodes_to_make_room(selected_node_ids, bbox_before, bbox_after)`. This matches exactly the pattern already used in `layout_upstream()` and `layout_selected()`.
- **Modified: `expand_upstream()`** — same: capture before/after bounding boxes and call `push_nodes_to_make_room()`.
- **No change for shrink variants:** Shrink makes nodes closer together; surrounding nodes cannot be in conflict unless they were already overlapping before the shrink. Push-away is only meaningful for expand.
- **H/V axis modes (Feature 4) interact here:** The existing `push_nodes_to_make_room()` uses `grew_up` (Y min decreased) and `grew_right` (X max increased) independently. This already handles axis-only expansions correctly — a horizontal-only expand will only push right, and a vertical-only expand will only push up. No changes to `push_nodes_to_make_room()` are needed.
- **collect_subtree_nodes()** is already available for the upstream case — `upstream_nodes` is the same list `_scale_upstream_nodes` iterates over.

**Implementation note:** `expand_selected()` currently does not have access to the selected node list outside `_scale_selected_nodes()`. The bounding box capture must be done in the public `expand_selected()` wrapper, which already calls `nuke.selectedNodes()` through the undo guard. Refactor: move `nuke.selectedNodes()` call into the wrapper and pass the list down, or duplicate the bounding box calls in the wrapper. The former (passing list down) is cleaner.

---

### Feature 6: Dot Font Size → Subtree Margin

**What it is:** When a Dot node sits at the root of a subtree (i.e., as the `node` argument to `_subtree_margin()`), inspect its font size knob to scale the margin — a large font Dot signals a section boundary and should get more breathing room.

**Integration points:**

- **Modified: `_subtree_margin(node, slot, node_count, mode_multiplier=None)`** — after computing `effective_margin`, check if `node.Class() == 'Dot'` and whether a font-size knob is accessible. Scale `effective_margin` by a font ratio (e.g., `dot_font_size / reference_dot_font_size`). Reference font size should be a pref or a constant.
- **New pref key: `dot_font_reference_size`** — the "normal" Dot font size (Nuke default is 100). Stored in `DEFAULTS` in `node_layout_prefs.py`. The margin scales linearly: a 200-point font produces 2× the margin of a 100-point font.
- **Nuke knob access:** Dot nodes expose font size via `node['note_font_size'].value()` (String_Knob in some Nuke versions) or `node['font_size']`. This must be wrapped in `try/except (KeyError, AttributeError)` to be safe across Nuke versions, falling back to `dot_font_reference_size`.
- **Scope:** `_subtree_margin()` is called from `compute_dims()` and `place_subtree()`. The Dot font scaling only activates when the `node` argument to `_subtree_margin()` is a Dot — this is the case when a Dot sits at a subtree connection point. The `slot` argument is not affected.

---

## Data Flow Changes

### Layout Entry Points — State Read Path (Feature 1)

```
layout_upstream() / layout_selected()
  → _read_node_state(root)          # NEW: check knobs on root node
      if state found: override scheme_multiplier, layout_mode
  → [existing layout chain]
  → place_subtree() / compute_dims() now receive layout_mode param  # NEW
  → for each placed node: _write_node_state(node, ...)              # NEW
```

### Scale Entry Points — Expand Push Path (Feature 5)

```
expand_selected()
  selected_nodes = nuke.selectedNodes()          # moved to wrapper
  bbox_before = compute_node_bounding_box(...)   # NEW
  _scale_selected_nodes(factor, axis=...)        # axis param NEW
  bbox_after = compute_node_bounding_box(...)    # NEW
  push_nodes_to_make_room(ids, bbox_before, bbox_after)  # NEW call

expand_upstream()
  upstream_nodes = collect_subtree_nodes(root)   # NEW: collect for bbox
  bbox_before = compute_node_bounding_box(...)   # NEW
  _scale_upstream_nodes(factor, axis=...)
  bbox_after = compute_node_bounding_box(...)    # NEW
  push_nodes_to_make_room(ids, bbox_before, bbox_after)  # NEW call
```

### Subtree Margin — Font Size Path (Feature 6)

```
_subtree_margin(node, slot, node_count, mode_multiplier)
  → compute effective_margin (existing)
  → if node.Class() == 'Dot':                   # NEW branch
        font_size = node['note_font_size'].value()  (try/except)
        effective_margin *= font_size / dot_font_reference_size
  → if mask input: apply ratio (existing)
  → return effective_margin
```

---

## Suggested Build Order

Dependencies between features determine the order. Features that extend the same functions must be sequenced so each integration is stable before the next builds on it.

### Phase 1: Prefs Groundwork (no algorithm changes)

**Why first:** Both horizontal spacing (Feature 2 needs `horizontal_gap`) and Dot font scaling (Feature 6 needs `dot_font_reference_size`) require new pref keys. Adding them to `DEFAULTS` and the prefs dialog first gives a clean foundation and keeps the prefs module stable for later phases.

- Add `horizontal_gap` (int, e.g., 120) to `DEFAULTS` in `node_layout_prefs.py`
- Add `dot_font_reference_size` (int, e.g., 100) to `DEFAULTS`
- Add corresponding fields to `node_layout_prefs_dialog.py` form
- No behavioral changes; existing tests pass unchanged

### Phase 2: Per-Node State Storage (Feature 1)

**Why second:** State storage is independent of all algorithm changes. Building it early means the horizontal layout (Feature 2) can store its `layout_mode` immediately upon implementation. No feature can replay prior decisions until this is in place.

- Implement `_write_node_state()` and `_read_node_state()` in `node_layout.py`
- Integrate read into `layout_upstream()` and `layout_selected()` entry points
- Integrate write after placement in the entry points (post-`place_subtree()` walk over subtree nodes)
- Verify idempotency: running layout twice does not duplicate tabs or knobs

### Phase 3: Dot Font Size → Subtree Margin (Feature 6)

**Why third:** This is a contained, low-risk change to `_subtree_margin()` only. It has no dependencies on the axis changes coming in later phases, and validating it in isolation is straightforward. Must come before horizontal layout because horizontal mode will call `_subtree_margin()` via the same path.

- Add Dot font size inspection branch to `_subtree_margin()` in `node_layout.py`
- Wrap knob access in `try/except (KeyError, AttributeError)` with fallback to pref default

### Phase 4: Multi-Input Fan Alignment (Feature 3)

**Why fourth:** Fan alignment modifies `compute_dims()` and `place_subtree()` — the same two functions that horizontal mode will modify in Phase 5. Building fan alignment first in vertical mode, with tests, establishes a stable baseline for the much larger horizontal mode change. Fan alignment is also independent of the scale/expand features.

- Add `_count_non_mask_side_inputs()` helper
- Modify `compute_dims()` to use fan height formula when non-mask side count >= 2
- Modify `place_subtree()` to fan side roots at same Y and flip mask inputs left
- Verify: existing staircase behavior unchanged when non-mask side count < 2

### Phase 5: Shrink/Expand H/V/Both Axis Modes + Expand Push-Away (Features 4 + 5)

**Why fifth (and combined):** The axis parameter change to `_scale_selected_nodes()` and `_scale_upstream_nodes()` and the push-away addition both happen in the `expand_*()` / `shrink_*()` wrappers. Doing them together avoids two refactor passes over the same wrappers. Push-away requires only the existing `push_nodes_to_make_room()` / `compute_node_bounding_box()` functions, which are already stable.

- Add `axis` parameter to `_scale_selected_nodes()` and `_scale_upstream_nodes()`
- Refactor `expand_selected()` to collect `selected_nodes` in wrapper; add before/after bbox + push call
- Refactor `expand_upstream()` similarly
- Add 8 new H/V axis entry point functions
- Register new menu entries in `menu.py`

### Phase 6: Horizontal B-Spine Layout (Feature 2)

**Why last:** This is the most invasive change — it adds a `layout_mode` parameter to `compute_dims()` and `place_subtree()`, which propagates through all recursive calls. By this phase, the full test suite covers all other features, providing a regression safety net. The per-node state storage (Phase 2) is already in place to store and replay `layout_mode="horizontal"`.

- Add `layout_mode` parameter to `compute_dims()` and `place_subtree()`
- Implement horizontal W/H formulas in `compute_dims()` for primary spine
- Implement left-placement of slot 0 in `place_subtree()` for horizontal mode
- Add `layout_upstream_horizontal()` and `layout_selected_horizontal()` entry points
- Register new menu entries in `menu.py`
- Verify: all existing vertical-mode tests pass with `layout_mode="vertical"` default

---

## Modified Components Summary

| Component | Changed? | What Changes |
|-----------|----------|-------------|
| `node_layout.py` | YES — heavily | New helpers `_write_node_state`, `_read_node_state`, `_count_non_mask_side_inputs`; modified `_subtree_margin`, `compute_dims`, `place_subtree`, `_scale_selected_nodes`, `_scale_upstream_nodes`, `expand_selected`, `expand_upstream`; new entry points for H/V axis modes and horizontal layout |
| `node_layout_prefs.py` | YES — minor | Two new `DEFAULTS` keys: `horizontal_gap`, `dot_font_reference_size` |
| `node_layout_prefs_dialog.py` | YES — minor | Two new `QLineEdit` fields and corresponding populate/save wiring |
| `menu.py` | YES — moderate | 8 new axis-mode entries + 2 new horizontal layout commands; rename Compact/Loose commands |
| `util.py` | NO | No changes required |
| `make_room.py` | NO | No changes required |

## New Components

No new Python modules are needed. All new code is contained within modifications to existing modules. The only new "components" are helper functions added to `node_layout.py`:

| Function | Location | Purpose |
|----------|----------|---------|
| `_write_node_state(node, layout_mode, scheme, scale_factor)` | `node_layout.py` | Write hidden tab + knobs to a node |
| `_read_node_state(node)` | `node_layout.py` | Read state dict from node knobs; returns `None` if absent |
| `_count_non_mask_side_inputs(input_slot_pairs, node)` | `node_layout.py` | Count non-mask side inputs for fan-mode branching |

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Propagating layout_mode via a global
**What:** Using a module-level `_CURRENT_LAYOUT_MODE` global (analogous to `_TOOLBAR_FOLDER_MAP`) to avoid adding a parameter to `compute_dims()` / `place_subtree()`.
**Why bad:** `layout_selected()` processes multiple roots in a loop; if each root could have a different stored `layout_mode`, a global cannot represent per-root state. Also, globals make the recursive functions harder to test in isolation.
**Instead:** Pass `layout_mode` as an explicit parameter, exactly as `scheme_multiplier` is passed.

### Anti-Pattern 2: Reading node state inside compute_dims() / place_subtree()
**What:** Calling `_read_node_state(node)` recursively inside the traversal to change per-node behavior mid-tree.
**Why bad:** A single layout operation should use one consistent mode/scheme throughout the subtree. Mixing modes within a single recursive pass produces undefined geometry. State is a replay hint, not a per-node override during traversal.
**Instead:** Read state once at the entry point for the root node; apply it to the whole operation.

### Anti-Pattern 3: Adding push-away to shrink operations
**What:** Calling `push_nodes_to_make_room()` after shrink to pull surrounding nodes inward.
**Why bad:** `push_nodes_to_make_room()` only pushes outward (it checks `grew_up` and `grew_right`). Shrink leaves a void; attempting to fill the void by pulling inward requires a completely different spatial algorithm and would silently do nothing with the current implementation.
**Instead:** Only call push-away after expand. Document clearly that shrink does not reclaim surrounding space.

### Anti-Pattern 4: Duplicating the tab knob creation across features
**What:** Feature 1 (state storage) and the existing diamond-resolution Dot code both create a `node_layout_tab` Tab_Knob. If `_write_node_state()` is not written defensively, a node that already has the tab (e.g., a diamond Dot) will raise an exception when the second `addKnob()` is called.
**Instead:** Always check `node.knob('node_layout_tab') is not None` before calling `addKnob()` for the tab. The state knobs (`node_layout_mode`, etc.) need the same guard.

---

## Scalability Considerations

| Concern | Current State | After v1.1 |
|---------|---------------|-----------|
| Knob writes on every layout | Not done today | `_write_node_state()` writes N knobs for every node in subtree — acceptable for DAGs up to ~500 nodes (~1,500 Nuke API calls) |
| Horizontal mode compute_dims complexity | N/A | Same O(n) traversal as vertical; no complexity change |
| Fan alignment Y-band calculation | N/A | O(k) where k = side inputs per node; negligible |
| Push-away after expand | Already used by layout ops | Adding it to expand_selected/expand_upstream adds one O(n) pass over all DAG nodes — same as existing layout ops |

---

## Sources

- Source-level analysis of `node_layout.py`, `util.py`, `node_layout_prefs.py`, `node_layout_prefs_dialog.py`, `menu.py`, `make_room.py` (read directly, 2026-03-05)
- `node_layout/tests/test_scale_nodes.py` — test patterns inform behavioral contracts for modified functions
- `.planning/PROJECT.md` — requirements, key decisions, active feature list
- Nuke DAG coordinate system: positive Y is down (per project CLAUDE.md)

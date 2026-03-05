# Feature Landscape

**Domain:** Nuke DAG auto-layout plugin — v1.1 new features
**Researched:** 2026-03-05
**Milestone context:** Subsequent milestone adding to existing v1.0 plugin

---

## Table Stakes

Features users expect given what the plugin already does. Missing or broken = the new milestone feels incomplete or regressive.

| Feature | Why Expected | Complexity | Dependencies on Existing Code |
|---------|--------------|------------|-------------------------------|
| Spacing rebalance (less vertical, more horizontal) | Current default spacing is too vertical-heavy; users doing re-layout find trees too tall. Horizontal gap preferences are absent from the prefs dialog entirely. | Low | Adds new prefs keys to `node_layout_prefs.py`; new fields in prefs dialog; new constants passed into `compute_dims` / `place_subtree` horizontal margin paths |
| Horizontal prefs for secondary vs mask gaps | Secondary inputs already get a different margin than primary; mask inputs already get a reduced ratio. But both share a single `base_subtree_margin`. Differentiating horizontal gap for mask separately is the natural completion of this system. | Low-Medium | `_subtree_margin()` already has `_is_mask_input()` branching; needs a second pref key and separate computation path for horizontal |
| Rename Compact/Loose commands | Commands are currently named "Compact Layout Upstream" / "Loose Layout Upstream". Tab-menu discoverability in Nuke requires scheme name at end (Nuke's tab-menu search is prefix-based). Users typing "Layout" should see all variants. | Low | Pure `menu.py` rename; no engine changes |
| Expand Selected/Upstream push-away | Expand already scales node positions. When the scaled tree grows beyond its original bounding box, it collides with surrounding nodes. The push logic already exists for layout operations; Expand should reuse it. | Medium | `push_nodes_to_make_room()` exists in `node_layout.py`; `expand_selected()` and `expand_upstream()` need to capture pre/post bounding boxes and call it |
| Group context fix for Dot node creation | When the user runs Layout Upstream while inside a Nuke Group DAG, `nuke.nodes.Dot()` creates nodes in the root context, not the group context. This is a silent correctness bug — wires appear connected but the new Dot lives outside the group. | Medium | `insert_dot_nodes()` and `place_subtree()` both call `nuke.nodes.Dot()`; need `group.begin()` / `group.end()` (or `with group:`) wrapper at the entry points |

---

## Differentiators

Features that meaningfully improve layout quality or user control beyond what the current plugin offers. Not expected by users yet, but high value once available.

| Feature | Value Proposition | Complexity | Dependencies on Existing Code |
|---------|-------------------|------------|-------------------------------|
| Multi-input fan alignment (same Y for 2+ non-mask inputs) | When a node has multiple A-inputs, the current engine places their subtree roots in a staircase pattern. Aligning them all to the same Y makes the compositing structure visually readable at a glance — the fan reads as a true merge point rather than a diagonal tangle. | High | Core change to `place_subtree()` Y staircase logic; `compute_dims()` must measure the fan's total height differently; backward-compat with single-input paths critical |
| Mask side-swap when 2+ non-mask inputs present | Today, mask always goes rightmost. With 2+ non-mask inputs already fanned right, putting mask right as well clusters too many branches. Moving mask to the left (as a negative-X offset from the consumer) removes visual clutter on the right side. The mask-always-right rule was explicitly noted as causing layout problems at 2+ non-mask count. | High | Requires `_reorder_inputs_mask_last()` to reverse for the ≥2 non-mask case; `place_subtree()` X positioning logic needs a left-side placement branch; `compute_dims()` width calculation must account for leftward expansion |
| Per-node state storage (hidden tab on each node) | Stores `layout_mode` (vertical/horizontal), `scheme` (compact/normal/loose), and `scale_factor` per node as hidden knobs. Layout and shrink/expand commands write these; re-layout reads them and honors them. This is what makes "least-surprise re-layout" possible — a node you've already compacted stays compact on next run. | Medium-High | New helper functions: `_ensure_node_layout_tab(node)`, `_read_node_state(node)`, `_write_node_state(node, ...)`; all entry points write state after layout; all entry points read and apply state before computing dims. The existing diamond-dot tab pattern (`node_layout_tab`) provides the exact knob-creation pattern to follow. |
| Horizontal B-spine layout command | The user explicitly identifies a spine of nodes that flows left-to-right rather than top-to-bottom. The command lays out the selected chain left-to-right (root leftmost, input[0] child rightmost), stores `layout_mode=horizontal` in per-node knobs, and normal re-layout replays this orientation automatically. Addresses the niche but real workflow where a compositing operator builds a horizontal processing chain and wants auto-layout to respect it. | High | Requires a new layout traversal branch in `place_subtree()` (or a parallel `place_subtree_horizontal()`) that swaps the X/Y role of inputs; `compute_dims()` needs a horizontal dimension variant; depends on per-node state storage being in place first |
| Shrink/Expand H/V/Both modes | Currently Shrink/Expand scale both axes uniformly. Users sometimes want to compress only vertical spacing (to fit more of the tree on screen) or only horizontal (to tighten a wide fan without squashing height). Separate menu entries + modifier key variants for H-only, V-only, and Both. | Medium | Extends `_scale_selected_nodes()` and `_scale_upstream_nodes()` with an `axes` parameter ('x', 'y', 'both'); new menu entries in `menu.py`; writes axis mode to per-node state if state storage is implemented |
| Dot font size as subtree margin signal | Nuke compositors sometimes increase the font size on a Dot node to visually mark a section boundary in the DAG. Scaling `_subtree_margin()` based on the font size of a Dot at the subtree root lets the compositor's own visual signals drive layout spacing — the bigger the section Dot, the more breathing room the layout gives that branch. | Medium | `_subtree_margin()` must check for Dot node and read `label_size` knob (or equivalent); prefs may need a font-scaling constant |

---

## Anti-Features

Features to explicitly avoid in this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Full Sugiyama / layered-graph layout algorithm | General-purpose DAG layout (Dagre, d3-dag, Graphviz) solves edge crossing minimization via NP-hard layer assignment. The codebase's tree-layout approach is intentionally simpler and faster because Nuke DAGs are trees in practice (diamonds handled via Dot insertion). Replacing the engine would be a full rewrite with no user-visible benefit for the common case. | Keep the existing two-phase (compute_dims + place_subtree) approach; extend it for horizontal mode rather than replacing it |
| Physics-based force layout | Force-directed layouts (Fruchterman-Reingold, spring-embedder) produce non-deterministic results and require iterative convergence. Artists need deterministic, repeatable layout so they can undo and redo reliably. | Keep deterministic recursive tree placement |
| GUI-based layout mode toggle on each node | Adding a visible UI element (checkbox, dropdown) to every node's parameter panel would clutter the node properties and add visual noise to every node in the DAG. | Use hidden knobs on a hidden tab — same pattern as the existing diamond-dot marker. The user doesn't interact with state directly; commands write it silently. |
| Keyboard shortcut customization in prefs | Already explicitly out of scope in v1.0 PROJECT.md. Conflict probability is low; documenting in README is sufficient. | Document taken shortcuts in README |
| Layout for entire DAG (no selection) | Running layout on the full DAG with no selection has unpredictable results on complex scripts with deliberate manual arrangements. The existing "Layout Upstream from selected node" scope is correct — it's opt-in. | Keep the selection-scoped entry points |
| Undo granularity per-node | Each node move being individually undoable was the pre-v1.0 state. v1.0 fixed this by wrapping in Nuke undo groups. All new commands must follow the same try/except/else undo group pattern. | Enforce undo group wrapping on every new entry point |

---

## Feature Dependencies

```
Spacing rebalance
  → adds horizontal pref keys (needed by all spacing paths)
  → Horizontal B-spine layout uses horizontal spacing constants

Per-node state storage
  → required before Horizontal B-spine layout (horizontal mode stored in knobs, replayed by normal layout)
  → required before Shrink/Expand H/V/Both (axis mode stored per-node)
  → required before per-scheme re-layout memory

Multi-input fan alignment
  → mask side-swap is a direct consequence of fan alignment being active (mask goes left when non-mask inputs fill the right side)
  → mask side-swap depends on multi-input fan alignment being implemented first

Expand push-away
  → reuses push_nodes_to_make_room() which exists
  → no dependencies on new features; can be implemented independently

Horizontal B-spine layout
  → depends on per-node state storage (without storage, replayed by normal layout is impossible)
  → depends on spacing rebalance for correct horizontal gap values

Group context fix
  → no dependencies; pure bug fix at entry-point level
  → must be done before or with any feature that adds new nuke.nodes.Dot() calls (horizontal mode, fan alignment)

Shrink/Expand H/V/Both
  → extends existing shrink/expand functions
  → optionally writes to per-node state storage (if state storage ships first)
  → can ship independently of state storage with Both mode as default fallback

Dot font size → subtree margin
  → independent of all other features; purely in _subtree_margin()
  → adds one pref key

Command renames
  → independent of all other features; pure menu.py change
```

---

## UX Considerations by Feature Area

### Horizontal B-spine Layout

**Expected behavior:** The user selects a chain of nodes and invokes "Layout Horizontal". The root node stays fixed; input[0] of each node moves to the right of the consumer (in the current engine, input[0] goes above). The resulting chain reads left-to-right. Side inputs (if any) on a horizontal node go above or below, not left.

**Edge cases:**
- A horizontal node whose input[0] is also horizontal: the chain continues rightward
- A horizontal node whose input[0] feeds a vertical subtree: the horizontal layout terminates and the vertical subtree is laid out normally above/below the junction point
- Diamond patterns on horizontal chains: the same Dot-insertion strategy applies; Dots get laid out horizontally inline
- Re-layout (normal Layout Upstream) encountering a node with `layout_mode=horizontal`: must switch to horizontal traversal for that node's subtree

**UX rule:** The horizontal command writes state; normal layout replays it. The user does not need to re-invoke the horizontal command on re-layout.

### Multi-Input Fan Alignment

**Expected behavior:** For a node with 2+ non-mask inputs, all subtree roots align to the same Y position. They spread leftward and rightward from the consumer's center. The mask input (if any) moves to the left of the consumer rather than the right.

**Edge cases:**
- Fan with 2 non-mask + 1 mask: mask goes left, non-mask inputs spread right
- Fan with 3+ non-mask: spread symmetrically or weighted by subtree width
- Fan where subtrees differ dramatically in height: alignment is at the top of each subtree root node (same Y for xpos), not bottom-aligned
- Interaction with scheme multiplier: fan gap between subtrees uses horizontal spacing constants, not vertical ones

**UX rule:** No user action needed to trigger fan alignment — it applies automatically when 2+ non-mask inputs are detected on any node during layout.

### Per-Node State Storage

**Expected behavior:** After any layout or scale command, each affected node gains (or updates) a hidden "Node Layout" tab with three knobs:
- `node_layout_mode` (String_Knob, values: "vertical" / "horizontal")
- `node_layout_scheme` (String_Knob, values: "compact" / "normal" / "loose")
- `node_layout_scale_factor` (Double_Knob, default 1.0)

Knobs are hidden (INVISIBLE flag) so they don't appear in the parameter panel. They persist when the .nk script is saved and reopened. Re-layout reads these knobs and honors them.

**Edge cases:**
- Node that already has the tab from a previous layout: update values, do not create duplicate tab or knobs
- Node that has the tab but is missing one knob (partial state from a plugin update): add the missing knob, preserve existing values
- Node created by the plugin (Dot nodes for diamond resolution and side input routing): these should also receive state storage so their mode is preserved
- Knob creation must happen inside the correct group context — same fix needed as the group context bug

**UX rule:** State is written silently. No dialog, no prompt. The user sees consistent re-layout behavior; they do not need to know about the knobs.

### Axis-Aware Shrink/Expand

**Expected behavior:** Three variants per direction:
- H-only: scale only X offsets from the anchor node; Y positions unchanged
- V-only: scale only Y offsets from the anchor node; X positions unchanged
- Both: existing behavior (scale both X and Y offsets uniformly)

**Edge cases:**
- H-only shrink on a very narrow subtree: must respect `snap_min` floor on X just as V-only shrink respects it on Y
- Shrink H-only on a horizontal B-spine: compresses the spine; nodes may land closer than snap threshold
- Upstream variant applies to all nodes in the upstream tree, not just the selection

**UX rule:** Separate menu entries for each variant (six new entries: Shrink H / Expand H / Shrink V / Expand V / Shrink Both / Expand Both, or reuse current Both entries + add H and V). Modifier keys are a secondary UX surface; menu discoverability is the primary requirement.

### Expand Push-Away

**Expected behavior:** After Expand Selected or Expand Upstream scales the tree, if the new bounding box is larger than the pre-expand bounding box, nodes outside the subtree that would overlap are pushed away. Direction of push follows the same logic as `push_nodes_to_make_room()`: up if tree grew upward, right if tree grew rightward.

**Edge cases:**
- Expand Upstream growing in both directions: push applies in both directions simultaneously
- Expand Selected where the selection is not a complete subtree: push still applies based on total bounding box growth
- Very large DAGs: push_nodes_to_make_room calls nuke.allNodes() — same O(n) performance profile as existing layout

**UX rule:** Push is automatic and always happens after expand. There is no option to expand without push.

---

## MVP Recommendation for v1.1

**Ship together (interdependent group):**
1. Spacing rebalance + horizontal prefs (foundation for everything else)
2. Multi-input fan alignment + mask side-swap (atomic pair; side-swap is meaningless without fan)
3. Per-node state storage (enables B-spine replay and H/V/Both modes)

**Ship together (consequent group):**
4. Horizontal B-spine layout command (requires state storage from above)
5. Shrink/Expand H/V/Both modes (requires state storage; extends current commands)
6. Expand push-away (simple add-on to existing expand commands; no new dependencies)

**Ship independently (isolated):**
7. Command renames — pure menu.py; do first as it has zero risk
8. Group context bug fix — do early; affects any feature that creates Dot nodes
9. Dot font size → subtree margin scaling — isolated to `_subtree_margin()`; lowest risk, add last

**Defer indefinitely:**
- The anti-features listed above (full Sugiyama, physics layout, GUI toggles on nodes, full-DAG layout)

---

## Sources

- Nuke compositing best practices (vertical spine convention, mask input clipping in horizontal layout): [keheka.com](https://www.keheka.com/best-practices-for-compositing-for-nuke/), [We Suck Less forum discussion](https://www.steakunderwater.com/wesuckless/viewtopic.php?t=4946)
- Nuke Python knob invisibility flag pattern: [Nukepedia Some Flags](http://www.nukepedia.com/python/some-flags), [Ben McEwan — Dynamic Knobs](https://benmcewan.com/blog/2020/06/20/dynamic-knobs-in-nuke/)
- Nuke group context and node creation: [Nuke Python Dev Guide (v13)](https://learn.foundry.com/nuke/developers/130/pythondevguide/dag.html), [Conrad Olson — Add Nodes Inside Group](https://conradolson.com/add-nodes-inside-a-group-with-python)
- Custom knob persistent state (updateValue pattern, INVISIBLE flag): [Erwan Leroy — Custom QT Knobs](https://erwanleroy.com/custom-qt-knobs-for-nuke-nodes-making-stars-gizmo-part-1-2/)
- DAG layout algorithms (Sugiyama layered layout, same-rank Y alignment): [Layered Graph Drawing — Wikipedia](https://en.wikipedia.org/wiki/Layered_graph_drawing), [d3-dag](https://github.com/erikbrinkman/d3-dag)
- Node overlap removal on expand: [GSoC 2024 Graphite Interactive Auto-Layout](https://github.com/GraphiteEditor/Graphite/discussions/1769), [Noverlap anti-collision](https://graphology.github.io/standard-library/layout-noverlap.html)
- Nuke Tab_Knob and knob flags reference: [Nuke Python API — Tab_Knob](https://learn.foundry.com/nuke/developers/140/pythonreference/_autosummary/nuke.Tab_Knob.html), [NDK Knob Flags](https://learn.foundry.com/nuke/developers/63/ndkdevguide/knobs-and-handles/knobflags.html)

**Confidence notes:**
- Horizontal layout clipping the mask input: MEDIUM — multiple community sources confirm; no single Foundry official doc
- INVISIBLE knob flag usage for state storage: HIGH — pattern is documented in official NDK and observed in multiple community implementations
- group.begin()/end() for Dot creation group context fix: HIGH — standard Nuke Python API pattern; confirmed by official documentation
- Fan alignment Y-alignment behavior: MEDIUM — derived from Sugiyama rank-alignment principles; specific Nuke implementation is author's design decision
- Dot font size knob name (`label_size`): LOW — not verified against Nuke API; needs confirmation against actual Dot node knobs before implementation

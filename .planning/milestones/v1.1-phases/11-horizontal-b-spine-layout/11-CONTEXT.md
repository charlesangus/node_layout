# Phase 11: Horizontal B-Spine Layout - Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Add "Layout Upstream Horizontal" and "Layout Selected Horizontal" commands that lay out the B-spine (input[0] chain) left-to-right — root node rightmost, each successive input(0) ancestor one step to the left. Side inputs (A and mask) continue to use vertical placement above each spine node. The layout mode is stored in per-node state and replayed automatically by subsequent normal "Layout Upstream" / "Layout Selected" commands.

No new preferences. No new commands beyond the two horizontal layout entries and their scheme variants.

</domain>

<decisions>
## Implementation Decisions

### Side inputs along the spine
- A inputs and mask inputs are placed **above** (lower Y) their spine node using the existing vertical placement formulas (`vertical_gap_between`, `_subtree_margin`) — same spacing logic as normal layout
- Fan alignment (Phase 9) applies normally when a spine node has 3+ non-mask inputs: A inputs fan out above the spine node with the Phase 9 routing Dot row at a uniform Y
- When fan is active on a spine node, mask goes **above** (same side as A inputs), not to the left — Phase 9 mask side-swap is suppressed in horizontal mode
- When a spine node has a mask input, the downstream spine segment (closer to root) **kinks downward** (higher Y) to clear the mask subtree's height, connected via a routing Dot beneath the masked spine node
- Multiple mask inputs on the spine produce a **cumulative staircase**: each mask kink drops the next downstream segment further (staircase steps down-and-right from the DAG arrows' perspective)

```
Diagram — mask kink geometry:
   s    m  s
   |    |  |
D--C--B-.  |
      |----A---root
                |
                .
<-parent tree---|

(s = side subtrees, m = mask subtree, . = routing Dot)
```

### Output pipe geometry
- A routing Dot (`node_layout_output_dot`) is placed directly below the root node at the standard vertical gap
- The Dot's input connects from root (above); its output connects to the parent tree consumer M (to the left)
- The Dot is marked with a `node_layout_output_dot` custom knob for identification on replay
- The Dot is **persisted and reused** on replay (same pattern as diamond-resolution Dots) — not recreated each time
- If root has no downstream consumer, skip the Dot entirely

```
Diagram — output pipe:
  D-C-B-A-root
            |
M-----------.
(M = parent tree consumer, . = output Dot)
```

### Horizontal spacing
- Step size between each B-spine node: `horizontal_subtree_gap` preference (same pref used elsewhere for H-axis gaps)
- Scheme multiplier applies: `scheme_multiplier` scales the spine step size, so "Layout Upstream Compact Horizontal" produces a narrower spine

### Menu commands
- Two new commands: "Layout Upstream Horizontal" and "Layout Selected Horizontal"
- Scheme variants follow existing naming pattern: "Layout Upstream Compact Horizontal", etc. — Claude's discretion on whether full scheme × horizontal matrix is exposed or just the base horizontal commands
- No keyboard shortcuts for horizontal commands

### Mode storage and replay
- `mode = "horizontal"` written to per-node state for all nodes touched by a horizontal layout (field already exists in `_DEFAULT_STATE`)
- Normal "Layout Upstream" / "Layout Selected" reads stored mode and invokes horizontal placement when `mode == "horizontal"` — no user re-specification needed
- Stored horizontal mode replays as horizontal regardless of input count (fan may still activate for side inputs above the spine, but the spine itself stays horizontal)

### Claude's Discretion
- Implementation structure of `place_subtree_horizontal()` — dedicated function, not axis-swapped call to existing `place_subtree()`
- Exact Y position of output Dot below root (standard `vertical_gap_between` formula)
- `node_layout_output_dot` knob value/structure (consistent with `node_layout_diamond_dot` pattern)
- Whether full scheme × horizontal command matrix is added to menu or just base horizontal commands
- Placement of horizontal commands in `menu.py` relative to existing layout commands

</decisions>

<specifics>
## Specific Ideas

- User-provided geometry diagram for mask kink (confirmed):
  ```
     s    m  s
     |    |  |
  D--C--B-.  |
        |----A---root
                  |
                  .
  <-parent tree---|
  ```
- User-provided output pipe diagram (confirmed):
  ```
  D-C-B-A-root
              |
  M-----------.
  ```
  Parent tree is always to the left of the horizontal subtree, to the left of D. Dot's input is straight up from root, output is straight left to M.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_DEFAULT_STATE["mode"]` — already `"vertical"` in `node_layout_state.py`; set to `"horizontal"` for horizontal layout nodes
- `read_node_state()` / `write_node_state()` — read mode at entry point, write after placement (existing pattern)
- `_horizontal_margin()` — existing H-gap helper using `horizontal_subtree_gap` pref; spine step uses this same pref
- `vertical_gap_between()` / `_subtree_margin()` — existing V-gap formulas reused for side inputs above spine nodes
- `node_layout_diamond_dot` knob pattern — `node_layout_output_dot` follows identical custom knob creation/lookup pattern
- `nuke.lastHitGroup()` — group context capture at entry point (established Phase 6 pattern)
- Fan geometry (`compute_dims` fan branch, `place_subtree` fan Dot row) — reused for side inputs above horizontal spine nodes when 3+ non-mask inputs present

### Established Patterns
- `layout_mode` propagates as explicit parameter like `scheme_multiplier` — never a module global; established in Phase 7 decisions
- Dedicated `place_subtree_horizontal()` — not a swapped-argument call to `place_subtree()`; established in Phase 7 decisions
- `compute_dims` memo key must include layout mode: `(id(node), scheme_multiplier, h_scale, v_scale)` → extend to include mode; established in Phase 7 decisions
- State read at entry points only (`layout_upstream`, `layout_selected`); never inside recursive calls — established Phase 7 rule
- Undo wrapping: `nuke.Undo.name(...)`, `nuke.Undo.begin()`, try/except/else with `cancel()`/`end()` — all commands follow this

### Integration Points
- `layout_upstream()` / `layout_selected()`: read `mode` from stored state at entry; dispatch to horizontal path when `mode == "horizontal"`
- `place_subtree_horizontal()`: new dedicated function; follows same signature pattern as `place_subtree()`; uses `horizontal_subtree_gap * scheme_multiplier` for spine step; calls existing vertical placement for side inputs
- `menu.py`: add "Layout Upstream Horizontal" and "Layout Selected Horizontal" entries (and scheme variants at Claude's discretion)
- Output Dot: created with `node_layout_output_dot` custom knob; wired between root and its downstream consumer; persisted across re-layout

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 11-horizontal-b-spine-layout*
*Context gathered: 2026-03-12*

# Phase 10: Shrink/Expand H/V/Both + Expand Push-Away - Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Add axis-specific (Horizontal / Vertical) variants of the 4 existing scale commands (Shrink/Expand × Selected/Upstream). H/V variants are menu-only. Add a "Repeat Last Scale" command with a keyboard shortcut that re-runs the last invoked scale variant. Push-away on Expand commands applies only in the expanded axis direction. Shrink commands never push.

</domain>

<decisions>
## Implementation Decisions

### New commands
- 8 new menu commands: Shrink/Expand × Selected/Upstream × Horizontal/Vertical
  - "Shrink Selected Horizontal", "Shrink Selected Vertical"
  - "Expand Selected Horizontal", "Expand Selected Vertical"
  - "Shrink Upstream Horizontal", "Shrink Upstream Vertical"
  - "Expand Upstream Horizontal", "Expand Upstream Vertical"
- 1 new command: "Repeat Last Scale" — repeats the last used scale command (any variant)
- No renaming of existing commands: "Shrink Selected", "Expand Selected", "Shrink Upstream", "Expand Upstream" keep their names (implicitly "Both")

### Keyboard shortcuts
- Existing shortcuts unchanged: `ctrl+,` (Shrink Sel), `ctrl+.` (Expand Sel), `ctrl+shift+,` (Shrink Up), `ctrl+shift+.` (Expand Up)
- H/V variants: menu-only, no keyboard shortcuts
- "Repeat Last Scale": `ctrl+/`

### Repeat Last Scale behavior
- One global "last" — tracks the most recently invoked scale command regardless of Selected vs Upstream
- Repeats the exact variant (axis + scope): if last was "Shrink Selected Horizontal", `ctrl+/` runs "Shrink Selected Horizontal" again
- If no prior scale operation in the session, defaults to Both (existing behavior)
- State stored in module-level variable (not persisted across Nuke restarts)

### Axis-specific scaling mechanics
- H-only: scales dx only (horizontal offsets); dy = unchanged; only `h_scale` accumulates in state
- V-only: scales dy only (vertical offsets); dx = unchanged; only `v_scale` accumulates in state
- Both: existing behavior (scales dx and dy, accumulates both h_scale and v_scale)
- `h_scale` and `v_scale` already stored separately in node state (Phase 7) — axis-independent accumulation works by design

### Push-away behavior
- Expand H-only: `push_nodes_to_make_room` naturally pushes only left/right (bbox only grew horizontally)
- Expand V-only: naturally pushes only up (bbox only grew vertically)
- No special push handling needed — existing bbox comparison logic covers directional push automatically
- Shrink variants (H, V, Both): no push-away — surrounding nodes stay in place

### Claude's Discretion
- Implementation structure: whether `_scale_selected_nodes` / `_scale_upstream_nodes` take an `axis` parameter ("h", "v", "both") or whether H/V variants call separate helper functions
- How "last scale" state is stored (module-level variable, what it stores — function reference vs (scope, axis, shrink/expand) tuple)
- Exact placement of new commands in menu.py relative to existing scale commands

</decisions>

<specifics>
## Specific Ideas

- "Repeat Last Scale" inspired by typical DAG editor UX: pick variant once from menu/tab, then repeat with shortcut
- `ctrl+/` chosen as repeat shortcut — physically adjacent to `ctrl+,` and `ctrl+.` on standard keyboards, natural extension of the scale command cluster

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_scale_selected_nodes(scale_factor)` — scales both axes; needs axis parameter added
- `_scale_upstream_nodes(scale_factor)` — same pattern
- `shrink_selected()`, `expand_selected()`, `shrink_upstream()`, `expand_upstream()` — existing wrappers; H/V variants follow identical structure
- `push_nodes_to_make_room(subtree_node_ids, bbox_before, bbox_after, current_group)` — already called in `expand_selected` and `expand_upstream`; H/V expand variants use same call, no changes needed
- `node_layout_state.read_node_state()` / `write_node_state()` — already stores `h_scale`/`v_scale` separately; axis-specific accumulation is just writing only one field

### Established Patterns
- Undo wrapping: `nuke.Undo.name(...)`, `nuke.Undo.begin()`, try/except/else with `cancel()`/`end()`
- `current_group = nuke.lastHitGroup()` as first call in expand functions (Group context)
- State accumulation: `round(stored_state["h_scale"] * scale_factor, 10)` — same pattern for axis variants, just only updating h_scale or v_scale

### Integration Points
- `_scale_selected_nodes()` / `_scale_upstream_nodes()`: add `axis` parameter; skip dy scaling when axis="h", skip dx scaling when axis="v"
- `menu.py`: add 8 H/V command entries + "Repeat Last Scale" with `ctrl+/` shortcut; place in same block as existing scale commands
- Module-level `_last_scale_fn` variable in `node_layout.py`: set by each scale command invocation, called by `repeat_last_scale()`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-shrink-expand-h-v-both-expand-push-away*
*Context gathered: 2026-03-12*

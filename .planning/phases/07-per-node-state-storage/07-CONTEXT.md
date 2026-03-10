# Phase 7: Per-Node State Storage - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Every node touched by a layout operation receives a hidden persistent knob storing layout state (mode, scheme, scale). State survives .nk save/close/reopen. Re-layout replays stored state unless an explicit scheme/mode command overrides it. Two "clear state" commands let users reset nodes to stateless. Creating new layout modes (horizontal) is Phase 11 — this phase lays the storage and replay mechanism.

</domain>

<decisions>
## Implementation Decisions

### State knob structure
- One `String_Knob('node_layout_state', 'Node Layout State')` per node, on a `node_layout_tab` tab
- Value is a JSON string: `{"scheme": "compact", "mode": "vertical", "h_scale": 0.8, "v_scale": 1.0}`
- Absent keys fall back to defaults (scheme=normal, mode=vertical, h_scale=1.0, v_scale=1.0)
- `INVISIBLE` flag set — hidden from Properties panel but NOT `DO_NOT_WRITE` (which blocks .nk persistence)
- All layout-touched nodes receive the knob, including diamond-resolution Dot nodes (no special-casing)
- Phase 7 always writes `"mode": "vertical"` — Phase 11 changes this to `"horizontal"` on affected nodes

### Scheme storage format
- Stored as string enum: `"compact"`, `"normal"`, or `"loose"`
- Decoupled from pref multiplier values — stored scheme resolves to the current pref value at replay time
- Extensible: future state fields (e.g. `"horizontal"` mode, additional scale axes) are new JSON keys

### Scheme replay logic
- `scheme_multiplier=None` at entry point now means: read stored scheme from each node, not "use normal"
- Each node uses its own stored scheme (per-node, not per-subtree-root)
- `compute_dims()` reads stored scheme from each node mid-recursion; memo key becomes `(id(node), scheme_for_node)` to prevent cache collisions on shared nodes
- Explicit scheme command (e.g. `layout_upstream_compact()`) overrides stored scheme AND writes the new scheme back to all affected nodes — so next unspecified re-layout replays the override
- Nodes with no stored state (first-ever layout): fall back to `normal_multiplier`

### Scale factor semantics
- `h_scale` and `v_scale` stored separately in JSON (supporting Phase 10's axis-specific shrink/expand)
- Shrink/Expand multiplies into existing stored scale (accumulates): `0.8 × 0.8 = 0.64`
- Re-layout replays the stored scale factor alongside scheme — reproduces both compact scheme AND accumulated scale
- A fresh layout run (after clear state) starts at scale 1.0

### Clear state commands
- Two new commands: `"Clear Layout State Selected"` and `"Clear Layout State Upstream"`
- Removes `node_layout_state` knob from each affected node; removes `node_layout_tab` tab if no other knobs remain on it
- After clear, next layout runs fresh: normal scheme, scale 1.0
- Registered in menu.py alongside existing layout commands

### Claude's Discretion
- How the JSON parse/write helpers are structured (module-level functions vs inline)
- Whether `node_layout_tab` is added fresh if absent, or assumed present on any node that already went through layout

</decisions>

<specifics>
## Specific Ideas

- State is intentionally inspectable: user can open Nuke's script editor and read the JSON on any node to understand what was stored
- "We need to add commands to clear stored scheme on selected/upstream" — user confirmed this is Phase 7 scope, not deferred

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `node_layout_tab` / `node_layout_diamond_dot` pattern (lines 252–276 in node_layout.py): established pattern for addKnob on layout-touched nodes — state knob follows same structure
- `scheme_multiplier` parameter thread through `compute_dims()` / `place_subtree()` / `layout_upstream()` / `layout_selected()`: existing propagation path; Phase 7 extends this to read from per-node state instead of defaulting to normal
- `layout_upstream_compact()` / `layout_upstream_loose()` (lines 696–709): entry points that pass explicit scheme_multiplier — these become the "override and write-back" path

### Established Patterns
- State reads at entry points (or mid-recursion with memo key discipline) — never fire slow Nuke API calls inside tight loops without memoization
- `try/except/else` for Nuke undo groups — undo.end() in else, undo.cancel() in except
- No `DO_NOT_WRITE` flag on custom knobs (it blocks .nk persistence — confirmed in prior research)
- `nuke.lastHitGroup()` for group context capture at entry points (Phase 6)

### Integration Points
- `layout_upstream()` and `layout_selected()` entry points: add state-write pass after `place_subtree()` completes; add state-read at top to resolve per-node schemes
- `compute_dims()` memo key: extend from `id(node)` to `(id(node), scheme_for_node)`
- `_scale_selected_nodes()` / `_scale_upstream_nodes()`: add state read (current h_scale/v_scale) + write (accumulated result) around scale operation
- `menu.py`: register `clear_layout_state_selected()` and `clear_layout_state_upstream()` commands

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-per-node-state-storage*
*Context gathered: 2026-03-10*

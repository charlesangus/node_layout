# Phase 8: Dot Font-Size Margin Scaling - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

When a labeled Dot node sits at or near a subtree's input slot, its font size is used as a section-boundary signal: a larger font produces proportionally more breathing room (margin) around that subtree. The `dot_font_reference_size` pref is the baseline. No new commands, no new UI — the pref is already exposed in the dialog (Phase 6 stub). This phase only wires font-size into the margin computation.

</domain>

<decisions>
## Implementation Decisions

### Scaling formula
- Linear ratio: `font_multiplier = font_size / dot_font_reference_size`
- Floor at 1.0 — a Dot with font size below the reference does NOT shrink the margin
- Cap at 4.0 — very large fonts (200px etc.) are clamped to 4× margin maximum
- Formula: `font_multiplier = min(max(font_size / reference_size, 1.0), 4.0)`

### Axes affected
- Both V-axis (`_subtree_margin`) and H-axis (`_horizontal_margin`) are scaled by the font multiplier
- Applies to all slots including the mask input slot (mask_input_ratio is already applied; font scale stacks on top)

### Stacking with other multipliers
- Font multiplier stacks multiplicatively with scheme multiplier, v_scale, and h_scale
- Composes freely — a big-font Dot under a Compact scheme can produce a margin that exceeds the base margin
- No override semantics; all three signals are independent

### Which Dot qualifies
- Walk upstream from `node.input(slot)` through consecutive Dot nodes
- Pick the **first Dot with a non-empty label** — that's the section-boundary marker
- Stop the walk immediately when encountering any non-Dot node
- If no labeled Dot is found before hitting a non-Dot (or if the immediate input is not a Dot), font_multiplier = 1.0 (no scaling)
- Diamond-resolution Dots (marked with `node_layout_diamond_dot` knob) are NOT special-cased; they will have empty labels in practice so they won't trigger scaling

### Example traversal
- Merge → Dot1 (no label) → Dot2 (labeled "BG elements") → Grade → Dot3
- Result: use Dot2's font size (first labeled Dot in the consecutive chain from the slot)
- Merge → Dot1 (no label) → Grade → Dot3 (labeled)
- Result: multiplier = 1.0 (chain broke at Grade; Dot3 is not reachable through the consecutive Dot walk)

### Claude's Discretion
- Whether `_dot_font_scale(node, slot)` is a standalone helper or inlined
- How to read `note_font_size` knob from Dot nodes (check knob existence safely)
- Where in `compute_dims()` / `place_subtree()` to inject the font_multiplier (alongside the existing v_scale/h_scale application)

</decisions>

<specifics>
## Specific Ideas

- The labeled-Dot-walk idea: a Dot with a big label font clearly marks a section boundary visually in the DAG; unlabeled Dots are just routing nodes and shouldn't trigger scaling
- "We'd take the label from Dot2 (or Dot1 if it had a label), but never Dot3" — confirmed that the walk stops at the first non-Dot node

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_subtree_margin(node, slot, node_count, mode_multiplier)` — sole V-axis margin call site; font_multiplier applies here
- `_horizontal_margin(node, slot)` — sole H-axis margin call site; font_multiplier applies here
- `dot_font_reference_size` pref — already in DEFAULTS (value: 20), already exposed in dialog under Advanced (Phase 6 stub)
- `node_layout_diamond_dot` knob pattern — already used to identify synthetic Dots (but won't matter since diamond Dots have no label)

### Established Patterns
- `_is_mask_input(node, slot)` — existing helper for slot classification; font walk uses the same `node.input(slot)` access pattern
- State reads at entry points; margin helpers are called per-slot inside `compute_dims()` and `place_subtree()` — font scale read is per-slot, lightweight
- Try/except for Nuke API calls (KeyError, AttributeError) — applies to knob access on Dot nodes

### Integration Points
- `_subtree_margin()` in `node_layout.py`: add `font_multiplier` (or compute internally via `_dot_font_scale(node, slot)`)
- `_horizontal_margin()` in `node_layout.py`: same — add font_multiplier
- `side_margins_v` and `side_margins_h` in `compute_dims()` and `place_subtree()`: currently apply `node_v_scale`/`node_h_scale`; font_multiplier would be applied at the same layer or baked into the helper
- `node_layout_prefs.prefs_singleton.get("dot_font_reference_size")` — read inside the font scale helper

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-dot-font-size-margin-scaling*
*Context gathered: 2026-03-11*

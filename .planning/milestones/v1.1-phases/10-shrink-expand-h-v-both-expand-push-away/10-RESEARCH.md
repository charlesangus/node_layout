# Phase 10: Shrink/Expand H/V/Both + Expand Push-Away - Research

**Researched:** 2026-03-12
**Domain:** Axis-specific scaling, module-level command state, Nuke menu registration
**Confidence:** HIGH

## Summary

Phase 10 adds eight axis-specific scale commands (Shrink/Expand × Selected/Upstream × H/V) plus a
"Repeat Last Scale" command. All mechanics are pure extensions of the existing Phase 7 scale
infrastructure. No new algorithms are needed: `_scale_selected_nodes` and `_scale_upstream_nodes`
already operate on `dx`/`dy` separately and write `h_scale`/`v_scale` as independent fields.
Adding an `axis` parameter (`"h"`, `"v"`, or `"both"`) and skipping the irrelevant axis is the
entire implementation of axis-specific scaling.

Push-away after Expand works without change. `push_nodes_to_make_room` compares bounding boxes
before and after scaling; if only horizontal spacing grew the bbox only grew horizontally and the
function naturally pushes only left/right. No directional switch or new arguments are required.

"Repeat Last Scale" stores the last invoked command as a module-level variable (`_last_scale_fn`)
set by every scale wrapper on each call. `repeat_last_scale()` simply calls it.

**Primary recommendation:** Add `axis` parameter to both `_scale_*` helpers, add 8 thin wrapper
functions that call with `axis="h"` or `axis="v"`, add `repeat_last_scale()`, and register all 9
new entries in menu.py.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- 8 new menu commands: Shrink/Expand × Selected/Upstream × Horizontal/Vertical
  - "Shrink Selected Horizontal", "Shrink Selected Vertical"
  - "Expand Selected Horizontal", "Expand Selected Vertical"
  - "Shrink Upstream Horizontal", "Shrink Upstream Vertical"
  - "Expand Upstream Horizontal", "Expand Upstream Vertical"
- 1 new command: "Repeat Last Scale" — repeats the last used scale command (any variant)
- No renaming of existing commands: "Shrink Selected", "Expand Selected", "Shrink Upstream",
  "Expand Upstream" keep their names (implicitly "Both")
- Existing shortcuts unchanged: `ctrl+,` (Shrink Sel), `ctrl+.` (Expand Sel),
  `ctrl+shift+,` (Shrink Up), `ctrl+shift+.` (Expand Up)
- H/V variants: menu-only, no keyboard shortcuts
- "Repeat Last Scale": `ctrl+/`
- Repeat Last Scale: one global "last" across all variants; defaults to Both if no prior
  scale in the session; stored in module-level variable (not persisted)
- H-only: scales dx only; dy unchanged; only `h_scale` accumulates
- V-only: scales dy only; dx unchanged; only `v_scale` accumulates
- Both: existing behavior unchanged
- Push-away for Expand H/V: existing `push_nodes_to_make_room` call with no changes
- Shrink variants: no push-away

### Claude's Discretion

- Implementation structure: whether `_scale_selected_nodes` / `_scale_upstream_nodes` take
  an `axis` parameter ("h", "v", "both") or whether H/V variants call separate helper functions
- How "last scale" state is stored (module-level variable, what it stores — function reference
  vs (scope, axis, shrink/expand) tuple)
- Exact placement of new commands in menu.py relative to existing scale commands

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SCALE-01 | Shrink/Expand Selected and Upstream commands support Horizontal, Vertical, and Both axis modes | Adding `axis` parameter to both `_scale_*` helpers covers this; dx/dy already computed separately |
| SCALE-02 | Axis mode is selectable via separate menu commands and via modifier keys on existing shortcuts | 8 new menu commands; CONTEXT.md locks H/V as menu-only (no modifier keys on existing shortcuts) |
| SCALE-03 | Expand Selected and Expand Upstream push surrounding nodes away after expanding (same push logic as regular layout) | Already implemented in `expand_selected` / `expand_upstream`; H/V variants reuse exact same push call |
</phase_requirements>

---

## Standard Stack

### Core (no new dependencies)
| Component | Where | Purpose | Notes |
|-----------|-------|---------|-------|
| `node_layout.py` | `/workspace/node_layout.py` | All scale functions live here | Modified in place |
| `menu.py` | `/workspace/menu.py` | Menu registration | 9 new `addCommand` calls |
| `node_layout_state.py` | `/workspace/node_layout_state.py` | Reads/writes `h_scale`/`v_scale` | No changes needed |

Phase 10 introduces zero new library dependencies.

### Key Constants (already defined in node_layout.py, line 912-913)
```python
SHRINK_FACTOR = 0.8
EXPAND_FACTOR = 1.25
```

---

## Architecture Patterns

### Axis Parameter Design (Claude's Discretion — recommended approach)

Add `axis` as an explicit keyword parameter with default `"both"` to preserve backward
compatibility for the existing wrappers that call without the argument:

```python
def _scale_selected_nodes(scale_factor, axis="both"):
    ...
    for node in selected_nodes:
        ...
        new_dx = round(dx * scale_factor) if axis != "v" else round(dx)
        new_dy = round(dy * scale_factor) if axis != "h" else round(dy)
        # snap_min floor — only apply when that axis is being scaled
        if axis != "v" and dx != 0 and abs(new_dx) < snap_min:
            new_dx = snap_min if dx > 0 else -snap_min
        if axis != "h" and dy != 0 and abs(new_dy) < snap_min:
            new_dy = snap_min if dy > 0 else -snap_min
        ...
    # State write-back — only accumulate the scaled axis
    for scale_node in selected_nodes:
        stored_state = node_layout_state.read_node_state(scale_node)
        if axis != "v":
            stored_state["h_scale"] = round(stored_state["h_scale"] * scale_factor, 10)
        if axis != "h":
            stored_state["v_scale"] = round(stored_state["v_scale"] * scale_factor, 10)
        node_layout_state.write_node_state(scale_node, stored_state)
```

Same pattern applies identically to `_scale_upstream_nodes`.

### Wrapper Function Pattern

Each H/V variant is a thin wrapper following the exact structure of the existing Both wrappers.
The Shrink variants are simpler (no push-away); Expand variants are identical to existing except
the inner call passes `axis=`:

```python
def shrink_selected_horizontal():
    if len(nuke.selectedNodes()) < 2:
        return
    global _last_scale_fn
    _last_scale_fn = shrink_selected_horizontal
    nuke.Undo.name("Shrink Selected Horizontal")
    nuke.Undo.begin()
    try:
        _scale_selected_nodes(SHRINK_FACTOR, axis="h")
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def expand_selected_horizontal():
    current_group = nuke.lastHitGroup()    # MUST be the first Nuke API call
    selected_nodes = nuke.selectedNodes()
    if len(selected_nodes) < 2:
        return
    global _last_scale_fn
    _last_scale_fn = expand_selected_horizontal
    node_ids = {id(n) for n in selected_nodes}
    bbox_before = compute_node_bounding_box(selected_nodes)
    nuke.Undo.name("Expand Selected Horizontal")
    nuke.Undo.begin()
    try:
        _scale_selected_nodes(EXPAND_FACTOR, axis="h")
        bbox_after = compute_node_bounding_box(selected_nodes)
        if bbox_before is not None and bbox_after is not None:
            push_nodes_to_make_room(node_ids, bbox_before, bbox_after, current_group)
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()
```

The existing Both wrappers (`shrink_selected`, `expand_selected`, `shrink_upstream`,
`expand_upstream`) must also set `_last_scale_fn = <self>` on each call so Repeat Last Scale
tracks them.

### Repeat Last Scale Pattern (Claude's Discretion — recommended approach)

Store a callable reference in a module-level variable. The default is `None` which maps to
`both` behavior at call time:

```python
_last_scale_fn = None   # module-level; not persisted

def repeat_last_scale():
    global _last_scale_fn
    if _last_scale_fn is None:
        # Default: same guard logic as shrink_selected (Both is the implicit default)
        # Per CONTEXT.md: "defaults to Both (existing behavior)"
        # Call shrink_selected or expand_selected? Neither is specified as default action —
        # decision: call expand_selected (expand is the "repeat" intent) or simply no-op.
        # CONTEXT.md says "defaults to Both (existing behavior)" — interpret as no-op until
        # a scale command has actually been run. Safest: early return.
        return
    _last_scale_fn()
```

Alternatively, storing the function reference means the function sets the variable to itself.
This avoids any indirect dispatch table.

**Note on "defaults to Both":** CONTEXT.md says "If no prior scale operation in the session,
defaults to Both (existing behavior)." The safest interpretation is a no-op (return early) rather
than picking an arbitrary shrink/expand direction as the default. Revisit in planning if explicit
default is required.

### Module-Level Variable Placement

`_last_scale_fn = None` belongs immediately below `SHRINK_FACTOR` / `EXPAND_FACTOR` constants
(line ~913 in current source) to group all scale-command globals together.

### Menu Registration Pattern

```python
# In menu.py — after existing scale commands, before separator + utility commands:
layout_menu.addCommand('Shrink Selected Horizontal', node_layout.shrink_selected_horizontal)
layout_menu.addCommand('Shrink Selected Vertical',   node_layout.shrink_selected_vertical)
layout_menu.addCommand('Expand Selected Horizontal', node_layout.expand_selected_horizontal)
layout_menu.addCommand('Expand Selected Vertical',   node_layout.expand_selected_vertical)
layout_menu.addCommand('Shrink Upstream Horizontal', node_layout.shrink_upstream_horizontal)
layout_menu.addCommand('Shrink Upstream Vertical',   node_layout.shrink_upstream_vertical)
layout_menu.addCommand('Expand Upstream Horizontal', node_layout.expand_upstream_horizontal)
layout_menu.addCommand('Expand Upstream Vertical',   node_layout.expand_upstream_vertical)
layout_menu.addCommand(
    'Repeat Last Scale',
    node_layout.repeat_last_scale,
    'ctrl+/',
    shortcutContext=2,
)
```

### Anti-Patterns to Avoid

- **Separate helper functions per axis:** Having `_scale_selected_nodes_h()` and
  `_scale_selected_nodes_v()` duplicates the entire loop body. The `axis` parameter is the
  correct factoring.
- **Checking axis inside state write-back incorrectly:** The snap_min floor must also be
  suppressed for the unchanged axis. Do not apply floor to dy when axis="h".
- **Using a string label for `_last_scale_fn` dispatch:** Storing a callable reference
  directly is simpler and avoids a secondary dispatch dict that can fall out of sync.
- **Calling `nuke.lastHitGroup()` after any other Nuke call:** The context comment in
  existing expand functions — "MUST be the first Nuke API call" — must be honored in H/V
  Expand variants too.
- **Missing `global _last_scale_fn` declaration:** Python requires `global` declaration
  before assignment to a module-level variable inside a function.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Directional push logic | Custom per-axis push router | Existing `push_nodes_to_make_room` | Already bbox-driven; naturally directional |
| Per-axis bounding box | Separate H/V bbox functions | Existing `compute_node_bounding_box` | Both axes captured; unused axis just matches before/after |
| State isolation per axis | New state fields or schema change | Existing `h_scale`/`v_scale` fields | Already stored independently; just skip the irrelevant write |
| Last-command tracking | Persistent storage, prefs key | Module-level callable variable | Session-only per spec; a variable is sufficient |

---

## Common Pitfalls

### Pitfall 1: snap_min floor applied to unchanged axis
**What goes wrong:** When axis="h", `dy` is left unchanged (`new_dy = round(dy)` == `dy`).
If the snap_min floor guard tests `abs(new_dy) < snap_min`, it will incorrectly clamp nodes
that happen to be within snap_min in the vertical direction.
**Why it happens:** Copy-paste of the Both-axis floor guard without adding the axis condition.
**How to avoid:** Gate each floor guard with `axis != "v"` (for dx) and `axis != "h"` (for dy).
**Warning signs:** A test that moves only horizontally finds nodes displaced vertically.

### Pitfall 2: existing Both wrappers not updated to set _last_scale_fn
**What goes wrong:** After the user runs "Shrink Selected" (Both), then `ctrl+/`, Repeat Last
Scale does nothing (or runs the previous H/V command).
**Why it happens:** The four existing wrappers were written before `_last_scale_fn` existed.
**How to avoid:** Add `global _last_scale_fn; _last_scale_fn = <self>` to all eight existing
wrappers (shrink_selected, expand_selected, shrink_upstream, expand_upstream) in addition to
the eight new ones.
**Warning signs:** `ctrl+/` after a Both command repeats a previous H/V command unexpectedly.

### Pitfall 3: state write-back for "unchanged" axis accumulates 1.0 × factor
**What goes wrong:** When axis="h", v_scale is written as `v_scale * scale_factor` instead of
being left alone, corrupting replay scaling in future layout runs.
**Why it happens:** The existing write-back loop unconditionally multiplies both scales.
**How to avoid:** Only multiply the scale for the axis being changed; leave the other unchanged.

### Pitfall 4: _last_scale_fn circular reference
**What goes wrong:** On first call, `_last_scale_fn = shrink_selected_horizontal` inside
`shrink_selected_horizontal` itself. This is intentional and safe — Python closures capture
the name, and the function will exist by the time it's called again.
**Why it happens:** It looks like it could cause recursion — it does not. The assignment stores
the callable; `repeat_last_scale` calls it at a later time.
**How to avoid:** No action needed; understand that storing `self` as a callable reference is
the correct pattern here.

### Pitfall 5: H-only expand doesn't actually grow the bbox horizontally
**What goes wrong:** Nodes only expand to the right (positive dx), so the bbox grows rightward.
Nodes that are to the LEFT of the anchor (negative dx direction) shrink toward the anchor.
**Why it happens:** Expanding means multiplying dx by factor > 1; for negative dx this makes dx
more negative (further left), actually growing the bbox leftward too.
**How to avoid:** No action needed — this is the correct symmetric behavior. Bbox comparison
in `push_nodes_to_make_room` only checks `after_max_x > before_max_x` (grew right) and
`after_min_y < before_min_y` (grew up). Left-expansion is not pushed (no node is already to
the left of a tree's left edge in normal Nuke usage). Verify empirically if left-push is needed.

---

## Code Examples

### Current _scale_selected_nodes signature (lines 932-968)
```python
def _scale_selected_nodes(scale_factor):
    selected_nodes = nuke.selectedNodes()
    if len(selected_nodes) < 2:
        return
    roots = find_selection_roots(selected_nodes)
    anchor_node = max(roots, key=lambda n: (n.ypos(), -n.xpos()))
    snap_min = get_dag_snap_threshold() - 1
    anchor_center_x = anchor_node.xpos() + anchor_node.screenWidth() / 2
    anchor_center_y = anchor_node.ypos() + anchor_node.screenHeight() / 2
    for node in selected_nodes:
        if node is anchor_node:
            continue
        node_center_x = node.xpos() + node.screenWidth() / 2
        node_center_y = node.ypos() + node.screenHeight() / 2
        dx = node_center_x - anchor_center_x
        dy = node_center_y - anchor_center_y
        new_dx = round(dx * scale_factor)
        new_dy = round(dy * scale_factor)
        if dx != 0 and abs(new_dx) < snap_min:
            new_dx = snap_min if dx > 0 else -snap_min
        if dy != 0 and abs(new_dy) < snap_min:
            new_dy = snap_min if dy > 0 else -snap_min
        new_center_x = anchor_center_x + new_dx
        new_center_y = anchor_center_y + new_dy
        node.setXpos(round(new_center_x - node.screenWidth() / 2))
        node.setYpos(round(new_center_y - node.screenHeight() / 2))
    for scale_node in selected_nodes:
        stored_state = node_layout_state.read_node_state(scale_node)
        stored_state["h_scale"] = round(stored_state["h_scale"] * scale_factor, 10)
        stored_state["v_scale"] = round(stored_state["v_scale"] * scale_factor, 10)
        node_layout_state.write_node_state(scale_node, stored_state)
```

### Modified signature for axis support
```python
def _scale_selected_nodes(scale_factor, axis="both"):
    ...
    new_dx = round(dx * scale_factor) if axis != "v" else round(dx)
    new_dy = round(dy * scale_factor) if axis != "h" else round(dy)
    if axis != "v" and dx != 0 and abs(new_dx) < snap_min:
        new_dx = snap_min if dx > 0 else -snap_min
    if axis != "h" and dy != 0 and abs(new_dy) < snap_min:
        new_dy = snap_min if dy > 0 else -snap_min
    ...
    for scale_node in selected_nodes:
        stored_state = node_layout_state.read_node_state(scale_node)
        if axis != "v":
            stored_state["h_scale"] = round(stored_state["h_scale"] * scale_factor, 10)
        if axis != "h":
            stored_state["v_scale"] = round(stored_state["v_scale"] * scale_factor, 10)
        node_layout_state.write_node_state(scale_node, stored_state)
```

### push_nodes_to_make_room — already directional (lines 682-727)
```python
def push_nodes_to_make_room(subtree_node_ids, bbox_before, bbox_after, current_group=None):
    ...
    grew_up = after_min_y < before_min_y
    grew_right = after_max_x > before_max_x
    if not grew_up and not grew_right:
        return
    push_up_amount = before_min_y - after_min_y if grew_up else 0
    push_right_amount = after_max_x - before_max_x if grew_right else 0
    ...
    if grew_up and node_bottom <= before_min_y:
        delta_y = -push_up_amount
    if grew_right and node_left >= before_max_x:
        delta_x = push_right_amount
```
Direction is determined entirely from bbox comparison — no changes needed for H/V expand.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Python `unittest` (stdlib) |
| Config file | none |
| Quick run command | `python3 -m unittest tests.test_scale_nodes` |
| Full suite command | `python3 -m unittest discover -s tests` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCALE-01 | `_scale_selected_nodes(axis="h")` leaves dy unchanged | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestAxisScalingBehavior.test_h_axis_leaves_dy_unchanged` | Wave 0 |
| SCALE-01 | `_scale_selected_nodes(axis="v")` leaves dx unchanged | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestAxisScalingBehavior.test_v_axis_leaves_dx_unchanged` | Wave 0 |
| SCALE-01 | `axis="both"` default matches previous behavior | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestAxisScalingBehavior.test_both_axis_unchanged` | Wave 0 |
| SCALE-01 | State write-back: only h_scale updated on axis="h" | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestAxisStateBehavior.test_h_axis_only_updates_h_scale` | Wave 0 |
| SCALE-01 | State write-back: only v_scale updated on axis="v" | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestAxisStateBehavior.test_v_axis_only_updates_v_scale` | Wave 0 |
| SCALE-01 | snap_min floor not applied to unchanged axis | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestAxisScalingBehavior.test_snap_floor_not_applied_to_unchanged_axis` | Wave 0 |
| SCALE-02 | 8 new functions present in node_layout module | AST | `python3 -m unittest tests.test_scale_nodes_axis.TestNewCommandsAST` | Wave 0 |
| SCALE-02 | `repeat_last_scale` exists and calls `_last_scale_fn` | AST | `python3 -m unittest tests.test_scale_nodes_axis.TestRepeatLastScaleAST` | Wave 0 |
| SCALE-02 | `_last_scale_fn` is updated by each wrapper invocation | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestRepeatLastScaleBehavior.test_last_fn_set_after_call` | Wave 0 |
| SCALE-02 | `repeat_last_scale` repeats the last called command | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestRepeatLastScaleBehavior.test_repeat_calls_last_fn` | Wave 0 |
| SCALE-02 | `repeat_last_scale` no-ops when no prior call | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestRepeatLastScaleBehavior.test_repeat_noop_when_none` | Wave 0 |
| SCALE-03 | `expand_selected_horizontal` calls `push_nodes_to_make_room` | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestExpandPushAway.test_expand_h_calls_push` | Wave 0 |
| SCALE-03 | `expand_selected_vertical` calls `push_nodes_to_make_room` | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestExpandPushAway.test_expand_v_calls_push` | Wave 0 |
| SCALE-03 | `shrink_selected_horizontal` does NOT call push | unit | `python3 -m unittest tests.test_scale_nodes_axis.TestExpandPushAway.test_shrink_h_no_push` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m unittest tests.test_scale_nodes tests.test_scale_nodes_axis`
- **Per wave merge:** `python3 -m unittest discover -s tests`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_scale_nodes_axis.py` — all new tests for SCALE-01, SCALE-02, SCALE-03
  (the entire test file is new; no existing file covers axis parameter behavior)
- [ ] No framework install needed — `unittest` is stdlib

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| No axis distinction in scale | `axis` parameter gates dx/dy scaling | Phase 10 addition |
| No repeat command | `_last_scale_fn` + `repeat_last_scale()` | Phase 10 addition |
| 4 scale menu commands | 13 scale menu commands (4 + 8 + 1) | Phase 10 addition |

---

## Open Questions

1. **Default behavior of "Repeat Last Scale" with no prior call**
   - What we know: CONTEXT.md says "defaults to Both (existing behavior)"
   - What's unclear: "Both" what — Shrink Both or Expand Both? Neither is specified.
   - Recommendation: No-op (return immediately) when `_last_scale_fn is None`. This is the
     safest interpretation and avoids surprising the user with an arbitrary action. Document in
     code comment.

2. **Ordering of the 8 new commands in menu.py**
   - What we know: CONTEXT.md delegates placement to Claude's discretion.
   - What's unclear: Grouping by scope (Selected vs Upstream) or by axis (H vs V) or by
     action (Shrink vs Expand).
   - Recommendation: Group by scope then action then axis, matching the existing command cluster:
     Shrink Selected H/V, Expand Selected H/V, Shrink Upstream H/V, Expand Upstream H/V.
     This mirrors the alphabetical tab-menu discoverability pattern established in CMD-01.

---

## Sources

### Primary (HIGH confidence)
- Direct source inspection: `/workspace/node_layout.py` lines 682-727 (push_nodes_to_make_room),
  lines 912-1076 (constants + all 4 scale wrappers + both scale helpers)
- Direct source inspection: `/workspace/node_layout_state.py` (state schema: h_scale, v_scale)
- Direct source inspection: `/workspace/menu.py` (existing menu registration pattern)
- Direct source inspection: `/workspace/tests/test_scale_nodes.py` (test stub and pattern)
- Confirmed test baseline: all 17 existing scale tests pass (python3 -m unittest tests.test_scale_nodes)

### Secondary (MEDIUM confidence)
- CONTEXT.md locked decisions — authoritative for this project
- STATE.md accumulated patterns — established project conventions

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new deps; all mechanics already present in codebase
- Architecture: HIGH — axis parameter pattern is direct extension of existing loop structure
- Pitfalls: HIGH — identified from first-principles analysis of the existing code
- Test map: HIGH — mirrors existing test_scale_nodes patterns exactly

**Research date:** 2026-03-12
**Valid until:** No external dependencies; valid until codebase changes (indefinite)

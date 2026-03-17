# Phase 11: Horizontal B-Spine Layout - Research

**Researched:** 2026-03-12
**Updated:** 2026-03-13 (as-built revision after all 3 plans complete)
**Domain:** Nuke DAG layout algorithm extension — horizontal spine geometry
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Side inputs along the spine:**
- A inputs and mask inputs are placed **above** (lower Y) their spine node using the existing vertical placement formulas (`vertical_gap_between`, `_subtree_margin`) — same spacing logic as normal layout
- Fan alignment (Phase 9) applies normally when a spine node has 3+ non-mask inputs: A inputs fan out above the spine node with the Phase 9 routing Dot row at a uniform Y
- When fan is active on a spine node, mask goes **above** (same side as A inputs), not to the left — Phase 9 mask side-swap is suppressed in horizontal mode
- When a spine node has a mask input, the downstream spine segment (closer to root) **kinks downward** (higher Y) to clear the mask subtree's height, connected via a routing Dot beneath the masked spine node
- Multiple mask inputs on the spine produce a **cumulative staircase**: each mask kink drops the next downstream segment further (staircase steps down-and-right from the DAG arrows' perspective)

Mask kink geometry:
```
   s    m  s
   |    |  |
D--C--B-.  |
      |----A---root
                |
                .
<-parent tree---|
(s = side subtrees, m = mask subtree, . = routing Dot)
```

**Output pipe geometry:**
- A routing Dot (`node_layout_output_dot`) is placed directly below the root node at the standard vertical gap
- The Dot's input connects from root (above); its output connects to the parent tree consumer M (to the left)
- The Dot is marked with a `node_layout_output_dot` custom knob for identification on replay
- The Dot is **persisted and reused** on replay (same pattern as diamond-resolution Dots) — not recreated each time
- If root has no downstream consumer, skip the Dot entirely

Output pipe diagram:
```
D-C-B-A-root
            |
M-----------.
(M = parent tree consumer, . = output Dot)
```

**Horizontal spacing:**
- Step size between each B-spine node: `horizontal_subtree_gap` preference (same pref used elsewhere for H-axis gaps)
- Scheme multiplier applies: `scheme_multiplier` scales the spine step size, so "Layout Upstream Compact Horizontal" produces a narrower spine

**Menu commands:**
- Two new commands: "Layout Upstream Horizontal" and "Layout Selected Horizontal"
- Scheme variants follow existing naming pattern: "Layout Upstream Compact Horizontal", etc. — Claude's discretion on whether full scheme × horizontal matrix is exposed or just the base horizontal commands
- No keyboard shortcuts for horizontal commands

**Mode storage and replay:**
- `mode = "horizontal"` written to per-node state for all nodes touched by a horizontal layout
- Normal "Layout Upstream" / "Layout Selected" reads stored mode and invokes horizontal placement when `mode == "horizontal"` — no user re-specification needed
- Stored horizontal mode replays as horizontal regardless of input count

### Claude's Discretion
- Implementation structure of `place_subtree_horizontal()` — dedicated function, not axis-swapped call to existing `place_subtree()`
- Exact Y position of output Dot below root (standard `vertical_gap_between` formula)
- `node_layout_output_dot` knob value/structure (consistent with `node_layout_diamond_dot` pattern)
- Whether full scheme × horizontal command matrix is added to menu or just base horizontal commands
- Placement of horizontal commands in `menu.py` relative to existing layout commands

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HORIZ-01 | User can run "Layout Upstream Horizontal" to lay out the B spine right-to-left — root node is rightmost, each successive input(0) ancestor steps left; output pipe from root extends downward to parent tree | `place_subtree_horizontal()` + `layout_upstream_horizontal()` wrapper + `node_layout_output_dot` Dot creation |
| HORIZ-02 | User can run "Layout Selected Horizontal" to lay out selected nodes in horizontal B-spine mode | `layout_selected_horizontal()` wrapper + `layout_selected()` dispatch on `mode == "horizontal"` |
| HORIZ-03 | Horizontal layout mode is stored in each node's state knob; normal "Layout Upstream/Selected" commands replay horizontal mode automatically | `_DEFAULT_STATE["mode"]` already exists; entry points read stored mode and dispatch to horizontal path |
</phase_requirements>

---

## Summary

Phase 11 adds horizontal B-spine layout to the existing `node_layout.py` engine. The core algorithmic work is `place_subtree_horizontal()` — a dedicated function that treats the B-spine (input[0] chain) as the main horizontal axis (stepping left from root) while delegating all side-input placement to the existing vertical formulas. This is a well-bounded addition: the coordinate geometry is straightforward once you understand that upstream=left in horizontal mode (negative X direction) and that side inputs still go above each spine node (negative Y direction, unchanged).

The two biggest design concerns are (1) the mask kink geometry — downstream spine segments must drop in Y to clear mask subtrees, producing a cumulative staircase — and (2) the output Dot, which routes the root's output leftward to its downstream consumer. Both have explicit geometry diagrams approved in CONTEXT.md. The memo key is extended to a 5-tuple including `layout_mode` to prevent cache collisions between vertical and horizontal calls on shared nodes.

State replay (HORIZ-03) is the simplest part: `_DEFAULT_STATE["mode"]` already existed, entry points already read stored state, and the write-back is conditional (`"horizontal"` or `"vertical"`) based on which path was taken.

**Primary recommendation:** Three plans — Plan 01: TDD RED scaffold; Plan 02: `place_subtree_horizontal()` + `_find_or_create_output_dot()` core; Plan 03: entry point wiring + menu + mode dispatch + compute_dims memo key.

**Implementation status (as of 2026-03-13):** COMPLETE. All 3 plans executed. All 10 tests GREEN. VERIFICATION passed 10/10.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `node_layout.py` | project | Layout engine — `place_subtree_horizontal()`, `_find_or_create_output_dot()`, entry points added here | All layout logic lives here |
| `node_layout_state.py` | project | Per-node state read/write — `_DEFAULT_STATE["mode"]` already had `"vertical"` | State helpers already present |
| `node_layout_prefs.py` | project | `horizontal_subtree_gap` pref drives spine step size | H-axis pref already used by `_horizontal_margin()` |
| `menu.py` | project | Registers "Layout Upstream Horizontal" and "Layout Selected Horizontal" | Established menu pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `unittest` / AST | stdlib | Tests without Nuke runtime | All Phase 11 tests — Nuke not available in CI |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Dedicated `place_subtree_horizontal()` | Axis-swapped call to `place_subtree()` | CONTEXT.md locked as dedicated function — different traversal logic for spine vs side inputs |
| Per-command horizontal menu entries | Prefs toggle | Commands are explicit, consistent with Phase 6 CMD-01 pattern; no hidden state for users |

---

## Architecture Patterns

### File Structure (as built)

```
node_layout.py
  _OUTPUT_DOT_KNOB_NAME = "node_layout_output_dot"   # module constant (line 10)
  + _find_or_create_output_dot()                       # new (line 349)
  + place_subtree_horizontal()                         # new (line 403)
  ~ compute_dims()                                     # modified: layout_mode param + 5-tuple memo key (line 518)
  ~ layout_upstream()                                  # modified: mode dispatch at line 950
  ~ layout_selected()                                  # modified: per-root mode dispatch at line 1061
  + layout_upstream_horizontal()                       # new entry point (line 1148)
  + layout_selected_horizontal()                       # new entry point (line 1236)

menu.py
  + "Layout Upstream Horizontal"    # after Clear Layout State commands
  + "Layout Selected Horizontal"    # after existing layout commands
```

### Pattern 1: place_subtree_horizontal() Two-Pass Spine Walk

**What:** Two-pass algorithm. First pass walks the spine ancestor-first (upstream to downstream), accumulating cumulative mask kink Y for each node. Second pass places each spine node at its final `(cur_x, spine_y + kink)`. Side inputs (slot 1+) are placed above each spine node using vertical formulas.

**Actual signature:**
```python
def place_subtree_horizontal(root, spine_x, spine_y, snap_threshold, node_count,
                             scheme_multiplier=None, per_node_h_scale=None,
                             per_node_v_scale=None, current_prefs=None,
                             current_group=None, memo=None):
```

**Key geometry (Nuke DAG: positive Y = down):**

```
Axis conventions in horizontal mode:
- B-spine direction: LEFT (negative X from root)
- "Above" side inputs: ABOVE (negative Y — same as vertical mode)
- Root is RIGHTMOST (highest X)
- Each upstream input[0] is step_x + node.screenWidth() to the LEFT

step_x = int(horizontal_subtree_gap * scheme_multiplier)   # gap portion only
cur_x for each spine node decremented by: step_x + upstream_node.screenWidth()

side input placement above spine node at (cur_x, cur_y):
  side_y = cur_y - vertical_gap_between(side, spine_node, ...) - side_node.screenHeight()
  side_x = _center_x(side_node.screenWidth(), cur_x, spine_node.screenWidth())

mask kink (spine node has mask input):
  mask_height = compute_dims(mask_node, ...)[1]
  mask_margin = _subtree_margin(spine_node, mask_slot, ...)
  cumulative_kink_y += mask_height + mask_margin
  # all nodes downstream (closer to root, lower index) drop by cumulative_kink_y
```

**Two-pass structure:**
```python
# Pass 1: accumulate kink amounts (walk from farthest ancestor toward root)
kink_y_per_index = [0] * len(spine_nodes)
cumulative_kink_y = 0
for reverse_index in range(len(spine_nodes) - 1, -1, -1):
    kink_y_per_index[reverse_index] = cumulative_kink_y
    # check mask inputs on this spine node; add their height to cumulative_kink_y

# Pass 2: place each node
cur_x = spine_x
for index, spine_node in enumerate(spine_nodes):
    cur_y = spine_y + kink_y_per_index[index]
    spine_node.setXpos(cur_x)
    spine_node.setYpos(cur_y)
    # place side inputs above...
    # advance cur_x leftward
```

### Pattern 2: _find_or_create_output_dot() — Actual Signature

**What:** Places a routing Dot below root; wired between root and consumer. Reuses existing Dot on replay (checks `consumer_node.input(consumer_slot)` for `node_layout_output_dot` knob before creating).

**Actual signature (differs from pre-implementation spec — consumer passed directly, not discovered):**
```python
def _find_or_create_output_dot(root, consumer_node, consumer_slot, current_group,
                               snap_threshold=None, scheme_multiplier=None):
```

**Reuse check:**
```python
currently_wired = consumer_node.input(consumer_slot)
if (currently_wired is not None
        and currently_wired.knob(_OUTPUT_DOT_KNOB_NAME) is not None):
    return currently_wired
```

**Dot position:**
```python
dot_x = root.xpos() + (root.screenWidth() - dot.screenWidth()) // 2
dot_y = (root.ypos() + root.screenHeight()
         + vertical_gap_between(dot, root, snap_threshold, scheme_multiplier))
```

**IMPORTANT:** Callers must discover the consumer themselves before calling `_find_or_create_output_dot`. The function does NOT search for the consumer. Pattern for consumer discovery:
```python
def _find_downstream_consumer(root, current_group):
    all_nodes = current_group.nodes() if current_group is not None else nuke.allNodes()
    for node in all_nodes:
        for slot in range(node.inputs()):
            if node.input(slot) is root:
                return node, slot
    return None, None
```

### Pattern 3: Mode Dispatch at Entry Points

```python
# In layout_upstream() — line 950:
root_mode = node_layout_state.read_node_state(root)["mode"]
if root_mode == "horizontal":
    place_subtree_horizontal(root, ...)
    _find_or_create_output_dot(root, consumer_node, consumer_slot, current_group)
    layout_mode_to_write = "horizontal"
else:
    # existing vertical path
    layout_mode_to_write = "vertical"

# State write-back:
stored_state["mode"] = layout_mode_to_write
```

**In `layout_selected()` — mode dispatch is per-root:** Each root in a multi-root selection reads its own stored mode independently. Roots in the same selection can mix horizontal and vertical.

### Pattern 4: compute_dims Memo Key — INLINE TUPLE REQUIRED

**CRITICAL CONSTRAINT:** The memo key MUST use inline tuple syntax, NOT a named `memo_key` variable.

The test `test_compute_dims_memo_key_includes_node_h_scale` uses AST text search for `node_h_scale` within 80 characters of `memo[`. A named variable (`memo[memo_key]`) breaks this check because `node_h_scale` is no longer adjacent to `memo[`.

**Correct (as built):**
```python
# line 521-522 of node_layout.py
if (id(node), scheme_multiplier, node_h_scale, node_v_scale, layout_mode) in memo:
    return memo[(id(node), scheme_multiplier, node_h_scale, node_v_scale, layout_mode)]
```

**Wrong (breaks AST test):**
```python
memo_key = (id(node), scheme_multiplier, node_h_scale, node_v_scale, layout_mode)
if memo_key in memo:
    return memo[memo_key]  # 'node_h_scale' not within 80 chars of 'memo['
```

**Signature:**
```python
def compute_dims(node, memo, snap_threshold, node_count, node_filter=None,
                 scheme_multiplier=None, per_node_h_scale=None,
                 per_node_v_scale=None, layout_mode="vertical"):
```

### Pattern 5: Undo Wrapping (entry points)

```python
def layout_upstream_horizontal(scheme_multiplier=None):
    global _TOOLBAR_FOLDER_MAP
    _TOOLBAR_FOLDER_MAP = None
    _clear_color_cache()
    current_group = nuke.lastHitGroup()   # MUST be first Nuke API call
    root = nuke.selectedNode()
    nuke.Undo.name("Layout Upstream Horizontal")
    nuke.Undo.begin()
    try:
        with current_group:
            # ... implementation
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()
```

### Anti-Patterns to Avoid

- **Reading state inside recursion:** Never call `read_node_state()` inside `place_subtree_horizontal()` or `compute_dims()` — breaks memoization (Phase 7 rule).
- **Module globals for layout mode:** `layout_mode` must propagate as an explicit parameter, never a module-level variable (Phase 7 decision).
- **Named memo_key variable:** Use inline tuple directly in `memo[...]` — AST test requires `node_h_scale` to be within 80 chars of `memo[`.
- **Swapped-argument call to `place_subtree()`:** The horizontal function is dedicated. Traversal logic differs fundamentally (spine walk vs tree recursion).
- **Recreating output Dots on every replay:** Check `consumer_node.input(consumer_slot)` for `node_layout_output_dot` knob before creating.
- **Auto-discovering consumer inside `_find_or_create_output_dot`:** Consumer is passed by the caller, not discovered internally — this is what the tests enforce.
- **Forgetting mask side-swap suppression:** In horizontal mode, Phase 9's mask-to-left behavior must NOT apply to spine nodes' side inputs. Mask goes above (negative Y), not left.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| H-axis spine step size | Custom gap formula | `int(horizontal_subtree_gap * scheme_multiplier)` via prefs | Pref already exists; consistent with Phase 6 |
| V-axis side input gaps | New gap logic | `vertical_gap_between()` + `_subtree_margin()` — identical to normal layout | Proven formulas; font scaling (Phase 8) comes free |
| State knob creation | New knob API | `write_node_state()` / `read_node_state()` from `node_layout_state` | Tab+String knob pattern handles INVISIBLE, JSON, persistence |
| Dot creation/wiring | `nuke.nodes.Dot()` calls inline | `_find_or_create_output_dot()` pattern | Auto-connection guard (deselect all first) must not be skipped |
| Group context | `nuke.thisGroup()` | `nuke.lastHitGroup()` (established Phase 6 pattern) | Works for both Ctrl-Enter and Group View panels |

**Key insight:** All gap formulas, state helpers, and Dot-wiring patterns are already proven in earlier phases. Phase 11 is geometry assembly, not infrastructure building.

---

## Common Pitfalls

### Pitfall 1: Y-axis sign in Nuke DAG
**What goes wrong:** Placing "above" nodes with positive Y offset instead of negative — nodes appear below root instead of above.
**Why it happens:** Nuke DAG has positive Y = down. "Above" (upstream) means LOWER Y value.
**How to avoid:** Always subtract when placing upstream nodes: `side_y = cur_y - raw_gap - side_node.screenHeight()`.
**Warning signs:** Side inputs appear below their spine node in the DAG.

### Pitfall 2: Memo key collision (horizontal vs vertical)
**What goes wrong:** `compute_dims()` returns wrong dimensions for nodes that appear in both a horizontal and a vertical layout in the same session.
**Why it happens:** Old memo key was a 4-tuple without layout_mode.
**How to avoid:** 5-tuple key: `(id(node), scheme_multiplier, node_h_scale, node_v_scale, layout_mode)`. Default `layout_mode="vertical"` ensures backward compatibility.
**Warning signs:** Nodes appear at wrong positions when mixing horizontal and vertical layouts.

### Pitfall 3: Output Dot auto-connection
**What goes wrong:** Nuke auto-connects newly created Dot to the most recently selected node instead of root.
**Why it happens:** Nuke's Dot auto-connect fires on creation if any node is selected.
**How to avoid:** Deselect all before `nuke.nodes.Dot()`, then `dot.setInput(0, root)` explicitly.
**Warning signs:** Output Dot connects to wrong node.

### Pitfall 4: Named memo_key variable breaks AST test
**What goes wrong:** `test_compute_dims_memo_key_includes_node_h_scale` fails even though the memo key is correct.
**Why it happens:** The test checks for `node_h_scale` within 80 characters of `memo[` in the source text. A named `memo_key = (...)` variable separates `node_h_scale` from `memo[memo_key]`.
**How to avoid:** Always use inline tuple directly: `memo[(id(node), scheme_multiplier, node_h_scale, node_v_scale, layout_mode)]`.
**Warning signs:** This specific test fails after any refactor of `compute_dims`.

### Pitfall 5: Mask side-swap suppression
**What goes wrong:** Phase 9's `_reorder_inputs_mask_last()` with `fan_active=True` moves mask to the left of the consumer — wrong in horizontal mode (mask should go above, not left).
**Why it happens:** `place_subtree_horizontal()` calls Phase 9 logic for side inputs without overriding mask reordering.
**How to avoid:** Side input placement in `place_subtree_horizontal()` uses `setXpos/setYpos` directly without calling `_reorder_inputs_mask_last()` or the fan-active mask-left path.
**Warning signs:** Mask input appears to the left of the spine node instead of above it.

### Pitfall 6: Cumulative mask kink accounting
**What goes wrong:** Each mask kink drops the baseline Y independently — downstream segments collide with mask subtrees.
**Why it happens:** Kink computed per-spine-node without summing previous drops.
**How to avoid:** Maintain `cumulative_kink_y` running total; assign to `kink_y_per_index[reverse_index]` before adding this node's own mask height. Two-pass algorithm.
**Warning signs:** Spine nodes with multiple mask inputs overlap or sit in the wrong vertical band.

### Pitfall 7: Output Dot persisted across undo
**What goes wrong:** After undo, output Dot persists in the DAG corrupting the graph.
**Why it happens:** Dot creation is inside the undo group — undo removes it; reuse check is also inside the undo group — reuse is also undone.
**How to avoid:** Dot creation and wiring inside `nuke.Undo.begin()/end()`. Undo removes the Dot on rollback. Replay creates a new one. Matches diamond-dot behavior.
**Warning signs:** DAG has orphan Dots after undo.

### Pitfall 8: _find_or_create_output_dot consumer discovery
**What goes wrong:** Passing `None` as `consumer_node` (because auto-discovery was expected inside the function) — function returns None, no Dot is created.
**Why it happens:** Original pre-implementation spec described internal consumer discovery. As-built signature requires caller to pass consumer directly.
**How to avoid:** Caller always calls `_find_downstream_consumer(root, current_group)` first; passes result to `_find_or_create_output_dot`.
**Warning signs:** No Dot created below root; downstream consumer wires go directly to root.

---

## Code Examples

Verified patterns from actual implementation:

### Dot knob creation (output dot — from _find_or_create_output_dot)
```python
# Source: node_layout.py _find_or_create_output_dot() line 386
dot = nuke.nodes.Dot()
dot.addKnob(nuke.Tab_Knob('node_layout_tab', 'Node Layout'))
dot.addKnob(nuke.Int_Knob(_OUTPUT_DOT_KNOB_NAME, 'Output Dot Marker'))
dot[_OUTPUT_DOT_KNOB_NAME].setValue(1)
dot.setInput(0, root)
consumer_node.setInput(consumer_slot, dot)
```

### State mode write-back — conditional on path
```python
# Source: node_layout.py layout_upstream() lines 971, 980
layout_mode_to_write = "horizontal" if root_mode == "horizontal" else "vertical"
# ...later in write-back loop:
stored_state["mode"] = layout_mode_to_write
node_layout_state.write_node_state(state_node, stored_state)
```

### compute_dims — layout_mode parameter and 5-tuple key
```python
# Source: node_layout.py lines 518-522
def compute_dims(node, memo, snap_threshold, node_count, node_filter=None,
                 scheme_multiplier=None, per_node_h_scale=None,
                 per_node_v_scale=None, layout_mode="vertical"):
    node_h_scale = per_node_h_scale.get(id(node), 1.0) if per_node_h_scale else 1.0
    node_v_scale = per_node_v_scale.get(id(node), 1.0) if per_node_v_scale else 1.0
    if (id(node), scheme_multiplier, node_h_scale, node_v_scale, layout_mode) in memo:
        return memo[(id(node), scheme_multiplier, node_h_scale, node_v_scale, layout_mode)]
```

### Menu command registration
```python
# Source: menu.py lines 29-30
layout_menu.addCommand('Layout Upstream Horizontal', node_layout.layout_upstream_horizontal)
layout_menu.addCommand('Layout Selected Horizontal', node_layout.layout_selected_horizontal)
```

### Deselect guard before Dot creation
```python
# Source: node_layout.py _find_or_create_output_dot() lines 383-384
for selected_node in nuke.selectedNodes():
    selected_node['selected'].setValue(False)
```

### Find downstream consumer of root
```python
# Source: established pattern used at entry points
def _find_downstream_consumer(root, current_group):
    all_nodes = current_group.nodes() if current_group is not None else nuke.allNodes()
    for node in all_nodes:
        for slot in range(node.inputs()):
            if node.input(slot) is root:
                return node, slot
    return None, None
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single vertical placement | Vertical + horizontal dispatch | Phase 11 | `layout_upstream/selected` read mode before dispatch |
| `mode = "vertical"` hardcoded in write-back | Conditional `"horizontal"` or `"vertical"` | Phase 11 | Enables HORIZ-03 replay |
| Memo key: `(id, scheme, h_scale, v_scale)` 4-tuple | 5-tuple `+ layout_mode` | Phase 11 | Prevents horizontal/vertical cache collision |
| `_find_or_create_output_dot(root, snap, scheme, group)` with internal consumer discovery | `(root, consumer_node, consumer_slot, group, snap=None, scheme=None)` | Phase 11 Plan 02 deviation | Tests are authoritative; consumer passed by caller |

**Deprecated/outdated:**
- Hardcoded `stored_state["mode"] = "vertical"` in both `layout_upstream()` and `layout_selected()` — now conditional.
- Any pre-implementation spec showing `_find_or_create_output_dot` with internal consumer discovery — as-built takes consumer as parameter.

---

## Open Questions

All open questions from original research are now resolved:

1. **compute_dims for horizontal subtrees** — RESOLVED: `place_subtree_horizontal()` calls `compute_dims()` only for side-input/mask subtrees (to know their height for kink drops). The spine walk is linear — no pre-computation needed for X positions.

2. **push_nodes_to_make_room in horizontal mode** — RESOLVED: `layout_upstream_horizontal()` calls `push_nodes_to_make_room()` with the existing function after placement. Leftward spine growth is handled by the before/after bounding-box comparison in the push logic.

3. **layout_selected horizontal — multiple roots** — RESOLVED: `layout_selected()` mode dispatch is per-root. Each root reads its own stored mode independently. Roots in the same selection can mix horizontal and vertical. `layout_selected_horizontal()` applies horizontal mode to each selected root independently.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Python unittest (stdlib) |
| Config file | none — direct `python3 -m unittest discover tests/` |
| Quick run command | `python3 -m unittest tests/test_horizontal_layout.py -v` |
| Full suite command | `python3 -m unittest discover tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HORIZ-01 | `place_subtree_horizontal()` places root rightmost, each input[0] one step left | unit | `python3 -m unittest tests/test_horizontal_layout.py::TestHorizontalSpine -v` | ✅ GREEN |
| HORIZ-01 | Output Dot created below root when downstream consumer exists | unit | `python3 -m unittest tests/test_horizontal_layout.py::TestOutputDot -v` | ✅ GREEN |
| HORIZ-01 | Output Dot reused (not recreated) on replay | unit | `python3 -m unittest tests/test_horizontal_layout.py::TestOutputDot -v` | ✅ GREEN |
| HORIZ-01 | Mask kink drops downstream segment by mask subtree height | unit | `python3 -m unittest tests/test_horizontal_layout.py::TestMaskKink -v` | ✅ GREEN |
| HORIZ-01 | Side inputs (A, fan) placed above spine node, not to the side | unit | `python3 -m unittest tests/test_horizontal_layout.py::TestSideInputPlacement -v` | ✅ GREEN |
| HORIZ-02 | `layout_selected_horizontal()` exists in node_layout.py (AST) | unit | `python3 -m unittest tests/test_horizontal_layout.py::TestHorizontalAST -v` | ✅ GREEN |
| HORIZ-02 | `layout_upstream_horizontal()` exists in node_layout.py (AST) | unit | `python3 -m unittest tests/test_horizontal_layout.py::TestHorizontalAST -v` | ✅ GREEN |
| HORIZ-03 | `layout_upstream()` dispatches to horizontal when stored mode is "horizontal" | unit | `python3 -m unittest tests/test_horizontal_layout.py::TestModeReplay -v` | ✅ GREEN |
| HORIZ-03 | `layout_selected()` dispatches to horizontal when stored mode is "horizontal" | unit | `python3 -m unittest tests/test_horizontal_layout.py::TestModeReplay -v` | ✅ GREEN |
| HORIZ-03 | compute_dims memo key includes layout_mode (AST) | unit | `python3 -m unittest tests/test_horizontal_layout.py::TestHorizontalAST -v` | ✅ GREEN |

### Sampling Rate
- **Per task commit:** `python3 -m unittest tests/test_horizontal_layout.py -q`
- **Per wave merge:** `python3 -m unittest discover tests/ -q`
- **Phase gate:** Full suite green (only pre-existing 4 errors from test_scale_nodes_axis nuke stub issue allowed)

### Wave 0 Gaps
None — `tests/test_horizontal_layout.py` created in Plan 01 and all 10 tests pass GREEN.

---

## Sources

### Primary (HIGH confidence)
- `/workspace/node_layout.py` — full source read; `place_subtree_horizontal()` at line 403, `_find_or_create_output_dot()` at line 349, `compute_dims()` at line 518, `layout_upstream_horizontal()` at line 1148, `layout_selected_horizontal()` at line 1236 — all directly examined
- `/workspace/node_layout_state.py` — `_DEFAULT_STATE`, `read_node_state()`, `write_node_state()` directly examined
- `/workspace/node_layout_prefs.py` — `DEFAULTS` dict including `horizontal_subtree_gap` directly examined
- `/workspace/.planning/phases/11-horizontal-b-spine-layout/11-CONTEXT.md` — locked decisions and geometry diagrams
- `/workspace/.planning/STATE.md` — accumulated decisions from Phases 6-11
- `/workspace/.planning/phases/11-horizontal-b-spine-layout/11-01-SUMMARY.md` — Plan 01 decisions
- `/workspace/.planning/phases/11-horizontal-b-spine-layout/11-02-SUMMARY.md` — Plan 02 decisions (including signature deviation)
- `/workspace/.planning/phases/11-horizontal-b-spine-layout/11-03-SUMMARY.md` — Plan 03 decisions (including inline memo key constraint)
- `/workspace/.planning/phases/11-horizontal-b-spine-layout/11-VERIFICATION.md` — 10/10 verification result

### Secondary (MEDIUM confidence)
- `/workspace/tests/test_horizontal_layout.py` — confirmed test pattern and stub extensions
- `/workspace/menu.py` — confirmed menu registration at lines 29-30

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all relevant code directly read from source
- Architecture: HIGH — geometry diagrams from CONTEXT.md + directly verified as-built implementation
- Pitfalls: HIGH — derived from direct code reading and Plan 02/03 deviation logs
- Implementation status: HIGH — VERIFICATION report 10/10, all tests GREEN

**Research date:** 2026-03-12
**Updated:** 2026-03-13 (post-implementation revision)
**Valid until:** Indefinite — all findings from internal codebase, no external dependencies

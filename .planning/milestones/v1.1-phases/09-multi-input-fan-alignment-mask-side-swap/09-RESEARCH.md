# Phase 9: Multi-Input Fan Alignment + Mask Side-Swap — Research

**Researched:** 2026-03-11
**Domain:** Python layout geometry — `compute_dims` / `place_subtree` branching in `node_layout.py`
**Confidence:** HIGH (all findings sourced directly from the project codebase; no external libraries involved)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Fan trigger**
- Fan activates when the consumer has **3 or more non-mask inputs** (input[0]/B counts as non-mask)
- 2 non-mask inputs: existing stacking behavior unchanged (B above, A to the right at staircase Y)
- 0 non-mask inputs (mask only): mask stays right, no change
- `all_side` mode: fan applies when 3+ non-mask inputs are present in that mode too

**Fan geometry — subtree root placement**
- B (input[0]) stays **directly above the consumer** (same column, same gap formula as current)
- A1, A2, etc. fan **rightward** from the consumer's right edge at the **same Y as B's subtree root**
- The shared fan-level Y is determined by `vertical_gap_between` for the B slot (existing formula — no change)

**Routing Dots**
- **All** inputs — including B — receive a routing Dot placed directly beneath their subtree root
- All routing Dots are at the **same Y row** (a uniform horizontal row between the fan roots and the consumer)
- The Dot row Y is determined by the existing `vertical_gap_between` formula for the B slot
- Consumer connects to all Dots; B's wire is straight down, A1/A2 wires are diagonal

**Mask side-swap (fan-active only)**
- When 3+ non-mask inputs: mask input is placed to the **LEFT** of the consumer
- Positioning: `right edge of mask subtree bbox = consumer_left_x - horizontal_mask_gap`
  (i.e., `mask_x = consumer_x - horizontal_mask_gap - mask_subtree_width`)
- Uses the existing `horizontal_mask_gap` pref — no new pref needed
- Mask also gets a routing Dot directly beneath its subtree root
- Mask subtree root is at its own Y (existing `_subtree_margin` with `mask_input_ratio` — V-axis logic unchanged)

**Mask side-swap trigger**
- Only swaps left when fan is active (3+ non-mask inputs)
- With 1 non-mask + mask: mask stays right as today

**Height formula (compute_dims)**
- Fan case: total height = `max(fan subtree heights)` + gap-to-fan + consumer height
  (NOT the current sum — same-Y means subtrees extend independently, not stacked)
- Horizontal spacing between fan columns prevents vertical overlap — no V constraint needed

**Claude's Discretion**
- Exact vertical position of the Dot row relative to the fan roots and consumer
- How the `all_side` fan path is structured in code (shared helper vs branching)
- How to detect "3+ non-mask inputs" cleanly given the existing `_is_mask_input` helper

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LAYOUT-01 | When a node has 2+ non-mask inputs, all immediate input nodes are placed at the same Y position (fan alignment), with their subtrees extending upward | Fan branch in `compute_dims` (max-height formula) and `place_subtree` (uniform Y for all non-mask roots + Dot row) |
| LAYOUT-02 | When a node has 2+ non-mask inputs, the mask input is placed to the left of all non-mask inputs | `_reorder_inputs_mask_last` becomes `_reorder_inputs_mask_first_when_fan`; `place_subtree` computes `mask_x = consumer_x - horizontal_mask_gap - mask_subtree_width` |
</phase_requirements>

---

## Summary

Phase 9 is a pure geometry change: no new prefs, no new commands, no new knobs. All work is confined to `compute_dims`, `place_subtree`, and `_reorder_inputs_mask_last` in `/workspace/node_layout.py`.

The fan trigger is **3 or more non-mask inputs** (the roadmap spec says "2+" but CONTEXT.md locked the threshold at 3+). The existing `_is_mask_input(node, i)` helper and the existing `n >= 3` branching skeleton in both `compute_dims` and `place_subtree` are the main scaffolding. The changes require replacing the staircase height formula with a max-height formula and repositioning all subtree roots to a shared Y level, plus adding a B-slot Dot to the routing row that previously only existed for side inputs.

The mask side-swap is structurally a reversal of `_reorder_inputs_mask_last`: instead of appending the mask to the tail (rightmost), in fan mode the mask goes to the front of the list — then `place_subtree` places the front item to the LEFT of the consumer rather than the right.

**Primary recommendation:** Introduce a `_is_fan_active(input_slot_pairs, node)` predicate, use it as the branching gate in both `compute_dims` and `place_subtree`, and rename / extend `_reorder_inputs_mask_last` to handle the fan-active mask-first case.

---

## Standard Stack

No new dependencies. This phase uses only the existing project module.

| File | Purpose | Scope of Change |
|------|---------|----------------|
| `/workspace/node_layout.py` | Core layout engine | `compute_dims`, `place_subtree`, `_reorder_inputs_mask_last` |
| `/workspace/tests/` | AST + stub-based unit tests | New test file `test_fan_alignment.py` |

---

## Architecture Patterns

### Existing Code Structure (what Phase 9 inherits)

```
compute_dims(node, ...)
  ├── not inputs              → (W=node_width, H=node_height)
  ├── all_side                → W = node_w + sum(margins_h + child_ws)
  │                             H = node_h + sum(child_hs) + 2*gap + inter_band_gaps
  └── else (normal mode)
        ├── n == 1            → W = max(node_w, child0_w)
        ├── n == 2            → W = max(child0_w, node_w + margin_h[1] + child1_w)
        └── n >= 3            → W = max(child0_w, node_w + sum(margins_h[1:]) + sum(child_ws[1:]))
                                H = node_h + sum(child_hs) + 2*gap + inter_band_gaps  ← CHANGES

place_subtree(node, x, y, ...)
  ├── all_side mode           → Dots for all inputs; staircase Y; rightward X
  ├── n == 1                  → centered above
  ├── n == 2                  → [0] centered; [1] rightward + Dot
  └── n >= 3                  → [0] centered; [1..n-1] rightward + Dots
                                Bottom-most Dot: Y centered beside root  ← CHANGES
                                Other Dots: staggered below input         ← CHANGES
```

### Pattern 1: Fan-Active Predicate

**What:** A single predicate function, called in both `compute_dims` and `place_subtree`, that decides whether the fan layout is in effect for a given consumer node + input list.

**When to use:** Immediately after `_reorder_inputs_mask_last` has been called, before the geometry branches.

**Example:**
```python
# Source: CONTEXT.md locked decisions
def _is_fan_active(input_slot_pairs, node):
    """Return True when 3+ non-mask inputs are present (fan mode)."""
    non_mask_count = sum(
        1 for slot, _ in input_slot_pairs if not _is_mask_input(node, slot)
    )
    return non_mask_count >= 3
```

This keeps the threshold rule in one place. Both `compute_dims` and `place_subtree` call it after building `input_slot_pairs`.

### Pattern 2: Mask-First Reordering (fan mode)

**What:** Extension of `_reorder_inputs_mask_last` that, in fan mode, moves the mask to the FRONT so that the placement loop handles it as a left-side item.

**When to use:** When `_is_fan_active` returns True, apply mask-first ordering; otherwise retain existing mask-last ordering.

**Design note (Claude's discretion):** The cleanest approach is to rename `_reorder_inputs_mask_last` to `_reorder_inputs` and give it a `fan_active` boolean parameter. Existing callers pass `fan_active=False` (default) and behavior is unchanged.

```python
# Conceptual sketch only — planner determines exact signature
def _reorder_inputs(input_slot_pairs, node, all_side, fan_active=False):
    if len(input_slot_pairs) <= 2:
        return input_slot_pairs
    if fan_active:
        # mask goes LEFT (front of list)
        ...
    else:
        # existing mask-last logic
        ...
```

### Pattern 3: Fan Height Formula in compute_dims

**What:** Replace the staircase `H = sum(child_hs) + ...` with `H = max(child_hs) + ...` for the fan-active `n >= 3` case.

**Geometry:**
```
# Current (staircase — stacked bands):
H = node_h + sum(child_hs) + 2 * gap_to_consumer + inter_band_gaps

# Fan (parallel — independent subtrees):
H = node_h + max(child_hs) + gap_to_consumer
```

The gap from the fan-root row to the consumer is `vertical_gap_between(inputs[0], node, snap_threshold, scheme_multiplier)` (B slot gap — unchanged).

Width formula (W) for the fan case is the same as the existing `n >= 3` staircase formula — no change needed.

**Note:** The mask subtree (when fan-active) is placed to the LEFT and does NOT contribute to W in the rightward direction. The W formula must exclude the mask from the right-side sum when computing the rightward spread. The mask contributes to a left-side extent which callers that read bounding boxes will pick up naturally.

### Pattern 4: Fan Y Placement in place_subtree

**What:** In fan mode, ALL non-mask inputs (including B / input[0]) get the same `y_position` (the fan-root row), then each gets a routing Dot placed at the same Dot-row Y directly below it.

**Geometry (Claude's discretion — Dot row position):**

The most natural placement puts the Dot row Y such that:
```
dot_y = y - gap_to_consumer + (consumer_height - dot_height) // 2
```
This mirrors the existing "bottom-most dot: centre it vertically beside the root" logic (lines 526–528 of current code) but applies it UNIFORMLY to all inputs in fan mode, including B.

**Fan root Y (same for all non-mask inputs):**
```python
fan_root_gap = vertical_gap_between(inputs[0], node, snap_threshold, scheme_multiplier)
fan_root_gap = max(snap_threshold - 1, int(fan_root_gap * node_v_scale))
fan_root_gap = max(fan_root_gap, side_margins_v[0])  # ensure Dot row fits
fan_y = y - fan_root_gap - inputs[0].screenHeight()
```

All non-mask inputs placed at `fan_y` regardless of index.

**Fan X (non-mask inputs):**
- B (index 0, or wherever B ends up after reorder): centered above consumer
- A1, A2, ... : step rightward from consumer's right edge using `side_margins_h`
  (same formula as existing `n >= 3` rightward spread)

**Mask X (fan-active):**
```python
mask_x = x - horizontal_mask_gap - mask_subtree_width
# where mask_subtree_width = child_dims[mask_index][0]
# and horizontal_mask_gap = _horizontal_margin(node, mask_slot) * node_h_scale
```

**Mask Y (unchanged):** mask subtree root at its own Y determined by `_subtree_margin` with `mask_input_ratio` — same as today.

### Pattern 5: Dot Row (all inputs get Dots in fan mode)

**What:** In the existing code, only side inputs (`i > 0`) get routing Dots. In fan mode, B (i == 0) ALSO gets a routing Dot.

**Current code (lines 504–514):**
```python
else:
    # Only non-primary inputs (i > 0) need dots.
    for i in range(1, n):
        ...
```

**Fan-mode change:** The loop expands to `range(0, n)` for ALL non-mask inputs. The mask also gets a Dot (it is a side input in all cases; existing side-Dot code already handles mask).

**Dot placement within recursion loop (lines 518–533):** The `is_side_dot` check and the `if i == n - 1` branch for "bottom-most dot" must be replaced in fan mode. In fan mode ALL Dots go to the same `dot_y` row regardless of index.

### Existing Code — Key Lines to Change

| Location | Line range | Current behaviour | Phase 9 change |
|----------|-----------|-------------------|----------------|
| `compute_dims` — `else` branch height | 358–365 | Staircase H (sum of child heights) | Fan case: H = max(child heights) + gap + node_h |
| `place_subtree` — Dot insertion | 504–514 | Only `i > 0` get Dots | Fan mode: `range(0, n)` for non-mask inputs |
| `place_subtree` — Dot Y placement | 526–533 | Bottom-most Dot centered beside root; others staggered | Fan mode: ALL Dots at same row Y |
| `place_subtree` — Y positions | 462–465 | Staircase Y per band | Fan mode: uniform `fan_y` for all non-mask inputs |
| `place_subtree` — X positions (n >= 3) | 482–488 | `[0]` centered; `[1..]` rightward | Same W logic; mask goes LEFT |
| `_reorder_inputs_mask_last` | 180–198 | Mask appended to end | Fan active: mask moved to front (or separate list) |

### Anti-Patterns to Avoid

- **Modifying the `all_side` branch for fan:** The `all_side` branch handles a different structural case (all in-filter inputs are side inputs because slot 0 is occupied externally). Fan mode is a separate branch — don't conflate them. CONTEXT.md says `all_side` fan applies when 3+ non-mask inputs; this means the fan check must run inside the `all_side` branch too.
- **Using a module global for fan state:** Every layout call in Phase 9 derives fan state from the local `input_slot_pairs` list, not a global. Keeping it local avoids re-entrant state bugs during recursion.
- **Changing the mask's V-axis formula:** CONTEXT.md explicitly locks the mask V-axis to the existing `_subtree_margin` / `mask_input_ratio` logic. Only the X placement changes.
- **Omitting B's Dot in fan mode:** The CONTEXT.md diagram shows ALL inputs — including B — with routing Dots. Omitting B's Dot would leave B connected via a bare diagonal wire, which breaks the visual row.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Counting non-mask inputs | Custom counter per call site | `_is_fan_active(input_slot_pairs, node)` helper calling `_is_mask_input` |
| Horizontal mask gap value | Hard-coded constant | `_horizontal_margin(node, mask_slot)` (already reads `horizontal_mask_gap` pref with font scaling) |
| Routing Dots for fan inputs | New Dot creation logic | Re-use the existing Dot creation pattern from lines 507–514; same 4-line block, expanded loop range |
| Mask subtree width | Manual traversal | `compute_dims(mask_input, ...)[0]` — already computed in `child_dims` list |

---

## Common Pitfalls

### Pitfall 1: Memo Cache Collision After Reordering

**What goes wrong:** `compute_dims` uses `(id(node), scheme_multiplier, node_h_scale, node_v_scale)` as memo key. After Phase 9 adds `_is_fan_active` branching INSIDE `compute_dims`, the same node could be computed with different active-fan states if it appears in two different subtrees with different parent contexts. In practice this can't happen for the consumer node itself, but if a shared subtree node feeds into a fan consumer through multiple paths, the memo result must still be correct.

**Why it happens:** `_is_fan_active` is a property of the CONSUMER, not the child. The child's own `compute_dims` call doesn't depend on whether its consumer is in fan mode — only the consumer's own dims calculation depends on fan state. So the child's memo entry is safe; only the consumer's entry needs to branch.

**How to avoid:** The fan branching goes at the consumer level inside `compute_dims`, not inside recursive child calls. The child recursion is unchanged. No memo key change is required.

**Warning signs:** If you find yourself passing a `fan_active` flag INTO recursive `compute_dims` calls, stop — that flag belongs only at the consumer level.

### Pitfall 2: Mask Appearing in the Right-Side Width Calculation

**What goes wrong:** The mask subtree is placed LEFT of the consumer, but if the mask is still included in the `sum(w for w, h in child_dims[1:])` used to compute total `W`, the bounding box will be over-wide to the right.

**Why it happens:** After `_reorder_inputs` puts the mask at index 0 (front), the existing `[1:]` slice for side inputs would include A1, A2, etc. but NOT the mask. However in the current `n >= 3` W formula, `child_dims[0]` is B (centered above) and `child_dims[1:]` are the rightward inputs. The mask is not in the `[1:]` slice, so once reordering is correct the W formula is automatically correct — the mask's width is NOT added to the right-side sum.

**How to avoid:** Verify the list order after `_reorder_inputs` is called: mask first, then B, then A1/A2. Ensure the rightward W formula only sums non-mask children.

### Pitfall 3: Dot Row Y Out of Sync Between compute_dims and place_subtree

**What goes wrong:** `compute_dims` uses `gap_to_consumer` to reserve vertical space for the Dot row. If `place_subtree` places the Dot row at a different Y (e.g., recalculated with a slightly different rounding), the Dot row sits outside the reserved space and overlaps the consumer node.

**Why it happens:** Both functions independently compute `vertical_gap_between` and apply `max(snap_threshold - 1, int(raw_gap * node_v_scale))`. If the fan-Y calculation in `place_subtree` uses a different formula than what `compute_dims` reserved for, the Dots land in the wrong row.

**How to avoid:** The Dot row Y is `y - gap_closest` (using the same `gap_closest` derived from B's `vertical_gap_between`). Both `compute_dims` and `place_subtree` must use the SAME formula for this value — derive it once with the same inputs.

### Pitfall 4: B's Dot Overwriting B's Subtree

**What goes wrong:** When B is already a Dot node (diamond resolution), the code `if inputs[i].Class() != 'Dot': create dot...` correctly skips creation. But in fan mode when we place B's routing Dot, the existing Dot for B may be a diamond Dot (with `node_layout_diamond_dot` knob and `hide_input=True`). These are NOT routing Dots and must not be treated as such.

**Why it happens:** The existing code at line 518 checks `is_side_dot = (all_side or i > 0) and inp.Class() == 'Dot' and not _hides_inputs(inp)`. Fan mode needs to extend this to include `i == 0` for the B-slot Dot, but the `not _hides_inputs(inp)` guard already prevents diamond Dots from being treated as routing Dots.

**How to avoid:** Keep the `not _hides_inputs(inp)` guard when extending the `is_side_dot` check to include `i == 0` in fan mode.

### Pitfall 5: Nuke DAG Coordinate Direction

**What goes wrong:** Inputs (upstream nodes) have SMALLER Y values than their consumers. When computing "fan roots above the consumer," subtract from `y` (consumer top-left Y), not add.

**Why it happens:** The project `CLAUDE.md` documents this: positive Y is DOWN, negative Y is UP in the DAG. Fan roots are placed at smaller Y (higher on screen) than the consumer.

**How to avoid:** Fan root Y = `consumer_y - gap - input_height`. The gap from B's `vertical_gap_between` is positive; subtracting it gives a higher position on screen.

---

## Code Examples

Verified patterns from the existing codebase:

### Existing `_reorder_inputs_mask_last` (lines 180–198)
```python
# Source: /workspace/node_layout.py lines 180-198
def _reorder_inputs_mask_last(input_slot_pairs, node, all_side):
    if len(input_slot_pairs) <= 2:
        return input_slot_pairs
    if all_side:
        non_mask = [(slot, inp) for slot, inp in input_slot_pairs if not _is_mask_input(node, slot)]
        mask_inputs = [(slot, inp) for slot, inp in input_slot_pairs if _is_mask_input(node, slot)]
        return non_mask + mask_inputs
    primary = input_slot_pairs[:1]
    side = input_slot_pairs[1:]
    side_non_mask = [(slot, inp) for slot, inp in side if not _is_mask_input(node, slot)]
    side_mask = [(slot, inp) for slot, inp in side if _is_mask_input(node, slot)]
    return primary + side_non_mask + side_mask
```

Phase 9 extends this to support a `fan_active` mode where mask goes FRONT (leftmost in list, placed leftward of consumer).

### Existing Dot Insertion for Side Inputs (lines 504–514)
```python
# Source: /workspace/node_layout.py lines 504-514
else:
    # Only non-primary inputs (i > 0) need dots.
    for i in range(1, n):
        if inputs[i].Class() != 'Dot':
            dot = nuke.nodes.Dot()
            for auto_slot in range(dot.inputs()):
                dot.setInput(auto_slot, None)
            dot.setInput(0, inputs[i])
            node.setInput(actual_slots[i], dot)
            inputs[i] = dot
```

Fan mode expands `range(1, n)` to `range(0, n)` for non-mask inputs (including B at index 0).

### Existing Bottom-Most Dot Y Centering (lines 526–528)
```python
# Source: /workspace/node_layout.py lines 526-528
if i == n - 1:
    # Bottom-most dot: centre it vertically beside the root node.
    dot_y = y + (node.screenHeight() - inp.screenHeight()) // 2
```

Fan mode replaces the `if i == n - 1` special case with a SINGLE uniform `dot_row_y` applied to ALL routing Dots.

### Existing Gap Formula (lines 456–459)
```python
# Source: /workspace/node_layout.py lines 456-459
raw_gap_closest = vertical_gap_between(inputs[n - 1], node, snap_threshold, scheme_multiplier)
gap_closest = max(snap_threshold - 1, int(raw_gap_closest * node_v_scale))
if n > 1 or all_side:
    gap_closest = max(gap_closest, side_margins_v[n - 1])
```

Fan mode uses the SAME formula for all inputs, derived from `inputs[0]` (B slot) rather than `inputs[n-1]` (which would be the last side input).

### Test Stub Pattern (AST-based, no Nuke runtime)
All Phase 9 tests follow the same stub pattern as `test_dot_font_scale.py`:
- Load `node_layout.py` via `importlib.util.spec_from_file_location`
- Inject `_nuke_stub` into `sys.modules["nuke"]` before loading
- Use `_StubNode` / `_StubDotNode` instances as fake Nuke nodes
- Call `compute_dims` and `place_subtree` directly and assert on returned dims and `node.xpos()` / `node.ypos()` values

Quick run command: `python3 -m unittest tests/test_fan_alignment.py`
Full suite: `python3 -m unittest discover tests`

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Python `unittest` (stdlib) |
| Config file | none |
| Quick run command | `python3 -m unittest tests/test_fan_alignment.py` |
| Full suite command | `python3 -m unittest discover tests` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LAYOUT-01 | Fan trigger: `_is_fan_active` returns True for 3+ non-mask inputs | unit | `python3 -m unittest tests/test_fan_alignment.py -k test_fan_active_predicate` | Wave 0 |
| LAYOUT-01 | `compute_dims` height uses `max(child_hs)` not `sum(child_hs)` in fan mode | unit | `python3 -m unittest tests/test_fan_alignment.py -k test_compute_dims_fan_height` | Wave 0 |
| LAYOUT-01 | All non-mask subtree roots land at same Y after `place_subtree` in fan mode | unit | `python3 -m unittest tests/test_fan_alignment.py -k test_fan_roots_same_y` | Wave 0 |
| LAYOUT-01 | All routing Dots (including B) land at same Dot-row Y in fan mode | unit | `python3 -m unittest tests/test_fan_alignment.py -k test_fan_dot_row_uniform_y` | Wave 0 |
| LAYOUT-01 | 2 non-mask inputs: staircase behavior is unchanged (regression) | unit | `python3 -m unittest tests/test_fan_alignment.py -k test_two_input_no_fan` | Wave 0 |
| LAYOUT-02 | Mask X position is LEFT of consumer in fan mode | unit | `python3 -m unittest tests/test_fan_alignment.py -k test_mask_left_of_consumer` | Wave 0 |
| LAYOUT-02 | Mask X formula: `consumer_x - horizontal_mask_gap - mask_subtree_width` | unit | `python3 -m unittest tests/test_fan_alignment.py -k test_mask_x_formula` | Wave 0 |
| LAYOUT-02 | With 1 non-mask + mask (2 total): mask stays RIGHT (regression) | unit | `python3 -m unittest tests/test_fan_alignment.py -k test_mask_right_when_no_fan` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m unittest tests/test_fan_alignment.py`
- **Per wave merge:** `python3 -m unittest discover tests`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_fan_alignment.py` — covers LAYOUT-01 and LAYOUT-02 (8 test methods listed above)

---

## State of the Art

| Old Approach | Phase 9 Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Staircase: all inputs stacked in vertical bands | Fan: same-Y roots for n >= 3 non-mask inputs | Phase 9 | More compact, visually parallel layout for complex compositing nodes |
| Mask always rightmost | Mask LEFT of consumer when fan active | Phase 9 | Mask wire no longer crosses A/B wires on busy nodes |
| Only side inputs (`i > 0`) get routing Dots | All inputs including B get Dots in fan mode | Phase 9 | Consistent routing row; B wire is as visible as A wires |

---

## Open Questions

1. **Dot row exact Y when `all_side` fan is active**
   - What we know: The non-`all_side` fan places the Dot row using B's `vertical_gap_between`. In `all_side` mode there is no B slot — the "closest" input is `inputs[n-1]` in the current `all_side` branch.
   - What's unclear: CONTEXT.md says fan applies in `all_side` mode when 3+ non-mask inputs are present — but which input's `vertical_gap_between` determines the shared Dot row Y?
   - Recommendation: Use `inputs[0]` (the first non-mask input in sorted order) as the gap reference for `all_side` fan, consistent with the non-`all_side` fan using B (also at index 0 after reorder).

2. **W formula when mask is left: does the mask subtree widen the TOTAL W?**
   - What we know: `push_nodes_to_make_room` reads the bounding box after layout. The bounding box naturally grows left if the mask is placed at `consumer_x - gap - mask_width`.
   - What's unclear: `compute_dims` returns `(W, H)` where W is measured from the consumer's left edge rightward. The mask's leftward extent is NOT captured in that W.
   - Recommendation: `compute_dims` W for the fan case should only measure the rightward spread (non-mask inputs + consumer). The mask's leftward contribution to the overall bounding box is captured by `compute_node_bounding_box` post-layout, which `push_nodes_to_make_room` uses. No change needed to `compute_dims` for the mask width.

---

## Sources

### Primary (HIGH confidence)
- `/workspace/node_layout.py` — `compute_dims` lines 316–369, `place_subtree` lines 372–543, `_reorder_inputs_mask_last` lines 180–198, `_is_mask_input` lines 104–116, `_horizontal_margin` lines 162–172, `_subtree_margin` lines 148–159
- `/workspace/.planning/phases/09-multi-input-fan-alignment-mask-side-swap/09-CONTEXT.md` — locked decisions, geometry specification, code-context section

### Secondary (MEDIUM confidence)
- `/workspace/.planning/REQUIREMENTS.md` — LAYOUT-01 and LAYOUT-02 requirement text
- `/workspace/tests/test_dot_font_scale.py` — reference for `_StubNode` / `_StubDotNode` stub pattern and `importlib` loading approach used in all test files

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no external dependencies; pure Python stdlib
- Architecture: HIGH — all geometry derived from reading `node_layout.py` directly; no speculation
- Pitfalls: HIGH — identified from reading the existing branching logic and the `is_side_dot` guard in `place_subtree`

**Research date:** 2026-03-11
**Valid until:** Stable (no external dependencies; valid until `node_layout.py` is structurally refactored)

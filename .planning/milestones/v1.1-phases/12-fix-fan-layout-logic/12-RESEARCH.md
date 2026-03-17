# Phase 12: fix-fan-layout-logic - Research

**Researched:** 2026-03-17
**Domain:** Python geometry arithmetic in node_layout.py (place_subtree fan branch, compute_dims fan branch)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Bug 1 fix — Dot row Y**
- Use the existing `gap_to_fan` space (already sized to accommodate the Dot row).
- Place the Dot row with `snap_threshold - 1` gap below the fan input roots AND `snap_threshold - 1` gap above the consumer — symmetric vertical margins on both sides.
- Formula: `dot_row_y = y - (snap_threshold - 1) - inp.screenHeight()` (Dot flush against `snap_threshold - 1` pixels above consumer).
- `gap_to_fan` is already computed as `max(snap_threshold - 1, raw_gap_b_scaled, side_margins_v[non_mask_start])` specifically to ensure the Dot fits in this gap.

**Bug 2 fix — A1/A2 X start position**
- A1's X should start at `max(consumer_right, B_subtree_right) + margin`, NOT just `consumer_right + margin`.
- `B_subtree_right = x_positions[non_mask_start] + child_dims[non_mask_start][0]`
- `consumer_right = x + node.screenWidth()`
- Change line 1074: `current_x = max(x + node.screenWidth(), x_positions[non_mask_start] + child_dims[non_mask_start][0]) + (side_margins_h[non_mask_start + 1] if non_mask_start + 1 < n else 0)`
- `x_positions[non_mask_start]` is already computed at line 1072 (centered above consumer), so it is available.

### Claude's Discretion
- Whether `compute_dims` W formula also needs to be updated to match (i.e., does the current W formula already account for B's rightward reach, or is it also wrong in a way that would cause callers to underestimate the fan bbox width?). Researcher/planner should audit this — if W is consistent with the old (wrong) X placement, it will need to be updated to match the new (correct) X placement.
- TDD structure: whether to write RED tests first or patch-and-test directly.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

Phase 12 fixes two geometry bugs that exist in the fan layout path introduced in Phase 9. Both bugs are pure arithmetic errors in `place_subtree` and (likely) `compute_dims` in `node_layout.py`. No new commands, prefs, or behaviors are added.

**Bug 1** is in `place_subtree` lines 1143–1146: the fan Dot row Y is computed with the staircase bottom-dot formula (`y + (node.screenHeight() - inp.screenHeight()) // 2`), which places the Dot at the consumer's vertical midpoint — on top of the consumer tile. The correct formula places the Dot at `y - (snap_threshold - 1) - inp.screenHeight()`, using the already-reserved `gap_to_fan` space.

**Bug 2** is in `place_subtree` line 1074: A1's starting X ignores B's subtree right edge. B is centered above the consumer, and when B is wide its subtree's right edge exceeds `consumer_right`, causing B's subtree to overlap A1. The fix is `current_x = max(consumer_right, B_subtree_right) + margin`. Additionally, `compute_dims` W formula has the same logical gap — it does not account for B's rightward overhang when computing the total fan bbox width, so it will understate W after the place_subtree fix.

**Primary recommendation:** Fix both place_subtree sites, audit and fix compute_dims W formula, then add two new regression tests to `test_fan_alignment.py` using the established TDD RED-first pattern.

---

## Standard Stack

No new libraries required. All work is in existing Python files.

| File | Purpose |
|------|---------|
| `/workspace/node_layout.py` | Core layout engine — both fix sites |
| `/workspace/tests/test_fan_alignment.py` | Home for all new fan regression tests |

---

## Architecture Patterns

### Established TDD Pattern (RED scaffold first)

All prior phases (9, 11.1, 11.2) follow: write failing tests, then fix code. This is the expected pattern for Phase 12.

**Wave 0:** Write new test methods in `test_fan_alignment.py`. Tests must FAIL before the fix is applied.
**Wave 1:** Apply code fixes. Tests must turn GREEN.

### Fix Site 1 — place_subtree fan Dot row Y (line 1145)

**Current (buggy) code:**
```python
# lines 1143-1146
if fan_active and n >= 3:
    # Fan mode: uniform Dot row — all Dots at the same Y regardless of index.
    dot_row_y = y + (node.screenHeight() - inp.screenHeight()) // 2
    dot_y = dot_row_y
```

**Corrected code:**
```python
if fan_active and n >= 3:
    # Fan mode: Dot row sits in gap above consumer, symmetric snap_threshold-1 margins.
    dot_row_y = y - (snap_threshold - 1) - inp.screenHeight()
    dot_y = dot_row_y
```

`y` is the consumer's top-left Y. `snap_threshold - 1` is the minimum gap floor used consistently throughout `place_subtree` and `compute_dims`. This places the Dot's top edge at `y - snap_threshold` and its bottom edge at `y - snap_threshold + inp.screenHeight()`, which is above consumer top (correct). `gap_to_fan` is already sized to `max(snap_threshold - 1, raw_gap_b_scaled, side_margins_v[non_mask_start])`, so the Dot fits within the reserved space.

### Fix Site 2 — place_subtree A1/A2 X start (line 1074)

**Current (buggy) code:**
```python
# line 1074
current_x = x + node.screenWidth() + (side_margins_h[non_mask_start + 1] if non_mask_start + 1 < n else 0)
```

**Corrected code:**
```python
# B_subtree_right uses x_positions[non_mask_start] already computed at line 1072
current_x = max(x + node.screenWidth(), x_positions[non_mask_start] + child_dims[non_mask_start][0]) + (side_margins_h[non_mask_start + 1] if non_mask_start + 1 < n else 0)
```

`x_positions[non_mask_start]` is set at line 1072 (B centered above consumer) before this code runs — it is already available. `child_dims[non_mask_start][0]` is B's subtree width.

### Fix Site 3 — compute_dims fan W formula (lines 896-904, Claude's Discretion)

**Audit result (HIGH confidence):** The current W formula does NOT account for B's rightward overhang.

Current fan-with-mask W formula (lines 899-900):
```python
W = max(non_mask_dims[0][0],
        node.screenWidth() + sum(side_margins_h[mask_count + 1:]) + sum(w for w, h in non_mask_dims[1:]))
```

After the place_subtree fix, when B_width > node_width, A1 starts at `B_subtree_right + margin` rather than `consumer_right + margin`. The extra horizontal push is `(B_width - node_width) // 2` (the B centering overhang). If compute_dims does not account for this, callers (e.g., `push_nodes_to_make_room` bbox sizing) will underestimate the fan bbox width.

**Corrected W formula (fan with mask):**
```python
b_w = non_mask_dims[0][0]
b_right_overhang = max(0, (b_w - node.screenWidth()) // 2)
W = max(b_w,
        node.screenWidth() + b_right_overhang + sum(side_margins_h[mask_count + 1:]) + sum(w for w, h in non_mask_dims[1:]))
```

**Corrected W formula (fan without mask, lines 902-904):**
```python
b_w = child_dims[0][0]
b_right_overhang = max(0, (b_w - node.screenWidth()) // 2)
W = max(b_w,
        node.screenWidth() + b_right_overhang + sum(side_margins_h[1:]) + sum(w for w, h in child_dims[1:]))
```

Note: `_center_x(b_w, x, node_w)` places B's left edge at `x + (node_w - b_w) // 2`. B's right edge = `x + (node_w + b_w) // 2`. Consumer's right edge = `x + node_w`. Overhang = `(b_w - node_w) // 2` when `b_w > node_w`, else 0.

### Anti-Patterns to Avoid

- **Using `gap_to_fan` variable in the Dot Y formula directly:** `gap_to_fan` is available in the Y-placement block above, but is NOT in scope at the Dot-placement section (lines 1143-1154). Use `snap_threshold - 1` directly, which is the formula for the gap floor.
- **Modifying the staircase Dot formula:** Lines 1147-1152 are unchanged — only the fan branch (lines 1143-1146) changes.
- **Forgetting to update compute_dims:** Fixing place_subtree without fixing compute_dims leaves bbox estimation wrong for callers.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Gap floor constant | Custom constant | `snap_threshold - 1` — already the project-wide floor |
| B center X | New formula | `_center_x(b_width, x, node_width)` — already used at line 1072 |
| Horizontal margin | Direct prefs read | `_horizontal_margin(node, slot)` — established margin helper |

---

## Common Pitfalls

### Pitfall 1: scope of `gap_to_fan` variable

**What goes wrong:** `gap_to_fan` is computed in the Y-placement block (lines 1026-1027) but the Dot-placement code is in the Recurse block (lines 1143-1146). Referencing `gap_to_fan` in the Dot section works IF both blocks are in the same function scope — which they are. However, the formula `y - (snap_threshold - 1) - inp.screenHeight()` is cleaner and does not depend on the variable being in scope at that point.

**How to avoid:** Use `y - (snap_threshold - 1) - inp.screenHeight()` per the locked decision. This formula is self-contained.

### Pitfall 2: integer division direction

**What goes wrong:** Nuke Y is positive-down. The consumer's top-left is at `y`. Upstream inputs are at lower Y values (negative direction). Adding `- (snap_threshold - 1) - inp.screenHeight()` moves the Dot ABOVE the consumer (correct). Using `+` would place it below (wrong).

**Warning signs:** Dot Y > consumer Y after fix.

### Pitfall 3: compute_dims W overhang uses integer division

**What goes wrong:** `_center_x` uses `//` (integer division): `x + (node_width - child_width) // 2`. The corresponding right overhang must also use `//` to stay consistent: `max(0, (b_w - node.screenWidth()) // 2)`. Using `/` introduces float and potential off-by-one.

### Pitfall 4: existing `test_fan_dot_row_uniform_y` test does not catch Bug 1

The test only asserts all Dots share the same Y value (uniformity). It does NOT assert the Y is in the correct range (above consumer, not on it). The test PASSES today with the buggy formula because all Dots are uniformly at the wrong Y. A new test must assert the Dot Y is within the `gap_to_fan` band, i.e., `dot_y < y` and `dot_y > y - gap_to_fan - dot_height`.

### Pitfall 5: Bug 2 test needs a wide B subtree to trigger the overlap

**What goes wrong:** If B's subtree width <= consumer width, `B_subtree_right <= consumer_right` and the max() in the fix makes no difference. The test only fails RED if B is wide enough to overhang.

**How to avoid:** Use a wide B stub (e.g., `width=500`) with a narrow consumer (e.g., `width=80`). This mirrors the Phase 11.2-01 pattern: "BUG-A test needs wide side-input (a, width=500) on spine node n."

---

## Code Examples

### Example: new Bug 1 regression test structure

```python
# Source: test_fan_alignment.py pattern (established in Phase 9)
def test_fan_dot_row_y_in_gap_not_on_consumer(self):
    """Fan Dot row Y must be in the gap above the consumer, not on the consumer tile."""
    consumer, inputs, non_mask_slots = self._build_three_input_consumer()
    consumer_y = 500
    nl.place_subtree(
        consumer, 500, consumer_y, self.memo, self.snap_threshold, self.node_count
    )
    dot_nodes = []
    for slot in non_mask_slots:
        node_at_slot = consumer._inputs[slot]
        if node_at_slot is not None and node_at_slot.Class() == "Dot":
            dot_nodes.append(node_at_slot)
    for dot in dot_nodes:
        dot_y = dot.ypos()
        # Dot must be ABOVE consumer top (strict less-than in Nuke positive-down Y)
        self.assertLess(dot_y, consumer_y,
            f"Dot must be above consumer top; dot_y={dot_y}, consumer_y={consumer_y}")
        # Dot bottom edge must clear consumer top by at least snap_threshold - 1
        dot_bottom = dot_y + dot.screenHeight()
        self.assertLessEqual(dot_bottom, consumer_y - (self.snap_threshold - 1),
            f"Dot bottom must be at least snap_threshold-1 above consumer; "
            f"dot_bottom={dot_bottom}, floor={consumer_y - (self.snap_threshold - 1)}")
```

### Example: new Bug 2 regression test structure

```python
def test_fan_a1_x_clears_b_subtree_right_edge(self):
    """A1 X must start after B's subtree right edge when B is wider than consumer."""
    # B subtree width=500 >> consumer width=80 — triggers the overhang
    input_b = _StubNode(width=500, height=28)
    input_a1 = _StubNode(width=80, height=28)
    input_a2 = _StubNode(width=80, height=28)
    consumer = _StubMergeNode(width=80, height=28, xpos=500, ypos=500)
    consumer._inputs = [input_b, input_a1, None, input_a2]
    nl.place_subtree(
        consumer, 500, 500, self.memo, self.snap_threshold, self.node_count
    )
    # B is centered above consumer: B left = 500 + (80 - 500) // 2 = 500 - 210 = 290
    # B right = 290 + 500 = 790
    # A1 must start at X > B right
    self.assertGreater(input_a1.xpos(), 500 + 80,  # at minimum past consumer right
        f"A1 must start past consumer right edge; a1_xpos={input_a1.xpos()}")
    # More specifically A1 must not overlap B's bounding box
    b_left = input_b.xpos()
    b_right = b_left + input_b.screenWidth()
    self.assertGreaterEqual(input_a1.xpos(), b_right,
        f"A1 must start at or past B subtree right; a1_xpos={input_a1.xpos()}, b_right={b_right}")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Staircase bottom-dot formula for fan Dots | Symmetric gap formula using `snap_threshold - 1` | Phase 12 | Dots land in reserved gap, not on consumer |
| A1 starts at `consumer_right + margin` | A1 starts at `max(consumer_right, B_subtree_right) + margin` | Phase 12 | No B/A1 overlap when B is wide |
| W ignores B rightward overhang | W adds `max(0, (b_w - node_w) // 2)` | Phase 12 | `compute_dims` correctly sizes fan bbox |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Python `unittest` (stdlib, no install needed) |
| Config file | none — direct module execution |
| Quick run command | `python3 -m unittest tests.test_fan_alignment -v` |
| Full suite command | `python3 -m unittest discover -s tests -v` |

### Phase Requirements to Test Map

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| Fan Dot row Y is above consumer top | unit | `python3 -m unittest tests.test_fan_alignment.TestPlaceSubtreeFanRoots.test_fan_dot_row_y_in_gap_not_on_consumer -v` | Wave 0 |
| A1 X clears B subtree right edge | unit | `python3 -m unittest tests.test_fan_alignment.TestPlaceSubtreeFanRoots.test_fan_a1_x_clears_b_subtree_right_edge -v` | Wave 0 |
| compute_dims W correct for wide B | unit | `python3 -m unittest tests.test_fan_alignment.TestComputeDimsFanWidth.test_compute_dims_fan_w_accounts_for_b_overhang -v` | Wave 0 |
| All existing fan tests still pass | regression | `python3 -m unittest tests.test_fan_alignment -v` | Already exists |

### Sampling Rate

- **Per task commit:** `python3 -m unittest tests.test_fan_alignment -v`
- **Per wave merge:** `python3 -m unittest discover -s tests -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] New test method `test_fan_dot_row_y_in_gap_not_on_consumer` in `TestPlaceSubtreeFanRoots` — covers Bug 1 absolute Y correctness
- [ ] New test method `test_fan_a1_x_clears_b_subtree_right_edge` in `TestPlaceSubtreeFanRoots` — covers Bug 2 A1 X position
- [ ] New test class `TestComputeDimsFanWidth` with `test_compute_dims_fan_w_accounts_for_b_overhang` — covers compute_dims W audit

---

## Open Questions

1. **compute_dims W formula: mask-absent fan path also needs fix**
   - What we know: Lines 901-904 handle fan-without-mask and have the same structural bug as lines 896-900 (mask path).
   - What's unclear: Whether any real topology reaches n >= 3 fan without a mask slot. In practice Merge2 always has a mask slot. Generic nodes (Grade etc.) can have 3+ inputs without a mask.
   - Recommendation: Fix both W paths (lines 896-900 and 901-904) symmetrically, same overhang formula.

2. **Integer arithmetic alignment with `_center_x`**
   - `_center_x` uses `//`: `x + (node_w - child_w) // 2`. B's right edge = `x + (node_w + child_w) // 2` (when node_w > child_w) or `x + child_w - (child_w - node_w) // 2` (when child_w > node_w).
   - The simpler way: B left = `_center_x(b_w, x, node_w)` = `x + (node_w - b_w) // 2`, so B right = B_left + b_w. This is what place_subtree uses directly via `x_positions[non_mask_start] + child_dims[non_mask_start][0]`. Use that same expression in compute_dims translated to relative coordinates.

---

## Sources

### Primary (HIGH confidence)

- Direct code read of `/workspace/node_layout.py` lines 880–934 (`compute_dims` fan branch)
- Direct code read of `/workspace/node_layout.py` lines 990–1164 (`place_subtree` fan branch including both fix sites)
- Direct code read of `/workspace/tests/test_fan_alignment.py` (all 8 existing tests)
- Context7 / project CONTEXT.md (locked decisions and formula specifications)

### Secondary (MEDIUM confidence)

- STATE.md accumulated context entries for Phase 9 fan decisions
- Integer arithmetic analysis of `_center_x` usage at line 1072 vs. `compute_dims` W formula

---

## Metadata

**Confidence breakdown:**
- Fix site identification: HIGH — exact lines confirmed by direct code read
- Bug 1 formula: HIGH — formula from locked CONTEXT.md, consistent with `gap_to_fan` reserved space
- Bug 2 formula: HIGH — formula from locked CONTEXT.md, `x_positions[non_mask_start]` available at line 1072
- compute_dims W audit: HIGH — audited directly; both fan W paths (mask and no-mask) have the same overhang gap
- Test pattern: HIGH — mirrors established Phase 9 / 11.2 TDD structure exactly

**Research date:** 2026-03-17
**Valid until:** Stable domain — valid until node_layout.py fan branch is changed (no external dependencies)

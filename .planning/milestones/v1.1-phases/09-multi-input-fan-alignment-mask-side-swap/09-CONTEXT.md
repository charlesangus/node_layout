# Phase 9: Multi-Input Fan Alignment + Mask Side-Swap - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

When a consumer node has 3 or more non-mask inputs, all immediate input subtree roots are placed at the same Y level (a fan), spreading rightward from the consumer's right edge. The mask input is placed to the LEFT of the consumer when the fan is active. No new commands, no new prefs — this is a change to the placement geometry in `compute_dims` and `place_subtree`.

> **Note:** The roadmap success criterion incorrectly states "two non-mask inputs." The correct trigger is **3 or more** non-mask inputs. A standard Merge (B + A = 2 non-mask inputs) is unaffected by this phase.

</domain>

<decisions>
## Implementation Decisions

### Fan trigger
- Fan activates when the consumer has **3 or more non-mask inputs** (input[0]/B counts as non-mask)
- 2 non-mask inputs: existing stacking behavior unchanged (B above, A to the right at staircase Y)
- 0 non-mask inputs (mask only): mask stays right, no change
- `all_side` mode: fan applies when 3+ non-mask inputs are present in that mode too

### Fan geometry — subtree root placement
- B (input[0]) stays **directly above the consumer** (same column, same gap formula as current)
- A1, A2, etc. fan **rightward** from the consumer's right edge at the **same Y as B's subtree root**
- The shared fan-level Y is determined by `vertical_gap_between` for the B slot (existing formula — no change)

### Routing Dots
- **All** inputs — including B — receive a routing Dot placed directly beneath their subtree root
- All routing Dots are at the **same Y row** (a uniform horizontal row between the fan roots and the consumer)
- The Dot row Y is determined by the existing vertical_gap_between formula for the B slot
- Consumer connects to all Dots; B's wire is straight down, A1/A2 wires are diagonal

### Mask side-swap (fan-active only)
- When 3+ non-mask inputs: mask input is placed to the **LEFT** of the consumer
- Positioning: `right edge of mask subtree bbox = consumer_left_x - horizontal_mask_gap`
  (i.e., `mask_x = consumer_x - horizontal_mask_gap - mask_subtree_width`)
- Uses the existing `horizontal_mask_gap` pref — no new pref needed
- Mask also gets a routing Dot directly beneath its subtree root
- Mask subtree root is at its own Y (existing `_subtree_margin` with `mask_input_ratio` — V-axis logic unchanged)

### Mask side-swap trigger
- Only swaps left when fan is active (3+ non-mask inputs)
- With 1 non-mask + mask: mask stays right as today

### Height formula (compute_dims)
- Fan case: total height = `max(fan subtree heights)` + gap-to-fan + consumer height
  (NOT the current sum — same-Y means subtrees extend independently, not stacked)
- Horizontal spacing between fan columns prevents vertical overlap — no V constraint needed

### Claude's Discretion
- Exact vertical position of the Dot row relative to the fan roots and consumer
- How the `all_side` fan path is structured in code (shared helper vs branching)
- How to detect "3+ non-mask inputs" cleanly given the existing `_is_mask_input` helper

</decisions>

<specifics>
## Specific Ideas

- Fan layout diagram (confirmed by user):
  ```
  [B]   [A1]   [A2]
   |     |      |
  [dot] [dot]  [dot]   ← all at the same Y row
   |     \      \
   |      \      \
  [Merge]----------
  ```
- Mask placement (fan active, confirmed):
  ```
  [mask]  [Merge]  [B]   [A1]   [A2]
     |       |      |     |      |
   [dot]  (connects to all dots via wires)
  ```
- "Right edge of the mask subtree bbox should be horizontal_mask_gap away from the root node"

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_is_mask_input(node, i)` — existing helper for slot classification; fan trigger uses this to count non-mask inputs
- `_reorder_inputs_mask_last()` — current function puts mask at END (rightmost); Phase 9 replaces this with mask-LEFT behavior when fan is active
- `_horizontal_margin(node, slot)` — existing H-gap helper using `horizontal_mask_gap` pref; mask-left placement uses same pref
- `_subtree_margin(node, slot, node_count, mode_multiplier)` — existing V-margin helper; mask V-axis is unchanged
- `vertical_gap_between(node, consumer, snap_threshold, scheme_multiplier)` — determines the fan-level Y (same as current B gap formula)

### Established Patterns
- `compute_dims` `all_side` branch (lines 331–341): sums subtree widths horizontally; fan case follows similar W logic
- `place_subtree` Dot insertion (lines 492–514): side-input Dots already inserted for `i > 0`; Phase 9 extends this to `i == 0` (B) in fan mode
- `place_subtree` "bottom-most dot" centering (lines 526–533): current rule for lowest Dot placement beside consumer; Phase 9 replaces with uniform Dot-row Y

### Integration Points
- `compute_dims()`: add fan branch — `max(child_dims)` for height instead of `sum`; W formula stays same as n >= 3 case (rightward spread)
- `place_subtree()`: add fan branch — all inputs (including B) get Dots; Dot row at uniform Y; B centered above consumer's column; A1/A2/etc. spread rightward; mask goes left using `consumer_x - horizontal_mask_gap - mask_subtree_width`
- `_reorder_inputs_mask_last()`: needs to detect fan-active state and move mask to front-of-list (leftmost) rather than end when 3+ non-mask inputs are present

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 09-multi-input-fan-alignment-mask-side-swap*
*Context gathered: 2026-03-11*

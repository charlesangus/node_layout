# Phase 12: fix-fan-layout-logic - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix two geometry bugs in the fan layout path (`place_subtree` fan branch, `compute_dims` fan branch). No new commands, no new prefs, no new behavior — this is a correctness fix for the existing fan mode implemented in Phase 9.

**Bug 1 — Dot row Y wrong:** Fan routing Dots are placed using the staircase bottom-dot formula (`y + (node.screenHeight() - inp.screenHeight()) // 2`), which puts the Dot at the consumer's vertical midpoint — visually ON TOP of the consumer node. The Dot row should sit in the gap between the fan input roots and the consumer, with symmetric margins on both sides.

**Bug 2 — A1/A2 X ignores B's subtree right edge:** A1's X position is computed from `x + consumer.screenWidth() + margin`, but B (input[0]) is centered above the consumer and its subtree can extend rightward past the consumer's right edge. When B has side inputs, B's subtree right edge can exceed A1's starting X, causing B's subtree to overlap A1 (and potentially A1's subtree to overlap A2).

</domain>

<decisions>
## Implementation Decisions

### Bug 1 fix — Dot row Y

- Use the existing `gap_to_fan` space (already sized to accommodate the Dot row).
- Place the Dot row with `snap_threshold - 1` gap below the fan input roots AND `snap_threshold - 1` gap above the consumer — symmetric vertical margins on both sides.
- Formula: `dot_row_y = y - (snap_threshold - 1) - inp.screenHeight()` (Dot flush against `snap_threshold - 1` pixels above consumer).
- The comment "We have margins set up for this; use them" — `gap_to_fan` is already computed as `max(snap_threshold - 1, raw_gap_b_scaled, side_margins_v[non_mask_start])` specifically to ensure the Dot fits in this gap.

### Bug 2 fix — A1/A2 X start position

- A1's X should start at `max(consumer_right, B_subtree_right) + margin`, NOT just `consumer_right + margin`.
- `B_subtree_right = x_positions[non_mask_start] + child_dims[non_mask_start][0]`
- `consumer_right = x + node.screenWidth()`
- Change line 1074: `current_x = max(x + node.screenWidth(), x_positions[non_mask_start] + child_dims[non_mask_start][0]) + (side_margins_h[non_mask_start + 1] if non_mask_start + 1 < n else 0)`
- `x_positions[non_mask_start]` is already computed at line 1072 (centered above consumer), so it's available.

### Claude's Discretion

- Whether `compute_dims` W formula also needs to be updated to match (i.e., does the current W formula already account for B's rightward reach, or is it also wrong in a way that would cause callers to underestimate the fan bbox width?). Researcher/planner should audit this — if W is consistent with the old (wrong) X placement, it will need to be updated to match the new (correct) X placement.
- TDD structure: whether to write RED tests first or patch-and-test directly.

</decisions>

<specifics>
## Specific Ideas

- Bug 2 is structurally identical to the Phase 11.2 fix — "place then measure then correct" — but applied to the B subtree right edge rather than the horizontal chain clearance.
- The dot_row_y bug was introduced in Phase 9 by copy-pasting the staircase bottom-dot formula (`y + (screenHeight - dotHeight) / 2`) without adapting it for the fan geometry.
- The `test_fan_dot_row_uniform_y` test only checks Y uniformity (all Dots at the same Y), NOT that the Y value is correct. A new regression test should assert the absolute Y range is within the gap, not ON the consumer.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets

- `_is_fan_active(input_slot_pairs, node)` — existing trigger check (line 183); no change needed
- `gap_to_fan` — already computed with the correct margins; use it for Dot Y derivation
- `side_margins_v[non_mask_start]` — vertical margin for the fan slot; already factored into `gap_to_fan`
- `x_positions[non_mask_start]` — B's X position; computed at line 1072 before the A1/A2 loop at line 1074

### Established Patterns

- TDD with RED scaffold first — all prior phases (9, 11.1, 11.2) follow: write failing tests, then fix
- `snap_threshold - 1` as minimum gap floor — consistent throughout `place_subtree` and `compute_dims`
- `assert_less` / position arithmetic in fan tests — `test_fan_alignment.py` is the home for new fan regression tests

### Integration Points

- `place_subtree` fan branch, lines 1143–1146: Bug 1 fix site (dot_row_y formula)
- `place_subtree` fan branch, line 1074: Bug 2 fix site (current_x initial value)
- `compute_dims` fan W formula, lines 896–904: May need audit — if W was computed assuming A1 starts at consumer_right (not B_subtree_right), W may understate the total width
- `tests/test_fan_alignment.py`: existing fan tests; new regression tests go here

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 12-fix-fan-layout-logic*
*Context gathered: 2026-03-17*

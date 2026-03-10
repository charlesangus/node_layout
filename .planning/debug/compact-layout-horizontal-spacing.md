---
status: investigating
trigger: "Compact Layout commands tighten horizontal spacing when they should only affect vertical gaps"
created: 2026-03-05T05:34:38Z
updated: 2026-03-05T05:34:38Z
symptoms_prefilled: true
goal: find_root_cause_only
---

## Current Focus

hypothesis: scheme_multiplier is applied to both horizontal and vertical spacing in three distinct places
test: reading code — _subtree_margin (used for X side placement), compute_dims W formula, and horizontal_clearance in layout_selected
expecting: all three confirmed as horizontal consumers of scheme_multiplier
next_action: document exact lines and form fix recommendation

## Symptoms

expected: Compact Layout only tightens vertical gaps between nodes
actual: Horizontal spacing between nodes also becomes tighter when using Compact Layout
errors: none — behavioural bug
reproduction: run layout_upstream_compact() or layout_selected_compact() with a multi-input tree
started: as designed — scheme_multiplier was threaded through all spacing without per-axis discrimination

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-03-05T05:34:38Z
  checked: _subtree_margin (line 118-128)
  found: effective_margin = int(base * mode_multiplier * math.sqrt(node_count) / math.sqrt(reference_count)); mode_multiplier IS scheme_multiplier
  implication: _subtree_margin is used for both vertical inter-band gaps (side_margins[i+1]) AND for horizontal X offsets (x + node.screenWidth() + side_margins[i]); so scheme_multiplier shrinks horizontal gaps too

- timestamp: 2026-03-05T05:34:38Z
  checked: compute_dims W formula (lines 288, 301, 305)
  found: |  W = node.screenWidth() + sum(side_margins) + sum(w ...) [all_side]  |  W = max(child_dims[0][0], node.screenWidth() + side_margins[1] + child_dims[1][0]) [n==2]  |  W = max(child_dims[0][0], node.screenWidth() + sum(side_margins[1:]) + ...) [n>=3]  — all use side_margins which are computed via _subtree_margin(mode_multiplier=scheme_multiplier)
  implication: the W (width) of subtrees shrinks when scheme_multiplier < 1, producing tighter horizontal packing

- timestamp: 2026-03-05T05:34:38Z
  checked: place_subtree X positions (lines 416, 426, 430, 434)
  found: current_x = x + node.screenWidth() + side_margins[0]  and  x + node.screenWidth() + side_margins[1]  and  current_x += child_dims[i][0] + side_margins[i+1]  — all side_margins are scheme_multiplier-scaled
  implication: actual X placement of side inputs is tighter under compact mode

- timestamp: 2026-03-05T05:34:38Z
  checked: layout_selected horizontal_clearance (lines 650-655)
  found: horizontal_clearance = int(base_subtree_margin * resolved_scheme_multiplier * sqrt(node_count) / sqrt(reference_count))
  implication: this is identical to _subtree_margin and uses resolved_scheme_multiplier, so the gap pushed between parallel subtrees in layout_selected also shrinks horizontally under compact mode

## Resolution

root_cause: |
  scheme_multiplier is applied unconditionally to every margin/gap computation regardless of axis.
  _subtree_margin(mode_multiplier=scheme_multiplier) produces values used as BOTH vertical inter-band gaps
  (side_margins[i+1] in the Y staircase) AND horizontal side offsets (side_margins[i] in the X placement).
  horizontal_clearance in layout_selected is also computed with resolved_scheme_multiplier.

  Specifically:
  - Line 124: effective_margin = int(base * mode_multiplier * ...) — single scalar used for both axes
  - Lines 288/301/305: compute_dims W uses side_margins (scheme_multiplier-scaled) for horizontal width
  - Lines 416/426/430/434: place_subtree uses side_margins for X coordinates
  - Lines 650-655: layout_selected horizontal_clearance uses resolved_scheme_multiplier

fix: |
  Separate the margin into a vertical component (scheme_multiplier-scaled) and a horizontal component
  (always uses normal_multiplier=1.0, i.e. unscaled).

  Simplest approach — add a parameter to _subtree_margin and the horizontal_clearance calculation:

  Option A — boolean flag:
    def _subtree_margin(node, slot, node_count, mode_multiplier=None, vertical_only=False):
        ...
        effective_multiplier = mode_multiplier if not vertical_only else 1.0
        effective_margin = int(base * effective_multiplier * ...)

    Then pass vertical_only=True when computing side_margins used for X placement, and always pass
    plain normal_multiplier (or no multiplier) for horizontal_clearance.

  Option B — two separate margin calls (clearer at call sites):
    Compute vertical_side_margins with scheme_multiplier and horizontal_side_margins with
    normal_multiplier, use the former for Y staircase and the latter for X positions and W.

  Option B is preferred for clarity. Concrete changes:

  1. In compute_dims: compute side_margins_h (for W) with mode_multiplier=normal_multiplier, but
     keep side_margins_v (for H) with mode_multiplier=scheme_multiplier.
     Lines 280, 290-291, 301, 305, 314-315 — use side_margins_h for W width sums,
     side_margins_v for H height sums.

  2. In place_subtree: compute side_margins_h with normal_multiplier for X positions (lines 416,
     426, 430, 434) and side_margins_v with scheme_multiplier for Y staircase (lines 403-409, 477).

  3. In layout_selected: compute horizontal_clearance without resolved_scheme_multiplier:
       horizontal_clearance = int(base * normal_multiplier * sqrt(node_count) / sqrt(reference_count))
     i.e. replace resolved_scheme_multiplier with prefs.get("normal_multiplier") in lines 650-654.

files_changed: []

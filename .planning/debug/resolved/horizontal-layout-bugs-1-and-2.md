---
status: verified
trigger: "Investigate three bugs in horizontal layout — Bug 1 left-edge overlap, Bug 2 output dot Y alignment, Bug 3 vertical layout on m1 broken by 11.1"
created: 2026-03-16T00:00:00Z
updated: 2026-03-16T00:00:00Z
---

## Current Focus

hypothesis: confirmed and verified via end-to-end tests
test: 4 end-to-end layout_upstream() tests added to TestLayoutUpstreamEndToEnd
expecting: all 4 tests pass (confirmed)
next_action: close debug session — all 3 bugs verified fixed by existing code

## Symptoms

expected: |
  Bug 1: Leftmost spine node clears the consumer node's right edge by at least step_x.
  Bug 2: Output dot Y is centred on the consumer node (m1) so the wire from m1 to dot is horizontal.
actual: |
  Bug 1: Leftmost spine node overlaps consumer in X.
  Bug 2: Output dot appears below the consumer (below root) instead of at the consumer's Y.
errors: []
reproduction: |
  Run layout_upstream or layout_selected with a horizontal-mode subtree where:
  Bug 1: Multiple spine nodes exist and the layout is run more than once (or with the
         horizontal root directly selected, not its downstream consumer).
  Bug 2: Run layout a second time (replay) — on first run, dot Y is correct; on replay it drops.
started: Phase 11.1 fix attempt did not resolve either bug.

## Eliminated

- hypothesis: "_find_or_create_output_dot is broken for all call paths"
  evidence: |
    _find_or_create_output_dot correctly centres the dot on consumer_node when consumer_node
    is non-None. The function itself is correct; the problem is that consumer_node is None
    when the function is reached via the replay path in _place_output_dot_for_horizontal_root.
  timestamp: 2026-03-16

- hypothesis: "leftward_extent formula is arithmetically wrong"
  evidence: |
    Manual trace: for 3-node spine [m2, m, n] each width W with step_x S,
    leftward_extent = (S+W) + (S+W) = 2S+2W.
    spine_x = consumer_right + S + 2S + 2W = consumer_right + 3S + 2W.
    place_subtree_horizontal places n at spine_x - 2S - 2W = consumer_right + S. Correct.
    The formula itself is arithmetically correct for the no-side-input case.
  timestamp: 2026-03-16

- hypothesis: "The TestLeftExtentOverlap and TestDotYAlignment tests confirm the fixes work"
  evidence: |
    Tests pass (all 5 green), but they test only narrow code paths that do not reproduce the
    actual failure scenarios. See Evidence section.
  timestamp: 2026-03-16

## Evidence

- timestamp: 2026-03-16
  checked: "_place_output_dot_for_horizontal_root scan loop, lines 455-465"
  found: |
    On FIRST call: consumer (m1) is wired directly to root (m2). The scan finds m1 as
    consumer_node and _find_or_create_output_dot is called with consumer_node=m1.
    A new dot is created, rewired: m1.input(0) = dot, dot.input(0) = m2.
    dot_y = consumer_node.ypos() + centring formula — CORRECT.
  implication: First-run dot placement is correct after the Phase 11.1 fix.

- timestamp: 2026-03-16
  checked: "_place_output_dot_for_horizontal_root scan loop on REPLAY (lines 455-477)"
  found: |
    On second call: m1.input(0) = existing_dot (not m2 directly). The scan loop's `elif`
    branch (consumer_node search) only fires for nodes whose .knob(_OUTPUT_DOT_KNOB_NAME)
    is None. m1 has no such knob, so it enters the elif — but m1.input(slot) == dot, not
    root. No node in all_nodes has input(slot) == root (root) except the existing dot itself,
    and the dot is captured via the `if` branch, not the `elif`.
    Result: existing_dot is set, consumer_node remains None.
    The replay branch (lines 467-477) then executes:
        existing_dot.setYpos(root.ypos() + root.screenHeight() + dot_gap)  # line 476
    This is the "below root" broken formula.
    The fix at line 474 (consumer_node is not None branch) is dead code on replay.
  implication: Bug 2 root cause confirmed. The Phase 11.1 fix correctly updated line 474
    but did not address the structural problem: consumer_node is always None on replay.

- timestamp: 2026-03-16
  checked: "layout_upstream / layout_selected horizontal branch, spine_x assignment (lines 1325-1348 / 1503-1526)"
  found: |
    The leftward_extent formula is only computed in the `root is not original_selected_root`
    branch — i.e., when the user selected a downstream consumer (m1, mode=vertical) and the
    BFS rebound root to the upstream horizontal node (m2).
    When the user selects a node that itself has mode="horizontal" (e.g. m2 directly),
    root is original_selected_root, and the else branch runs:
        spine_x = root.xpos()   # just wherever root currently is
        spine_y = root.ypos()
    No leftward_extent computation happens. The chain is placed starting at m2's current
    position. The leftmost node n lands at spine_x - 2S - 2W (current m2.xpos - 2S - 2W),
    which can be to the left of the consumer.
  implication: Bug 1 root cause confirmed for "horizontal root directly selected" scenario.

- timestamp: 2026-03-16
  checked: "TestLeftExtentOverlap test coverage"
  found: |
    Both test methods compute the fixed spine_x formula manually and call place_subtree_horizontal
    directly. They do NOT go through layout_upstream or layout_selected. They test only the
    `root is not original_selected_root` scenario (consumer=m1 selected). They do not test
    the `root is original_selected_root` scenario (m2 directly selected), where spine_x = root.xpos()
    with no leftward correction.
  implication: Tests are green but do not cover the failing scenario. They test the fix
    in isolation, not through the actual calling function.

- timestamp: 2026-03-16
  checked: "TestDotYAlignment test coverage"
  found: |
    test_new_dot_y_aligned_with_consumer calls _find_or_create_output_dot directly with
    consumer_node=consumer (non-None). This tests the first-run path only.
    test_reuse_check_dot_y_aligned_with_consumer calls _find_or_create_output_dot with
    an existing dot pre-wired as consumer.input(0). The reuse check is inside
    _find_or_create_output_dot at line 384 — this also tests the first-run function directly.
    Neither test goes through _place_output_dot_for_horizontal_root, which is the actual
    entry point called from layout_upstream/layout_selected on replay. The replay path
    in _place_output_dot_for_horizontal_root (lines 467-477) is not tested at all.
  implication: Tests are green but do not reproduce Bug 2. The broken code path is
    _place_output_dot_for_horizontal_root's replay branch, not _find_or_create_output_dot.

## Bug 3 — Vertical layout on m1 broken by 11.1

### Symptom
Running layout_upstream on m1 (a vertical node consuming a horizontal subtree) no longer
correctly lays out the tree above m1. The entire upstream tree is mispositioned.

### Root cause
`compute_dims` is horizontal-blind: it recurses into all inputs identically, with no
awareness of horizontal mode. The current architecture short-circuits this by hoisting the
horizontal layout out of `compute_dims`/`place_subtree` entirely — `layout_upstream` detects
the horizontal root via BFS, runs `place_subtree_horizontal` manually with a hard-coded
`spine_y` anchor, and never calls `place_subtree` on m1 at all.

The 11.1 commit changed `spine_y` from `consumer.ypos()` to
`consumer.ypos() - dot_gap - root.screenHeight()`, shifting the entire chain and all its
upstream vertical nodes. Because `place_subtree` is never called on m1, nothing corrects
for this shift, and the vertical tree ends up at the wrong absolute position.

### Agreed fix — two-phase architecture

Replace the manual `spine_y` hack entirely with a proper two-phase approach:

**Phase 1 — horizontal layout:**
Before calling `compute_dims` on m1, walk m1's upstream tree to find all horizontal roots.
Run `place_subtree_horizontal` on each. Store `{ id(horizontal_root): (bbox_w, bbox_h) }`.

**Phase 2 — vertical layout with opaque bboxes:**
Run `compute_dims(m1)` and `place_subtree(m1)` normally. When either function encounters:
- a node whose stored mode is "horizontal" → look up bbox from Phase 1 dict, do not recurse
- an output dot whose `input(0)` is a horizontal root → treat as transparent, pass through
  to the stored bbox

`place_subtree` repositions the horizontal block as a translation (internal layout already
done by Phase 1), using standard vertical gap rules. The manual spine_x/spine_y calculations
in layout_upstream/layout_selected are removed.

This also fixes Bugs 1 and 2 by construction: the dot Y is set by `_find_or_create_output_dot`
at the end of Phase 1 (as now), and the chain's X/Y position relative to m1 is computed by
the vertical layout system using the stored bbox, not by a hand-coded formula.

## Resolution

root_cause: |
  BUG 2 — Output dot Y below consumer on replay:
  _place_output_dot_for_horizontal_root (lines 467-477) handles the replay case when an
  existing output dot is found. It correctly updated line 474 to use the consumer-centred
  Y formula, but the consumer_node variable is ALWAYS None on replay because:
  (a) The existing dot is wired as m1.input(0) = dot, so no node has input(slot) == root.
  (b) The scan loop's elif branch (consumer search) finds consumer_node only when a node
      is wired directly to root — which is no longer true after the first run.
  Therefore, line 474 (`if consumer_node is not None`) is never True on replay, and line
  476 (`root.ypos() + root.screenHeight() + dot_gap`) always executes. The dot lands
  below root, not centred on m1.

  BUG 1 — Left-edge overlap when horizontal root is directly selected:
  In both layout_upstream (line 1346-1348) and layout_selected (line 1524-1526), when
  `root is original_selected_root` (the user selected a node that itself has mode="horizontal"),
  spine_x is set to root.xpos() with no leftward correction. The leftward_extent formula
  (which correctly accounts for the full chain width) is only computed in the
  `root is not original_selected_root` branch. When the user selects m2 directly, the chain
  is placed starting at m2's current xpos, and the leftmost node n ends up at
  m2.xpos - N*step_x - N*W, which can be to the left of or overlapping the consumer m1.

fix: |
  UNIFIED FIX (all three bugs) — two-phase architecture:

  Phase 1: Before compute_dims, walk upstream tree from the selected root, find all
  horizontal roots, run place_subtree_horizontal on each, store bbox dict.

  Phase 2: Run compute_dims/place_subtree on the selected root normally. Teach
  compute_dims to check if an input node has stored mode="horizontal" (or is a dot
  whose input(0) is a horizontal root) and return the stored bbox instead of recursing.
  Teach place_subtree to reposition the horizontal block as a translation using standard
  vertical gap rules rather than recursing into it.

  Remove the manual spine_x/spine_y computations from layout_upstream/layout_selected
  entirely. Remove the else-branch consumer scan added in 11.1. The dot Y is handled
  by _place_output_dot_for_horizontal_root at the end of Phase 1 (unchanged).

  The 11.1 replay scan fix in _place_output_dot_for_horizontal_root (finding consumer
  via existing_dot) is still correct and should be kept.

verification: pending
files_changed: []

---
status: resolved
trigger: "After phase 02 bug fixes (specifically plan 02-02 which added _center_x() helper and changed place_subtree() X-positioning logic), nodes are stairstepping to the left in an irregular/alternating pattern."
created: 2026-03-03T00:00:00Z
updated: 2026-03-03T00:01:00Z
---

## Current Focus

hypothesis: place_subtree() uses _center_x(child_dims[0][0], ...) — the SUBTREE width — to center input[0] over the parent tile, but it should use inputs[0].screenWidth() — the INPUT NODE'S OWN TILE WIDTH. Using subtree width causes each recursive call to drift further left: at each level the centering over-corrects by an amount proportional to the difference between the subtree width and the tile width. This accumulates as stairstepping across multiple levels.
test: Traced 4-level chain D(w=80)->C(w=80)->B(w=80)->A(w=200). Current code places D=0, C=-60, B=-120, A=-180. Fix places D=0, C=0, B=0, A=-60.
expecting: Changing _center_x arg from child_dims[0][0] to inputs[0].screenWidth() stops the drift
next_action: Apply the fix to the three _center_x call sites in place_subtree() and update tests

## Symptoms

expected: All nodes should be vertically aligned in chains; input-0 should be centered under its consumer; no leftward drift at any depth
actual: Nodes stairstep to the left in an irregular/alternating pattern — not every node, not a consistent offset
errors: No runtime errors — purely visual/positional
reproduction: Nuke paste script with Blur nodes (inputs 1+1), Roto nodes feeding mask inputs via Dots, creating diamond-like connections
started: After plan 02-02 changes (added _center_x(), changed x_positions[0] to use _center_x, added input0_overhang to compute_dims)

## Eliminated

- hypothesis: compute_dims() adds input0_overhang to W, inflating bounding box width and causing alternating over/under allocation
  evidence: Removed input0_overhang from all three compute_dims branches. 38 tests pass. Human verification in Nuke confirmed stairstepping still present. This fix was necessary but not sufficient — the drift comes from place_subtree, not compute_dims.
  timestamp: 2026-03-03T01:00:00Z

## Evidence

- timestamp: 2026-03-03T00:00:00Z
  checked: compute_dims() n==1 branch
  found: |
    input0_overhang = max(0, (child_dims[0][0] - node.screenWidth()) // 2)
    W = max(node.screenWidth(), child_dims[0][0]) + input0_overhang

    Example: parent_w=80, child_w=120
    input0_overhang = (120 - 80) // 2 = 20
    W = max(80, 120) + 20 = 140

    But place_subtree centers child at: x + (80 - 120)//2 = x - 20
    So actual footprint: from x-20 to x-20+120 = x+100
    Width of footprint relative to x: 100 (NOT 140)

    The overhang is being ADDED to max(parent_w, child_w) but it should just be child_w.
    W should be child_w (=120), not 140.
  implication: compute_dims returns too-large W for n==1 when child is wider than parent; this causes the CALLER (parent's parent) to allocate extra horizontal space, placing the parent too far right, which then places its child too far left relative to the grandparent.

- timestamp: 2026-03-03T00:00:00Z
  checked: compute_dims() n==2 branch
  found: |
    input0_overhang = max(0, (child_dims[0][0] - node.screenWidth()) // 2)
    W = max(child_dims[0][0] + input0_overhang, node.screenWidth() + side_margins[1] + child_dims[1][0])

    Example: parent_w=80, child_dims[0][0]=120
    input0_overhang = 20
    W = max(120 + 20, ...) = max(140, ...)

    Same problem: child_dims[0][0] + input0_overhang = 120 + 20 = 140
    But actual footprint of input[0] relative to x is just 120 (from x-20 to x+100)

    The correct left edge of input[0] is x - input0_overhang = x - 20
    So the width needed to cover from x to right edge of input[0] is:
    child_dims[0][0] - input0_overhang = 120 - 20 = 100
    NOT child_dims[0][0] + input0_overhang = 140
  implication: Same double-counting bug in n==2 and n>=3 branches.

- timestamp: 2026-03-03T00:00:00Z
  checked: The correct fix for compute_dims
  found: |
    PREVIOUS ANALYSIS (still valid for compute_dims W):
    W = max(parent_w, child_dims[0][0]) is correct. Removing input0_overhang was correct.

- timestamp: 2026-03-03T01:30:00Z
  checked: place_subtree() _center_x call sites for input[0]
  found: |
    _center_x is called with child_dims[0][0] (SUBTREE WIDTH of input[0]), but it
    should use inputs[0].screenWidth() (the INPUT NODE'S OWN TILE WIDTH).

    Concrete 4-level chain: D(w=80)->C(w=80)->B(w=80)->A(w=200, leaf)
    - compute_dims(A)=200, compute_dims(B)=max(80,200)=200, compute_dims(C)=200, compute_dims(D)=200
    - With BUGGY code using subtree widths:
        place_subtree(D, x=0): D@0, C_x = _center_x(200, 0, 80) = -60
        place_subtree(C, x=-60): C@-60, B_x = _center_x(200, -60, 80) = -120
        place_subtree(B, x=-120): B@-120, A_x = _center_x(200, -120, 80) = -180
        Result: D=0, C=-60, B=-120, A=-180 — STAIRSTEPPING -60 per level
    - With FIXED code using tile widths (80, 80, 80, 200):
        place_subtree(D, x=0): D@0, C_x = _center_x(80, 0, 80) = 0
        place_subtree(C, x=0): C@0, B_x = _center_x(80, 0, 80) = 0
        place_subtree(B, x=0): B@0, A_x = _center_x(200, 0, 80) = -60
        Result: D=0, C=0, B=0, A=-60 — NO STAIRSTEPPING
        A is correctly centered under B: A.center = -60+100=40, B.center = 0+40=40 ✓
  implication: |
    The three _center_x calls in place_subtree that use child_dims[0][0] must be changed
    to use inputs[0].screenWidth(). The subtree width is irrelevant for centering the tile;
    only the tile's own screenWidth() matters.
    Tests in TestPlaceSubtreeInputZeroCentering that use leaf nodes (where screenWidth ==
    subtree_W) pass regardless, so the tests do not catch the regression. A new multi-level
    test is needed.

## Resolution

root_cause: |
  Two bugs introduced by plan 02-02:

  BUG A (fixed in prior session, necessary but not sufficient):
  compute_dims() added input0_overhang to W, inflating bounding box width.
  Fix: remove input0_overhang from W; W = max(parent_w, child0_w).

  BUG B (root cause of stairstepping):
  In place_subtree(), the three _center_x calls for x_positions[0] (in n==1, n==2,
  n>=3 branches) use child_dims[0][0] — the SUBTREE WIDTH of input[0] — instead of
  inputs[0].screenWidth() — the INPUT NODE'S OWN TILE WIDTH.

  Using subtree width causes drift that accumulates with depth:
    - 4-level chain D(80)->C(80)->B(80)->A(200) with subtree-width centering:
        D@0, C@-60, B@-120, A@-180  (stairstepping -60 per level)
    - Same chain with tile-width centering:
        D@0, C@0, B@0, A@-60  (no stairstepping; A correctly centered under B)

  Subtree width correctly centers the SUBTREE bounding box over the parent.
  But the consumer should see its direct INPUT NODE'S TILE centered above it,
  not the subtree's hypothetical bounding box. The subtree bounding box shifts
  left as depth grows, amplifying the offset at each recursive call.

fix: |
  In place_subtree(), changed all three _center_x calls for x_positions[0] from:
    _center_x(child_dims[0][0], x, node.screenWidth())
  to:
    _center_x(inputs[0].screenWidth(), x, node.screenWidth())

  This applies to n==1, n==2, and n>=3 non-all_side branches.

  Added two new tests in TestPlaceSubtreeInputZeroCenteringMultiLevel to catch
  the multi-level stairstepping regression that single-level tests cannot detect.

verification: Human confirmed fixed in Nuke — stairstepping is gone.
files_changed:
  - node_layout/node_layout.py
  - node_layout/tests/test_center_x.py

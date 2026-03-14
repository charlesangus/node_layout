---
phase: quick-1
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - node_layout.py
  - tests/test_horizontal_layout.py
autonomous: true
requirements: [HORIZ-01]

must_haves:
  truths:
    - "A subtree (upstream beyond spine) lands directly above the leftmost spine node, not diagonally upper-left"
    - "B connection (leftmost Dot) is placed at spine Y to the left of the leftmost spine node"
    - "place_only mode creates a leftmost Dot if one does not already exist (same as recursive mode)"
    - "A subtree and spine nodes do not overlap in either mode"
    - "Behavior is consistent: recursive and place_only produce equivalent geometry"
  artifacts:
    - path: "node_layout.py"
      provides: "Fixed is_last_spine_node block in place_subtree_horizontal()"
      contains: "upstream_x = dot_x"
    - path: "tests/test_horizontal_layout.py"
      provides: "Tests for corrected A/B placement geometry"
      exports: ["TestHighestSubtreePlacement"]
  key_links:
    - from: "place_subtree_horizontal (is_last_spine_node block)"
      to: "upstream_root placement"
      via: "upstream_x derived from Dot X, not cur_x - step_x - upstream_w"
      pattern: "upstream_x.*dot_x"
---

<objective>
Fix the "highest subtree" (A/upstream) placement in place_subtree_horizontal().

The leftmost spine node's input[0] should route: A subtree UP above the spine node,
with a Dot at spine Y for the horizontal wire from B (the direct left continuation).
Currently both recursive and place_only modes place A diagonally upper-left (wrong).
place_only never creates a Dot even when none exists (wrong).

Purpose: Correct geometry so A subtrees appear directly above the leftmost spine node,
Dots are always created in both modes, and no overlaps occur.

Output: Fixed node_layout.py + test coverage for corrected placement geometry.
</objective>

<execution_context>
@/home/latuser/.claude/get-shit-done/workflows/execute-plan.md
@/home/latuser/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md

<interfaces>
<!-- Key geometry facts for the executor. -->
<!-- Positive Y = DOWN in Nuke DAG (upstream nodes have lower Y). -->
<!-- place_subtree_horizontal() is at ~line 450; is_last_spine_node block at lines 666-742. -->

Coordinate system:
  - Spine extends LEFT (lower X) from root
  - Upstream (A) subtree goes UP (lower Y) from the leftmost spine node
  - Dot (B routing node) sits at spine Y to the LEFT of the leftmost spine node

Current (broken) placement in is_last_spine_node block:

  # recursive mode:
  upstream_x = cur_x - step_x - upstream_w    # places A far LEFT -- WRONG
  upstream_y = cur_y - horizontal_side_gap - upstream_root.screenHeight()  # correct

  # place_only mode:
  # ... never creates a Dot   -- WRONG
  # ... places A far LEFT     -- WRONG

Required (correct) placement:

  # Both modes: create Dot if none exists (same as recursive already does for Dot creation)
  if leftmost_dot is None:
      leftmost_dot = _find_or_create_leftmost_dot(spine_node, current_group)

  # Dot position: at spine Y, just to the left of the leftmost spine node.
  # Use same formula as the existing recursive branch for dot_y (vertically centered
  # on the spine node). For dot_x: step_x left of cur_x, centered on the Dot width.
  dot_x = cur_x - step_x - leftmost_dot.screenWidth()
  dot_y = cur_y + (spine_node.screenHeight() - leftmost_dot.screenHeight()) // 2
  leftmost_dot.setXpos(dot_x)
  leftmost_dot.setYpos(dot_y)

  # A subtree: centered above the Dot (same X column), using horizontal_side_gap above spine.
  upstream_x = dot_x + (leftmost_dot.screenWidth() - upstream_root.screenWidth()) // 2
  upstream_y = cur_y - horizontal_side_gap - upstream_root.screenHeight()

Existing helper: _find_or_create_leftmost_dot(leftmost_spine_node, current_group)
  - Returns existing Dot if input[0] already has _LEFTMOST_DOT_KNOB_NAME knob
  - Creates new Dot wired upstream_root -> Dot -> spine_node otherwise
  - Must be called with current_group context (uses `with current_group:`)
  - Defined at ~line 404

_LEFTMOST_DOT_KNOB_NAME = constant string identifying the leftmost Dot marker knob
  (already used in detection logic at lines 672-679)

Existing test stub class: test_horizontal_layout.py has _StubNode, _StubNuke, full
  stub infrastructure. New test class TestHighestSubtreePlacement should follow the
  same patterns as TestSideInputPlacement or TestHorizontalSpine.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add failing tests for corrected A/B placement geometry</name>
  <files>tests/test_horizontal_layout.py</files>
  <behavior>
    - Test: recursive mode places upstream_root X centered above the Dot (not far left)
    - Test: recursive mode places upstream_root Y = cur_y - horizontal_side_gap - upstream_root.screenHeight()
    - Test: recursive mode creates a leftmost Dot when none exists (Dot at spine Y)
    - Test: place_only mode also creates a leftmost Dot when none exists
    - Test: place_only mode places A subtree above the Dot (not far left)
    - Test: Dot X is to the left of the leftmost spine node (dot_x < spine_node.xpos())
    - Test: A subtree root X is within one screenWidth of Dot X (centered above it)
    - Test: A subtree and spine do not overlap (upstream_root.xpos() + upstream_root.screenWidth() <= spine_node.xpos() or upstream_root.xpos() >= spine_node.xpos() + spine_node.screenWidth() or upstream_root.ypos() + upstream_root.screenHeight() <= spine_node.ypos())
  </behavior>
  <action>
    Add class TestHighestSubtreePlacement to tests/test_horizontal_layout.py.

    Use the existing _StubNode / stub nuke infrastructure already in the file.
    The class needs a setUp that builds a minimal spine (1-2 nodes) with an upstream
    A node connected beyond the spine (not in spine_set).

    For place_only tests: build a stub that has an existing upstream node at an
    arbitrary position (not at the expected target). Verify the node moves to the
    correct Y (above spine) and the X is near the Dot X column.

    For Dot creation tests: verify that after calling place_subtree_horizontal with
    a spine_set that excludes the upstream node, a Dot with _LEFTMOST_DOT_KNOB_NAME
    knob exists on the leftmost spine node's input(0).

    Run tests after writing: python3 -m unittest tests/test_horizontal_layout.py::TestHighestSubtreePlacement -v
    Expected: ALL FAIL (RED) because implementation is still broken.
  </action>
  <verify>
    <automated>python3 -m unittest tests/test_horizontal_layout.py::TestHighestSubtreePlacement -v 2>&1 | tail -20</automated>
  </verify>
  <done>Tests exist, all fail RED with AssertionError (not SyntaxError or ImportError). Full suite still passes its existing GREEN tests.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Fix is_last_spine_node block in place_subtree_horizontal()</name>
  <files>node_layout.py</files>
  <behavior>
    - Both recursive and place_only modes call _find_or_create_leftmost_dot() when leftmost_dot is None
    - Dot is positioned: dot_x = cur_x - step_x - leftmost_dot.screenWidth(), dot_y centered on spine node height
    - upstream_root X = dot_x centered on upstream_root width (upstream_x = dot_x + (leftmost_dot.screenWidth() - upstream_root.screenWidth()) // 2)
    - upstream_root Y = cur_y - horizontal_side_gap - upstream_root.screenHeight() (unchanged from current)
    - recursive mode calls place_subtree() at (upstream_x, upstream_y) after computing dims
    - place_only mode translates entire A subtree by delta to reach (upstream_x, upstream_y)
    - place_only mode also repositions existing leftmost Dot (same logic as recursive)
  </behavior>
  <action>
    Edit the is_last_spine_node block in place_subtree_horizontal() (lines ~666-742).

    The current block has two divergent branches (recursive / place_only) with different
    Dot-creation and upstream_x logic. Unify them:

    1. BEFORE the recursive/place_only branch split, always create the Dot if missing:
       ```python
       if leftmost_dot is None:
           leftmost_dot = _find_or_create_leftmost_dot(spine_node, current_group)
       ```

    2. BEFORE the branch split, compute Dot position (same formula for both modes):
       ```python
       if leftmost_dot is not None:
           dot_x = cur_x - step_x - leftmost_dot.screenWidth()
           dot_y = cur_y + (spine_node.screenHeight() - leftmost_dot.screenHeight()) // 2
           leftmost_dot.setXpos(dot_x)
           leftmost_dot.setYpos(dot_y)
       ```

    3. Compute upstream target position (same formula for both modes):
       ```python
       if leftmost_dot is not None:
           upstream_x = dot_x + (leftmost_dot.screenWidth() - upstream_root.screenWidth()) // 2
       else:
           upstream_x = cur_x - step_x - upstream_root.screenWidth()
       upstream_y = cur_y - horizontal_side_gap - upstream_root.screenHeight()
       ```

    4. In recursive branch: remove the old dot positioning / upstream_x computation
       (now done above). Keep only: compute_dims call and place_subtree() call using
       the pre-computed upstream_x, upstream_y.

    5. In place_only branch: remove the old upstream_x, upstream_y, Dot repositioning
       logic (now done above). Keep only the delta-translate loop using pre-computed
       upstream_x, upstream_y.

    For place_only, collect_subtree_nodes(upstream_root) is still needed for the
    translation loop. upstream_count is only needed in recursive for compute_dims.

    After editing, read the block back and verify the structure is clean — no
    duplicated Dot positioning, no old upstream_x = cur_x - step_x - upstream_w
    remaining.

    Run: python3 -m unittest tests/test_horizontal_layout.py -v
    Expected: TestHighestSubtreePlacement turns GREEN. No previously-GREEN tests regress.
    Run full suite: python3 -m unittest discover tests/ -q
  </action>
  <verify>
    <automated>python3 -m unittest tests/test_horizontal_layout.py -v 2>&1 | tail -30 && python3 -m unittest discover tests/ -q 2>&1 | tail -10</automated>
  </verify>
  <done>TestHighestSubtreePlacement all GREEN. Full test suite shows no new failures beyond pre-existing known failures (test_scale_nodes_axis nuke stub issue). The is_last_spine_node block has unified Dot creation before the mode branch.</done>
</task>

</tasks>

<verification>
After both tasks:
- python3 -m unittest tests/test_horizontal_layout.py -v — all TestHighestSubtreePlacement tests GREEN
- python3 -m unittest discover tests/ -q — no regressions
- Read the is_last_spine_node block in node_layout.py and confirm:
  - _find_or_create_leftmost_dot called outside the recursive/place_only branch
  - dot_x = cur_x - step_x - leftmost_dot.screenWidth() (not the old upstream_x formula)
  - upstream_x centered on dot_x (not cur_x - step_x - upstream_w)
  - No old `upstream_x = cur_x - step_x - upstream_w` remaining
</verification>

<success_criteria>
- A subtree placed directly above the leftmost spine node (at Dot X column), not diagonally upper-left
- Dot always created in both recursive and place_only modes when none exists
- Dot positioned at spine Y (horizontally aligned with spine), to the left of leftmost spine node
- No overlaps between A subtree and spine nodes
- All existing tests remain GREEN
</success_criteria>

<output>
After completion, create `.planning/quick/1-fix-highest-subtree-placement-in-horizon/1-SUMMARY.md`
</output>

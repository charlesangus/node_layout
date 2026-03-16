"""RED test scaffold for horizontal B-spine layout in node_layout.py (11-01 TDD).

These tests verify the Phase 11 contract (HORIZ-01, HORIZ-02, HORIZ-03):
- place_subtree_horizontal() places the root rightmost and each input(0) ancestor
  one step to the left along the X axis (B-spine = horizontal)
- Side inputs (A inputs, mask) are placed above each spine node (lower Y — negative direction)
- When a spine node has a mask input, the downstream spine segment kinks downward (higher Y)
  to clear the mask subtree, accumulating a staircase as multiple mask nodes occur
- An output Dot (node_layout_output_dot) is placed below the root node and routes leftward
  to the downstream consumer; it is reused (not recreated) on replay
- layout_upstream_horizontal() and layout_selected_horizontal() are entry points
- Normal layout_upstream()/layout_selected() dispatch to the horizontal path when
  the stored mode is "horizontal" (mode replay / HORIZ-03)

Expected RED state: ALL 10 tests FAIL with AttributeError or AssertionError.
- AttributeError: functions place_subtree_horizontal, layout_upstream_horizontal,
  layout_selected_horizontal, _find_or_create_output_dot do not exist yet
- AssertionError: the AST checks fail because those function names are absent from source
"""
import sys
import ast
import types
import importlib.util
import os
import unittest


NODE_LAYOUT_PATH = "/workspace/node_layout.py"
NODE_LAYOUT_PREFS_PATH = "/workspace/node_layout_prefs.py"
NODE_LAYOUT_STATE_PATH = "/workspace/node_layout_state.py"


# ---------------------------------------------------------------------------
# Stub nuke module so node_layout.py can be imported without Nuke runtime.
# ---------------------------------------------------------------------------


class _StubKnob:
    def __init__(self, val=0):
        self._val = val

    def value(self):
        return self._val

    def getValue(self):
        return self._val

    def setValue(self, value):
        self._val = value


class _StubNode:
    """Minimal stand-in for a nuke.Node."""

    def __init__(self, width=80, height=28, xpos=0, ypos=0, node_class="Grade",
                 knobs=None, num_inputs=0):
        self._width = width
        self._height = height
        self._xpos = xpos
        self._ypos = ypos
        self._class = node_class
        self._knobs = knobs if knobs is not None else {"tile_color": _StubKnob(0)}
        self._inputs = [None] * num_inputs if num_inputs > 0 else []

    def screenWidth(self):
        return self._width

    def screenHeight(self):
        return self._height

    def xpos(self):
        return self._xpos

    def ypos(self):
        return self._ypos

    def setXpos(self, value):
        self._xpos = value

    def setYpos(self, value):
        self._ypos = value

    def Class(self):
        return self._class

    def inputs(self):
        return len(self._inputs)

    def input(self, index):
        if 0 <= index < len(self._inputs):
            return self._inputs[index]
        return None

    def setInput(self, slot, node):
        while len(self._inputs) <= slot:
            self._inputs.append(None)
        self._inputs[slot] = node

    def knob(self, name):
        return self._knobs.get(name)

    def addKnob(self, knob_obj):
        pass

    def inputLabel(self, index):
        return ""

    def __getitem__(self, name):
        if name in self._knobs:
            return self._knobs[name]
        knob = _StubKnob(0)
        self._knobs[name] = knob
        return knob


class _StubDotNode(_StubNode):
    """Dot node stub — 12x12, Class returns 'Dot', has node_layout_output_dot knob."""

    def __init__(self, has_output_dot_knob=False, **kwargs):
        kwargs.setdefault("width", 12)
        kwargs.setdefault("height", 12)
        kwargs.setdefault("node_class", "Dot")
        super().__init__(**kwargs)
        if has_output_dot_knob:
            self._knobs["node_layout_output_dot"] = _StubKnob(1)

    def inputLabel(self, index):
        return ""


def _make_preferences_node():
    node = _StubNode(node_class="Preferences")
    node._knobs = {
        "dag_snap_threshold": _StubKnob(8),
        "NodeColor": _StubKnob(0),
    }
    node.knobs = lambda: node._knobs
    return node


class _StubUndo:
    @staticmethod
    def name(label):
        pass

    @staticmethod
    def begin():
        pass

    @staticmethod
    def end():
        pass

    @staticmethod
    def cancel():
        pass


class _StubTab_Knob:
    def __init__(self, *args, **kwargs):
        pass


class _StubInt_Knob:
    def __init__(self, name, label=""):
        self.name = name
        self.label = label

    def setValue(self, value):
        pass


_stub_all_nodes_list = []

_nuke_stub = types.ModuleType("nuke")
_nuke_stub.Node = _StubNode
_nuke_stub.allNodes = lambda: list(_stub_all_nodes_list)
_nuke_stub.selectedNodes = lambda: []
_nuke_stub.selectedNode = lambda: _StubNode()
_nuke_stub.toNode = lambda name: _make_preferences_node() if name == "preferences" else None
_nuke_stub.menu = lambda name: None
_nuke_stub.Undo = _StubUndo
_nuke_stub.Tab_Knob = _StubTab_Knob
_nuke_stub.Int_Knob = _StubInt_Knob
_nuke_stub.lastHitGroup = lambda: None
_nuke_stub.nodes = types.SimpleNamespace(
    Dot=lambda: _StubDotNode()
)

# Load node_layout_prefs first (no Nuke dependency).
_prefs_spec = importlib.util.spec_from_file_location("node_layout_prefs", NODE_LAYOUT_PREFS_PATH)
_node_layout_prefs_module = importlib.util.module_from_spec(_prefs_spec)
_prefs_spec.loader.exec_module(_node_layout_prefs_module)
sys.modules["node_layout_prefs"] = _node_layout_prefs_module

# Provide a minimal node_layout_state stub so node_layout.py can import it.
if "node_layout_state" not in sys.modules:
    _state_spec = importlib.util.spec_from_file_location("node_layout_state", NODE_LAYOUT_STATE_PATH)
    _node_layout_state_module = importlib.util.module_from_spec(_state_spec)
    sys.modules["node_layout_state"] = _node_layout_state_module
    sys.modules["nuke"] = _nuke_stub
    _state_spec.loader.exec_module(_node_layout_state_module)

sys.modules["nuke"] = _nuke_stub

# Load node_layout using a unique alias to avoid sys.modules collisions.
_spec = importlib.util.spec_from_file_location(
    "node_layout_horizontal", NODE_LAYOUT_PATH
)
nl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nl)


def _reset_prefs():
    """Restore prefs to DEFAULTS without touching any file."""
    singleton = _node_layout_prefs_module.prefs_singleton
    for key, default_value in _node_layout_prefs_module.DEFAULTS.items():
        singleton.set(key, default_value)


# ---------------------------------------------------------------------------
# TestHorizontalAST — verifies required functions exist in node_layout.py
# No Nuke stub needed; fails RED because functions are not yet implemented.
# ---------------------------------------------------------------------------


class TestHorizontalAST(unittest.TestCase):
    """AST checks that required horizontal layout functions exist in node_layout.py.

    All 3 tests fail RED: the functions are not present in the source file yet.
    """

    @classmethod
    def setUpClass(cls):
        with open(NODE_LAYOUT_PATH, "r") as source_file:
            source_text = source_file.read()
        tree = ast.parse(source_text, filename=NODE_LAYOUT_PATH)
        cls.function_names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }

    def test_place_subtree_horizontal_exists(self):
        """place_subtree_horizontal must be defined in node_layout.py."""
        self.assertIn(
            "place_subtree_horizontal",
            self.function_names,
            "place_subtree_horizontal() is missing from node_layout.py — "
            "must be added in Phase 11 Plan 02"
        )

    def test_layout_selected_horizontal_place_only_exists(self):
        """layout_selected_horizontal_place_only must be defined in node_layout.py."""
        self.assertIn(
            "layout_selected_horizontal_place_only",
            self.function_names,
            "layout_selected_horizontal_place_only() is missing from node_layout.py"
        )

    def test_layout_selected_horizontal_exists(self):
        """layout_selected_horizontal must be defined in node_layout.py."""
        self.assertIn(
            "layout_selected_horizontal",
            self.function_names,
            "layout_selected_horizontal() is missing from node_layout.py — "
            "must be added in Phase 11 Plan 02"
        )


# ---------------------------------------------------------------------------
# TestHorizontalSpine — verifies spine X placement geometry
# ---------------------------------------------------------------------------


class TestHorizontalSpine(unittest.TestCase):
    """place_subtree_horizontal() places root rightmost and each input(0) one step left.

    In Nuke DAG: positive X is right, negative X is left.
    Root = rightmost (highest X). Upstream input(0) steps left (lower X).
    """

    def setUp(self):
        _reset_prefs()
        self.snap_threshold = 8
        self.node_count = 3

    def test_single_node_placed_at_root_x(self):
        """Single-node chain: place_subtree_horizontal places node at the given root_x."""
        root = _StubNode(width=80, height=28, xpos=500, ypos=200)
        root._inputs = []  # no inputs

        nl.place_subtree_horizontal(
            root,
            spine_x=500,
            spine_y=200,
            snap_threshold=self.snap_threshold,
            node_count=self.node_count,
        )

        self.assertEqual(
            root.xpos(), 500,
            "single-node horizontal layout: root must be placed at spine_x=500, "
            f"got xpos={root.xpos()}"
        )

    def test_two_node_spine_step_left(self):
        """Root -> A chain: A must be placed to the LEFT of root (lower X) by at least step_x.

        In Nuke DAG positive X is right; 'left' = lower X value.
        step_x = horizontal_subtree_gap (default pref value) × scheme_multiplier (1.0 default).
        """
        ancestor = _StubNode(width=80, height=28, xpos=0, ypos=0)
        root = _StubNode(width=80, height=28, xpos=500, ypos=200)
        root._inputs = [ancestor]  # input(0) = ancestor

        horizontal_subtree_gap = _node_layout_prefs_module.prefs_singleton.get(
            "horizontal_subtree_gap"
        )

        nl.place_subtree_horizontal(
            root,
            spine_x=500,
            spine_y=200,
            snap_threshold=self.snap_threshold,
            node_count=self.node_count,
        )

        expected_max_x = root.xpos() - horizontal_subtree_gap
        self.assertLess(
            ancestor.xpos(),
            root.xpos(),
            "ancestor (input[0]) must be placed LEFT of root in horizontal layout — "
            f"ancestor.xpos={ancestor.xpos()}, root.xpos={root.xpos()}"
        )
        self.assertLessEqual(
            ancestor.xpos(),
            expected_max_x,
            "ancestor must be at least step_x to the left of root — "
            f"ancestor.xpos={ancestor.xpos()}, expected <= {expected_max_x}"
        )


# ---------------------------------------------------------------------------
# TestOutputDot — verifies output Dot creation and reuse
# ---------------------------------------------------------------------------


class TestOutputDot(unittest.TestCase):
    """_find_or_create_output_dot creates a Dot below root, reuses on replay.

    Output Dot geometry:
      - Dot.ypos() > root.ypos() (positive Y = below root in Nuke DAG)
      - Dot is horizontally centered on root tile
    """

    def setUp(self):
        _reset_prefs()

    def test_output_dot_created_below_root(self):
        """_find_or_create_output_dot must place the Dot below root (higher Y value).

        In Nuke DAG positive Y is down, so Dot.ypos() > root.ypos() means below.
        """
        root = _StubNode(width=80, height=28, xpos=500, ypos=200, node_class="Grade")
        consumer = _StubNode(width=80, height=28, xpos=200, ypos=200, node_class="Grade")
        # consumer's input(0) connects to root — this is the downstream wire
        consumer.setInput(0, root)

        current_group = None
        dot = nl._find_or_create_output_dot(root, consumer, 0, current_group)

        self.assertIsNotNone(dot, "_find_or_create_output_dot must return a Dot node, got None")
        self.assertGreater(
            dot.ypos(),
            root.ypos(),
            "output Dot must be placed BELOW root (higher Y in Nuke DAG) — "
            f"dot.ypos={dot.ypos()}, root.ypos={root.ypos()}"
        )

    def test_output_dot_reused_on_replay(self):
        """Calling _find_or_create_output_dot twice must return the same Dot (no duplicate).

        On the second call, the existing Dot (with node_layout_output_dot knob) must be
        returned unchanged — not replaced by a new Dot.
        """
        root = _StubNode(width=80, height=28, xpos=500, ypos=200, node_class="Grade")
        consumer = _StubNode(width=80, height=28, xpos=200, ypos=200, node_class="Grade")
        consumer.setInput(0, root)

        current_group = None
        dot_first = nl._find_or_create_output_dot(root, consumer, 0, current_group)

        # Simulate replay: consumer.input(0) is now the Dot (wired by first call)
        # Second call should detect the existing Dot and return it.
        dot_second = nl._find_or_create_output_dot(root, consumer, 0, current_group)

        self.assertIs(
            dot_first,
            dot_second,
            "_find_or_create_output_dot must return the SAME Dot on replay — "
            "got two different Dot objects (creates duplicate on second call)"
        )


# ---------------------------------------------------------------------------
# TestMaskKink — verifies mask kink causes downstream spine Y to drop
# ---------------------------------------------------------------------------


class TestMaskKink(unittest.TestCase):
    """Mask input on a spine node causes downstream spine segment's Y to be higher (lower value).

    Nuke DAG: positive Y = down. 'Downstream = closer to root' in the spine walk.
    A mask kink means the root segment sits at a HIGHER Y value (lower in screen)
    than the spine node above it, so it clears the mask subtree overhead.

    single_mask_kink_drops_downstream:
      spine: root -> spine_a (spine_a has mask_node at its mask slot)
      after horizontal layout:
        root.ypos() > spine_a.ypos()   (root drops down to clear mask above spine_a)
    """

    def setUp(self):
        _reset_prefs()
        self.snap_threshold = 8
        self.node_count = 4

    def test_single_mask_kink_drops_downstream(self):
        """Mask input on spine_a causes root to sit at a higher Y (lower on screen) than spine_a.

        In Nuke DAG positive Y is down. root.ypos() > spine_a.ypos() means root is
        below spine_a on screen, which is the kink geometry.
        """
        mask_node = _StubNode(width=80, height=28, xpos=0, ypos=0, node_class="Grade")

        # spine_a: input(0)=None (end of spine), mask slot has mask_node.
        # Using inputLabel to signal mask slot: simulate a Merge2-style node
        # where slot 2 is the mask.
        class _SpineNodeWithMask(_StubNode):
            def inputLabel(self, index):
                return "M" if index == 2 else {0: "B", 1: "A"}.get(index, "A{}".format(index))

        spine_a = _SpineNodeWithMask(width=80, height=28, xpos=0, ypos=0, node_class="Merge2")
        spine_a.setInput(0, None)   # end of B-spine
        spine_a.setInput(2, mask_node)

        root = _StubNode(width=80, height=28, xpos=500, ypos=200, node_class="Grade")
        root.setInput(0, spine_a)   # root's input(0) is spine_a

        nl.place_subtree_horizontal(
            root,
            spine_x=500,
            spine_y=200,
            snap_threshold=self.snap_threshold,
            node_count=self.node_count,
        )

        self.assertGreater(
            root.ypos(),
            spine_a.ypos(),
            "mask kink: root must sit at higher Y (further down screen) than spine_a — "
            f"root.ypos={root.ypos()}, spine_a.ypos={spine_a.ypos()}"
        )


# ---------------------------------------------------------------------------
# TestSideInputPlacement — verifies A-inputs are placed above spine node
# ---------------------------------------------------------------------------


class TestSideInputPlacement(unittest.TestCase):
    """Side (A) input is placed ABOVE its spine node — lower Y value in Nuke DAG.

    In Nuke DAG positive Y is down, negative Y is up.
    'Above' means A.ypos() < spine_node.ypos().
    """

    def setUp(self):
        _reset_prefs()
        self.snap_threshold = 8
        self.node_count = 3

    def test_side_input_above_spine_node(self):
        """A-input (input[1] of the spine root) must be placed above the spine node.

        After horizontal layout, side_input.ypos() < spine_root.ypos().
        'Above' in Nuke DAG = lower Y value.
        """
        side_input = _StubNode(width=80, height=28, xpos=0, ypos=0, node_class="Grade")
        root = _StubNode(width=80, height=28, xpos=500, ypos=200, node_class="Grade")
        # root has a B-spine input and a side A-input
        root.setInput(0, None)       # no B-spine predecessor
        root.setInput(1, side_input) # A-input (side input)

        nl.place_subtree_horizontal(
            root,
            spine_x=500,
            spine_y=200,
            snap_threshold=self.snap_threshold,
            node_count=self.node_count,
        )

        self.assertLess(
            side_input.ypos(),
            root.ypos(),
            "side (A) input must be placed ABOVE its spine node (lower Y in Nuke DAG) — "
            f"side_input.ypos={side_input.ypos()}, root.ypos={root.ypos()}"
        )


# ---------------------------------------------------------------------------
# TestModeReplay — verifies layout_upstream() body contains horizontal dispatch
# ---------------------------------------------------------------------------


class TestModeReplay(unittest.TestCase):
    """layout_upstream() must dispatch to the horizontal path when stored mode is 'horizontal'.

    Verified via AST: the function body must contain a string literal "horizontal"
    (the dispatch branch), confirming that the mode-read-and-dispatch pattern is present.
    """

    @classmethod
    def setUpClass(cls):
        with open(NODE_LAYOUT_PATH, "r") as source_file:
            source_text = source_file.read()
        cls.tree = ast.parse(source_text, filename=NODE_LAYOUT_PATH)

    def _get_function_body_source(self, function_name):
        """Return the source lines for the named top-level function."""
        with open(NODE_LAYOUT_PATH, "r") as source_file:
            all_lines = source_file.readlines()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                start = node.lineno - 1
                end = node.end_lineno
                return "".join(all_lines[start:end])
        return ""

    def test_layout_upstream_reads_mode_and_dispatches(self):
        """layout_upstream() must contain a dispatch branch for mode == 'horizontal'.

        Verified by checking that the string 'horizontal' appears in the function body
        AND that 'place_subtree_horizontal' is referenced (the dispatch call).
        This fails RED because neither mode-read nor horizontal dispatch exists yet.
        """
        function_source = self._get_function_body_source("layout_upstream")
        self.assertNotEqual(
            function_source, "",
            "layout_upstream() function not found in node_layout.py"
        )
        self.assertIn(
            "horizontal",
            function_source,
            "layout_upstream() must contain a dispatch branch for mode='horizontal' — "
            "string 'horizontal' not found in function body"
        )
        self.assertIn(
            "place_subtree_horizontal",
            function_source,
            "layout_upstream() must call place_subtree_horizontal() in its horizontal "
            "dispatch branch — 'place_subtree_horizontal' not found in function body"
        )


# ---------------------------------------------------------------------------
# TestHighestSubtreePlacement — verifies A/B placement geometry for the
# leftmost spine node (is_last_spine_node block in place_subtree_horizontal)
# ---------------------------------------------------------------------------


class _StubContextManager:
    """Minimal context manager so `with current_group:` works with a non-None stub."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class TestHighestSubtreePlacement(unittest.TestCase):
    """Geometry tests for A-subtree and leftmost Dot placement at the farthest spine node.

    Nuke DAG coordinate system:
      - Positive Y is DOWN; negative Y is UP.
      - Upstream nodes (input[0]) appear at lower Y values (higher on screen).
      - Positive X is right; spine extends leftward (lower X from root).

    The leftmost spine node's input[0] (the A/upstream subtree) must be placed
    DIRECTLY ABOVE the Dot, not diagonally upper-left.  The Dot sits at spine Y,
    to the left of the leftmost spine node.
    """

    def setUp(self):
        _reset_prefs()
        self.snap_threshold = 8
        self.node_count = 3
        self.current_group = _StubContextManager()
        # Read the gap pref used by the implementation.
        self.horizontal_side_gap = _node_layout_prefs_module.prefs_singleton.get(
            "horizontal_side_vertical_gap"
        )
        self.horizontal_subtree_gap = _node_layout_prefs_module.prefs_singleton.get(
            "horizontal_subtree_gap"
        )

    # ------------------------------------------------------------------
    # Helper: build a 1-node spine with an upstream A node (no prior Dot).
    # The upstream node is connected as input[0] of the spine node, and
    # spine_set excludes the upstream so it is treated as the A subtree.
    # ------------------------------------------------------------------

    def _build_spine_with_upstream(self):
        """Return (spine_root, upstream_node, spine_set).

        spine_root: single-node spine placed at (500, 200).
        upstream_node: input[0] of spine_root, not in spine_set.
        spine_set: {id(spine_root)}, causing upstream_node to be treated as A.
        """
        upstream_node = _StubNode(width=80, height=28, xpos=0, ypos=0, node_class="Grade")
        spine_root = _StubNode(width=80, height=28, xpos=500, ypos=200, node_class="Grade")
        spine_root.setInput(0, upstream_node)
        spine_set = {id(spine_root)}
        return spine_root, upstream_node, spine_set

    # ------------------------------------------------------------------
    # Recursive mode tests
    # ------------------------------------------------------------------

    def test_recursive_creates_leftmost_dot(self):
        """Recursive mode must create a leftmost Dot when none exists.

        After calling place_subtree_horizontal with side_layout_mode='recursive',
        spine_root.input(0) should be a Dot with _LEFTMOST_DOT_KNOB_NAME knob,
        or the upstream node's parent should be a Dot. The Dot must exist.
        """
        spine_root, upstream_node, spine_set = self._build_spine_with_upstream()

        nl.place_subtree_horizontal(
            spine_root,
            spine_x=500,
            spine_y=200,
            snap_threshold=self.snap_threshold,
            node_count=self.node_count,
            spine_set=spine_set,
            side_layout_mode="recursive",
            current_group=self.current_group,
        )

        # After recursive run, spine_root.input(0) should be the Dot.
        primary = spine_root.input(0)
        self.assertIsNotNone(
            primary,
            "After recursive layout, spine_root.input(0) must not be None — expected Dot"
        )
        self.assertIsNotNone(
            primary.knob(nl._LEFTMOST_DOT_KNOB_NAME),
            "spine_root.input(0) must have _LEFTMOST_DOT_KNOB_NAME knob — "
            f"got knob={primary.knob(nl._LEFTMOST_DOT_KNOB_NAME)} on node class={primary.Class()}"
        )

    def test_recursive_dot_x_left_of_spine_node(self):
        """Recursive mode: leftmost Dot must be placed to the LEFT of the spine node.

        dot.xpos() < spine_root.xpos() because the Dot is a step left in the X axis.
        """
        spine_root, upstream_node, spine_set = self._build_spine_with_upstream()

        nl.place_subtree_horizontal(
            spine_root,
            spine_x=500,
            spine_y=200,
            snap_threshold=self.snap_threshold,
            node_count=self.node_count,
            spine_set=spine_set,
            side_layout_mode="recursive",
            current_group=self.current_group,
        )

        dot = spine_root.input(0)
        self.assertIsNotNone(dot, "Dot must be created")
        self.assertLess(
            dot.xpos(),
            spine_root.xpos(),
            "leftmost Dot must have xpos < spine_root.xpos() — "
            f"dot.xpos={dot.xpos()}, spine_root.xpos={spine_root.xpos()}"
        )

    def test_recursive_upstream_x_near_dot_x(self):
        """Recursive mode: upstream_root center X must align with Dot center X.

        The correct formula is:
            upstream_x = dot_x + (dot.screenWidth() - upstream_root.screenWidth()) // 2

        This centers the upstream node horizontally over the Dot, so the vertical wire
        from upstream_root drops straight down to the Dot.

        The old broken formula was:
            upstream_x = cur_x - step_x - upstream_w   (places A far left of the Dot)

        Verification: the center X of upstream_root must equal the center X of the Dot
        within 1 pixel (integer arithmetic may cause off-by-one).
        """
        spine_root, upstream_node, spine_set = self._build_spine_with_upstream()

        nl.place_subtree_horizontal(
            spine_root,
            spine_x=500,
            spine_y=200,
            snap_threshold=self.snap_threshold,
            node_count=self.node_count,
            spine_set=spine_set,
            side_layout_mode="recursive",
            current_group=self.current_group,
        )

        dot = spine_root.input(0)
        self.assertIsNotNone(dot, "Dot must be created for X-alignment check")
        upstream_center_x = upstream_node.xpos() + upstream_node.screenWidth() // 2
        dot_center_x = dot.xpos() + dot.screenWidth() // 2
        center_offset = abs(upstream_center_x - dot_center_x)
        self.assertLessEqual(
            center_offset,
            1,
            "upstream_root center X must align with Dot center X (within 1 px) — "
            f"upstream center={upstream_center_x}, dot center={dot_center_x}, "
            f"offset={center_offset}"
        )

    def test_recursive_upstream_y_above_spine(self):
        """Recursive mode: upstream_root Y must be above the spine (lower Y value).

        upstream_root.ypos() < spine_root.ypos() because in Nuke DAG positive Y is down.
        """
        spine_root, upstream_node, spine_set = self._build_spine_with_upstream()

        nl.place_subtree_horizontal(
            spine_root,
            spine_x=500,
            spine_y=200,
            snap_threshold=self.snap_threshold,
            node_count=self.node_count,
            spine_set=spine_set,
            side_layout_mode="recursive",
            current_group=self.current_group,
        )

        self.assertLess(
            upstream_node.ypos(),
            spine_root.ypos(),
            "upstream_root must be above spine (lower Y in Nuke DAG) — "
            f"upstream_node.ypos={upstream_node.ypos()}, spine_root.ypos={spine_root.ypos()}"
        )

    def test_recursive_no_overlap_upstream_and_spine(self):
        """Recursive mode: upstream_root and spine_root must not overlap.

        Overlap check: either
          - upstream_root.xpos() + upstream_root.screenWidth() <= spine_root.xpos(), OR
          - upstream_root.xpos() >= spine_root.xpos() + spine_root.screenWidth(), OR
          - upstream_root.ypos() + upstream_root.screenHeight() <= spine_root.ypos()
        At least one condition must hold.
        """
        spine_root, upstream_node, spine_set = self._build_spine_with_upstream()

        nl.place_subtree_horizontal(
            spine_root,
            spine_x=500,
            spine_y=200,
            snap_threshold=self.snap_threshold,
            node_count=self.node_count,
            spine_set=spine_set,
            side_layout_mode="recursive",
            current_group=self.current_group,
        )

        no_horizontal_overlap = (
            upstream_node.xpos() + upstream_node.screenWidth() <= spine_root.xpos()
            or upstream_node.xpos() >= spine_root.xpos() + spine_root.screenWidth()
        )
        no_vertical_overlap = (
            upstream_node.ypos() + upstream_node.screenHeight() <= spine_root.ypos()
        )
        self.assertTrue(
            no_horizontal_overlap or no_vertical_overlap,
            "upstream_root and spine_root must not overlap — "
            f"upstream: ({upstream_node.xpos()}, {upstream_node.ypos()}, "
            f"w={upstream_node.screenWidth()}, h={upstream_node.screenHeight()}), "
            f"spine: ({spine_root.xpos()}, {spine_root.ypos()}, "
            f"w={spine_root.screenWidth()}, h={spine_root.screenHeight()})"
        )

    # ------------------------------------------------------------------
    # place_only mode tests
    # ------------------------------------------------------------------

    def test_place_only_creates_leftmost_dot(self):
        """place_only mode must create a leftmost Dot when none exists.

        The current implementation never calls _find_or_create_leftmost_dot in
        place_only mode — so this test fails RED until the fix is applied.
        """
        spine_root, upstream_node, spine_set = self._build_spine_with_upstream()

        nl.place_subtree_horizontal(
            spine_root,
            spine_x=500,
            spine_y=200,
            snap_threshold=self.snap_threshold,
            node_count=self.node_count,
            spine_set=spine_set,
            side_layout_mode="place_only",
            current_group=self.current_group,
        )

        primary = spine_root.input(0)
        self.assertIsNotNone(
            primary,
            "After place_only layout, spine_root.input(0) must not be None — expected Dot"
        )
        self.assertIsNotNone(
            primary.knob(nl._LEFTMOST_DOT_KNOB_NAME),
            "place_only mode must create a Dot with _LEFTMOST_DOT_KNOB_NAME when none exists — "
            f"got knob={primary.knob(nl._LEFTMOST_DOT_KNOB_NAME)}"
        )

    def test_place_only_upstream_x_near_dot_x(self):
        """place_only mode: upstream_root center X must align with Dot center X.

        After the fix, upstream_x is derived from dot_x (centered on Dot width):
            upstream_x = dot_x + (dot.screenWidth() - upstream_root.screenWidth()) // 2

        The broken implementation places A at cur_x - step_x - upstream_right_extent
        which is far left of the Dot.

        Verification: the center X of upstream_root must equal the center X of the Dot
        within 1 pixel (integer arithmetic may cause off-by-one).
        """
        spine_root, upstream_node, spine_set = self._build_spine_with_upstream()

        nl.place_subtree_horizontal(
            spine_root,
            spine_x=500,
            spine_y=200,
            snap_threshold=self.snap_threshold,
            node_count=self.node_count,
            spine_set=spine_set,
            side_layout_mode="place_only",
            current_group=self.current_group,
        )

        dot = spine_root.input(0)
        if dot is None or dot.knob(nl._LEFTMOST_DOT_KNOB_NAME) is None:
            self.fail(
                "place_only mode must create a Dot — cannot verify upstream X without Dot. "
                "Fix Dot creation first."
            )

        upstream_center_x = upstream_node.xpos() + upstream_node.screenWidth() // 2
        dot_center_x = dot.xpos() + dot.screenWidth() // 2
        center_offset = abs(upstream_center_x - dot_center_x)
        self.assertLessEqual(
            center_offset,
            1,
            "place_only: upstream_root center X must align with Dot center X (within 1 px) — "
            f"upstream center={upstream_center_x}, dot center={dot_center_x}, "
            f"offset={center_offset}"
        )

    def test_place_only_upstream_y_above_spine(self):
        """place_only mode: upstream_root Y must be above the spine (lower Y value).

        upstream_root.ypos() < spine_root.ypos() — negative Y direction = up.
        """
        spine_root, upstream_node, spine_set = self._build_spine_with_upstream()

        nl.place_subtree_horizontal(
            spine_root,
            spine_x=500,
            spine_y=200,
            snap_threshold=self.snap_threshold,
            node_count=self.node_count,
            spine_set=spine_set,
            side_layout_mode="place_only",
            current_group=self.current_group,
        )

        self.assertLess(
            upstream_node.ypos(),
            spine_root.ypos(),
            "place_only: upstream_root must be above spine (lower Y in Nuke DAG) — "
            f"upstream_node.ypos={upstream_node.ypos()}, spine_root.ypos={spine_root.ypos()}"
        )

    def test_place_only_dot_x_left_of_spine_node(self):
        """place_only mode: Dot must be placed to the LEFT of the spine node.

        dot.xpos() < spine_root.xpos() — Dot is one step left of the spine node.
        """
        spine_root, upstream_node, spine_set = self._build_spine_with_upstream()

        nl.place_subtree_horizontal(
            spine_root,
            spine_x=500,
            spine_y=200,
            snap_threshold=self.snap_threshold,
            node_count=self.node_count,
            spine_set=spine_set,
            side_layout_mode="place_only",
            current_group=self.current_group,
        )

        dot = spine_root.input(0)
        if dot is None or dot.knob(nl._LEFTMOST_DOT_KNOB_NAME) is None:
            self.fail(
                "place_only mode must create a Dot — cannot verify Dot X without Dot. "
                "Fix Dot creation first."
            )

        self.assertLess(
            dot.xpos(),
            spine_root.xpos(),
            "place_only: leftmost Dot must have xpos < spine_root.xpos() — "
            f"dot.xpos={dot.xpos()}, spine_root.xpos={spine_root.xpos()}"
        )


# ---------------------------------------------------------------------------
# TestDownstreamReplayAnchor — verifies layout_upstream horizontal anchor places
# the chain to the RIGHT of the downstream consumer (not above it).
# ---------------------------------------------------------------------------


class TestDownstreamReplayAnchor(unittest.TestCase):
    """layout_upstream horizontal anchor must place the chain to the RIGHT of the consumer.

    When the ancestor walk finds a different upstream root (root is not original_selected_root),
    the spine_x formula must be:
        spine_x = original_selected_root.xpos() + original_selected_root.screenWidth() + horizontal_gap
        spine_y = original_selected_root.ypos()

    The old vertical formula (placing above with loose_gap) must be replaced.

    Test approach: AST inspection of layout_upstream() body. The horizontal anchor block
    must contain the corrected right-of-consumer formula pattern. This detects regression
    without needing to call layout_upstream() in the stub environment.
    """

    @classmethod
    def setUpClass(cls):
        with open(NODE_LAYOUT_PATH, "r") as source_file:
            cls.source_text = source_file.read()
        cls.tree = ast.parse(cls.source_text, filename=NODE_LAYOUT_PATH)

    def _get_layout_upstream_source(self):
        """Extract the source text of the layout_upstream function body."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef) and node.name == "layout_upstream":
                # Extract lines corresponding to this function
                lines = self.source_text.splitlines()
                start_line = node.lineno - 1
                end_line = node.end_lineno
                return "\n".join(lines[start_line:end_line])
        return ""

    def test_horizontal_replay_placed_right_of_consumer(self):
        """layout_upstream horizontal anchor must use screenWidth() + horizontal_gap formula.

        The corrected spine_x formula places the horizontal chain to the RIGHT of the
        downstream consumer node:
            spine_x = original_selected_root.xpos() + original_selected_root.screenWidth() + horizontal_gap

        This test confirms the vertical formula has been replaced. It fails RED when the
        old 'above consumer' formula (using loose_gap / _DOT_TILE_HEIGHT) is present.
        """
        fn_source = self._get_layout_upstream_source()
        self.assertNotEqual(fn_source, "", "layout_upstream() not found in source")

        # The corrected formula must reference screenWidth() followed by horizontal_gap
        # within the spine_x assignment in the horizontal anchor block.
        # We check for the key pattern: screenWidth() used in spine_x with a gap addition.
        has_right_of_consumer_formula = (
            "screenWidth() + horizontal_gap" in fn_source
        )
        self.assertTrue(
            has_right_of_consumer_formula,
            "layout_upstream() horizontal anchor block must use right-of-consumer formula:\n"
            "  spine_x = original_selected_root.xpos() + original_selected_root.screenWidth() + horizontal_gap\n"
            "Found old vertical formula instead (loose_gap / _DOT_TILE_HEIGHT). "
            "Fix: replace the above-consumer anchor with right-of-consumer anchor in layout_upstream()."
        )

    def test_vertical_formula_removed_from_horizontal_anchor(self):
        """The old vertical formula using _DOT_TILE_HEIGHT must be removed from layout_upstream.

        The old buggy code used:
            spine_y = original_selected_root.ypos() - loose_gap - _DOT_TILE_HEIGHT - loose_gap - root.screenHeight()
        This formula placed the chain ABOVE the consumer (vertical semantics).
        After the fix, _DOT_TILE_HEIGHT must not appear in the horizontal anchor block.
        """
        fn_source = self._get_layout_upstream_source()
        self.assertNotEqual(fn_source, "", "layout_upstream() not found in source")

        self.assertNotIn(
            "_DOT_TILE_HEIGHT",
            fn_source,
            "layout_upstream() horizontal anchor block must NOT contain _DOT_TILE_HEIGHT — "
            "this is a sign the old vertical formula (above-consumer placement) is still present. "
            "Replace it with the right-of-consumer formula: "
            "spine_x = original_selected_root.xpos() + original_selected_root.screenWidth() + horizontal_gap"
        )

    def test_spine_y_equals_consumer_ypos(self):
        """After the fix, spine_y must be original_selected_root.ypos() (same Y as consumer).

        The corrected anchor places the horizontal chain at the consumer's Y level
        (extending to the right), not above it. The formula must be:
            spine_y = original_selected_root.ypos()
        """
        fn_source = self._get_layout_upstream_source()
        self.assertNotEqual(fn_source, "", "layout_upstream() not found in source")

        # Check that spine_y = original_selected_root.ypos() pattern exists
        # in the horizontal anchor block (not the else branch)
        has_consumer_y_formula = (
            "spine_y = original_selected_root.ypos()" in fn_source
        )
        self.assertTrue(
            has_consumer_y_formula,
            "layout_upstream() horizontal anchor must set spine_y = original_selected_root.ypos()\n"
            "to place the chain at the same Y level as the consumer (not above it)."
        )


# ---------------------------------------------------------------------------
# TestPlaceOutputDotForHorizontalRootReplay — verifies _place_output_dot_for_horizontal_root
# uses id()-based identity comparison so Nuke proxy wrappers are matched correctly.
# ---------------------------------------------------------------------------


class TestPlaceOutputDotForHorizontalRootReplay(unittest.TestCase):
    """_place_output_dot_for_horizontal_root must reuse the existing Dot on replay.

    The function scans allNodes() to find either:
    - An existing output Dot (node_layout_output_dot knob) whose input[0] is root
    - A downstream consumer with root wired into one of its slots

    Regression guard: the identity check must use id(node.input(0)) == id(root)
    (not `is`) so Nuke proxy wrapper objects are matched correctly. The stub
    environment uses real Python identity so both `is` and id() work; this test
    documents the contract and guards against regression back to bare `is`.
    """

    def setUp(self):
        _reset_prefs()
        _stub_all_nodes_list.clear()

    def tearDown(self):
        _stub_all_nodes_list.clear()

    def test_place_output_dot_reused_on_replay(self):
        """Calling _place_output_dot_for_horizontal_root twice must return the same Dot.

        First call creates a new Dot (consumer.input(0) is root).
        Second call must detect the existing Dot via id()-based identity and reuse it —
        no duplicate Dot should be created.
        """
        root = _StubNode(width=80, height=28, xpos=500, ypos=200, node_class="Grade")
        consumer = _StubNode(width=80, height=28, xpos=500, ypos=400, node_class="Grade",
                             num_inputs=2)
        consumer.setInput(0, root)

        # Populate allNodes so the function can scan them
        _stub_all_nodes_list.extend([root, consumer])

        dot_first = nl._place_output_dot_for_horizontal_root(root, current_group=None)

        self.assertIsNotNone(dot_first, "_place_output_dot_for_horizontal_root must return a Dot")

        # Dot is now in the node graph — add it to allNodes for second call
        _stub_all_nodes_list.append(dot_first)

        dot_second = nl._place_output_dot_for_horizontal_root(root, current_group=None)

        self.assertIs(
            dot_first,
            dot_second,
            "_place_output_dot_for_horizontal_root must return the SAME Dot on replay — "
            "identity check (id()-based) must detect the existing Dot and reuse it, "
            "not create a new one"
        )

    def test_place_output_dot_no_duplicate_when_consumer_present(self):
        """First call creates a Dot; consumer's slot is rewired through the Dot.

        After the first call, the consumer's input[0] should be the new Dot,
        not root directly. This verifies the wiring plumbing works correctly.
        """
        root = _StubNode(width=80, height=28, xpos=500, ypos=200, node_class="Grade")
        consumer = _StubNode(width=80, height=28, xpos=500, ypos=400, node_class="Grade",
                             num_inputs=2)
        consumer.setInput(0, root)
        _stub_all_nodes_list.extend([root, consumer])

        dot = nl._place_output_dot_for_horizontal_root(root, current_group=None)

        self.assertIsNotNone(dot, "Must create a Dot when consumer exists")
        # After creation, consumer.input(0) should point to the Dot
        self.assertIs(
            consumer.input(0),
            dot,
            "consumer.input(0) must be rewired to the Dot after first call"
        )


# ---------------------------------------------------------------------------
# TestLeftExtentOverlap — RED regression tests for Bug 1
# The horizontal chain's leftmost node must not overlap the consumer node.
# Currently FAILS because spine_x only accounts for root (m2) clearance,
# not the full leftward extent of the chain.
# ---------------------------------------------------------------------------


class TestLeftExtentOverlap(unittest.TestCase):
    """Leftmost spine node must clear the consumer's right edge by at least step_x.

    Bug 1: When a horizontal chain (n, m, m2) is placed right of consumer m1,
    the current spine_x formula only ensures root (m2) clears m1. Each additional
    spine node steps further left by (step_x + node.screenWidth()), so n can
    end up to the left of (or overlapping) m1.

    Fix: spine_x must be shifted right by the full leftward extent so the
    leftmost node lands right of consumer with a clean step_x gap.

    All test methods here FAIL RED against unmodified node_layout.py.
    They go GREEN after the Bug 1 fix is applied in Plan 11.1-02.
    """

    def setUp(self):
        _reset_prefs()
        _stub_all_nodes_list.clear()
        self.snap_threshold = 8
        self.node_count = 3
        self.step_x = int(
            _node_layout_prefs_module.prefs_singleton.get("horizontal_subtree_gap")
            * _node_layout_prefs_module.prefs_singleton.get("normal_multiplier")
        )
        self.horizontal_gap = _node_layout_prefs_module.prefs_singleton.get(
            "horizontal_subtree_gap"
        )

    def tearDown(self):
        _stub_all_nodes_list.clear()

    def _build_three_node_chain(self):
        """Return (m2, m, n, consumer, spine_set).

        m2 = root (rightmost), m = m2.input(0), n = m.input(0).
        consumer = downstream node placed at xpos=500, width=80.
        spine_set = {id(m2), id(m), id(n)}.
        spine_x_broken = consumer.xpos() + consumer.screenWidth() + horizontal_gap
        (the current bug: only clears m2, not n).
        """
        consumer = _StubNode(width=80, height=28, xpos=500, ypos=400, node_class="Grade")
        n = _StubNode(width=80, height=28, xpos=0, ypos=0, node_class="Grade")
        m = _StubNode(width=80, height=28, xpos=0, ypos=0, node_class="Grade")
        m2 = _StubNode(width=80, height=28, xpos=0, ypos=0, node_class="Grade")

        m.setInput(0, n)
        m2.setInput(0, m)
        consumer.setInput(0, m2)

        spine_set = {id(m2), id(m), id(n)}
        return m2, m, n, consumer, spine_set

    def test_layout_upstream_variant_leftmost_clears_consumer(self):
        """Leftmost spine node (n) must not overlap consumer after layout_upstream anchor.

        layout_upstream computes spine_x as:
            spine_x = consumer.xpos() + consumer.screenWidth() + horizontal_gap

        This places only root (m2) right of consumer. Nodes m and n step further
        left, potentially overlapping consumer.

        Verification: call place_subtree_horizontal with the broken spine_x and assert
            n.xpos() >= consumer.xpos() + consumer.screenWidth() + step_x
        This assertion FAILS because the current formula places n too far left.
        """
        m2, m, n, consumer, spine_set = self._build_three_node_chain()
        _stub_all_nodes_list.extend([n, m, m2, consumer])

        # Replicate the current (broken) spine_x formula from layout_upstream:
        broken_spine_x = (
            consumer.xpos() + consumer.screenWidth() + self.horizontal_gap
        )
        spine_y = consumer.ypos()

        nl.place_subtree_horizontal(
            m2,
            spine_x=broken_spine_x,
            spine_y=spine_y,
            snap_threshold=self.snap_threshold,
            node_count=self.node_count,
            spine_set=spine_set,
            side_layout_mode="place_only",
        )

        consumer_right_edge = consumer.xpos() + consumer.screenWidth()
        minimum_clearance = consumer_right_edge + self.step_x
        self.assertGreaterEqual(
            n.xpos(),
            minimum_clearance,
            "Bug 1: leftmost spine node (n) must clear consumer right edge by at least "
            f"step_x={self.step_x}px — "
            f"n.xpos={n.xpos()}, consumer_right={consumer_right_edge}, "
            f"required >= {minimum_clearance}. "
            "The current broken formula only anchors m2 (root) right of consumer; "
            "n steps {}-{}={} px further left.".format(
                broken_spine_x,
                2 * (self.step_x + n.screenWidth()),
                broken_spine_x - 2 * (self.step_x + n.screenWidth()),
            )
        )

    def test_layout_selected_variant_leftmost_clears_consumer(self):
        """layout_selected also uses the broken spine_x formula — same overlap bug.

        layout_selected's `root is not original_selected_root` branch mirrors
        layout_upstream's branch with the identical formula. This test verifies
        the same overlap occurs when entered via that path, using the same
        place_subtree_horizontal call pattern as layout_selected would produce.

        This assertion FAILS RED until the Bug 1 fix is applied to layout_selected.
        """
        m2, m, n, consumer, spine_set = self._build_three_node_chain()
        _stub_all_nodes_list.extend([n, m, m2, consumer])

        # Same broken formula from layout_selected's horizontal anchor block.
        broken_spine_x = (
            consumer.xpos() + consumer.screenWidth() + self.horizontal_gap
        )
        spine_y = consumer.ypos()

        nl.place_subtree_horizontal(
            m2,
            spine_x=broken_spine_x,
            spine_y=spine_y,
            snap_threshold=self.snap_threshold,
            node_count=self.node_count,
            spine_set=spine_set,
            side_layout_mode="place_only",
        )

        consumer_right_edge = consumer.xpos() + consumer.screenWidth()
        minimum_clearance = consumer_right_edge + self.step_x
        self.assertGreaterEqual(
            n.xpos(),
            minimum_clearance,
            "Bug 1 (layout_selected path): leftmost spine node (n) must clear consumer "
            f"right edge by at least step_x={self.step_x}px — "
            f"n.xpos={n.xpos()}, consumer_right={consumer_right_edge}, "
            f"required >= {minimum_clearance}."
        )


# ---------------------------------------------------------------------------
# TestDotYAlignment — RED regression tests for Bug 2
# When a downstream consumer exists, the output dot's Y must be centred on
# the consumer's Y so the wire from consumer to dot is horizontal.
# Currently FAILS because dot is placed at root.ypos() + root.screenHeight() + dot_gap.
# ---------------------------------------------------------------------------


class TestDotYAlignment(unittest.TestCase):
    """Output dot Y must be centred on consumer node Y when consumer is known.

    Bug 2: All three dot-positioning code paths in _find_or_create_output_dot
    place the dot at root.ypos() + root.screenHeight() + dot_gap (below root).
    The dot should sit at consumer's Y level so the wire from consumer to dot
    is horizontal (same Y), matching the target geometry:

        m1-------.
                 |  (horizontal wire at m1's Y)
                 .  <- output dot, Y centred on m1

    Fix: dot_y = consumer_node.ypos() + (consumer_node.screenHeight() - dot.screenHeight()) // 2

    Tests test_new_dot_y_aligned_with_consumer and test_reuse_check_dot_y_aligned_with_consumer
    FAIL RED against unmodified node_layout.py.
    Test test_no_consumer_returns_none PASSES (regression guard for the no-consumer path).
    """

    def setUp(self):
        _reset_prefs()
        _stub_all_nodes_list.clear()

    def tearDown(self):
        _stub_all_nodes_list.clear()

    def test_new_dot_y_aligned_with_consumer(self):
        """New dot creation path: dot Y must be centred on consumer Y, not below root.

        Calls _find_or_create_output_dot when no dot exists yet (new-dot creation path,
        lines ~404-408 in node_layout.py). Currently dot_y = root.ypos() + root.screenHeight()
        + dot_gap, which places the dot below root. The fix changes this to:
            dot_y = consumer_node.ypos() + (consumer_node.screenHeight() - dot.screenHeight()) // 2

        This test FAILS RED because current code gives dot_y=192 (below root)
        but the assertion requires dot_y=308 (centred on consumer at y=300).
        """
        root = _StubNode(width=80, height=28, xpos=200, ypos=100, node_class="Grade")
        consumer = _StubNode(width=80, height=28, xpos=500, ypos=300, node_class="Grade")
        _stub_all_nodes_list.extend([root, consumer])

        # Wire consumer's slot 0 to root (standard horizontal chain downstream wiring).
        consumer.setInput(0, root)

        dot = nl._find_or_create_output_dot(root, consumer, 0, None)

        self.assertIsNotNone(dot, "_find_or_create_output_dot must return a Dot node")

        expected_dot_y = consumer.ypos() + (consumer.screenHeight() - dot.screenHeight()) // 2
        self.assertEqual(
            dot.ypos(),
            expected_dot_y,
            "Bug 2: output dot Y must be centred on consumer Y so the consumer-to-dot wire "
            f"is horizontal — dot.ypos()={dot.ypos()}, expected={expected_dot_y} "
            f"(consumer.ypos={consumer.ypos()}, consumer.screenHeight={consumer.screenHeight()}, "
            f"dot.screenHeight={dot.screenHeight()}). "
            f"Current broken value: root.ypos + root.screenHeight + dot_gap = "
            f"{root.ypos()} + {root.screenHeight()} + dot_gap"
        )

    def test_reuse_check_dot_y_aligned_with_consumer(self):
        """Reuse-check path: repositioned dot Y must be centred on consumer Y.

        When consumer_node.input(consumer_slot) already has the node_layout_output_dot
        knob, _find_or_create_output_dot repositions the existing dot (lines ~387-390).
        Currently it uses the same broken formula (below root). The fix must also apply
        here:
            dot_y = consumer_node.ypos() + (consumer_node.screenHeight() - dot.screenHeight()) // 2

        This test FAILS RED because current code gives the below-root Y instead of
        the consumer-centred Y.
        """
        root = _StubNode(width=80, height=28, xpos=200, ypos=100, node_class="Grade")
        consumer = _StubNode(width=80, height=28, xpos=500, ypos=300, node_class="Grade")
        existing_dot = _StubDotNode(has_output_dot_knob=True, xpos=0, ypos=0)
        _stub_all_nodes_list.extend([root, consumer, existing_dot])

        # Pre-wire: existing_dot takes root as its input; consumer's slot 0 is the dot.
        existing_dot.setInput(0, root)
        consumer.setInput(0, existing_dot)

        returned_dot = nl._find_or_create_output_dot(root, consumer, 0, None)

        self.assertIsNotNone(returned_dot, "Must return existing dot on reuse-check path")

        expected_dot_y = consumer.ypos() + (consumer.screenHeight() - returned_dot.screenHeight()) // 2
        self.assertEqual(
            returned_dot.ypos(),
            expected_dot_y,
            "Bug 2 (reuse-check path): repositioned dot Y must be centred on consumer Y — "
            f"dot.ypos()={returned_dot.ypos()}, expected={expected_dot_y} "
            f"(consumer.ypos={consumer.ypos()}). "
            "Current broken code uses root.ypos + root.screenHeight + dot_gap instead."
        )

    def test_no_consumer_returns_none(self):
        """When consumer_node is None, _find_or_create_output_dot must return None.

        This is the no-consumer guard (standalone horizontal chain with no downstream
        node). No dot should be created; the function returns None immediately.

        This test PASSES RED (regression guard — must still pass after the Bug 2 fix).
        """
        root = _StubNode(width=80, height=28, xpos=200, ypos=100, node_class="Grade")
        _stub_all_nodes_list.append(root)

        result = nl._find_or_create_output_dot(root, None, 0, None)

        self.assertIsNone(
            result,
            "_find_or_create_output_dot must return None when consumer_node is None — "
            f"got {result!r} instead"
        )


if __name__ == "__main__":
    unittest.main()

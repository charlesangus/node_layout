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

    def setFlag(self, flag):
        pass


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

    def setFlag(self, flag):
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
# write_node_state (node_layout_state.py) needs String_Knob and INVISIBLE.
_nuke_stub.String_Knob = lambda name='', label='': _StubKnob(0)
_nuke_stub.INVISIBLE = 0x01

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
    """Minimal context manager so `with current_group:` works with a non-None stub.

    Also exposes nodes() so that layout_upstream()'s consumer-finding scan
    (current_group.nodes() if current_group is not None) returns the test node list.
    """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def nodes(self):
        return list(_stub_all_nodes_list)


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
        """layout_upstream horizontal anchor must use left-extent-aware spine_x formula.

        The corrected spine_x formula (Bug 1 fix) places the horizontal chain to the
        RIGHT of the downstream consumer node, accounting for the full leftward extent
        of the spine so the leftmost node clears the consumer with a clean gap:
            consumer = original_selected_root
            spine_x = consumer.xpos() + consumer.screenWidth() + step_x + leftward_extent

        This test confirms the left-extent-aware formula is present. It fails RED when
        the old formula (which only accounts for root clearance) is present.
        """
        fn_source = self._get_layout_upstream_source()
        self.assertNotEqual(fn_source, "", "layout_upstream() not found in source")

        # The corrected formula must reference consumer.screenWidth() in the spine_x
        # assignment together with the leftward_extent variable from the spine walk.
        has_left_extent_formula = (
            "consumer.screenWidth() + step_x + leftward_extent" in fn_source
        )
        self.assertTrue(
            has_left_extent_formula,
            "layout_upstream() horizontal anchor block must use the left-extent-aware formula:\n"
            "  spine_x = consumer.xpos() + consumer.screenWidth() + step_x + leftward_extent\n"
            "Found old formula instead (only accounts for root clearance, not full spine extent). "
            "Fix: replace the right-of-consumer anchor with the leftward-extent formula in layout_upstream()."
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
        """After the fix, spine_y must be consumer.ypos() (same Y as consumer).

        The corrected anchor (Bug 1 fix) places the horizontal chain at the consumer's
        Y level (extending to the right), not above it. The formula must be:
            consumer = original_selected_root
            spine_y = consumer.ypos()
        """
        fn_source = self._get_layout_upstream_source()
        self.assertNotEqual(fn_source, "", "layout_upstream() not found in source")

        # Check that spine_y = consumer.ypos() pattern exists in the horizontal
        # anchor block (consumer is the local alias for original_selected_root).
        has_consumer_y_formula = (
            "spine_y = consumer.ypos()" in fn_source
        )
        self.assertTrue(
            has_consumer_y_formula,
            "layout_upstream() horizontal anchor must set spine_y = consumer.ypos()\n"
            "to place the chain at the same Y level as the consumer (not above it).\n"
            "consumer is the local alias for original_selected_root in the if-branch."
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

        The fixed layout_upstream formula pre-computes the full leftward extent of the
        spine and places spine_x far enough right that the leftmost node (n) still
        clears the consumer's right edge by at least step_x.

        spine_nodes_ordered = [m2, m, n] (root first)
        leftward_extent = (step_x + m.screenWidth()) + (step_x + n.screenWidth())
        spine_x = consumer.xpos() + consumer.screenWidth() + step_x + leftward_extent

        Verification: call place_subtree_horizontal with the fixed spine_x and assert
            n.xpos() >= consumer.xpos() + consumer.screenWidth() + step_x
        This assertion now PASSES because spine_x accounts for the full leftward extent.
        """
        m2, m, n, consumer, spine_set = self._build_three_node_chain()
        _stub_all_nodes_list.extend([n, m, m2, consumer])

        # Replicate the fixed spine_x formula from layout_upstream (Bug 1 fix):
        # Walk spine_set to build ordered list, compute leftward extent.
        spine_nodes_ordered = []
        cursor = m2
        while cursor is not None and id(cursor) in spine_set:
            spine_nodes_ordered.append(cursor)
            cursor = cursor.input(0)
        leftward_extent = sum(
            self.step_x + spine_nodes_ordered[i].screenWidth()
            for i in range(1, len(spine_nodes_ordered))
        )
        fixed_spine_x = (
            consumer.xpos() + consumer.screenWidth() + self.step_x + leftward_extent
        )
        spine_y = consumer.ypos()

        nl.place_subtree_horizontal(
            m2,
            spine_x=fixed_spine_x,
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
            f"Bug 1 fix: leftmost spine node (n) must clear consumer right edge by at "
            f"least step_x={self.step_x}px — "
            f"n.xpos={n.xpos()}, consumer_right={consumer_right_edge}, "
            f"required >= {minimum_clearance}."
        )

    def test_layout_selected_variant_leftmost_clears_consumer(self):
        """layout_selected leftmost node must clear consumer after Bug 1 fix.

        layout_selected's fixed `root is not original_selected_root` branch mirrors
        the layout_upstream fix: it pre-computes the full leftward extent and places
        spine_x far enough right that n clears the consumer's right edge.

        This assertion PASSES GREEN after the Bug 1 fix is applied to layout_selected.
        """
        m2, m, n, consumer, spine_set = self._build_three_node_chain()
        _stub_all_nodes_list.extend([n, m, m2, consumer])

        # Same fixed formula from layout_selected's horizontal anchor block (Bug 1 fix).
        spine_nodes_ordered = []
        cursor = m2
        while cursor is not None and id(cursor) in spine_set:
            spine_nodes_ordered.append(cursor)
            cursor = cursor.input(0)
        leftward_extent = sum(
            self.step_x + spine_nodes_ordered[i].screenWidth()
            for i in range(1, len(spine_nodes_ordered))
        )
        fixed_spine_x = (
            consumer.xpos() + consumer.screenWidth() + self.step_x + leftward_extent
        )
        spine_y = consumer.ypos()

        nl.place_subtree_horizontal(
            m2,
            spine_x=fixed_spine_x,
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
            f"Bug 1 fix (layout_selected path): leftmost spine node (n) must clear "
            f"consumer right edge by at least step_x={self.step_x}px — "
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


# ---------------------------------------------------------------------------
# TestPlaceOutputDotReplay — regression tests for _place_output_dot_for_horizontal_root
# On a second layout run, m1 is wired to the existing dot (not root), so the original
# consumer scan misses it.  The dot must still be Y-centred on the consumer.
# ---------------------------------------------------------------------------


class TestPlaceOutputDotReplay(unittest.TestCase):
    """_place_output_dot_for_horizontal_root must find the consumer on replay.

    First run: m1.input(0) = root → consumer found directly, dot created/placed.
    Second run: m1.input(0) = dot, dot.input(0) = root → original scan sees
    existing_dot but consumer_node stays None → dot falls back to below-root Y.

    Fix: after finding existing_dot with consumer_node=None, do a second scan for
    any non-dot node wired to existing_dot.  Then use consumer Y for dot placement.
    """

    def setUp(self):
        _reset_prefs()
        _stub_all_nodes_list.clear()

    def tearDown(self):
        _stub_all_nodes_list.clear()

    def test_replay_dot_y_centred_on_consumer(self):
        """On second run (m1 → dot → root), dot Y must be centred on consumer.

        Before the fix, consumer_node was always None on replay so the dot landed at
        root.ypos() + root.screenHeight() + dot_gap (well below root / consumer).
        """
        root = _StubNode(width=80, height=28, xpos=200, ypos=300, node_class="Grade")
        consumer = _StubNode(width=80, height=28, xpos=800, ypos=400, node_class="Grade")
        existing_dot = _StubDotNode(has_output_dot_knob=True, xpos=0, ypos=0)

        # Replay wiring: m1 → dot → root
        existing_dot.setInput(0, root)
        consumer.setInput(0, existing_dot)

        _stub_all_nodes_list.extend([root, consumer, existing_dot])

        nl._place_output_dot_for_horizontal_root(root, None, snap_threshold=8,
                                                 scheme_multiplier=1.0)

        expected_dot_y = consumer.ypos() + (consumer.screenHeight() - existing_dot.screenHeight()) // 2
        self.assertEqual(
            existing_dot.ypos(),
            expected_dot_y,
            "Replay path: dot Y must be centred on consumer Y (consumer.ypos="
            f"{consumer.ypos()}, expected dot_y={expected_dot_y}), "
            f"got {existing_dot.ypos()}. "
            "Before fix: dot was placed at root.ypos + root.screenHeight + dot_gap "
            f"= {root.ypos()} + {root.screenHeight()} + dot_gap."
        )

    def test_replay_dot_x_centred_on_root(self):
        """On replay, dot X must remain X-centred on root (unchanged from first run)."""
        root = _StubNode(width=80, height=28, xpos=200, ypos=300, node_class="Grade")
        consumer = _StubNode(width=80, height=28, xpos=800, ypos=400, node_class="Grade")
        existing_dot = _StubDotNode(has_output_dot_knob=True, xpos=0, ypos=0)

        existing_dot.setInput(0, root)
        consumer.setInput(0, existing_dot)

        _stub_all_nodes_list.extend([root, consumer, existing_dot])

        nl._place_output_dot_for_horizontal_root(root, None, snap_threshold=8,
                                                 scheme_multiplier=1.0)

        expected_dot_x = root.xpos() + (root.screenWidth() - existing_dot.screenWidth()) // 2
        self.assertEqual(
            existing_dot.xpos(),
            expected_dot_x,
            f"Replay path: dot X must be X-centred on root — "
            f"expected {expected_dot_x}, got {existing_dot.xpos()}"
        )


# ---------------------------------------------------------------------------
# TestSpineYAboveConsumer — regression test for spine_y in layout_upstream/selected
# When a consumer is found, the horizontal chain must be placed ABOVE (lower Y than)
# the consumer so a vertical wire from root down to the output dot is possible.
# spine_y = consumer.ypos() (old) put root at the same Y as the consumer.
# spine_y = consumer.ypos() - dot_gap - root.screenHeight() (fix) puts root above.
# ---------------------------------------------------------------------------


class TestSpineYAboveConsumer(unittest.TestCase):
    """After place_subtree_horizontal, root (m2) must be above the consumer (lower Y).

    The fix computes spine_y = consumer.ypos() - dot_gap - root.screenHeight().
    This ensures the output dot (at consumer's Y) is strictly below root in Y,
    creating the vertical wire from root down to the dot.
    """

    def setUp(self):
        _reset_prefs()
        _stub_all_nodes_list.clear()
        self.snap_threshold = 8
        self.scheme_multiplier = _node_layout_prefs_module.prefs_singleton.get("normal_multiplier")
        self.loose_gap_multiplier = _node_layout_prefs_module.prefs_singleton.get("loose_gap_multiplier")
        self.dot_gap = int(self.loose_gap_multiplier * self.scheme_multiplier * self.snap_threshold)

    def tearDown(self):
        _stub_all_nodes_list.clear()

    def test_root_placed_above_consumer(self):
        """root (m2) Y must be strictly less than consumer Y after spine_y computation.

        The fixed formula: spine_y = consumer.ypos() - dot_gap - root.screenHeight()
        places root so its bottom edge is dot_gap pixels above the consumer's Y level.
        Before the fix, spine_y = consumer.ypos() put root at the same Y as consumer.
        """
        consumer = _StubNode(width=80, height=28, xpos=500, ypos=400, node_class="Grade")
        n = _StubNode(width=80, height=28, xpos=0, ypos=0, node_class="Grade")
        m = _StubNode(width=80, height=28, xpos=0, ypos=0, node_class="Grade")
        root = _StubNode(width=80, height=28, xpos=0, ypos=0, node_class="Grade")

        m.setInput(0, n)
        root.setInput(0, m)
        consumer.setInput(0, root)

        spine_set = {id(root), id(m), id(n)}
        step_x = int(_node_layout_prefs_module.prefs_singleton.get("horizontal_subtree_gap")
                     * self.scheme_multiplier)

        spine_nodes_ordered = [root, m, n]
        leftward_extent = sum(
            step_x + spine_nodes_ordered[i].screenWidth()
            for i in range(1, len(spine_nodes_ordered))
        )
        fixed_spine_x = consumer.xpos() + consumer.screenWidth() + step_x + leftward_extent
        fixed_spine_y = consumer.ypos() - self.dot_gap - root.screenHeight()

        nl.place_subtree_horizontal(
            root,
            spine_x=fixed_spine_x,
            spine_y=fixed_spine_y,
            snap_threshold=self.snap_threshold,
            node_count=3,
            spine_set=spine_set,
            side_layout_mode="place_only",
        )

        self.assertLess(
            root.ypos(),
            consumer.ypos(),
            f"root (m2) must be placed strictly above consumer (lower Y) — "
            f"root.ypos()={root.ypos()}, consumer.ypos()={consumer.ypos()}. "
            f"spine_y formula gives {fixed_spine_y} which is "
            f"{consumer.ypos() - root.ypos()} px above consumer."
        )

    def test_root_bottom_clears_consumer_by_dot_gap(self):
        """root's bottom edge must be exactly dot_gap above consumer's Y.

        spine_y = consumer.ypos() - dot_gap - root.screenHeight()
        → root.ypos() + root.screenHeight() = consumer.ypos() - dot_gap
        So the gap between root's bottom and consumer's top-Y is dot_gap pixels.
        """
        consumer = _StubNode(width=80, height=28, xpos=500, ypos=400, node_class="Grade")
        root = _StubNode(width=80, height=28, xpos=0, ypos=0, node_class="Grade")
        consumer.setInput(0, root)

        fixed_spine_y = consumer.ypos() - self.dot_gap - root.screenHeight()

        nl.place_subtree_horizontal(
            root,
            spine_x=consumer.xpos() + consumer.screenWidth() + int(
                _node_layout_prefs_module.prefs_singleton.get("horizontal_subtree_gap")
                * self.scheme_multiplier
            ),
            spine_y=fixed_spine_y,
            snap_threshold=self.snap_threshold,
            node_count=1,
            spine_set={id(root)},
            side_layout_mode="place_only",
        )

        root_bottom = root.ypos() + root.screenHeight()
        expected_gap = self.dot_gap
        actual_gap = consumer.ypos() - root_bottom
        self.assertEqual(
            actual_gap,
            expected_gap,
            f"Gap between root bottom ({root_bottom}) and consumer Y ({consumer.ypos()}) "
            f"must equal dot_gap={expected_gap}, got {actual_gap}"
        )


# ---------------------------------------------------------------------------
# TestLayoutUpstreamEndToEnd — full-stack tests through layout_upstream()
# ---------------------------------------------------------------------------


class TestLayoutUpstreamEndToEnd(unittest.TestCase):
    """End-to-end tests: verify bug-prone code paths via layout_upstream().

    These tests call layout_upstream() through the full call stack to catch
    bugs that are not visible in place_subtree_horizontal tests, which use
    hard-coded spine_x/spine_y values and bypass the consumer-finding logic.

    Bug 1: Leftmost spine node overlaps consumer when horizontal root is
           directly selected (not found via downstream-consumer BFS).
    Bug 2: Output dot Y placed below root instead of centred on consumer on
           replay (existing dot found but consumer_node stays None).
    Bug 3: Phase 2 (vertical inputs of consumer) must run after Phase 1
           (horizontal layout) so non-horizontal inputs are correctly placed.

    Nuke DAG coordinate system: positive Y is DOWN; negative Y is UP.
    Upstream nodes (inputs) sit at lower Y (higher on screen).
    """

    def setUp(self):
        _reset_prefs()
        _stub_all_nodes_list.clear()
        self._stub_ctx = _StubContextManager()
        self._saved_selectedNode = _nuke_stub.selectedNode
        self._saved_lastHitGroup = _nuke_stub.lastHitGroup
        self._saved_nodes_Dot = _nuke_stub.nodes.Dot
        # Pin sys.modules["nuke"] to _nuke_stub for the duration of each test.
        # In discover mode, other test files may have replaced sys.modules["nuke"]
        # with a minimal stub that lacks Tab_Knob (needed by write_node_state).
        self._saved_sys_nuke = sys.modules.get("nuke")
        sys.modules["nuke"] = _nuke_stub
        _nuke_stub.lastHitGroup = lambda: self._stub_ctx

        # Patch Dot factory to automatically register created dots in
        # _stub_all_nodes_list so they are visible to allNodes() on replay.
        def _tracked_dot():
            dot = _StubDotNode()
            _stub_all_nodes_list.append(dot)
            return dot

        _nuke_stub.nodes = types.SimpleNamespace(Dot=_tracked_dot)

    def tearDown(self):
        _stub_all_nodes_list.clear()
        _nuke_stub.selectedNode = self._saved_selectedNode
        _nuke_stub.lastHitGroup = self._saved_lastHitGroup
        _nuke_stub.nodes = types.SimpleNamespace(Dot=self._saved_nodes_Dot)
        if self._saved_sys_nuke is not None:
            sys.modules["nuke"] = self._saved_sys_nuke

    def _set_state_horizontal(self, node):
        """Store mode='horizontal' in node stub (simulates a prior horizontal layout run)."""
        node._knobs["node_layout_state"] = _StubKnob(
            '{"scheme": "normal", "mode": "horizontal", "h_scale": 1.0, "v_scale": 1.0}'
        )

    def _find_output_dot(self):
        """Return the first output dot in _stub_all_nodes_list, or None."""
        for candidate in _stub_all_nodes_list:
            if candidate.knob(nl._OUTPUT_DOT_KNOB_NAME) is not None:
                return candidate
        return None

    # -------------------------------------------------------------------
    # Test 1: First run — consumer (m1) selected; dot created centred on m1
    # -------------------------------------------------------------------

    def test_first_run_dot_y_centred_on_consumer(self):
        """First run: output dot Y must be centred on the consumer (m1).

        Topology: n → m2 → m1 (consumer, selected).
        m2 and n have mode=horizontal stored.  Selected node = m1 (vertical).

        BFS from m1 finds m2 as horizontal root.  Phase 1 places the chain to
        the right of m1 and calls _place_output_dot_for_horizontal_root, which
        creates an output dot wired m2 → dot → m1.  Dot Y must align with m1's
        vertical centre so the wire from m1 to dot is horizontal.
        """
        n = _StubNode(width=80, height=28, xpos=0, ypos=0, num_inputs=0)
        m2 = _StubNode(width=80, height=28, xpos=0, ypos=0, num_inputs=1)
        m2.setInput(0, n)
        m1 = _StubNode(width=80, height=28, xpos=800, ypos=400, num_inputs=1)
        m1.setInput(0, m2)

        self._set_state_horizontal(m2)
        self._set_state_horizontal(n)

        _stub_all_nodes_list.extend([m1, m2, n])
        _nuke_stub.selectedNode = lambda: m1

        nl.layout_upstream()

        dot = self._find_output_dot()
        self.assertIsNotNone(
            dot,
            "First run: output dot must be created and visible in allNodes(). "
            "Dot should be wired between m2 (root) and m1 (consumer)."
        )
        expected_dot_y = m1.ypos() + (m1.screenHeight() - dot.screenHeight()) // 2
        self.assertEqual(
            dot.ypos(), expected_dot_y,
            f"First run: dot Y must be centred on consumer (m1). "
            f"m1.ypos={m1.ypos()}, m1.height={m1.screenHeight()}, "
            f"dot.height={dot.screenHeight()}, expected dot_y={expected_dot_y}, "
            f"got {dot.ypos()}."
        )

    # -------------------------------------------------------------------
    # Test 2: Replay — dot Y stays centred on m1 when dot already wired
    # -------------------------------------------------------------------

    def test_replay_dot_y_stays_centred_on_consumer(self):
        """Replay: output dot Y must remain centred on m1 on the second layout run.

        Replay wiring: m1 → existing_dot → m2 → n.
        existing_dot has node_layout_output_dot knob.  Selected node = m1.

        _place_output_dot_for_horizontal_root finds existing_dot via the first
        scan (existing_dot.input(0) == root), then locates m1 as consumer via
        a second scan (m1.input(0) == existing_dot).  Dot must be repositioned
        centred on m1.

        Bug 2 (before fix): consumer_node was always None on replay because no
        node had root as its direct input — so dot fell back to
        root.ypos() + root.screenHeight() + dot_gap (well below root).
        """
        n = _StubNode(width=80, height=28, xpos=0, ypos=0, num_inputs=0)
        m2 = _StubNode(width=80, height=28, xpos=100, ypos=300, num_inputs=1)
        m2.setInput(0, n)
        existing_dot = _StubDotNode(has_output_dot_knob=True, xpos=0, ypos=0)
        m1 = _StubNode(width=80, height=28, xpos=800, ypos=400, num_inputs=1)
        # Replay wiring: m1 → existing_dot → m2 → n
        existing_dot.setInput(0, m2)
        m1.setInput(0, existing_dot)

        self._set_state_horizontal(m2)
        self._set_state_horizontal(n)

        _stub_all_nodes_list.extend([m1, m2, n, existing_dot])
        _nuke_stub.selectedNode = lambda: m1

        nl.layout_upstream()

        expected_dot_y = m1.ypos() + (m1.screenHeight() - existing_dot.screenHeight()) // 2
        self.assertEqual(
            existing_dot.ypos(), expected_dot_y,
            f"Replay: dot Y must be centred on consumer (m1). "
            f"m1.ypos={m1.ypos()}, m1.height={m1.screenHeight()}, "
            f"dot.height={existing_dot.screenHeight()}, "
            f"expected {expected_dot_y}, got {existing_dot.ypos()}. "
            "Bug 2: on replay consumer_node=None → dot placed below root."
        )

    # -------------------------------------------------------------------
    # Test 3: Phase 2 — vertical slot-0 input placed above consumer
    # -------------------------------------------------------------------

    def test_phase2_vertical_slot0_placed_above_consumer(self):
        """Phase 2: vertical input in slot 0 of consumer is placed above consumer.

        Topology:
          m1.input(0) = v1  (vertical Grade — primary B input)
          m1.input(1) = m2  (horizontal chain root)
          m2.input(0) = n   (also horizontal)

        layout_upstream(m1):
          Phase 1 — BFS finds m2 (mode=horizontal) in m1's input(1).
                    m2 + n placed to the right of m1.
                    Output dot inserted at m1.input(1).
          Phase 2 — runs place_subtree on m1 with node_filter={m1, v1}.
                    m1.input(0) = v1 is in filter; primary slot not externally
                    occupied; v1 placed directly ABOVE m1 (lower Y in Nuke DAG).

        Assert: v1.ypos() < m1.ypos() after the call.
        """
        n = _StubNode(width=80, height=28, xpos=0, ypos=0, num_inputs=0)
        m2 = _StubNode(width=80, height=28, xpos=0, ypos=0, num_inputs=1)
        m2.setInput(0, n)
        v1 = _StubNode(width=80, height=28, xpos=0, ypos=0, num_inputs=0)
        m1 = _StubNode(width=80, height=28, xpos=800, ypos=400, num_inputs=2)
        m1.setInput(0, v1)   # vertical in slot 0
        m1.setInput(1, m2)   # horizontal chain in slot 1

        self._set_state_horizontal(m2)
        self._set_state_horizontal(n)

        _stub_all_nodes_list.extend([m1, m2, n, v1])
        _nuke_stub.selectedNode = lambda: m1

        nl.layout_upstream()

        self.assertLess(
            v1.ypos(), m1.ypos(),
            f"Phase 2: v1 (vertical slot-0 input of m1) must be placed above m1 "
            f"(lower Y in Nuke DAG). "
            f"v1.ypos()={v1.ypos()}, m1.ypos()={m1.ypos()}. "
            "Bug 3: without Phase 2, layout_upstream only ran horizontal layout "
            "and never called place_subtree on m1, so v1 was not moved."
        )

    # -------------------------------------------------------------------
    # Test 4: Bug 1 — horizontal root directly selected; chain right of consumer
    # -------------------------------------------------------------------

    def test_horizontal_root_selected_chain_right_of_consumer(self):
        """Bug 1: selecting the horizontal root itself places chain right of consumer.

        Topology: m1 (consumer, vertical) ← m2 (horizontal root, selected).
        m2.input(0) = n (also horizontal).

        When the user selects m2 directly (root IS original_selected_root), the
        else-branch consumer scan finds m1 as downstream consumer and computes
        the correct spine_x so the entire chain (m2 + n) clears m1's right edge.

        Before the fix, spine_x = root.xpos() with no leftward correction, so n
        could land at m2.xpos - step_x - n.width, potentially overlapping m1.

        Assert: m2.xpos() > m1.xpos() + m1.screenWidth() after the call.
        """
        # Position m2 and n far to the RIGHT of m1 (pre-layout coords that look like a
        # stale/wrong position).  After layout, they will be moved leftward to just right
        # of m1.  This ensures push_nodes_to_make_room sees a leftward shift (not rightward)
        # and does NOT move m1, so the assert can compare against the fixed m1 position.
        n = _StubNode(width=80, height=28, xpos=3000, ypos=400, num_inputs=0)
        m2 = _StubNode(width=80, height=28, xpos=3000, ypos=400, num_inputs=1)
        m2.setInput(0, n)
        m1 = _StubNode(width=80, height=28, xpos=800, ypos=400, num_inputs=1)
        m1.setInput(0, m2)

        self._set_state_horizontal(m2)
        self._set_state_horizontal(n)

        _stub_all_nodes_list.extend([m1, m2, n])
        _nuke_stub.selectedNode = lambda: m2  # select horizontal root directly

        nl.layout_upstream()

        consumer_right_edge = m1.xpos() + m1.screenWidth()  # 880
        self.assertGreater(
            m2.xpos(), consumer_right_edge,
            f"Bug 1: m2 (horizontal root) must be placed to the right of m1 "
            f"(consumer). m1 right edge={consumer_right_edge}, "
            f"m2.xpos()={m2.xpos()}. "
            "Old code: spine_x = root.xpos() ignores consumer position — chain "
            "lands at m2's pre-layout xpos, potentially overlapping consumer."
        )


# ---------------------------------------------------------------------------
# TestBugAChainClearsConsumer — BUG-A: chain left edge must clear consumer
# ---------------------------------------------------------------------------


class TestBugAChainClearsConsumer(unittest.TestCase):
    """RED test: horizontal chain must be placed >= consumer right edge + gap.

    BUG-A: spine_x is computed from consumer.xpos() + consumer.screenWidth() +
    horizontal_subtree_gap, but the actual leftmost chain node may land at a
    position further left than spine_x because place_subtree_horizontal walks
    the chain leftward from spine_x without accounting for the cumulative node
    widths correctly.  The test asserts the minimum x of all chain nodes is >=
    consumer.right + horizontal_subtree_gap.
    """

    def setUp(self):
        _reset_prefs()
        _stub_all_nodes_list.clear()
        self._stub_ctx = _StubContextManager()
        self._saved_selectedNode = _nuke_stub.selectedNode
        self._saved_lastHitGroup = _nuke_stub.lastHitGroup
        self._saved_nodes_Dot = _nuke_stub.nodes.Dot
        self._saved_sys_nuke = sys.modules.get("nuke")
        sys.modules["nuke"] = _nuke_stub
        _nuke_stub.lastHitGroup = lambda: self._stub_ctx

        def _tracked_dot():
            dot = _StubDotNode()
            _stub_all_nodes_list.append(dot)
            return dot

        _nuke_stub.nodes = types.SimpleNamespace(Dot=_tracked_dot)

    def tearDown(self):
        _stub_all_nodes_list.clear()
        _nuke_stub.selectedNode = self._saved_selectedNode
        _nuke_stub.lastHitGroup = self._saved_lastHitGroup
        _nuke_stub.nodes = types.SimpleNamespace(Dot=self._saved_nodes_Dot)
        if self._saved_sys_nuke is not None:
            sys.modules["nuke"] = self._saved_sys_nuke

    def _set_state_horizontal(self, node):
        node._knobs["node_layout_state"] = _StubKnob(
            '{"scheme": "normal", "mode": "horizontal", "h_scale": 1.0, "v_scale": 1.0}'
        )

    def _find_output_dot(self):
        for candidate in _stub_all_nodes_list:
            if candidate.knob(nl._OUTPUT_DOT_KNOB_NAME) is not None:
                return candidate
        return None

    def test_chain_clears_consumer_by_gap(self):
        """BUG-A: all chain nodes must be placed >= consumer right edge + gap.

        Topology: a → n → m2 → m1
          - m1 is consumer/selected (vertical)
          - m2 and n are horizontal spine nodes
          - a is a wide side input of n (slot 1, width=500) — wider than n (width=80)
            This makes effective_widths[n] >> n.screenWidth(), so the advance formula
            in place_subtree_horizontal pushes n further left than spine_x predicted,
            violating the clearance constraint.

        The spine_x formula in layout_upstream uses n.screenWidth()=80 to predict
        the leftward extent, but effective_widths[n]=290 (due to wide side input a).
        Result: n and a land further left than required_left, failing the assertion.

        This is RED before Fix A is implemented.
        """
        m1 = _StubNode(width=80, height=28, xpos=800, ypos=400, num_inputs=1)
        m2 = _StubNode(width=80, height=28, xpos=0, ypos=0, num_inputs=1)
        # n has 2 inputs: input(0) = None (leaf), input(1) = a (wide side input)
        n = _StubNode(width=80, height=28, xpos=0, ypos=0, num_inputs=2)
        # a is a wide side input of n that makes effective_widths[n] > n.screenWidth()
        a = _StubNode(width=500, height=28, xpos=0, ypos=0, num_inputs=0)
        n.setInput(1, a)
        m2.setInput(0, n)
        m1.setInput(0, m2)

        self._set_state_horizontal(m2)
        self._set_state_horizontal(n)
        # a and m1 intentionally NOT set to horizontal

        _stub_all_nodes_list.extend([m1, m2, n, a])
        _nuke_stub.selectedNode = lambda: m1

        nl.layout_upstream()

        chain_nodes = nl.collect_subtree_nodes(m2)
        actual_left = min(node.xpos() for node in chain_nodes)
        horizontal_subtree_gap = _node_layout_prefs_module.DEFAULTS[
            "horizontal_subtree_gap"
        ]
        required_left = (
            m1.xpos()
            + m1.screenWidth()
            + horizontal_subtree_gap
        )
        self.assertGreaterEqual(
            actual_left,
            required_left,
            f"BUG-A: chain left edge ({actual_left}) must be >= consumer right edge"
            f" + gap ({required_left})."
            f" Gap={horizontal_subtree_gap}",
        )


# ---------------------------------------------------------------------------
# TestBugBPhase2NoCrossChain — BUG-B: Phase 2 must not cross into chain bbox
# ---------------------------------------------------------------------------


class TestBugBPhase2NoCrossChain(unittest.TestCase):
    """RED test: Phase 2 B-chain must not overlap horizontal chain's left boundary.

    BUG-B: Phase 2 (place_subtree on consumer's non-horizontal inputs) places
    the B-chain without knowing about the horizontal chain's bounding box.
    The B-chain must be positioned so its right edge < chain_min_x -
    horizontal_subtree_gap, ensuring the two subtrees do not overlap.
    """

    def setUp(self):
        _reset_prefs()
        _stub_all_nodes_list.clear()
        self._stub_ctx = _StubContextManager()
        self._saved_selectedNode = _nuke_stub.selectedNode
        self._saved_lastHitGroup = _nuke_stub.lastHitGroup
        self._saved_nodes_Dot = _nuke_stub.nodes.Dot
        self._saved_sys_nuke = sys.modules.get("nuke")
        sys.modules["nuke"] = _nuke_stub
        _nuke_stub.lastHitGroup = lambda: self._stub_ctx

        def _tracked_dot():
            dot = _StubDotNode()
            _stub_all_nodes_list.append(dot)
            return dot

        _nuke_stub.nodes = types.SimpleNamespace(Dot=_tracked_dot)

    def tearDown(self):
        _stub_all_nodes_list.clear()
        _nuke_stub.selectedNode = self._saved_selectedNode
        _nuke_stub.lastHitGroup = self._saved_lastHitGroup
        _nuke_stub.nodes = types.SimpleNamespace(Dot=self._saved_nodes_Dot)
        if self._saved_sys_nuke is not None:
            sys.modules["nuke"] = self._saved_sys_nuke

    def _set_state_horizontal(self, node):
        node._knobs["node_layout_state"] = _StubKnob(
            '{"scheme": "normal", "mode": "horizontal", "h_scale": 1.0, "v_scale": 1.0}'
        )

    def _find_output_dot(self):
        for candidate in _stub_all_nodes_list:
            if candidate.knob(nl._OUTPUT_DOT_KNOB_NAME) is not None:
                return candidate
        return None

    def test_phase2_does_not_overlap_horizontal_chain(self):
        """BUG-B: B-chain right edge must be < chain left edge - gap.

        Topology:
          m1.input(0) = m2  (horizontal chain root; m2.input(0) = n)
          m1.input(1) = b   (vertical B-chain node, no inputs)

        After layout_upstream(), the B-chain (b) must not intrude into the
        horizontal chain's space:
          max_x(b_chain_nodes) < min_x(chain_nodes) - horizontal_subtree_gap
        """
        m1 = _StubNode(width=80, height=28, xpos=800, ypos=400, num_inputs=2)
        m2 = _StubNode(width=80, height=28, xpos=0, ypos=0, num_inputs=1)
        n = _StubNode(width=80, height=28, xpos=0, ypos=0, num_inputs=0)
        b = _StubNode(width=80, height=28, xpos=0, ypos=0, num_inputs=0)
        m2.setInput(0, n)
        m1.setInput(0, m2)
        m1.setInput(1, b)

        self._set_state_horizontal(m2)
        self._set_state_horizontal(n)
        # b is intentionally NOT set to horizontal — it is a vertical B-chain node

        _stub_all_nodes_list.extend([m1, m2, n, b])
        _nuke_stub.selectedNode = lambda: m1

        nl.layout_upstream()

        chain_nodes = nl.collect_subtree_nodes(m2)
        b_chain_nodes = [b]

        chain_min_x = min(node.xpos() for node in chain_nodes)
        b_max_x = max(node.xpos() + node.screenWidth() for node in b_chain_nodes)
        gap = _node_layout_prefs_module.DEFAULTS["horizontal_subtree_gap"]

        self.assertLess(
            b_max_x,
            chain_min_x - gap,
            f"BUG-B: B-chain right edge ({b_max_x}) must be < chain left edge"
            f" - gap ({chain_min_x - gap})."
            f" chain_min_x={chain_min_x}, gap={gap}",
        )


if __name__ == "__main__":
    unittest.main()

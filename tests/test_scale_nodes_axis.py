"""RED test scaffold for Phase 10: Axis-specific scaling, repeat-last-scale, expand push-away.

Tests verify (all expected to FAIL RED until implementation in Plan 02):
- axis="h" leaves dy unchanged, only scales dx
- axis="v" leaves dx unchanged, only scales dy
- axis="both" scales both dx and dy (regression guard — but will fail RED because axis param not yet accepted)
- snap floor is NOT applied to the unchanged axis
- axis="h" only updates h_scale in state, v_scale unchanged
- axis="v" only updates v_scale in state, h_scale unchanged
- AST: 8 new wrapper functions present in node_layout.py
- AST: _last_scale_fn module-level variable present
- AST: repeat_last_scale function present
- _last_scale_fn is set after calling a scale wrapper
- repeat_last_scale calls the stored function
- repeat_last_scale is a no-op when _last_scale_fn is None
- expand_selected_horizontal calls push_nodes_to_make_room
- expand_selected_vertical calls push_nodes_to_make_room
- shrink_selected_horizontal does NOT call push_nodes_to_make_room
"""
import ast
import sys
import types
import importlib.util
import os
import unittest
from unittest.mock import patch, MagicMock


NODE_LAYOUT_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")
NODE_LAYOUT_PREFS_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout_prefs.py")

EXPAND_FACTOR = 1.25  # matches EXPAND_FACTOR in node_layout.py


# ---------------------------------------------------------------------------
# Stub nuke module — follows the same pattern as tests/test_scale_nodes.py
# so both files coexist in the same test run without stub conflicts.
# ---------------------------------------------------------------------------


class _StubKnob:
    def __init__(self, val=0):
        self._val = val

    def value(self):
        return self._val

    def getValue(self):
        return self._val


class _StubWritableKnob:
    """Stub knob supporting getValue/setValue for state storage."""

    def __init__(self, val=''):
        self._val = val
        self.name = ''

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
                 knobs=None):
        self._width = width
        self._height = height
        self._xpos = xpos
        self._ypos = ypos
        self._class = node_class
        self._knobs = knobs if knobs is not None else {"tile_color": _StubKnob(0)}
        self._inputs = []

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

    def knob(self, name):
        return self._knobs.get(name)

    def addKnob(self, knob):
        if hasattr(knob, 'name') and knob.name not in self._knobs:
            self._knobs[knob.name] = knob

    def inputLabel(self, index):
        return ""

    def __getitem__(self, name):
        if name in self._knobs:
            return self._knobs[name]
        writable_knob = _StubWritableKnob()
        self._knobs[name] = writable_knob
        return writable_knob


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


def _make_stub_knob(name='', label=''):
    knob = _StubWritableKnob()
    knob.name = name
    return knob


# Register the nuke stub if not already present.
if "nuke" not in sys.modules:
    _nuke_stub = types.ModuleType("nuke")
    _nuke_stub.Node = _StubNode
    _nuke_stub.allNodes = lambda: []
    _nuke_stub.selectedNodes = lambda: []
    _nuke_stub.selectedNode = lambda: _StubNode()
    _nuke_stub.toNode = lambda name: _make_preferences_node() if name == "preferences" else None
    _nuke_stub.menu = lambda name: None
    _nuke_stub.Undo = _StubUndo
    sys.modules["nuke"] = _nuke_stub

# Augment whichever nuke stub is active with knob factories used by write_node_state.
_active_nuke = sys.modules["nuke"]
if not hasattr(_active_nuke, "Tab_Knob"):
    _active_nuke.Tab_Knob = lambda name='', label='': _make_stub_knob(name, label)
if not hasattr(_active_nuke, "String_Knob"):
    _active_nuke.String_Knob = lambda name='', label='': _make_stub_knob(name, label)
if not hasattr(_active_nuke, "INVISIBLE"):
    _active_nuke.INVISIBLE = 0x01
if not hasattr(_active_nuke, "lastHitGroup"):
    _active_nuke.lastHitGroup = lambda: None

# Load node_layout_prefs if not already loaded.
if "node_layout_prefs" not in sys.modules:
    _prefs_spec = importlib.util.spec_from_file_location(
        "node_layout_prefs", NODE_LAYOUT_PREFS_PATH
    )
    _node_layout_prefs_module = importlib.util.module_from_spec(_prefs_spec)
    _prefs_spec.loader.exec_module(_node_layout_prefs_module)
    sys.modules["node_layout_prefs"] = _node_layout_prefs_module
else:
    _node_layout_prefs_module = sys.modules["node_layout_prefs"]

# Load a fresh copy of node_layout so this file always uses the latest source.
_module_path = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")
_spec = importlib.util.spec_from_file_location("node_layout_axis_tests_fresh", _module_path)
_nl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_nl)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_selected_nodes(nodes):
    """Override nuke.selectedNodes on the nuke module that _nl actually uses."""
    _nl.nuke.selectedNodes = lambda: nodes


def _set_selected_node(node):
    """Override nuke.selectedNode on the nuke module that _nl actually uses."""
    _nl.nuke.selectedNode = lambda: node


def _make_regular_node(xpos, ypos):
    return _StubNode(width=80, height=28, xpos=xpos, ypos=ypos)


# ---------------------------------------------------------------------------
# TestAxisScalingBehavior
# ---------------------------------------------------------------------------


class TestAxisScalingBehavior(unittest.TestCase):
    """Behavioral tests for axis-specific scaling (h / v / both)."""

    def setUp(self):
        # Restore nuke stub reference after each test in case another test mutated it.
        _nl.nuke = sys.modules["nuke"]

    def test_h_axis_leaves_dy_unchanged(self):
        """axis='h': horizontal scale applied, vertical distance unchanged."""
        # anchor at (0, 200); non-anchor offset +200 H and +100 V from anchor center
        # anchor center: (40, 214); non-anchor: we want dx=200, dy=100
        # non_anchor center = (240, 314); non_anchor top-left = (200, 300)
        anchor = _make_regular_node(xpos=0, ypos=200)
        non_anchor = _make_regular_node(xpos=200, ypos=300)

        anchor_center_y = anchor.ypos() + anchor.screenHeight() / 2  # 214
        non_anchor_center_y_before = non_anchor.ypos() + non_anchor.screenHeight() / 2  # 314
        original_dy = non_anchor_center_y_before - anchor_center_y  # 100

        _set_selected_nodes([anchor, non_anchor])
        _nl._scale_selected_nodes(EXPAND_FACTOR, axis="h")

        non_anchor_center_y_after = non_anchor.ypos() + non_anchor.screenHeight() / 2
        actual_dy = non_anchor_center_y_after - anchor_center_y

        # dy must be unchanged
        self.assertEqual(
            actual_dy,
            original_dy,
            f"axis='h' must not change dy; expected {original_dy}, got {actual_dy}",
        )
        # dx must have changed
        anchor_center_x = anchor.xpos() + anchor.screenWidth() / 2  # 40
        non_anchor_center_x_after = non_anchor.xpos() + non_anchor.screenWidth() / 2
        actual_dx = non_anchor_center_x_after - anchor_center_x
        self.assertNotEqual(
            actual_dx,
            200,
            "axis='h' must scale dx; dx was unchanged",
        )

    def test_v_axis_leaves_dx_unchanged(self):
        """axis='v': vertical scale applied, horizontal distance unchanged."""
        anchor = _make_regular_node(xpos=0, ypos=200)
        non_anchor = _make_regular_node(xpos=200, ypos=300)

        anchor_center_x = anchor.xpos() + anchor.screenWidth() / 2  # 40
        non_anchor_center_x_before = non_anchor.xpos() + non_anchor.screenWidth() / 2  # 240
        original_dx = non_anchor_center_x_before - anchor_center_x  # 200

        _set_selected_nodes([anchor, non_anchor])
        _nl._scale_selected_nodes(EXPAND_FACTOR, axis="v")

        non_anchor_center_x_after = non_anchor.xpos() + non_anchor.screenWidth() / 2
        actual_dx = non_anchor_center_x_after - anchor_center_x

        # dx must be unchanged
        self.assertEqual(
            actual_dx,
            original_dx,
            f"axis='v' must not change dx; expected {original_dx}, got {actual_dx}",
        )
        # dy must have changed
        anchor_center_y = anchor.ypos() + anchor.screenHeight() / 2
        non_anchor_center_y_after = non_anchor.ypos() + non_anchor.screenHeight() / 2
        actual_dy = non_anchor_center_y_after - anchor_center_y
        self.assertNotEqual(
            actual_dy,
            100,
            "axis='v' must scale dy; dy was unchanged",
        )

    def test_both_axis_unchanged(self):
        """axis='both': both dx and dy change — regression guard for default behaviour.

        _scale_selected_nodes picks the most downstream node (highest ypos) as the internal
        pivot. Here non_anchor (ypos=300) is the pivot; anchor (ypos=200) is the node that
        moves. Measurements are therefore taken from the pivot's perspective:
        distance = anchor.center - pivot.center.
        """
        anchor = _make_regular_node(xpos=0, ypos=200)
        non_anchor = _make_regular_node(xpos=200, ypos=300)

        # non_anchor is the internal pivot (ypos=300 > ypos=200)
        pivot_center_x = non_anchor.xpos() + non_anchor.screenWidth() / 2   # 240
        pivot_center_y = non_anchor.ypos() + non_anchor.screenHeight() / 2  # 314
        original_dx = (anchor.xpos() + anchor.screenWidth() / 2) - pivot_center_x    # 40 - 240 = -200
        original_dy = (anchor.ypos() + anchor.screenHeight() / 2) - pivot_center_y   # 214 - 314 = -100

        _set_selected_nodes([anchor, non_anchor])
        _nl._scale_selected_nodes(EXPAND_FACTOR, axis="both")

        actual_dx = (anchor.xpos() + anchor.screenWidth() / 2) - pivot_center_x
        actual_dy = (anchor.ypos() + anchor.screenHeight() / 2) - pivot_center_y

        self.assertNotEqual(actual_dx, original_dx, "axis='both' must scale dx")
        self.assertNotEqual(actual_dy, original_dy, "axis='both' must scale dy")

    def test_snap_floor_not_applied_to_unchanged_axis(self):
        """axis='h': a tiny vertical distance (3px) must NOT be snapped to snap_min floor."""
        # snap_threshold = 8 so snap_min = 7; vertical distance of 3 is below snap_min
        # With axis='h', the vertical distance must remain 3px (unchanged, floor not applied)
        anchor = _make_regular_node(xpos=0, ypos=200)
        # dy = 3: non_anchor center_y = anchor_center_y + 3
        # anchor_center_y = 200 + 14 = 214; non_anchor_center_y = 217; non_anchor ypos = 203
        non_anchor = _make_regular_node(xpos=200, ypos=203)

        anchor_center_y = anchor.ypos() + anchor.screenHeight() / 2  # 214
        non_anchor_center_y_before = non_anchor.ypos() + non_anchor.screenHeight() / 2  # 217
        original_dy = non_anchor_center_y_before - anchor_center_y  # 3

        _set_selected_nodes([anchor, non_anchor])
        _nl._scale_selected_nodes(EXPAND_FACTOR, axis="h")

        non_anchor_center_y_after = non_anchor.ypos() + non_anchor.screenHeight() / 2
        actual_dy = non_anchor_center_y_after - anchor_center_y

        self.assertEqual(
            actual_dy,
            original_dy,
            f"axis='h' must not apply snap floor to unchanged V axis; "
            f"expected dy={original_dy}, got dy={actual_dy} (snap floor was incorrectly applied)",
        )


# ---------------------------------------------------------------------------
# TestAxisStateBehavior
# ---------------------------------------------------------------------------


class TestAxisStateBehavior(unittest.TestCase):
    """State write-back tests: axis='h' only updates h_scale, axis='v' only updates v_scale."""

    def setUp(self):
        _nl.nuke = sys.modules["nuke"]

    def test_h_axis_only_updates_h_scale(self):
        """axis='h': h_scale accumulates, v_scale remains 1.0."""
        anchor = _make_regular_node(xpos=0, ypos=200)
        non_anchor = _make_regular_node(xpos=200, ypos=300)

        _set_selected_nodes([anchor, non_anchor])
        _nl._scale_selected_nodes(EXPAND_FACTOR, axis="h")

        state = _nl.node_layout_state.read_node_state(non_anchor)
        self.assertAlmostEqual(
            state["h_scale"],
            EXPAND_FACTOR,
            places=9,
            msg=f"h_scale should be {EXPAND_FACTOR} after axis='h' scale, got {state['h_scale']}",
        )
        self.assertAlmostEqual(
            state["v_scale"],
            1.0,
            places=9,
            msg=f"v_scale must remain 1.0 after axis='h' scale, got {state['v_scale']}",
        )

    def test_v_axis_only_updates_v_scale(self):
        """axis='v': v_scale accumulates, h_scale remains 1.0."""
        anchor = _make_regular_node(xpos=0, ypos=200)
        non_anchor = _make_regular_node(xpos=200, ypos=300)

        _set_selected_nodes([anchor, non_anchor])
        _nl._scale_selected_nodes(EXPAND_FACTOR, axis="v")

        state = _nl.node_layout_state.read_node_state(non_anchor)
        self.assertAlmostEqual(
            state["v_scale"],
            EXPAND_FACTOR,
            places=9,
            msg=f"v_scale should be {EXPAND_FACTOR} after axis='v' scale, got {state['v_scale']}",
        )
        self.assertAlmostEqual(
            state["h_scale"],
            1.0,
            places=9,
            msg=f"h_scale must remain 1.0 after axis='v' scale, got {state['h_scale']}",
        )


# ---------------------------------------------------------------------------
# TestNewCommandsAST
# ---------------------------------------------------------------------------


class TestNewCommandsAST(unittest.TestCase):
    """AST-based tests: new wrapper functions and _last_scale_fn variable exist in node_layout.py."""

    @classmethod
    def setUpClass(cls):
        with open(NODE_LAYOUT_PATH) as source_file:
            cls._source = source_file.read()
        cls._tree = ast.parse(cls._source)

    def _module_level_function_names(self):
        """Return the set of function names defined at module scope."""
        return {
            node.name
            for node in cls._tree.body
            if isinstance(node, ast.FunctionDef)
            for cls in [self.__class__]
        }

    def _top_level_function_names(self):
        return {
            node.name
            for node in self.__class__._tree.body
            if isinstance(node, ast.FunctionDef)
        }

    def test_8_new_functions_present(self):
        """All 8 new axis wrapper functions must be defined at module scope in node_layout.py."""
        expected_functions = [
            "shrink_selected_horizontal",
            "shrink_selected_vertical",
            "expand_selected_horizontal",
            "expand_selected_vertical",
            "shrink_upstream_horizontal",
            "shrink_upstream_vertical",
            "expand_upstream_horizontal",
            "expand_upstream_vertical",
        ]
        defined = self._top_level_function_names()
        for function_name in expected_functions:
            self.assertIn(
                function_name,
                defined,
                f"Missing module-scope function: {function_name}",
            )

    def test_last_scale_fn_variable_present(self):
        """node_layout.py must have a module-level assignment '_last_scale_fn = None'."""
        assignment_targets = []
        for tree_node in self.__class__._tree.body:
            if isinstance(tree_node, ast.Assign):
                for target in tree_node.targets:
                    if isinstance(target, ast.Name):
                        assignment_targets.append(target.id)
        self.assertIn(
            "_last_scale_fn",
            assignment_targets,
            "Module-level '_last_scale_fn = None' assignment not found in node_layout.py",
        )


# ---------------------------------------------------------------------------
# TestRepeatLastScaleAST
# ---------------------------------------------------------------------------


class TestRepeatLastScaleAST(unittest.TestCase):
    """AST test: repeat_last_scale function must be defined at module scope."""

    @classmethod
    def setUpClass(cls):
        with open(NODE_LAYOUT_PATH) as source_file:
            source = source_file.read()
        cls._tree = ast.parse(source)

    def test_repeat_last_scale_function_present(self):
        """repeat_last_scale must be a FunctionDef at module scope in node_layout.py."""
        top_level_names = {
            node.name
            for node in self.__class__._tree.body
            if isinstance(node, ast.FunctionDef)
        }
        self.assertIn(
            "repeat_last_scale",
            top_level_names,
            "repeat_last_scale not found as a module-level function in node_layout.py",
        )


# ---------------------------------------------------------------------------
# TestRepeatLastScaleBehavior
# ---------------------------------------------------------------------------


class TestRepeatLastScaleBehavior(unittest.TestCase):
    """Behavioral tests for repeat_last_scale and _last_scale_fn tracking."""

    def setUp(self):
        _nl.nuke = sys.modules["nuke"]
        # Reset _last_scale_fn before each test.
        _nl._last_scale_fn = None

    def test_last_fn_set_after_call(self):
        """Calling a scale wrapper (shrink_selected) sets _last_scale_fn to that wrapper."""
        # Arrange: need 2+ selected nodes for the function to proceed
        anchor = _make_regular_node(xpos=0, ypos=200)
        non_anchor = _make_regular_node(xpos=200, ypos=0)
        _set_selected_nodes([anchor, non_anchor])

        _nl.shrink_selected()

        self.assertIs(
            _nl._last_scale_fn,
            _nl.shrink_selected,
            f"_last_scale_fn should be shrink_selected after calling it, "
            f"got {_nl._last_scale_fn}",
        )

    def test_repeat_calls_last_fn(self):
        """repeat_last_scale() calls _last_scale_fn exactly once."""
        mock_fn = MagicMock()
        _nl._last_scale_fn = mock_fn

        _nl.repeat_last_scale()

        mock_fn.assert_called_once_with()

    def test_repeat_noop_when_none(self):
        """repeat_last_scale() is a no-op (no exception) when _last_scale_fn is None."""
        _nl._last_scale_fn = None

        try:
            _nl.repeat_last_scale()
        except Exception as caught_exception:
            self.fail(
                f"repeat_last_scale() raised an exception when _last_scale_fn is None: "
                f"{caught_exception}"
            )


# ---------------------------------------------------------------------------
# TestExpandPushAway
# ---------------------------------------------------------------------------


class TestExpandPushAway(unittest.TestCase):
    """expand H/V wrappers call push_nodes_to_make_room; shrink wrappers do not."""

    def setUp(self):
        _nl.nuke = sys.modules["nuke"]
        # Reset _last_scale_fn
        _nl._last_scale_fn = None

    def test_expand_h_calls_push(self):
        """expand_selected_horizontal() must call push_nodes_to_make_room."""
        anchor = _make_regular_node(xpos=0, ypos=200)
        non_anchor = _make_regular_node(xpos=200, ypos=0)
        _set_selected_nodes([anchor, non_anchor])

        with patch.object(_nl, "push_nodes_to_make_room") as mock_push:
            _nl.expand_selected_horizontal()
            mock_push.assert_called_once()

    def test_expand_v_calls_push(self):
        """expand_selected_vertical() must call push_nodes_to_make_room."""
        anchor = _make_regular_node(xpos=0, ypos=200)
        non_anchor = _make_regular_node(xpos=200, ypos=0)
        _set_selected_nodes([anchor, non_anchor])

        with patch.object(_nl, "push_nodes_to_make_room") as mock_push:
            _nl.expand_selected_vertical()
            mock_push.assert_called_once()

    def test_shrink_h_no_push(self):
        """shrink_selected_horizontal() must NOT call push_nodes_to_make_room."""
        anchor = _make_regular_node(xpos=0, ypos=200)
        non_anchor = _make_regular_node(xpos=200, ypos=0)
        _set_selected_nodes([anchor, non_anchor])

        with patch.object(_nl, "push_nodes_to_make_room") as mock_push:
            _nl.shrink_selected_horizontal()
            mock_push.assert_not_called()


if __name__ == "__main__":
    unittest.main()

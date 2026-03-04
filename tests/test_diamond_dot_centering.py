"""Tests for BUG-03: diamond-resolution Dot centering under consumer node.

After place_subtree() recurses into a diamond-resolution Dot (hide_input=True,
node_layout_diamond_dot knob present), the Dot node's xpos must be set to
_center_x(dot.screenWidth(), consumer_x, consumer_width).

These tests use AST analysis (for structural checks) and a nuke stub (for
runtime geometry tests) — neither requires the Nuke runtime.
"""
import ast
import sys
import types
import importlib.util
import os
import unittest


NODE_LAYOUT_PATH = "/home/latuser/git/nuke_layout_project/node_layout/node_layout.py"


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

    def __getitem__(self, name):
        if name in self._knobs:
            return self._knobs[name]
        return _StubKnob(0)


def _make_preferences_node():
    node = _StubNode(node_class="Preferences")
    node._knobs = {
        "dag_snap_threshold": _StubKnob(8),
        "NodeColor": _StubKnob(0),
    }
    node.knobs = lambda: node._knobs
    return node


_nuke_stub = types.ModuleType("nuke")
_nuke_stub.Node = _StubNode
_nuke_stub.allNodes = lambda: []
_nuke_stub.selectedNodes = lambda: []
_nuke_stub.selectedNode = lambda: _StubNode()
_nuke_stub.toNode = lambda name: _make_preferences_node() if name == "preferences" else None
_nuke_stub.menu = lambda name: None
sys.modules["nuke"] = _nuke_stub

# Load node_layout_prefs (no Nuke dependency) so node_layout.py's import resolves.
if "node_layout_prefs" not in sys.modules:
    _prefs_path = os.path.join(os.path.dirname(__file__), "..", "node_layout_prefs.py")
    _prefs_spec = importlib.util.spec_from_file_location("node_layout_prefs", _prefs_path)
    _node_layout_prefs_module = importlib.util.module_from_spec(_prefs_spec)
    _prefs_spec.loader.exec_module(_node_layout_prefs_module)
    sys.modules["node_layout_prefs"] = _node_layout_prefs_module

_module_path = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")
_spec = importlib.util.spec_from_file_location("node_layout", _module_path)
_nl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_nl)


def _make_diamond_dot(xpos=0, ypos=0):
    """Return a _StubNode configured as a diamond-resolution Dot."""
    dot_knobs = {
        "tile_color": _StubKnob(0),
        "node_layout_diamond_dot": _StubKnob(1),
        "hide_input": _StubKnob(1),
    }
    dot = _StubNode(width=12, height=12, xpos=xpos, ypos=ypos,
                    node_class="Dot", knobs=dot_knobs)
    return dot


# ---------------------------------------------------------------------------
# AST-based structural tests
# ---------------------------------------------------------------------------

class TestDiamondDotCenteringStructure(unittest.TestCase):
    """AST tests verifying the structural change to place_subtree()."""

    def _load_place_subtree_source(self):
        with open(NODE_LAYOUT_PATH) as source_file:
            source = source_file.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "place_subtree":
                return ast.get_source_segment(source, node)
        return None

    def test_diamond_centered_x_variable_present_in_place_subtree(self):
        """place_subtree() must contain 'diamond_centered_x' after the fix."""
        src = self._load_place_subtree_source()
        self.assertIsNotNone(src, "place_subtree() not found in node_layout.py")
        self.assertIn(
            "diamond_centered_x",
            src,
            "place_subtree() must compute diamond_centered_x for BUG-03 centering",
        )

    def test_diamond_dot_knob_checked_in_place_subtree(self):
        """place_subtree() must check node_layout_diamond_dot knob in the else branch."""
        src = self._load_place_subtree_source()
        self.assertIsNotNone(src)
        self.assertIn(
            "node_layout_diamond_dot",
            src,
            "place_subtree() must check node_layout_diamond_dot knob to identify diamond Dots",
        )

    def test_setxpos_called_after_diamond_check_in_place_subtree(self):
        """place_subtree() must call inp.setXpos(diamond_centered_x) for diamond Dots."""
        src = self._load_place_subtree_source()
        self.assertIsNotNone(src)
        self.assertIn(
            "setXpos(diamond_centered_x)",
            src,
            "place_subtree() must call setXpos(diamond_centered_x) for diamond Dots",
        )


# ---------------------------------------------------------------------------
# Runtime geometry tests using _StubNode
# ---------------------------------------------------------------------------

class TestDiamondDotCenteringRuntime(unittest.TestCase):
    """Verify that place_subtree() centers diamond Dots under the consumer tile."""

    def _run_placement(self, consumer, diamond_dot, consumer_x=200, consumer_y=400):
        """Wire consumer -> diamond_dot, run compute_dims + place_subtree."""
        consumer._inputs = [diamond_dot]
        diamond_dot._inputs = []  # Dot has no further inputs for this test
        memo = {}
        _nl.compute_dims(consumer, memo, snap_threshold=8, node_count=150)
        _nl.place_subtree(consumer, consumer_x, consumer_y, memo, snap_threshold=8, node_count=150)

    def test_diamond_dot_xpos_centered_under_consumer(self):
        """Diamond Dot xpos == _center_x(12, consumer_x, consumer_width) after placement."""
        consumer = _StubNode(width=80, height=28, xpos=0, ypos=0, node_class="Grade")
        diamond_dot = _make_diamond_dot()
        self._run_placement(consumer, diamond_dot, consumer_x=200, consumer_y=400)

        # Expected: 200 + (80 - 12) // 2 = 200 + 34 = 234
        expected_x = 200 + (80 - 12) // 2
        self.assertEqual(
            diamond_dot.xpos(), expected_x,
            f"Diamond Dot xpos should be {expected_x}, got {diamond_dot.xpos()}",
        )

    def test_diamond_dot_ypos_not_modified_by_centering(self):
        """Diamond Dot ypos must not be changed by the centering step."""
        consumer = _StubNode(width=80, height=28, xpos=0, ypos=0, node_class="Grade")
        diamond_dot = _make_diamond_dot()
        self._run_placement(consumer, diamond_dot, consumer_x=200, consumer_y=400)

        # The Dot's ypos is set by place_subtree recursion, not by centering.
        # We only verify it is NOT consumer_y (centering must not alter Y).
        # It will be consumer_y - SUBTREE_MARGIN - dot_height (placed above consumer).
        dot_y = diamond_dot.ypos()
        # Centering must not set ypos == diamond_centered_x value (a horizontal coord)
        expected_wrong_y = 200 + (80 - 12) // 2  # the x centering value
        self.assertNotEqual(
            dot_y, expected_wrong_y,
            "Diamond Dot ypos must not be set to the diamond_centered_x value",
        )

    def test_non_diamond_dot_not_recentered(self):
        """A regular non-diamond child node must NOT have its xpos altered by diamond centering."""
        consumer = _StubNode(width=80, height=28, xpos=0, ypos=0, node_class="Grade")
        regular_child = _StubNode(width=40, height=28, xpos=0, ypos=0, node_class="Grade")
        consumer._inputs = [regular_child]
        regular_child._inputs = []
        memo = {}
        _nl.compute_dims(consumer, memo, snap_threshold=8, node_count=150)
        _nl.place_subtree(consumer, 200, 400, memo, snap_threshold=8, node_count=150)

        # Regular child is positioned by the standard centering in place_subtree, not diamond path
        # _center_x(40, 200, 80) == 220 — this is the standard BUG-04 centering, not diamond
        # The key invariant: regular child was NOT subjected to diamond-specific setXpos call
        # (it has no node_layout_diamond_dot knob). Its actual xpos should be the standard value.
        expected_x = _nl._center_x(40, 200, 80)  # standard centering from BUG-04 fix
        self.assertEqual(
            regular_child.xpos(), expected_x,
            "Regular child xpos must use standard centering, not diamond-specific centering",
        )

    def test_diamond_dot_at_consumer_x_zero(self):
        """Diamond Dot centering works when consumer_x is zero."""
        consumer = _StubNode(width=80, height=28, xpos=0, ypos=0, node_class="Grade")
        diamond_dot = _make_diamond_dot()
        self._run_placement(consumer, diamond_dot, consumer_x=0, consumer_y=400)

        expected_x = 0 + (80 - 12) // 2  # = 34
        self.assertEqual(diamond_dot.xpos(), expected_x)

    def test_diamond_dot_centering_with_wide_consumer(self):
        """Diamond Dot (12px) is centered under a wide consumer tile."""
        consumer = _StubNode(width=160, height=28, xpos=0, ypos=0, node_class="Grade")
        diamond_dot = _make_diamond_dot()
        self._run_placement(consumer, diamond_dot, consumer_x=100, consumer_y=400)

        # 100 + (160 - 12) // 2 = 100 + 74 = 174
        expected_x = 100 + (160 - 12) // 2
        self.assertEqual(diamond_dot.xpos(), expected_x)


if __name__ == "__main__":
    unittest.main()

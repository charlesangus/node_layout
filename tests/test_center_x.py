"""Tests for _center_x() helper and BUG-04 input-0 centering fix.

These tests exercise pure geometry calculations that do not require the Nuke
runtime.  We import only the functions defined before any Nuke API calls are
needed, using a stub nuke module so the import succeeds in a plain Python
environment.
"""
import sys
import types
import importlib.util
import os
import unittest

# ---------------------------------------------------------------------------
# Stub nuke module so node_layout.py can be imported without a Nuke runtime.
# ---------------------------------------------------------------------------


class _StubKnob:
    def __init__(self, val):
        self._val = val

    def value(self):
        return self._val

    def getValue(self):
        return self._val


class _StubNode:
    """Minimal stand-in for a nuke.Node, supporting the geometry knobs used
    by the functions under test."""

    def __init__(self, width=80, height=28, xpos=0, ypos=0, node_class="Grade"):
        self._width = width
        self._height = height
        self._xpos = xpos
        self._ypos = ypos
        self._class = node_class
        self._knobs = {
            "tile_color": _StubKnob(0),
        }

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
        return 0

    def input(self, index):
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
    # Nuke preferences nodes expose a knobs() method returning a dict keyed by name.
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

# Now we can import the module under test.
_module_path = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")
_spec = importlib.util.spec_from_file_location("node_layout", _module_path)
_nl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_nl)


# -------------------------------------------------------------------------
# Tests for _center_x()
# -------------------------------------------------------------------------

class TestCenterX(unittest.TestCase):
    """Unit tests for the _center_x() helper."""

    def test_equal_widths_returns_parent_x(self):
        """When child and parent have the same width, centering == parent_x."""
        result = _nl._center_x(child_width=80, parent_x=100, parent_width=80)
        self.assertEqual(result, 100)

    def test_narrower_child_returns_positive_offset(self):
        """A narrower child should be placed to the right of parent_x."""
        # parent 80 wide, child 40 wide -> offset = (80 - 40) // 2 = 20
        result = _nl._center_x(child_width=40, parent_x=100, parent_width=80)
        self.assertEqual(result, 120)

    def test_wider_child_returns_negative_offset(self):
        """A wider child extends left of parent_x; result < parent_x."""
        # parent 80 wide, child 200 wide -> offset = (80 - 200) // 2 = -60
        result = _nl._center_x(child_width=200, parent_x=100, parent_width=80)
        self.assertEqual(result, 40)

    def test_zero_child_width(self):
        """Zero-width child (edge case) centers at parent_x + parent_width // 2."""
        result = _nl._center_x(child_width=0, parent_x=0, parent_width=80)
        self.assertEqual(result, 40)

    def test_zero_parent_x(self):
        """Works correctly when parent_x is zero."""
        result = _nl._center_x(child_width=40, parent_x=0, parent_width=80)
        self.assertEqual(result, 20)


# -------------------------------------------------------------------------
# Tests for compute_dims() W formula with input0_overhang
# -------------------------------------------------------------------------

class TestComputeDimsOverhang(unittest.TestCase):
    """Verify that compute_dims() accounts for input[0] left overhang."""

    def test_n1_no_overhang_when_child_narrower(self):
        """n==1, child narrower: W == node_width (no overhang)."""
        # node 80 wide, child 40 wide: overhang = max(0, (40-80)//2) = 0
        # W = max(80, 40) + 0 = 80
        node = _StubNode(width=80)
        child = _StubNode(width=40)
        node.inputs = lambda: 1
        node.input = lambda i: child if i == 0 else None
        child.inputs = lambda: 0
        child.input = lambda i: None

        memo = {}
        dims = _nl.compute_dims(node, memo, snap_threshold=8)
        w, h = dims
        # With no overhang, W should be node width (80)
        self.assertEqual(w, 80)

    def test_n1_child_wider_than_parent(self):
        """n==1, child wider than parent: W == child_width (no overhang added).

        When a wider input[0] is centered over its consumer, it extends equally
        left and right.  The total bounding width of the subtree is exactly
        child_width — the same as max(parent_width, child_width).  Adding an
        extra overhang term inflates W and causes stairstepping at higher depths.
        """
        # parent 80 wide, child 200 wide:
        # child centered at x + (80 - 200)//2 = x - 60
        # child right edge at x - 60 + 200 = x + 140
        # Total bounding width from left edge (x - 60): 200  (== child_width)
        # W must be max(80, 200) = 200, NOT 200 + 60 = 260
        node = _StubNode(width=80)
        child = _StubNode(width=200)
        node.inputs = lambda: 1
        node.input = lambda i: child if i == 0 else None
        child.inputs = lambda: 0
        child.input = lambda i: None

        memo = {}
        dims = _nl.compute_dims(node, memo, snap_threshold=8)
        w, h = dims
        self.assertEqual(w, 200)

    def test_n1_equal_width_no_overhang(self):
        """n==1, equal widths: overhang == 0, W == node_width."""
        node = _StubNode(width=80)
        child = _StubNode(width=80)
        node.inputs = lambda: 1
        node.input = lambda i: child if i == 0 else None
        child.inputs = lambda: 0
        child.input = lambda i: None

        memo = {}
        dims = _nl.compute_dims(node, memo, snap_threshold=8)
        w, h = dims
        self.assertEqual(w, 80)


# -------------------------------------------------------------------------
# Tests for place_subtree() x_positions[0] centering
# -------------------------------------------------------------------------

class TestPlaceSubtreeInputZeroCentering(unittest.TestCase):
    """Verify that place_subtree() centers input[0] over the consumer."""

    def test_n1_input0_centered_when_narrower(self):
        """n==1, child narrower than parent: child placed to the right of parent_x."""
        parent = _StubNode(width=80, xpos=200, ypos=400)
        child = _StubNode(width=40, xpos=0, ypos=0)
        parent.inputs = lambda: 1
        parent.input = lambda i: child if i == 0 else None
        child.inputs = lambda: 0
        child.input = lambda i: None

        memo = {}
        _nl.compute_dims(parent, memo, snap_threshold=8)
        _nl.place_subtree(parent, 200, 400, memo, snap_threshold=8)

        # Expected: child_x = parent_x + (parent_width - child_width) // 2
        expected_x = 200 + (80 - 40) // 2  # = 220
        self.assertEqual(child.xpos(), expected_x)

    def test_n1_input0_at_parent_x_when_equal_width(self):
        """n==1, equal widths: child_x == parent_x (no offset)."""
        parent = _StubNode(width=80, xpos=100, ypos=400)
        child = _StubNode(width=80, xpos=0, ypos=0)
        parent.inputs = lambda: 1
        parent.input = lambda i: child if i == 0 else None
        child.inputs = lambda: 0
        child.input = lambda i: None

        memo = {}
        _nl.compute_dims(parent, memo, snap_threshold=8)
        _nl.place_subtree(parent, 100, 400, memo, snap_threshold=8)

        self.assertEqual(child.xpos(), 100)

    def test_n1_input0_left_of_parent_x_when_wider(self):
        """n==1, child wider than parent: child_x < parent_x (extends left)."""
        parent = _StubNode(width=80, xpos=200, ypos=400)
        child = _StubNode(width=200, xpos=0, ypos=0)
        parent.inputs = lambda: 1
        parent.input = lambda i: child if i == 0 else None
        child.inputs = lambda: 0
        child.input = lambda i: None

        memo = {}
        _nl.compute_dims(parent, memo, snap_threshold=8)
        _nl.place_subtree(parent, 200, 400, memo, snap_threshold=8)

        expected_x = 200 + (80 - 200) // 2  # = 200 - 60 = 140
        self.assertEqual(child.xpos(), expected_x)


class TestPlaceSubtreeInputZeroCenteringMultiLevel(unittest.TestCase):
    """Verify that centering input[0] over a consumer uses the INPUT NODE'S tile width,
    not its subtree width.  Using subtree width accumulates drift across levels.

    Chain: D(w=80) -> C(w=80) -> B(w=80) -> A(w=200, leaf)

    compute_dims results (after the input0_overhang fix):
      compute_dims(A) = (200, _)
      compute_dims(B) = (max(80, 200), _) = (200, _)
      compute_dims(C) = (max(80, 200), _) = (200, _)
      compute_dims(D) = (max(80, 200), _) = (200, _)

    With the WRONG approach (using child_dims[i][0] = subtree width for centering):
      place_subtree(D, x=0): D@0, C_x = _center_x(200, 0, 80) = -60
      place_subtree(C, x=-60): C@-60, B_x = _center_x(200, -60, 80) = -120
      place_subtree(B, x=-120): B@-120, A_x = _center_x(200, -120, 80) = -180
      -> stairstepping: -60 per level

    With the CORRECT approach (using inputs[0].screenWidth() = tile width for centering):
      place_subtree(D, x=0): D@0, C_x = _center_x(80, 0, 80) = 0
      place_subtree(C, x=0): C@0, B_x = _center_x(80, 0, 80) = 0
      place_subtree(B, x=0): B@0, A_x = _center_x(200, 0, 80) = -60
      -> no drift; D, C, B all at x=0; A centered under B
    """

    def _make_chain_node(self, width, child=None):
        node = _StubNode(width=width)
        if child is None:
            node.inputs = lambda: 0
            node.input = lambda i: None
        else:
            node.inputs = lambda: 1
            node.input = lambda i: child if i == 0 else None
        return node

    def test_four_level_chain_no_stairstepping(self):
        """D->C->B->A (widths 80,80,80,200): D, C, B placed at same x; no drift per level."""
        a = self._make_chain_node(width=200)
        b = self._make_chain_node(width=80, child=a)
        c = self._make_chain_node(width=80, child=b)
        d = self._make_chain_node(width=80, child=c)

        memo = {}
        _nl.compute_dims(d, memo, snap_threshold=8)
        _nl.place_subtree(d, 0, 400, memo, snap_threshold=8)

        # D, C, B all have the same tile width as D; centering over each other should
        # produce no horizontal drift.  They must all be placed at the same x (0).
        self.assertEqual(c.xpos(), 0, "C must be at x=0 (same column as D, no drift)")
        self.assertEqual(b.xpos(), 0, "B must be at x=0 (same column as D and C, no drift)")

    def test_four_level_chain_leaf_centered_correctly(self):
        """D->C->B->A: leaf A (width 200) must be centered under B (width 80) at x=0."""
        a = self._make_chain_node(width=200)
        b = self._make_chain_node(width=80, child=a)
        c = self._make_chain_node(width=80, child=b)
        d = self._make_chain_node(width=80, child=c)

        memo = {}
        _nl.compute_dims(d, memo, snap_threshold=8)
        _nl.place_subtree(d, 0, 400, memo, snap_threshold=8)

        # A (width 200) should be centered under B (width 80, xpos=0):
        # A_x = 0 + (80 - 200) // 2 = -60
        expected_a_x = 0 + (80 - 200) // 2  # = -60
        self.assertEqual(a.xpos(), expected_a_x, "A must be centered under B, not further left")


if __name__ == "__main__":
    unittest.main()

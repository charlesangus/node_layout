"""Tests for BUG-05: secondary input margin application symmetry.

These tests verify that the gap before each side input at reordered position i
uses side_margins[i] consistently in both compute_dims() and place_subtree().

Key invariant: for a node with n inputs [primary, side1, side2, ...]:
  - side1 is placed at: x + node_width + side_margins[1]
  - side2 is placed at: x + node_width + side_margins[1] + child1_width + side_margins[2]
  - compute_dims W accounts for: node_width + sum(side_margins[1:]) + sum(side child widths)

Both compute_dims and place_subtree must use the same margin index for each
side input slot, ensuring total widths are consistent.
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
    def __init__(self, val=0):
        self._val = val

    def value(self):
        return self._val

    def getValue(self):
        return self._val


class _StubNode:
    def __init__(self, width=80, height=28, xpos=0, ypos=0, node_class="Grade"):
        self._width = width
        self._height = height
        self._xpos = xpos
        self._ypos = ypos
        self._class = node_class
        self._knobs = {"tile_color": _StubKnob(0)}

    def screenWidth(self): return self._width
    def screenHeight(self): return self._height
    def xpos(self): return self._xpos
    def ypos(self): return self._ypos
    def setXpos(self, v): self._xpos = v
    def setYpos(self, v): self._ypos = v
    def Class(self): return self._class
    def inputs(self): return 0
    def input(self, i): return None
    def setInput(self, slot, node): pass
    def knob(self, name): return self._knobs.get(name)
    def __getitem__(self, name): return self._knobs.get(name, _StubKnob(0))


def _make_prefs():
    node = _StubNode(node_class="Preferences")
    node._knobs = {"dag_snap_threshold": _StubKnob(8), "NodeColor": _StubKnob(0)}
    node.knobs = lambda: node._knobs
    return node


class _StubDotNode(_StubNode):
    """Stub for a Dot node created by place_subtree's dot-insertion logic."""

    def __init__(self):
        super().__init__(width=12, height=12, node_class="Dot")
        self._connected_input = None
        self._slot_connections = {}

    def Class(self):
        return "Dot"

    def inputs(self):
        return 1

    def input(self, i):
        return self._slot_connections.get(i)

    def setInput(self, slot, node):
        self._slot_connections[slot] = node

    def knob(self, name):
        return self._knobs.get(name)


class _StubNodesModule:
    """Stub for nuke.nodes namespace — provides Dot() factory."""

    @staticmethod
    def Dot():
        return _StubDotNode()


if "nuke" not in sys.modules:
    _nuke_stub = types.ModuleType("nuke")
    _nuke_stub.Node = _StubNode
    _nuke_stub.nodes = _StubNodesModule()
    _nuke_stub.allNodes = lambda: []
    _nuke_stub.selectedNodes = lambda: []
    _nuke_stub.selectedNode = lambda: _StubNode()
    _nuke_stub.toNode = lambda name: _make_prefs() if name == "preferences" else None
    _nuke_stub.menu = lambda name: None
    sys.modules["nuke"] = _nuke_stub
else:
    # Patch nodes attribute if not present (when nuke module was set up by test_center_x)
    _nuke_existing = sys.modules["nuke"]
    if not hasattr(_nuke_existing, "nodes"):
        _nuke_existing.nodes = _StubNodesModule()

# Load node_layout_prefs (no Nuke dependency) so node_layout.py's import resolves.
if "node_layout_prefs" not in sys.modules:
    _prefs_path = os.path.join(os.path.dirname(__file__), "..", "node_layout_prefs.py")
    _prefs_spec = importlib.util.spec_from_file_location("node_layout_prefs", _prefs_path)
    _prefs_module = importlib.util.module_from_spec(_prefs_spec)
    _prefs_spec.loader.exec_module(_prefs_module)
    sys.modules["node_layout_prefs"] = _prefs_module

_node_layout_prefs_module = sys.modules["node_layout_prefs"]

_PREFS_DEFAULTS = {
    "base_subtree_margin": 300,
    "horizontal_subtree_gap": 150,
    "horizontal_mask_gap": 50,
    "dot_font_reference_size": 20,
    "scaling_reference_count": 150,
    "compact_multiplier": 0.6,
    "normal_multiplier": 1.0,
    "loose_multiplier": 1.5,
    "loose_gap_multiplier": 12.0,
    "mask_input_ratio": 0.333,
}


def _reset_prefs():
    """Restore prefs_singleton to canonical defaults so tests are isolated from disk state."""
    singleton = _node_layout_prefs_module.prefs_singleton
    for key, val in _PREFS_DEFAULTS.items():
        singleton.set(key, val)

# Load module under test.
_module_path = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")
_spec = importlib.util.spec_from_file_location("node_layout_margins", _module_path)
_nl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_nl)

# At node_count=150 (the scaling reference count) with default prefs
# (normal_multiplier=1.0), _subtree_margin() returns base_subtree_margin (300 in
# this test's _PREFS_DEFAULTS) — used for V-axis gap assertions.
_SUBTREE_MARGIN_AT_REFERENCE = 300

# H-axis margins now come from _horizontal_margin() which reads horizontal_subtree_gap
# directly from prefs (no sqrt scaling). Default is 150.
_HORIZONTAL_MARGIN_AT_REFERENCE = 150


def _make_node(width=80, height=28, xpos=0, ypos=0, node_class="Grade"):
    """Create a stub node with no inputs."""
    node = _StubNode(width=width, height=height, xpos=xpos, ypos=ypos, node_class=node_class)
    node.inputs = lambda: 0
    node.input = lambda i: None
    return node


def _wire(parent, children_by_slot):
    """Wire parent to children: {slot_index: child_node}."""
    slot_count = max(children_by_slot.keys()) + 1

    def _inputs():
        return slot_count

    def _input(i):
        return children_by_slot.get(i)

    parent.inputs = _inputs
    parent.input = _input


class TestMarginSymmetryN2(unittest.TestCase):
    """n==2: verify that side input uses side_margins[1] consistently."""

    def setUp(self):
        _reset_prefs()

    def test_side_input_x_uses_slot1_margin(self):
        """n==2 non-all_side: side input placed at x + node_w + horizontal_margin[slot1]."""
        # H-axis margin now uses _horizontal_margin() -> horizontal_subtree_gap (150)
        parent = _make_node(width=80, xpos=100, ypos=400)
        child_primary = _make_node(width=80)  # input slot 0
        child_side = _make_node(width=60)     # input slot 1 (non-mask -> horizontal_subtree_gap)
        _wire(parent, {0: child_primary, 1: child_side})

        memo = {}
        _nl.compute_dims(parent, memo, snap_threshold=8, node_count=150)
        _nl.place_subtree(parent, 100, 400, memo, snap_threshold=8, node_count=150)

        expected_side_x = 100 + 80 + _HORIZONTAL_MARGIN_AT_REFERENCE  # x + node_w + h_margin[1]
        self.assertEqual(child_side.xpos(), expected_side_x)

    def test_compute_dims_n2_includes_slot1_margin_in_W(self):
        """n==2: compute_dims W includes side_margins_h[1] between node and side child."""
        parent = _make_node(width=80)
        child_primary = _make_node(width=80)
        child_side = _make_node(width=60)
        _wire(parent, {0: child_primary, 1: child_side})

        memo = {}
        dims = _nl.compute_dims(parent, memo, snap_threshold=8, node_count=150)
        w, h = dims

        # W = max(child0_w + overhang, node_w + h_margin[1] + child1_w)
        # child0 == node_w == 80, so overhang = 0
        # W = max(80, 80 + 150 + 60) = 290
        expected_w = max(80, 80 + _HORIZONTAL_MARGIN_AT_REFERENCE + 60)
        self.assertEqual(w, expected_w)


class TestMarginSymmetryN3(unittest.TestCase):
    """n==3: verify that gap before each side input uses that input's own slot margin."""

    def setUp(self):
        _reset_prefs()

    def test_side_inputs_placed_with_correct_margins(self):
        """n==3: child[1] at x+node_w+h_margin[1]; child[2] at x+node_w+h_margin[1]+child1_w+h_margin[2]."""
        parent = _make_node(width=80, xpos=0, ypos=400)
        child0 = _make_node(width=80)   # slot 0: primary (above)
        child1 = _make_node(width=60)   # slot 1: first side input -> horizontal_subtree_gap (150)
        child2 = _make_node(width=40)   # slot 2: second side input -> horizontal_subtree_gap (150)

        _wire(parent, {0: child0, 1: child1, 2: child2})

        memo = {}
        _nl.compute_dims(parent, memo, snap_threshold=8, node_count=150)
        _nl.place_subtree(parent, 0, 400, memo, snap_threshold=8, node_count=150)

        # child1 should be placed at x + node_w + side_margins_h[1] = 0 + 80 + 150 = 230
        expected_child1_x = 0 + 80 + _HORIZONTAL_MARGIN_AT_REFERENCE
        self.assertEqual(child1.xpos(), expected_child1_x)

        # child2 placed at: x + node_w + h_margin[1] + child1_w + h_margin[2]
        # = 0 + 80 + 150 + 60 + 150 = 440
        expected_child2_x = 0 + 80 + _HORIZONTAL_MARGIN_AT_REFERENCE + 60 + _HORIZONTAL_MARGIN_AT_REFERENCE
        self.assertEqual(child2.xpos(), expected_child2_x)

    def test_compute_dims_n3_total_width_matches_placement(self):
        """n==3: compute_dims W covers node + h_margin[1] + child1 + h_margin[2] + child2."""
        parent = _make_node(width=80)
        child0 = _make_node(width=80)
        child1 = _make_node(width=60)
        child2 = _make_node(width=40)
        _wire(parent, {0: child0, 1: child1, 2: child2})

        memo = {}
        dims = _nl.compute_dims(parent, memo, snap_threshold=8, node_count=150)
        w, h = dims

        # W = max(child0_w + overhang, node_w + sum(h_margins[1:3]) + sum(side_child widths))
        # overhang = max(0, (80 - 80) // 2) = 0
        # W = max(80, 80 + 150 + 150 + 60 + 40) = max(80, 480) = 480
        expected_w = max(80, 80 + 2 * _HORIZONTAL_MARGIN_AT_REFERENCE + 60 + 40)
        self.assertEqual(w, expected_w)

    def test_margin_consistent_between_dims_and_placement(self):
        """The rightmost side child's x + width must equal W computed by compute_dims (relative)."""
        parent = _make_node(width=80, xpos=0, ypos=400)
        child0 = _make_node(width=80)
        child1 = _make_node(width=60)
        child2 = _make_node(width=40)
        _wire(parent, {0: child0, 1: child1, 2: child2})

        memo = {}
        dims = _nl.compute_dims(parent, memo, snap_threshold=8, node_count=150)
        tree_width = dims[0]

        _nl.place_subtree(parent, 0, 400, memo, snap_threshold=8, node_count=150)

        # The rightmost side child's right edge: child2_x + child2_width
        rightmost_right = child2.xpos() + child2.screenWidth()
        # tree_width represents the maximum horizontal span from x=0
        self.assertEqual(rightmost_right, tree_width)


if __name__ == "__main__":
    unittest.main()

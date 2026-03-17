"""Behavioral tests for _scale_selected_nodes and _scale_upstream_nodes.

Tests verify:
- Anchor tiebreaker: on Y tie, leftmost node (min xpos) wins
- Center-based offsets: Dot nodes (with centering offset) move same fractional distance as regular nodes
- round() not int(): a 100px center-to-center offset * 0.8 lands at exactly 80px, not 79 or 81
- Anchor xpos does not change after repeated shrinks
- Minimum floor: no node's center-to-center distance falls below snap_threshold-1 (unless original offset was 0)
- _scale_upstream_nodes uses center-based offsets; no floor applied
- AST: (n.ypos(), -n.xpos()) tiebreaker present in _scale_selected_nodes source
- AST: round() used, int() absent from both scale functions
- AST: screenWidth() / 2 present in both scale functions
- AST: snap_min floor guard present in _scale_selected_nodes source
"""
import ast
import sys
import types
import importlib.util
import os
import unittest


NODE_LAYOUT_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")
NODE_LAYOUT_PREFS_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout_prefs.py")


# ---------------------------------------------------------------------------
# Stub nuke module — must match the stub used in test_prefs_integration.py
# so both can coexist in the same test run.
# ---------------------------------------------------------------------------


class _StubKnob:
    def __init__(self, val=0):
        self._val = val

    def value(self):
        return self._val

    def getValue(self):
        return self._val


class _StubWritableKnob:
    """Stub knob that supports getValue/setValue for state storage tests."""

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
    """Factory for knob stubs used by write_node_state (Tab_Knob / String_Knob factories)."""
    knob = _StubWritableKnob()
    knob.name = name
    return knob


# Only register the stub if "nuke" not already registered (to avoid conflict with
# test_prefs_integration.py when running in the same process).
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

# Ensure write_node_state knob factories are present on whichever nuke stub is active.
# This is needed because test_scale_nodes.py may inherit a stub from another test file
# that lacks Tab_Knob / String_Knob / INVISIBLE.
_active_nuke = sys.modules["nuke"]
if not hasattr(_active_nuke, "Tab_Knob"):
    _active_nuke.Tab_Knob = lambda name='', label='': _make_stub_knob(name, label)
if not hasattr(_active_nuke, "String_Knob"):
    _active_nuke.String_Knob = lambda name='', label='': _make_stub_knob(name, label)
if not hasattr(_active_nuke, "INVISIBLE"):
    _active_nuke.INVISIBLE = 0x01

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

# Always load a fresh copy of node_layout so this test file uses the latest source
# regardless of module-cache state from other test files loaded in the same process.
_module_path = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")
_spec = importlib.util.spec_from_file_location("node_layout_scale_tests_fresh", _module_path)
_nl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_nl)


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _get_function_source(func_name):
    """Return the source text of func_name from node_layout.py."""
    with open(NODE_LAYOUT_PATH) as source_file:
        source = source_file.read()
    tree = ast.parse(source)
    for ast_node in ast.walk(tree):
        if isinstance(ast_node, ast.FunctionDef) and ast_node.name == func_name:
            return ast.get_source_segment(source, ast_node)
    return None


# ---------------------------------------------------------------------------
# Helper: configure nuke stub to return a specific selected-nodes list.
# These helpers update the nuke module as seen by _nl (which may differ from
# sys.modules["nuke"] if test_undo_wrapping.py replaced the stub after _nl was loaded).
# ---------------------------------------------------------------------------


def _set_selected_nodes(nodes):
    """Override nuke.selectedNodes on the nuke module that _nl actually uses."""
    _nl.nuke.selectedNodes = lambda: nodes


def _set_selected_node(node):
    """Override nuke.selectedNode on the nuke module that _nl actually uses."""
    _nl.nuke.selectedNode = lambda: node


# ---------------------------------------------------------------------------
# TestScaleSelectedNodesAST — structural source checks
# ---------------------------------------------------------------------------


class TestScaleSelectedNodesAST(unittest.TestCase):
    """AST-based checks that _scale_selected_nodes uses correct patterns."""

    def test_anchor_tiebreaker_present(self):
        """_scale_selected_nodes source must contain the (n.ypos(), -n.xpos()) tiebreaker."""
        source = _get_function_source("_scale_selected_nodes")
        self.assertIsNotNone(source, "_scale_selected_nodes not found in source")
        self.assertIn(
            "n.ypos(), -n.xpos()",
            source,
            "_scale_selected_nodes missing (n.ypos(), -n.xpos()) tiebreaker",
        )

    def test_no_int_conversion_in_scale_selected(self):
        """_scale_selected_nodes must use round() not int() for integer conversions."""
        source = _get_function_source("_scale_selected_nodes")
        self.assertIsNotNone(source, "_scale_selected_nodes not found in source")
        self.assertNotIn(
            "int(",
            source,
            "_scale_selected_nodes still uses int() — should use round()",
        )

    def test_center_based_offset_in_scale_selected(self):
        """_scale_selected_nodes must use screenWidth() / 2 for center computation."""
        source = _get_function_source("_scale_selected_nodes")
        self.assertIsNotNone(source, "_scale_selected_nodes not found in source")
        self.assertIn(
            "screenWidth() / 2",
            source,
            "_scale_selected_nodes missing screenWidth() / 2 for center-based offsets",
        )

    def test_snap_min_floor_guard_in_scale_selected(self):
        """_scale_selected_nodes must contain snap_min floor guard."""
        source = _get_function_source("_scale_selected_nodes")
        self.assertIsNotNone(source, "_scale_selected_nodes not found in source")
        self.assertIn(
            "snap_min",
            source,
            "_scale_selected_nodes missing snap_min floor guard",
        )


class TestScaleUpstreamNodesAST(unittest.TestCase):
    """AST-based checks that _scale_upstream_nodes uses correct patterns."""

    def test_center_based_offset_in_scale_upstream(self):
        """_scale_upstream_nodes must use screenWidth() / 2 for center computation."""
        source = _get_function_source("_scale_upstream_nodes")
        self.assertIsNotNone(source, "_scale_upstream_nodes not found in source")
        self.assertIn(
            "screenWidth() / 2",
            source,
            "_scale_upstream_nodes missing screenWidth() / 2 for center-based offsets",
        )

    def test_no_int_conversion_in_scale_upstream(self):
        """_scale_upstream_nodes must use round() not int() for integer conversions."""
        source = _get_function_source("_scale_upstream_nodes")
        self.assertIsNotNone(source, "_scale_upstream_nodes not found in source")
        self.assertNotIn(
            "int(",
            source,
            "_scale_upstream_nodes still uses int() — should use round()",
        )

    def test_snap_min_floor_guard_in_scale_upstream(self):
        """_scale_upstream_nodes must contain snap_min floor guard (Plan 06: matching _scale_selected_nodes)."""
        source = _get_function_source("_scale_upstream_nodes")
        self.assertIsNotNone(source, "_scale_upstream_nodes not found in source")
        self.assertIn(
            "snap_min",
            source,
            "_scale_upstream_nodes missing snap_min floor guard — must match _scale_selected_nodes pattern",
        )


# ---------------------------------------------------------------------------
# TestScaleSelectedNodesBehavior — behavioral correctness
# ---------------------------------------------------------------------------


class TestScaleSelectedNodesBehavior(unittest.TestCase):
    """Behavioral tests for _scale_selected_nodes using stub nodes."""

    # Regular node dimensions matching Nuke defaults
    _NODE_W = 80
    _NODE_H = 28

    def _make_regular_node(self, xpos, ypos):
        return _StubNode(width=self._NODE_W, height=self._NODE_H, xpos=xpos, ypos=ypos)

    def _make_dot_node(self, xpos, ypos):
        """Dot nodes in Nuke are 12x12. Their xpos includes a 34px centering correction
        relative to a standard 80-wide node column."""
        return _StubNode(width=12, height=12, xpos=xpos, ypos=ypos, node_class="Dot")

    def test_anchor_is_bottom_right_on_y_tie(self):
        """On Y tie, the leftmost node (lowest xpos) wins as anchor; its position is unchanged."""
        # Two nodes at the same Y. Leftmost (xpos=0) should be anchor.
        anchor_candidate = self._make_regular_node(xpos=0, ypos=200)
        non_anchor = self._make_regular_node(xpos=200, ypos=200)

        # non_anchor starts 200px to the right of anchor at top-left
        # center offsets: non_anchor_center_x = 200 + 40 = 240; anchor_center_x = 0 + 40 = 40
        # dx = 240 - 40 = 200; after 0.8 shrink → 160; new xpos = 40 + 160 - 40 = 160

        _set_selected_nodes([anchor_candidate, non_anchor])
        _nl._scale_selected_nodes(0.8)

        # Anchor xpos must not change
        self.assertEqual(
            anchor_candidate.xpos(),
            0,
            f"Anchor xpos changed from 0 to {anchor_candidate.xpos()}",
        )
        # non_anchor moved
        self.assertNotEqual(
            non_anchor.xpos(),
            200,
            "Non-anchor node did not move after shrink",
        )

    def test_anchor_chosen_by_max_ypos_leftmost_on_tie(self):
        """When multiple nodes share the maximum ypos, the one with the lowest xpos is anchor."""
        left_bottom = self._make_regular_node(xpos=0, ypos=500)
        right_bottom = self._make_regular_node(xpos=400, ypos=500)
        upper = self._make_regular_node(xpos=200, ypos=100)

        _set_selected_nodes([left_bottom, right_bottom, upper])
        _nl._scale_selected_nodes(0.8)

        # left_bottom is anchor (max Y=500, leftmost xpos=0): must not move
        self.assertEqual(left_bottom.xpos(), 0, f"Anchor left_bottom.xpos moved: {left_bottom.xpos()}")
        self.assertEqual(left_bottom.ypos(), 500, f"Anchor left_bottom.ypos moved: {left_bottom.ypos()}")

    def test_round_not_int_precision(self):
        """A 100px center-to-center offset * 0.8 lands at exactly 80px (round, not int/truncate)."""
        # anchor at origin; movable node placed so center-to-center dx = 100
        # anchor center_x = 0 + 40 = 40
        # movable node: we want center_x such that center_x - 40 = 100 => center_x = 140
        # movable xpos = center_x - screenWidth/2 = 140 - 40 = 100
        # After 0.8 shrink: new_dx = round(100 * 0.8) = 80
        # new_center_x = 40 + 80 = 120; new_xpos = 120 - 40 = 80

        anchor_node = self._make_regular_node(xpos=0, ypos=200)
        movable_node = self._make_regular_node(xpos=100, ypos=0)

        _set_selected_nodes([anchor_node, movable_node])
        _nl._scale_selected_nodes(0.8)

        # movable_node should be at xpos=80
        self.assertEqual(
            movable_node.xpos(),
            80,
            f"Expected xpos=80 after shrink, got {movable_node.xpos()} "
            "(int() truncation would give 79 or similar)",
        )

    def test_anchor_xpos_unchanged_after_repeated_shrinks(self):
        """Anchor xpos remains the same after 5 successive shrink operations."""
        anchor_node = self._make_regular_node(xpos=0, ypos=200)
        movable_node = self._make_regular_node(xpos=300, ypos=0)
        initial_anchor_xpos = anchor_node.xpos()

        for _ in range(5):
            _set_selected_nodes([anchor_node, movable_node])
            _nl._scale_selected_nodes(0.8)

        self.assertEqual(
            anchor_node.xpos(),
            initial_anchor_xpos,
            f"Anchor xpos changed after repeated shrinks: expected {initial_anchor_xpos}, got {anchor_node.xpos()}",
        )

    def test_minimum_floor_prevents_too_close(self):
        """After shrinking, no node's center-to-center distance to anchor falls below snap_threshold-1."""
        snap_threshold = 8
        snap_min = snap_threshold - 1

        # anchor at center_x=40; movable node at center-to-center distance of 10px
        # (slightly above snap_min=7). After 0.8 shrink: round(10*0.8)=8 > 7, no floor needed.
        # Use a very small distance (6px) that after shrink would be 4.8 → round=5, below floor.
        # center-to-center dx = 6: movable center_x = 40 + 6 = 46; movable xpos = 46 - 40 = 6
        anchor_node = self._make_regular_node(xpos=0, ypos=200)
        movable_node = self._make_regular_node(xpos=6, ypos=0)

        _set_selected_nodes([anchor_node, movable_node])
        _nl._scale_selected_nodes(0.8)

        # new_dx = round(6*0.8) = 5, which is less than snap_min=7
        # floor should clamp it to snap_min=7 (positive direction)
        # new_center_x = 40 + 7 = 47; new_xpos = 47 - 40 = 7
        anchor_center_x = 0 + self._NODE_W / 2  # 40
        movable_center_x = movable_node.xpos() + self._NODE_W / 2
        center_distance = abs(movable_center_x - anchor_center_x)

        self.assertGreaterEqual(
            center_distance,
            snap_min,
            f"Center-to-center distance {center_distance} is below snap_min={snap_min} — floor not applied",
        )

    def test_zero_offset_node_stays_zero(self):
        """A node at the exact same center as the anchor (dx=0) does not get clamped to snap_min."""
        # Two nodes stacked at the same position (unusual but valid edge case)
        anchor_node = self._make_regular_node(xpos=0, ypos=200)
        # Only dy is non-zero; dx is zero
        same_col_node = self._make_regular_node(xpos=0, ypos=0)

        _set_selected_nodes([anchor_node, same_col_node])
        _nl._scale_selected_nodes(0.8)

        # X should remain 0 (not clamped to snap_min)
        self.assertEqual(
            same_col_node.xpos(),
            0,
            f"Zero-dx node was incorrectly clamped: xpos={same_col_node.xpos()}",
        )

    def test_dot_node_moves_same_fractional_distance_as_regular_node(self):
        """A Dot node at the same logical column as a regular node moves the same fractional
        center-to-center distance from the anchor.

        Dot nodes have width=12. Their xpos in Nuke includes a +34px centering correction
        relative to a standard 80-wide column. Both Dot and regular node start 200px
        center-to-center from the anchor. After 0.8 shrink both should end 160px away.
        """
        # Anchor at origin
        anchor_node = self._make_regular_node(xpos=0, ypos=200)
        anchor_center_x = 0 + self._NODE_W / 2  # 40

        # Regular node: center-to-center dx = 200
        # regular xpos = anchor_center_x + 200 - NODE_W/2 = 40 + 200 - 40 = 200
        regular_node = self._make_regular_node(xpos=200, ypos=0)

        # Dot node: Dot width=12, same center-to-center dx=200
        # dot center_x = anchor_center_x + 200 = 240
        # dot xpos = 240 - 12/2 = 240 - 6 = 234  (includes centering offset vs regular column)
        dot_node = self._make_dot_node(xpos=234, ypos=0)

        _set_selected_nodes([anchor_node, regular_node, dot_node])
        _nl._scale_selected_nodes(0.8)

        regular_center_x_after = regular_node.xpos() + self._NODE_W / 2
        dot_center_x_after = dot_node.xpos() + 12 / 2

        regular_dx_after = regular_center_x_after - anchor_center_x
        dot_dx_after = dot_center_x_after - anchor_center_x

        self.assertEqual(
            regular_dx_after,
            160,
            f"Regular node center-to-center distance after shrink: expected 160, got {regular_dx_after}",
        )
        self.assertEqual(
            dot_dx_after,
            160,
            f"Dot node center-to-center distance after shrink: expected 160, got {dot_dx_after} "
            "(top-left offset bug: Dot drifted disproportionately)",
        )


# ---------------------------------------------------------------------------
# TestScaleUpstreamNodesBehavior — behavioral correctness
# ---------------------------------------------------------------------------


class TestScaleUpstreamNodesBehavior(unittest.TestCase):
    """Behavioral tests for _scale_upstream_nodes using stub nodes."""

    _NODE_W = 80
    _NODE_H = 28

    def _make_regular_node(self, xpos, ypos):
        return _StubNode(width=self._NODE_W, height=self._NODE_H, xpos=xpos, ypos=ypos)

    def _make_dot_node(self, xpos, ypos):
        return _StubNode(width=12, height=12, xpos=xpos, ypos=ypos, node_class="Dot")

    def test_upstream_dot_moves_same_fractional_distance_as_regular_node(self):
        """A Dot node in the upstream tree moves the same center-to-center distance as
        a regular upstream node at the same logical column."""
        anchor_node = self._make_regular_node(xpos=0, ypos=200)
        anchor_center_x = 0 + self._NODE_W / 2  # 40

        # Regular upstream node: center-to-center dx = 200
        regular_upstream = self._make_regular_node(xpos=200, ypos=0)

        # Dot upstream node: same center-to-center dx = 200
        # dot xpos = anchor_center_x + 200 - 12/2 = 234
        dot_upstream = self._make_dot_node(xpos=234, ypos=0)

        # Stub collect_subtree_nodes to return anchor + both upstream nodes
        original_collect = _nl.collect_subtree_nodes
        _nl.collect_subtree_nodes = lambda n: [n, regular_upstream, dot_upstream]
        _set_selected_node(anchor_node)

        try:
            _nl._scale_upstream_nodes(0.8)
        finally:
            _nl.collect_subtree_nodes = original_collect

        regular_center_x_after = regular_upstream.xpos() + self._NODE_W / 2
        dot_center_x_after = dot_upstream.xpos() + 12 / 2

        regular_dx_after = regular_center_x_after - anchor_center_x
        dot_dx_after = dot_center_x_after - anchor_center_x

        self.assertEqual(
            regular_dx_after,
            160,
            f"Regular upstream center-to-center after shrink: expected 160, got {regular_dx_after}",
        )
        self.assertEqual(
            dot_dx_after,
            160,
            f"Dot upstream center-to-center after shrink: expected 160, got {dot_dx_after} "
            "(top-left bug: Dot drifted disproportionately)",
        )

    def test_upstream_round_precision(self):
        """A 100px center-to-center offset * 0.8 lands at exactly 80px in upstream scaling."""
        anchor_node = self._make_regular_node(xpos=0, ypos=200)
        # movable xpos=100 → center_x=140; anchor center_x=40; dx=100
        movable_node = self._make_regular_node(xpos=100, ypos=0)

        original_collect = _nl.collect_subtree_nodes
        _nl.collect_subtree_nodes = lambda n: [n, movable_node]
        _set_selected_node(anchor_node)

        try:
            _nl._scale_upstream_nodes(0.8)
        finally:
            _nl.collect_subtree_nodes = original_collect

        self.assertEqual(
            movable_node.xpos(),
            80,
            f"Expected xpos=80 after upstream shrink, got {movable_node.xpos()}",
        )

    def test_anchor_xpos_unchanged_in_upstream(self):
        """Anchor node's xpos does not change after _scale_upstream_nodes."""
        anchor_node = self._make_regular_node(xpos=0, ypos=200)
        upstream_node = self._make_regular_node(xpos=200, ypos=0)
        initial_anchor_xpos = anchor_node.xpos()

        original_collect = _nl.collect_subtree_nodes
        _nl.collect_subtree_nodes = lambda n: [n, upstream_node]
        _set_selected_node(anchor_node)

        try:
            _nl._scale_upstream_nodes(0.8)
        finally:
            _nl.collect_subtree_nodes = original_collect

        self.assertEqual(
            anchor_node.xpos(),
            initial_anchor_xpos,
            f"Anchor xpos changed from {initial_anchor_xpos} to {anchor_node.xpos()}",
        )


if __name__ == "__main__":
    unittest.main()

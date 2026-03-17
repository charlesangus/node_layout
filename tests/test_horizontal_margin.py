"""Tests for _horizontal_margin() in node_layout.py (06-02 Task 1 TDD).

These tests verify the H-axis decoupling:
- _horizontal_margin() is defined and reads horizontal_subtree_gap / horizontal_mask_gap
- compute_dims() uses _horizontal_margin for side_margins_h
- place_subtree() uses _horizontal_margin for side_margins_h
- layout_selected() uses horizontal_subtree_gap directly for horizontal_clearance (no sqrt formula)
- Behavioral: _horizontal_margin returns 150 for non-mask, 50 for mask (defaults)
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

    def inputLabel(self, index):
        return ""

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


_nuke_stub = types.ModuleType("nuke")
_nuke_stub.Node = _StubNode
_nuke_stub.allNodes = lambda: []
_nuke_stub.selectedNodes = lambda: []
_nuke_stub.selectedNode = lambda: _StubNode()
_nuke_stub.toNode = lambda name: _make_preferences_node() if name == "preferences" else None
_nuke_stub.menu = lambda name: None
_nuke_stub.Undo = _StubUndo
sys.modules["nuke"] = _nuke_stub

# Load node_layout_prefs (no Nuke dependency) so node_layout.py import resolves it.
_prefs_spec = importlib.util.spec_from_file_location("node_layout_prefs", NODE_LAYOUT_PREFS_PATH)
_node_layout_prefs_module = importlib.util.module_from_spec(_prefs_spec)
_prefs_spec.loader.exec_module(_node_layout_prefs_module)
sys.modules["node_layout_prefs"] = _node_layout_prefs_module

_module_path = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")
_spec = importlib.util.spec_from_file_location("node_layout_horizontal", _module_path)
_nl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_nl)


def _reset_prefs():
    """Restore prefs to DEFAULTS without touching any file."""
    singleton = _node_layout_prefs_module.prefs_singleton
    for key, default_value in _node_layout_prefs_module.DEFAULTS.items():
        singleton.set(key, default_value)


# ---------------------------------------------------------------------------
# AST Tests
# ---------------------------------------------------------------------------


class TestHorizontalMarginAST(unittest.TestCase):
    """AST structural tests for _horizontal_margin() integration."""

    @classmethod
    def setUpClass(cls):
        with open(NODE_LAYOUT_PATH) as source_file:
            cls.source = source_file.read()
        cls.tree = ast.parse(cls.source)
        cls.funcs = {
            node.name: node
            for node in ast.walk(cls.tree)
            if isinstance(node, ast.FunctionDef)
        }

    def test_horizontal_margin_is_defined(self):
        """_horizontal_margin must be a defined function in node_layout.py."""
        self.assertIn(
            "_horizontal_margin",
            self.funcs,
            "_horizontal_margin function not found in node_layout.py",
        )

    def test_horizontal_margin_references_horizontal_mask_gap(self):
        """_horizontal_margin body must reference 'horizontal_mask_gap'."""
        func_node = self.funcs["_horizontal_margin"]
        func_source = ast.get_source_segment(self.source, func_node)
        self.assertIn(
            "horizontal_mask_gap",
            func_source,
            "_horizontal_margin does not reference horizontal_mask_gap",
        )

    def test_horizontal_margin_references_horizontal_subtree_gap(self):
        """_horizontal_margin body must reference 'horizontal_subtree_gap'."""
        func_node = self.funcs["_horizontal_margin"]
        func_source = ast.get_source_segment(self.source, func_node)
        self.assertIn(
            "horizontal_subtree_gap",
            func_source,
            "_horizontal_margin does not reference horizontal_subtree_gap",
        )

    def test_horizontal_margin_calls_is_mask_input(self):
        """_horizontal_margin body must call _is_mask_input."""
        func_node = self.funcs["_horizontal_margin"]
        func_source = ast.get_source_segment(self.source, func_node)
        self.assertIn(
            "_is_mask_input",
            func_source,
            "_horizontal_margin does not call _is_mask_input",
        )

    def test_compute_dims_uses_horizontal_margin_for_side_margins_h(self):
        """compute_dims body must contain both 'side_margins_h' and '_horizontal_margin'."""
        func_node = self.funcs["compute_dims"]
        func_source = ast.get_source_segment(self.source, func_node)
        self.assertIn(
            "_horizontal_margin",
            func_source,
            "compute_dims does not use _horizontal_margin",
        )
        self.assertIn(
            "side_margins_h",
            func_source,
            "compute_dims missing side_margins_h",
        )

    def test_place_subtree_uses_horizontal_margin_for_side_margins_h(self):
        """place_subtree body must contain both 'side_margins_h' and '_horizontal_margin'."""
        func_node = self.funcs["place_subtree"]
        func_source = ast.get_source_segment(self.source, func_node)
        self.assertIn(
            "_horizontal_margin",
            func_source,
            "place_subtree does not use _horizontal_margin",
        )
        self.assertIn(
            "side_margins_h",
            func_source,
            "place_subtree missing side_margins_h",
        )

    def test_layout_selected_horizontal_clearance_uses_horizontal_subtree_gap(self):
        """layout_selected horizontal_clearance must reference horizontal_subtree_gap."""
        func_node = self.funcs["layout_selected"]
        func_source = ast.get_source_segment(self.source, func_node)
        clearance_idx = func_source.find("horizontal_clearance")
        self.assertGreater(
            clearance_idx,
            -1,
            "horizontal_clearance not found in layout_selected",
        )
        # Extract window around the assignment (covers multi-line expressions)
        clearance_end = func_source.find("\n", clearance_idx + 100)
        if clearance_end == -1:
            clearance_end = len(func_source)
        clearance_block = func_source[clearance_idx:clearance_end]
        self.assertIn(
            "horizontal_subtree_gap",
            clearance_block,
            f"horizontal_clearance block must use horizontal_subtree_gap; block: {clearance_block!r}",
        )

    def test_layout_selected_horizontal_clearance_no_base_subtree_margin(self):
        """layout_selected horizontal_clearance must NOT reference base_subtree_margin."""
        func_node = self.funcs["layout_selected"]
        func_source = ast.get_source_segment(self.source, func_node)
        clearance_idx = func_source.find("horizontal_clearance")
        self.assertGreater(clearance_idx, -1, "horizontal_clearance not found in layout_selected")
        # Extract a broad window (the old formula was 5 lines)
        clearance_end_idx = clearance_idx + 300
        clearance_block = func_source[clearance_idx:min(clearance_end_idx, len(func_source))]
        self.assertNotIn(
            "base_subtree_margin",
            clearance_block,
            f"horizontal_clearance block must NOT reference base_subtree_margin; block: {clearance_block!r}",
        )


# ---------------------------------------------------------------------------
# Behavioral Tests
# ---------------------------------------------------------------------------


class TestHorizontalMarginBehavioral(unittest.TestCase):
    """Behavioral tests for _horizontal_margin() return values."""

    def setUp(self):
        _reset_prefs()

    def _make_non_mask_node(self):
        return _StubNode(node_class="Grade")

    def _make_merge2_node(self):
        return _StubNode(node_class="Merge2")

    def test_horizontal_margin_non_mask_returns_horizontal_subtree_gap_default(self):
        """_horizontal_margin for a non-mask slot returns horizontal_subtree_gap (default 250)."""
        non_mask_node = self._make_non_mask_node()
        result = _nl._horizontal_margin(non_mask_node, 0)
        expected = _node_layout_prefs_module.prefs_singleton.get("horizontal_subtree_gap")
        self.assertEqual(
            result,
            expected,
            f"Expected horizontal_subtree_gap={expected}, got {result}",
        )
        # Also verify against hard-coded default value
        self.assertEqual(result, 250, f"Default horizontal_subtree_gap is 250, got {result}")

    def test_horizontal_margin_mask_slot_returns_horizontal_mask_gap_default(self):
        """_horizontal_margin for a mask slot (Merge2 slot 2) returns horizontal_mask_gap (default 50)."""
        merge_node = self._make_merge2_node()
        result = _nl._horizontal_margin(merge_node, 2)
        expected = _node_layout_prefs_module.prefs_singleton.get("horizontal_mask_gap")
        self.assertEqual(
            result,
            expected,
            f"Expected horizontal_mask_gap={expected}, got {result}",
        )
        # Also verify against hard-coded default value
        self.assertEqual(result, 50, f"Default horizontal_mask_gap is 50, got {result}")

    def test_horizontal_margin_respects_overridden_horizontal_subtree_gap(self):
        """_horizontal_margin returns the overridden horizontal_subtree_gap value."""
        _node_layout_prefs_module.prefs_singleton.set("horizontal_subtree_gap", 200)
        non_mask_node = self._make_non_mask_node()
        result = _nl._horizontal_margin(non_mask_node, 0)
        self.assertEqual(result, 200, f"Expected overridden gap 200, got {result}")

    def test_horizontal_margin_respects_overridden_horizontal_mask_gap(self):
        """_horizontal_margin returns the overridden horizontal_mask_gap for mask slots."""
        _node_layout_prefs_module.prefs_singleton.set("horizontal_mask_gap", 30)
        merge_node = self._make_merge2_node()
        result = _nl._horizontal_margin(merge_node, 2)
        self.assertEqual(result, 30, f"Expected overridden mask gap 30, got {result}")


if __name__ == "__main__":
    unittest.main()

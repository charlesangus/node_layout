"""Tests verifying that node_layout.py reads spacing values from prefs at call time.

These tests run without the Nuke runtime — they use the real node_layout_prefs module
(no Nuke dependency) and a nuke stub to import node_layout.py.

Verifications:
- _subtree_margin() with node_count=1 returns a smaller value than with node_count=150
  (sqrt scaling produces lower margin for small subtrees)
- _subtree_margin() for a mask input slot returns approximately 1/3 of the non-mask margin
  (mask_input_ratio = 0.333)
- vertical_gap_between() returns int(12.0 * snap_threshold) by default
  (loose_gap_multiplier default is 12)
- If prefs_singleton.get("loose_gap_multiplier") is overridden to 8.0,
  vertical_gap_between() returns 8 * snap_threshold for non-color-matched nodes
- After removing SUBTREE_MARGIN: 'SUBTREE_MARGIN' not in src (verified by reading source)
"""
import ast
import importlib.util
import os
import sys
import types
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

# Load the real node_layout_prefs (no Nuke dependency) into sys.modules first
# so that node_layout.py's `import node_layout_prefs` resolves to it.
_prefs_spec = importlib.util.spec_from_file_location("node_layout_prefs", NODE_LAYOUT_PREFS_PATH)
_node_layout_prefs_module = importlib.util.module_from_spec(_prefs_spec)
_prefs_spec.loader.exec_module(_node_layout_prefs_module)
sys.modules["node_layout_prefs"] = _node_layout_prefs_module

_module_path = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")
_spec = importlib.util.spec_from_file_location("node_layout", _module_path)
_nl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_nl)


# ---------------------------------------------------------------------------
# Helper: reset prefs singleton to defaults between tests
# ---------------------------------------------------------------------------

_PREFS_DEFAULTS = {
    "base_subtree_margin": 200,
    "horizontal_subtree_gap": 250,
    "horizontal_side_vertical_gap": 150,
    "horizontal_mask_gap": 50,
    "dot_font_reference_size": 20,
    "compact_multiplier": 0.6,
    "normal_multiplier": 1.0,
    "loose_multiplier": 1.5,
    "loose_gap_multiplier": 8.0,
    "mask_input_ratio": 0.333,
    "scaling_reference_count": 150,
}


def _reset_prefs():
    """Restore prefs_singleton to default values without touching any file."""
    singleton = _node_layout_prefs_module.prefs_singleton
    for key, default_value in _PREFS_DEFAULTS.items():
        singleton.set(key, default_value)


# ---------------------------------------------------------------------------
# AST helper for signature inspection
# ---------------------------------------------------------------------------


def _get_function_node(func_name):
    """Return the ast.FunctionDef node for func_name from node_layout.py."""
    with open(NODE_LAYOUT_PATH) as source_file:
        source = source_file.read()
    tree = ast.parse(source)
    for ast_node in ast.walk(tree):
        if isinstance(ast_node, ast.FunctionDef) and ast_node.name == func_name:
            return ast_node
    return None


def _get_arg_names(func_name):
    """Return list of positional argument names for func_name."""
    func_node = _get_function_node(func_name)
    if func_node is None:
        return []
    return [arg.arg for arg in func_node.args.args]


# ---------------------------------------------------------------------------
# TestPrefsIntegration
# ---------------------------------------------------------------------------






class TestGeometricScalingCommands(unittest.TestCase):
    """Verify geometric scaling commands exist and are correctly defined in source."""

    # --- AST: public scaling functions ---

    def test_public_scaling_functions_exist(self):
        """shrink_selected, expand_selected, shrink_upstream, expand_upstream must be defined."""
        with open(NODE_LAYOUT_PATH) as source_file:
            source = source_file.read()
        tree = ast.parse(source)
        defined_functions = {
            ast_node.name
            for ast_node in ast.walk(tree)
            if isinstance(ast_node, ast.FunctionDef)
        }
        for expected_function_name in (
            "shrink_selected",
            "expand_selected",
            "shrink_upstream",
            "expand_upstream",
        ):
            self.assertIn(
                expected_function_name,
                defined_functions,
                f"Function {expected_function_name!r} not found in node_layout.py",
            )

    # --- AST: private helper functions ---

    def test_scale_helper_functions_exist(self):
        """_scale_selected_nodes and _scale_upstream_nodes must be defined."""
        with open(NODE_LAYOUT_PATH) as source_file:
            source = source_file.read()
        tree = ast.parse(source)
        defined_functions = {
            ast_node.name
            for ast_node in ast.walk(tree)
            if isinstance(ast_node, ast.FunctionDef)
        }
        for expected_function_name in ("_scale_selected_nodes", "_scale_upstream_nodes"):
            self.assertIn(
                expected_function_name,
                defined_functions,
                f"Function {expected_function_name!r} not found in node_layout.py",
            )

    # --- AST: SHRINK_FACTOR and EXPAND_FACTOR module-level constants ---

    def test_shrink_and_expand_factor_constants_exist(self):
        """SHRINK_FACTOR and EXPAND_FACTOR must be assigned at module level in source."""
        with open(NODE_LAYOUT_PATH) as source_file:
            source = source_file.read()
        tree = ast.parse(source)
        module_level_assigned_names = set()
        for ast_node in tree.body:
            if isinstance(ast_node, ast.Assign):
                for target in ast_node.targets:
                    if isinstance(target, ast.Name):
                        module_level_assigned_names.add(target.id)
        for expected_constant_name in ("SHRINK_FACTOR", "EXPAND_FACTOR"):
            self.assertIn(
                expected_constant_name,
                module_level_assigned_names,
                f"Module-level constant {expected_constant_name!r} not found in node_layout.py",
            )


class TestSchemeDifferentiation(unittest.TestCase):
    """Behavioral tests verifying scheme_multiplier produces measurably different spacing."""

    def setUp(self):
        # Reset prefs to defaults before each test
        _node_layout_prefs_module.prefs_singleton._prefs = dict(_node_layout_prefs_module.DEFAULTS)

    def test_vertical_gap_compact_smaller_than_normal(self):
        """Compact scheme (0.6) produces smaller gap than Normal (1.0)."""
        node_a = _StubNode(node_class="Grade", knobs={"tile_color": _StubKnob(0x00ff0000)})
        node_b = _StubNode(node_class="Blur", knobs={"tile_color": _StubKnob(0x0000ff00)})
        snap_threshold = 8
        normal_gap = _nl.vertical_gap_between(
            node_a, node_b, snap_threshold, scheme_multiplier=1.0
        )
        compact_gap = _nl.vertical_gap_between(
            node_a, node_b, snap_threshold, scheme_multiplier=0.6
        )
        self.assertLess(compact_gap, normal_gap)
        self.assertEqual(compact_gap, int(8.0 * 0.6 * snap_threshold))

    def test_vertical_gap_loose_larger_than_normal(self):
        """Loose scheme (1.5) produces larger gap than Normal (1.0)."""
        node_a = _StubNode(node_class="Grade", knobs={"tile_color": _StubKnob(0x00ff0000)})
        node_b = _StubNode(node_class="Blur", knobs={"tile_color": _StubKnob(0x0000ff00)})
        snap_threshold = 8
        normal_gap = _nl.vertical_gap_between(node_a, node_b, snap_threshold, scheme_multiplier=1.0)
        loose_gap = _nl.vertical_gap_between(node_a, node_b, snap_threshold, scheme_multiplier=1.5)
        self.assertGreater(loose_gap, normal_gap)
        self.assertEqual(loose_gap, int(8.0 * 1.5 * snap_threshold))

    def test_scheme_multiplier_constants_in_source(self):
        """SHRINK_FACTOR=0.8 and EXPAND_FACTOR=1.25 are module-level constants."""
        with open(NODE_LAYOUT_PATH) as source_file:
            source = source_file.read()
        tree = ast.parse(source)
        assignments = {
            node.targets[0].id: node.value.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
        }
        self.assertAlmostEqual(assignments.get("SHRINK_FACTOR"), 0.8)
        self.assertAlmostEqual(assignments.get("EXPAND_FACTOR"), 1.25)

    def test_layout_upstream_signature_has_scheme_multiplier(self):
        """layout_upstream() signature includes scheme_multiplier parameter."""
        with open(NODE_LAYOUT_PATH) as source_file:
            source = source_file.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "layout_upstream":
                arg_names = [arg.arg for arg in node.args.args + node.args.kwonlyargs]
                self.assertIn("scheme_multiplier", arg_names)
                return
        self.fail("layout_upstream not found in source")

    def test_layout_selected_signature_has_scheme_multiplier(self):
        """layout_selected() signature includes scheme_multiplier parameter."""
        with open(NODE_LAYOUT_PATH) as source_file:
            source = source_file.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "layout_selected":
                arg_names = [arg.arg for arg in node.args.args + node.args.kwonlyargs]
                self.assertIn("scheme_multiplier", arg_names)
                return
        self.fail("layout_selected not found in source")




if __name__ == "__main__":
    unittest.main()

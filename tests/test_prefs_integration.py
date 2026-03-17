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
- compute_dims() and place_subtree() signatures accept node_count as a parameter
  (verified by AST inspection of function signatures)
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


class TestPrefsIntegration(unittest.TestCase):
    """Verify that node_layout.py reads spacing from prefs at call time."""

    def setUp(self):
        _reset_prefs()

    def _make_non_mask_node(self):
        """Return a simple node with slot 0 as a non-mask (Grade) input."""
        node = _StubNode(node_class="Grade")
        return node

    def _make_merge2_node(self):
        """Return a Merge2 node stub (slot 2 is mask for Merge2)."""
        node = _StubNode(node_class="Merge2")
        return node

    # --- sqrt scaling ---

    def test_subtree_margin_increases_with_node_count(self):
        """_subtree_margin() returns a larger value for node_count=150 than for node_count=1."""
        non_mask_node = self._make_non_mask_node()
        margin_small = _nl._subtree_margin(non_mask_node, 0, node_count=1)
        margin_large = _nl._subtree_margin(non_mask_node, 0, node_count=150)
        self.assertLess(
            margin_small,
            margin_large,
            f"Expected margin for node_count=1 ({margin_small})"
            f" < margin for node_count=150 ({margin_large})",
        )

    def test_subtree_margin_at_reference_count_equals_base(self):
        """_subtree_margin() at node_count=scaling_reference_count returns base_subtree_margin."""
        non_mask_node = self._make_non_mask_node()
        margin = _nl._subtree_margin(non_mask_node, 0, node_count=150)
        # With normal_multiplier=1.0 and sqrt(150)/sqrt(150)=1.0, result should equal
        # base_subtree_margin (200).
        self.assertEqual(margin, 200)

    # --- mask input ratio ---

    def test_subtree_margin_mask_slot_is_approx_one_third(self):
        """_subtree_margin() for a mask slot returns approximately 1/3 of non-mask margin."""
        merge_node = self._make_merge2_node()
        # For Merge2, slot 2 is the mask input.
        non_mask_margin = _nl._subtree_margin(merge_node, 0, node_count=150)
        mask_margin = _nl._subtree_margin(merge_node, 2, node_count=150)
        # mask_input_ratio default is 0.333
        expected_mask_margin = int(non_mask_margin * 0.333)
        self.assertEqual(mask_margin, expected_mask_margin)

    def test_subtree_margin_mask_less_than_non_mask(self):
        """_subtree_margin() mask slot value is strictly less than non-mask slot."""
        merge_node = self._make_merge2_node()
        non_mask_margin = _nl._subtree_margin(merge_node, 0, node_count=150)
        mask_margin = _nl._subtree_margin(merge_node, 2, node_count=150)
        self.assertLess(mask_margin, non_mask_margin)

    # --- vertical_gap_between with default prefs ---

    def test_vertical_gap_between_uses_loose_gap_multiplier_default(self):
        """vertical_gap_between() returns int(8.0 * snap_threshold) for non-matching nodes."""
        # Two nodes with different tile colors (both 0 from stub) and different classes
        # will hit the 'same color' branch only if colors truly match. Since both have
        # tile_color=0 and same default color from prefs, make them different classes
        # to avoid the same_toolbar_folder short-circuit. Actually, since our stub
        # returns None for all toolbar lookups, same_toolbar_folder returns True.
        # We need to force the loose branch: use same_tile_color = False by giving
        # different tile colors.
        node_a = _StubNode(node_class="Grade", knobs={"tile_color": _StubKnob(0x00ff0000)})
        node_b = _StubNode(node_class="Blur", knobs={"tile_color": _StubKnob(0x0000ff00)})
        snap_threshold = 8
        gap = _nl.vertical_gap_between(node_a, node_b, snap_threshold)
        self.assertEqual(gap, int(8.0 * snap_threshold))

    # --- vertical_gap_between with overridden prefs ---

    def test_vertical_gap_between_respects_overridden_loose_gap_multiplier(self):
        """vertical_gap_between() uses the overridden loose_gap_multiplier at call time."""
        _node_layout_prefs_module.prefs_singleton.set("loose_gap_multiplier", 8.0)
        node_a = _StubNode(node_class="Grade", knobs={"tile_color": _StubKnob(0x00ff0000)})
        node_b = _StubNode(node_class="Blur", knobs={"tile_color": _StubKnob(0x0000ff00)})
        snap_threshold = 8
        gap = _nl.vertical_gap_between(node_a, node_b, snap_threshold)
        self.assertEqual(gap, int(8.0 * snap_threshold))

    # --- Constant removal verification ---

    def test_subtree_margin_constant_absent_from_source(self):
        """node_layout.py must not contain the string 'SUBTREE_MARGIN'."""
        with open(NODE_LAYOUT_PATH) as source_file:
            source = source_file.read()
        self.assertNotIn(
            "SUBTREE_MARGIN",
            source,
            "SUBTREE_MARGIN still referenced in node_layout.py — missed replacement site",
        )

    def test_mask_input_margin_constant_absent_from_source(self):
        """node_layout.py must not contain the string 'MASK_INPUT_MARGIN'."""
        with open(NODE_LAYOUT_PATH) as source_file:
            source = source_file.read()
        self.assertNotIn(
            "MASK_INPUT_MARGIN",
            source,
            "MASK_INPUT_MARGIN still referenced in node_layout.py — missed replacement site",
        )

    # --- Function signature verification ---

    def test_compute_dims_accepts_node_count(self):
        """compute_dims() signature must include node_count as a parameter."""
        arg_names = _get_arg_names("compute_dims")
        self.assertIn(
            "node_count",
            arg_names,
            f"compute_dims() missing node_count parameter; got: {arg_names}",
        )

    def test_place_subtree_accepts_node_count(self):
        """place_subtree() signature must include node_count as a parameter."""
        arg_names = _get_arg_names("place_subtree")
        self.assertIn(
            "node_count",
            arg_names,
            f"place_subtree() missing node_count parameter; got: {arg_names}",
        )

    def test_subtree_margin_accepts_node_count(self):
        """_subtree_margin() signature must include node_count as a parameter."""
        arg_names = _get_arg_names("_subtree_margin")
        self.assertIn(
            "node_count",
            arg_names,
            f"_subtree_margin() missing node_count parameter; got: {arg_names}",
        )

    def test_node_layout_prefs_imported_in_source(self):
        """node_layout.py must import node_layout_prefs."""
        with open(NODE_LAYOUT_PATH) as source_file:
            source = source_file.read()
        self.assertIn(
            "import node_layout_prefs",
            source,
            "node_layout.py does not import node_layout_prefs",
        )


class TestSchemeMultiplierPipeline(unittest.TestCase):
    """Verify scheme_multiplier parameter threading and scheme entry-point functions."""

    def setUp(self):
        _reset_prefs()

    # --- AST: vertical_gap_between signature ---

    def test_vertical_gap_between_has_scheme_multiplier_param(self):
        """vertical_gap_between() must have 4 parameters including scheme_multiplier."""
        arg_names = _get_arg_names("vertical_gap_between")
        self.assertIn(
            "scheme_multiplier",
            arg_names,
            f"vertical_gap_between() missing scheme_multiplier parameter; got: {arg_names}",
        )

    # --- AST: compute_dims signature ---

    def test_compute_dims_has_scheme_multiplier_param(self):
        """compute_dims() signature must include scheme_multiplier parameter."""
        arg_names = _get_arg_names("compute_dims")
        self.assertIn(
            "scheme_multiplier",
            arg_names,
            f"compute_dims() missing scheme_multiplier parameter; got: {arg_names}",
        )

    # --- Behavioral: compact gap is scaled by scheme_multiplier ---

    def test_vertical_gap_between_compact_scheme(self):
        """vertical_gap_between with scheme_multiplier=0.6 returns int(8.0 * 0.6 * snap)."""
        node_a = _StubNode(node_class="Grade", knobs={"tile_color": _StubKnob(0x00ff0000)})
        node_b = _StubNode(node_class="Blur", knobs={"tile_color": _StubKnob(0x0000ff00)})
        snap_threshold = 8
        gap = _nl.vertical_gap_between(node_a, node_b, snap_threshold, scheme_multiplier=0.6)
        expected = int(8.0 * 0.6 * snap_threshold)
        self.assertEqual(
            gap,
            expected,
            f"Expected compact gap {expected}, got {gap}",
        )

    # --- AST: scheme entry-point functions exist ---

    def test_scheme_entry_point_functions_exist(self):
        """layout_upstream_compact, layout_selected_compact, layout_upstream_loose,
        layout_selected_loose must be defined."""
        with open(NODE_LAYOUT_PATH) as source_file:
            source = source_file.read()
        tree = ast.parse(source)
        defined_functions = {
            ast_node.name
            for ast_node in ast.walk(tree)
            if isinstance(ast_node, ast.FunctionDef)
        }
        for expected_function_name in (
            "layout_upstream_compact",
            "layout_selected_compact",
            "layout_upstream_loose",
            "layout_selected_loose",
        ):
            self.assertIn(
                expected_function_name,
                defined_functions,
                f"Function {expected_function_name!r} not found in node_layout.py",
            )


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


class TestHorizontalOnlyScheme(unittest.TestCase):
    """Verify that scheme_multiplier only affects vertical spacing, not horizontal.

    After the fix, side_margins_h (used for X/W) must always equal normal_multiplier
    regardless of the scheme in use, while side_margins_v (used for Y staircase) reflects
    the compact/loose scheme_multiplier.

    These tests verify the behavioral contract using _subtree_margin() calls directly:
    - Horizontal margin (mode_multiplier=normal_multiplier): unaffected by compact scheme
    - Vertical margin (mode_multiplier=compact_multiplier): smaller than normal
    - horizontal_clearance in layout_selected source must not reference resolved_scheme_multiplier
    - side_margins_h and side_margins_v must appear in both compute_dims and place_subtree
    """

    def setUp(self):
        _node_layout_prefs_module.prefs_singleton._prefs = dict(_node_layout_prefs_module.DEFAULTS)

    def _make_non_mask_node(self):
        return _StubNode(node_class="Grade")

    def test_horizontal_margin_unaffected_by_compact_scheme(self):
        """_horizontal_margin() returns horizontal_subtree_gap (250) regardless of any scheme.

        H-axis is now fully decoupled: _horizontal_margin() reads a direct pref value,
        not a sqrt-scaled formula. The result must equal horizontal_subtree_gap (default 250)
        even when compact_multiplier is set, because _horizontal_margin() ignores multipliers.
        """
        non_mask_node = self._make_non_mask_node()
        expected_gap = _node_layout_prefs_module.prefs_singleton.get("horizontal_subtree_gap")

        horizontal_margin = _nl._horizontal_margin(non_mask_node, 0)

        self.assertEqual(
            horizontal_margin,
            expected_gap,
            f"_horizontal_margin must return horizontal_subtree_gap={expected_gap},"
            f" got {horizontal_margin}",
        )
        self.assertEqual(
            horizontal_margin,
            250,
            f"Default horizontal_subtree_gap must be 250, got {horizontal_margin}",
        )

    def test_vertical_margin_affected_by_compact_scheme(self):
        """When mode_multiplier=compact_multiplier (0.6), margin is smaller than normal."""
        non_mask_node = self._make_non_mask_node()
        normal_margin = _nl._subtree_margin(non_mask_node, 0, node_count=150, mode_multiplier=1.0)
        compact_margin = _nl._subtree_margin(non_mask_node, 0, node_count=150, mode_multiplier=0.6)
        self.assertLess(
            compact_margin,
            normal_margin,
            f"Compact vertical margin ({compact_margin}) must be less than normal"
            f" ({normal_margin})",
        )

    def test_vertical_margin_affected_by_loose_scheme(self):
        """When mode_multiplier=loose_multiplier (1.5), margin is larger than normal."""
        non_mask_node = self._make_non_mask_node()
        normal_margin = _nl._subtree_margin(non_mask_node, 0, node_count=150, mode_multiplier=1.0)
        loose_margin = _nl._subtree_margin(non_mask_node, 0, node_count=150, mode_multiplier=1.5)
        self.assertGreater(
            loose_margin,
            normal_margin,
            f"Loose vertical margin ({loose_margin}) must be greater than normal ({normal_margin})",
        )

    def test_side_margins_h_and_v_appear_in_compute_dims(self):
        """side_margins_h and side_margins_v must appear in compute_dims source."""
        with open(NODE_LAYOUT_PATH) as source_file:
            source = source_file.read()
        tree = ast.parse(source)
        for ast_node in ast.walk(tree):
            if isinstance(ast_node, ast.FunctionDef) and ast_node.name == "compute_dims":
                func_source = ast.get_source_segment(source, ast_node)
                self.assertIn(
                    "side_margins_h",
                    func_source,
                    "side_margins_h not found in compute_dims",
                )
                self.assertIn(
                    "side_margins_v",
                    func_source,
                    "side_margins_v not found in compute_dims",
                )
                return
        self.fail("compute_dims not found in source")

    def test_side_margins_h_and_v_appear_in_place_subtree(self):
        """side_margins_h and side_margins_v must appear in place_subtree source."""
        with open(NODE_LAYOUT_PATH) as source_file:
            source = source_file.read()
        tree = ast.parse(source)
        for ast_node in ast.walk(tree):
            if isinstance(ast_node, ast.FunctionDef) and ast_node.name == "place_subtree":
                func_source = ast.get_source_segment(source, ast_node)
                self.assertIn(
                    "side_margins_h",
                    func_source,
                    "side_margins_h not found in place_subtree",
                )
                self.assertIn(
                    "side_margins_v",
                    func_source,
                    "side_margins_v not found in place_subtree",
                )
                return
        self.fail("place_subtree not found in source")

    def test_horizontal_clearance_does_not_use_resolved_scheme_multiplier(self):
        """horizontal_clearance in layout_selected must not reference resolved_scheme_multiplier
        or base_subtree_margin — it must be a direct get('horizontal_subtree_gap') call."""
        with open(NODE_LAYOUT_PATH) as source_file:
            source = source_file.read()
        tree = ast.parse(source)
        for ast_node in ast.walk(tree):
            if isinstance(ast_node, ast.FunctionDef) and ast_node.name == "layout_selected":
                func_source = ast.get_source_segment(source, ast_node)
                # Find the horizontal_clearance assignment block
                clearance_idx = func_source.find("horizontal_clearance")
                self.assertGreater(
                    clearance_idx,
                    -1,
                    "horizontal_clearance not found in layout_selected",
                )
                # Extract a window around the assignment (the new form is a single line)
                clearance_block_end = func_source.find("\n", clearance_idx + 200)
                if clearance_block_end == -1:
                    clearance_block_end = len(func_source)
                clearance_block = func_source[clearance_idx:clearance_block_end]
                self.assertNotIn(
                    "resolved_scheme_multiplier",
                    clearance_block,
                    "horizontal_clearance block must not reference resolved_scheme_multiplier; "
                    f"block: {clearance_block!r}",
                )
                self.assertNotIn(
                    "base_subtree_margin",
                    clearance_block,
                    "horizontal_clearance block must not reference base_subtree_margin "
                    "(new contract: direct horizontal_subtree_gap read, no sqrt formula); "
                    f"block: {clearance_block!r}",
                )
                return
        self.fail("layout_selected not found in source")


if __name__ == "__main__":
    unittest.main()

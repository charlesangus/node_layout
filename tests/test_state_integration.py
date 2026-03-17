"""
test_state_integration.py — AST structural tests for per-node state integration.

These tests assert that specific structural properties exist in node_layout.py
to verify that Plans 02-04 have wired up the state helpers correctly.

Tests that check future-plan code are intentionally RED until those plans are
implemented.  Do not skip them — they are the acceptance criteria for each plan.
"""

import ast
import pathlib
import unittest

_NL_SOURCE_PATH = pathlib.Path(__file__).parent.parent / 'node_layout.py'


def _read_source():
    return _NL_SOURCE_PATH.read_text()


def _get_function_source(source_text, function_name):
    """Return the source of the named top-level function, or None if not found."""
    tree = ast.parse(source_text)
    for ast_node in ast.walk(tree):
        if isinstance(ast_node, ast.FunctionDef) and ast_node.name == function_name:
            return ast.get_source_segment(source_text, ast_node)
    return None


# ---------------------------------------------------------------------------
# TestStateWriteBackAST — RED until Plan 02 implements write-back
# ---------------------------------------------------------------------------

class TestStateWriteBackAST(unittest.TestCase):
    """Verify that layout functions call write_node_state after place_subtree."""

    def test_state_write_after_place_subtree_in_layout_upstream(self):
        """layout_upstream must call write_node_state after place_subtree (Plan 02)."""
        source = _read_source()
        func_source = _get_function_source(source, 'layout_upstream')
        self.assertIsNotNone(func_source, "layout_upstream function not found in node_layout.py")

        place_pos = func_source.find('place_subtree(')
        write_pos = func_source.find('write_node_state')

        self.assertGreater(place_pos, -1, "place_subtree( not found in layout_upstream")
        self.assertGreater(write_pos, -1, "write_node_state not found in layout_upstream")
        self.assertGreater(
            write_pos, place_pos,
            "write_node_state must appear after place_subtree in layout_upstream"
        )

    def test_state_write_after_place_subtree_in_layout_selected(self):
        """layout_selected must call write_node_state after place_subtree (Plan 02)."""
        source = _read_source()
        func_source = _get_function_source(source, 'layout_selected')
        self.assertIsNotNone(func_source, "layout_selected function not found in node_layout.py")

        place_pos = func_source.find('place_subtree(')
        write_pos = func_source.find('write_node_state')

        self.assertGreater(place_pos, -1, "place_subtree( not found in layout_selected")
        self.assertGreater(write_pos, -1, "write_node_state not found in layout_selected")
        self.assertGreater(
            write_pos, place_pos,
            "write_node_state must appear after place_subtree in layout_selected"
        )


# ---------------------------------------------------------------------------
# TestMemoKeyAST — RED until Plan 03 updates the memoization key
# ---------------------------------------------------------------------------

class TestMemoKeyAST(unittest.TestCase):
    """Verify compute_dims uses a tuple memo key that includes layout_mode."""

    def test_compute_dims_memo_key_is_tuple(self):
        """compute_dims must use (id(node), ...) tuple as memo key (Plan 03)."""
        source = _read_source()
        func_source = _get_function_source(source, 'compute_dims')
        self.assertIsNotNone(func_source, "compute_dims function not found in node_layout.py")

        self.assertIn(
            '(id(node)',
            func_source,
            "compute_dims memo key must be a tuple starting with id(node)"
        )


# ---------------------------------------------------------------------------
# TestSchemeReplayAST — RED until Plan 03 adds per-node scheme replay
# ---------------------------------------------------------------------------

class TestSchemeReplayAST(unittest.TestCase):
    """Verify layout_upstream reads per-node state when scheme is None."""

    def test_layout_upstream_reads_per_node_state_when_scheme_is_none(self):
        """layout_upstream must call read_node_state to replay stored scheme (Plan 03)."""
        source = _read_source()
        func_source = _get_function_source(source, 'layout_upstream')
        self.assertIsNotNone(func_source, "layout_upstream function not found in node_layout.py")

        self.assertIn(
            'read_node_state',
            func_source,
            "layout_upstream must call read_node_state for per-node scheme replay"
        )


# ---------------------------------------------------------------------------
# TestScaleWriteBackAST — RED until Plan 04 adds scale write-back
# ---------------------------------------------------------------------------

class TestScaleWriteBackAST(unittest.TestCase):
    """Verify scale functions write state after scaling nodes."""

    def test_scale_selected_writes_state_after_scaling(self):
        """_scale_selected_nodes must call write_node_state after scaling (Plan 04)."""
        source = _read_source()
        func_source = _get_function_source(source, '_scale_selected_nodes')
        self.assertIsNotNone(
            func_source,
            "_scale_selected_nodes function not found in node_layout.py"
        )

        self.assertIn(
            'write_node_state',
            func_source,
            "_scale_selected_nodes must call write_node_state after scaling"
        )

    def test_scale_upstream_writes_state_after_scaling(self):
        """_scale_upstream_nodes must call write_node_state after scaling (Plan 04)."""
        source = _read_source()
        func_source = _get_function_source(source, '_scale_upstream_nodes')
        self.assertIsNotNone(
            func_source,
            "_scale_upstream_nodes function not found in node_layout.py"
        )

        self.assertIn(
            'write_node_state',
            func_source,
            "_scale_upstream_nodes must call write_node_state after scaling"
        )


# ---------------------------------------------------------------------------
# TestUpstreamAnchorAST — RED until Plan 06 fixes _scale_upstream_nodes() pivot
# ---------------------------------------------------------------------------

class TestUpstreamAnchorAST(unittest.TestCase):
    """Verify _scale_upstream_nodes uses root_node as pivot."""

    def test_scale_upstream_uses_root_node_as_anchor(self):
        """_scale_upstream_nodes must use root_node (the selected node) as anchor so it stays
        fixed."""
        source = _read_source()
        func_source = _get_function_source(source, '_scale_upstream_nodes')
        self.assertIsNotNone(
            func_source,
            "_scale_upstream_nodes function not found in node_layout.py"
        )

        self.assertIn(
            'anchor_node = root_node',
            func_source,
            "_scale_upstream_nodes must set anchor_node = root_node (not max(upstream_nodes, ...))"
        )


# ---------------------------------------------------------------------------
# TestScaleParamsAST — RED until Plan 07 extends compute_dims/place_subtree
# ---------------------------------------------------------------------------

class TestScaleParamsAST(unittest.TestCase):
    """Verify compute_dims and place_subtree accept per-node h_scale/v_scale dicts (Plan 07)."""

    def test_compute_dims_has_per_node_h_scale_param(self):
        """compute_dims must have per_node_h_scale=None as a keyword parameter (Plan 07)."""
        source = _read_source()
        func_source = _get_function_source(source, 'compute_dims')
        self.assertIsNotNone(func_source, "compute_dims function not found in node_layout.py")

        self.assertIn(
            'per_node_h_scale=None',
            func_source,
            "compute_dims must have per_node_h_scale=None keyword parameter"
        )

    def test_place_subtree_has_per_node_h_scale_param(self):
        """place_subtree must have per_node_h_scale=None as a keyword parameter (Plan 07)."""
        source = _read_source()
        func_source = _get_function_source(source, 'place_subtree')
        self.assertIsNotNone(func_source, "place_subtree function not found in node_layout.py")

        self.assertIn(
            'per_node_h_scale=None',
            func_source,
            "place_subtree must have per_node_h_scale=None keyword parameter"
        )

    def test_compute_dims_memo_key_includes_node_h_scale(self):
        """compute_dims memo key must include node_h_scale (per-node scale lookup) (Plan 07)."""
        source = _read_source()
        func_source = _get_function_source(source, 'compute_dims')
        self.assertIsNotNone(func_source, "compute_dims function not found in node_layout.py")

        self.assertIn(
            'node_h_scale',
            func_source[func_source.find('memo['):func_source.find('memo[') + 80]
            if 'memo[' in func_source else func_source,
            "compute_dims memo key must include node_h_scale"
        )


# ---------------------------------------------------------------------------
# TestScaleWiringAST — RED until Plan 07 wires layout_upstream/layout_selected
# ---------------------------------------------------------------------------

class TestScaleWiringAST(unittest.TestCase):
    """Verify layout_upstream and layout_selected read and pass h_scale/v_scale (Plan 07)."""

    def test_layout_upstream_builds_per_node_h_scale(self):
        """layout_upstream must build per_node_h_scale dict (Plan 07)."""
        source = _read_source()
        func_source = _get_function_source(source, 'layout_upstream')
        self.assertIsNotNone(func_source, "layout_upstream function not found in node_layout.py")

        self.assertIn(
            'per_node_h_scale',
            func_source,
            "layout_upstream must build per_node_h_scale dict"
        )

    def test_layout_upstream_builds_per_node_v_scale(self):
        """layout_upstream must build per_node_v_scale dict (Plan 07)."""
        source = _read_source()
        func_source = _get_function_source(source, 'layout_upstream')
        self.assertIsNotNone(func_source, "layout_upstream function not found in node_layout.py")

        self.assertIn(
            'per_node_v_scale',
            func_source,
            "layout_upstream must build per_node_v_scale dict"
        )

    def test_layout_upstream_passes_per_node_h_scale_to_compute_dims(self):
        """layout_upstream must pass per_node_h_scale dict to compute_dims (Plan 07)."""
        source = _read_source()
        func_source = _get_function_source(source, 'layout_upstream')
        self.assertIsNotNone(func_source, "layout_upstream function not found in node_layout.py")

        self.assertIn(
            'per_node_h_scale=per_node_h_scale',
            func_source,
            "layout_upstream must pass per_node_h_scale=per_node_h_scale"
            " to compute_dims/place_subtree"
        )

    def test_layout_upstream_passes_per_node_v_scale_to_compute_dims(self):
        """layout_upstream must pass per_node_v_scale dict to compute_dims (Plan 07)."""
        source = _read_source()
        func_source = _get_function_source(source, 'layout_upstream')
        self.assertIsNotNone(func_source, "layout_upstream function not found in node_layout.py")

        self.assertIn(
            'per_node_v_scale=per_node_v_scale',
            func_source,
            "layout_upstream must pass per_node_v_scale=per_node_v_scale"
            " to compute_dims/place_subtree"
        )

    def test_layout_selected_builds_per_node_h_scale(self):
        """layout_selected must build per_node_h_scale dict (Plan 07)."""
        source = _read_source()
        func_source = _get_function_source(source, 'layout_selected')
        self.assertIsNotNone(func_source, "layout_selected function not found in node_layout.py")

        self.assertIn(
            'per_node_h_scale',
            func_source,
            "layout_selected must build per_node_h_scale dict"
        )

    def test_layout_selected_builds_per_node_v_scale(self):
        """layout_selected must build per_node_v_scale dict (Plan 07)."""
        source = _read_source()
        func_source = _get_function_source(source, 'layout_selected')
        self.assertIsNotNone(func_source, "layout_selected function not found in node_layout.py")

        self.assertIn(
            'per_node_v_scale',
            func_source,
            "layout_selected must build per_node_v_scale dict"
        )


if __name__ == '__main__':
    unittest.main()

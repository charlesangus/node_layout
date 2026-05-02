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


if __name__ == '__main__':
    unittest.main()

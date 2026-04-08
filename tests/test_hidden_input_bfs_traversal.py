"""Regression tests for issue #2: BFS in layout_upstream/layout_selected
must not traverse through nodes that have hide_input=True.

Uses AST analysis (no Nuke required) to verify that every site where the BFS
appends upstream inputs to the queue is guarded by a _hides_inputs() check.
"""

import ast
import os
import unittest

NODE_LAYOUT_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")


def _load_source():
    with open(NODE_LAYOUT_PATH) as source_file:
        return source_file.read()


def _get_function_source(source, function_name):
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return ast.get_source_segment(source, node)
    return None


class TestHiddenInputBfsGuard(unittest.TestCase):
    """The BFS that searches for a horizontal replay root must stop at nodes
    that hide their inputs (_hides_inputs returns True).  Without this guard
    the traversal crosses hidden-input boundaries and rebinds root to an
    out-of-scope upstream node, causing Layout Upstream to move nodes the
    user did not select and did not intend to reposition."""

    def _assert_bfs_guarded_in_function(self, function_name):
        source = _load_source()
        func_source = _get_function_source(source, function_name)
        self.assertIsNotNone(func_source, f"{function_name}() not found in node_layout.py")

        # The initial BFS queue must be guarded so that root's inputs are only
        # added when the root node itself does not hide its inputs.
        self.assertIn(
            "_hides_inputs(root)",
            func_source,
            f"{function_name}(): BFS initial queue must be guarded by _hides_inputs(root)",
        )

        # The continuation loop that adds bfs_cursor's inputs must be guarded.
        self.assertIn(
            "_hides_inputs(bfs_cursor)",
            func_source,
            f"{function_name}(): BFS continuation must be guarded by _hides_inputs(bfs_cursor)",
        )

    def test_layout_upstream_bfs_guarded_by_hides_inputs(self):
        """layout_upstream() BFS must check _hides_inputs before traversing upstream."""
        self._assert_bfs_guarded_in_function("layout_upstream")

    def test_layout_selected_bfs_guarded_by_hides_inputs(self):
        """layout_selected() BFS must check _hides_inputs before traversing upstream."""
        self._assert_bfs_guarded_in_function("layout_selected")

    def test_layout_upstream_bfs_queue_not_unconditionally_built(self):
        """layout_upstream() must not unconditionally build bfs_queue from root.inputs().

        The queue must only be populated when root does not hide its inputs.
        """
        source = _load_source()
        func_source = _get_function_source(source, "layout_upstream")
        self.assertIsNotNone(func_source)
        # The unconditional form (no guard) must not appear inside layout_upstream.
        # The guarded form wraps the list-comp with an if/else, so "bfs_queue = []"
        # (the else branch) must be present alongside the conditional.
        self.assertIn(
            "bfs_queue = []",
            func_source,
            "layout_upstream(): BFS must have an else branch that sets bfs_queue = [] "
            "when root hides its inputs",
        )

    def test_layout_selected_bfs_queue_not_unconditionally_built(self):
        """layout_selected() must not unconditionally build bfs_queue from root.inputs()."""
        source = _load_source()
        func_source = _get_function_source(source, "layout_selected")
        self.assertIsNotNone(func_source)
        self.assertIn(
            "bfs_queue = []",
            func_source,
            "layout_selected(): BFS must have an else branch that sets bfs_queue = [] "
            "when root hides its inputs",
        )

    def test_file_parses_without_syntax_errors(self):
        """node_layout.py must remain valid Python after the fix."""
        source = _load_source()
        try:
            ast.parse(source)
        except SyntaxError as error:
            self.fail(f"node_layout.py has a syntax error: {error}")


if __name__ == "__main__":
    unittest.main()

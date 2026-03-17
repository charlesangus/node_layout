"""Tests for BUG-02: layout_selected() stale node references.

These tests use AST analysis to verify that node_filter is built as a set of
node objects (not id() integers) and that all membership checks use direct
object comparisons. AST analysis is used because the code imports `nuke`
which is only available inside Nuke.
"""

import ast
import os
import unittest

NODE_LAYOUT_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")


def _load_source():
    with open(NODE_LAYOUT_PATH) as source_file:
        return source_file.read()


def _get_function_source(source, function_name):
    """Return the source lines belonging to the named function."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return ast.get_source_segment(source, node)
    return None


class TestNodeFilterObjectMembership(unittest.TestCase):

    def test_node_filter_not_built_with_id_integers(self):
        """node_filter must NOT be built as set(id(n) for n in selected_nodes)."""
        source = _load_source()
        self.assertNotIn(
            "node_filter = set(id(n)",
            source,
            "node_filter must not use id() integers — use node objects directly",
        )

    def test_node_filter_built_as_set_of_objects(self):
        """layout_selected() must build node_filter = set(selected_nodes)."""
        source = _load_source()
        self.assertIn(
            "node_filter = set(selected_nodes)",
            source,
            "node_filter must be built as set(selected_nodes) in layout_selected()",
        )

    def test_passes_node_filter_uses_object_membership(self):
        """_passes_node_filter() must use 'node in node_filter', not 'id(node) in node_filter'."""
        source = _load_source()
        passes_filter_source = _get_function_source(source, "_passes_node_filter")
        self.assertIsNotNone(passes_filter_source, "_passes_node_filter() not found")
        self.assertNotIn(
            "id(node) in node_filter",
            passes_filter_source,
            "_passes_node_filter() must not use id(node) — use 'node in node_filter'",
        )
        self.assertIn(
            "node in node_filter",
            passes_filter_source,
            "_passes_node_filter() must use 'node in node_filter'",
        )

    def test_passes_node_filter_input_uses_object_membership(self):
        """_passes_node_filter() diamond-Dot check must use 'node.input(0) in node_filter'."""
        source = _load_source()
        passes_filter_source = _get_function_source(source, "_passes_node_filter")
        self.assertIsNotNone(passes_filter_source)
        self.assertNotIn(
            "id(node.input(0)) in node_filter",
            passes_filter_source,
            "_passes_node_filter() must not use id(node.input(0)) — use object membership",
        )
        self.assertIn(
            "node.input(0) in node_filter",
            passes_filter_source,
            "_passes_node_filter() must use 'node.input(0) in node_filter' for diamond-Dot check",
        )

    def test_insert_dot_nodes_uses_object_membership_for_node(self):
        """insert_dot_nodes() must use 'node not in node_filter', not id(node)."""
        source = _load_source()
        insert_dot_source = _get_function_source(source, "insert_dot_nodes")
        self.assertIsNotNone(insert_dot_source, "insert_dot_nodes() not found")
        self.assertNotIn(
            "id(node) not in node_filter",
            insert_dot_source,
            "insert_dot_nodes() must not use id(node) — use 'node not in node_filter'",
        )
        self.assertIn(
            "node not in node_filter",
            insert_dot_source,
            "insert_dot_nodes() must use 'node not in node_filter'",
        )

    def test_insert_dot_nodes_uses_object_membership_for_inp(self):
        """insert_dot_nodes() must use 'inp not in node_filter', not id(inp)."""
        source = _load_source()
        insert_dot_source = _get_function_source(source, "insert_dot_nodes")
        self.assertIsNotNone(insert_dot_source)
        self.assertNotIn(
            "id(inp) not in node_filter",
            insert_dot_source,
            "insert_dot_nodes() must not use id(inp) — use 'inp not in node_filter'",
        )
        self.assertIn(
            "inp not in node_filter",
            insert_dot_source,
            "insert_dot_nodes() must use 'inp not in node_filter'",
        )

    def test_collect_subtree_nodes_uses_object_membership(self):
        """collect_subtree_nodes() must use 'node not in node_filter', not id(node)."""
        source = _load_source()
        collect_source = _get_function_source(source, "collect_subtree_nodes")
        self.assertIsNotNone(collect_source, "collect_subtree_nodes() not found")
        self.assertNotIn(
            "id(node) not in node_filter",
            collect_source,
            "collect_subtree_nodes() must not use id(node) — use 'node not in node_filter'",
        )
        self.assertIn(
            "node not in node_filter",
            collect_source,
            "collect_subtree_nodes() must use 'node not in node_filter'",
        )

    def test_final_selected_ids_derived_from_node_filter_objects(self):
        """final_selected_ids must be derived from node_filter via {id(n) for n in node_filter}."""
        source = _load_source()
        self.assertIn(
            "final_selected_ids = {id(n) for n in node_filter}",
            source,
            "final_selected_ids must be derived from node_filter via {id(n) for n in node_filter}",
        )

    def test_file_parses_without_syntax_errors(self):
        """node_layout.py must be valid Python syntax."""
        source = _load_source()
        try:
            ast.parse(source)
        except SyntaxError as error:
            self.fail(f"node_layout.py has a syntax error: {error}")


if __name__ == "__main__":
    unittest.main()

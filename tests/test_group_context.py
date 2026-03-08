"""Tests verifying that node_layout.py wraps Group context correctly.

These are AST-based structural tests — they inspect the source code of
node_layout.py to verify that:
- layout_upstream() captures nuke.thisGroup() before any other Nuke API call
- layout_upstream() wraps its work inside 'with current_group:'
- layout_upstream() calls nuke.Undo.begin() before 'with current_group:'
- layout_selected() captures nuke.thisGroup() before any other Nuke API call
- layout_selected() wraps its work inside 'with current_group:'
- push_nodes_to_make_room() accepts a current_group parameter
- push_nodes_to_make_room() uses current_group.nodes() when current_group provided
- push_nodes_to_make_room() still has nuke.allNodes() as the fallback branch
"""
import ast
import unittest


NODE_LAYOUT_PATH = "/workspace/node_layout.py"


def _get_function_source(source, function_name):
    """Return the source text of function_name using ast.get_source_segment."""
    tree = ast.parse(source)
    for ast_node in ast.walk(tree):
        if isinstance(ast_node, ast.FunctionDef) and ast_node.name == function_name:
            return ast.get_source_segment(source, ast_node)
    return None


class TestGroupContextWrapping(unittest.TestCase):
    """AST tests verifying group context wrapping in entry points and push function."""

    def _read_source(self):
        with open(NODE_LAYOUT_PATH) as source_file:
            return source_file.read()

    def test_layout_upstream_captures_current_group_first(self):
        """layout_upstream() must capture current_group = nuke.thisGroup() before nuke.selectedNode()."""
        source = self._read_source()
        func_source = _get_function_source(source, "layout_upstream")
        self.assertIsNotNone(func_source, "layout_upstream not found in node_layout.py")

        capture_text = "current_group = nuke.thisGroup()"
        selected_node_text = "nuke.selectedNode()"

        self.assertIn(
            capture_text,
            func_source,
            f"layout_upstream() must contain '{capture_text}'",
        )
        capture_index = func_source.index(capture_text)
        selected_node_index = func_source.index(selected_node_text)
        self.assertLess(
            capture_index,
            selected_node_index,
            f"'{capture_text}' (at {capture_index}) must appear before "
            f"'{selected_node_text}' (at {selected_node_index}) in layout_upstream()",
        )

    def test_layout_upstream_uses_with_current_group(self):
        """layout_upstream() body must contain 'with current_group:'."""
        source = self._read_source()
        func_source = _get_function_source(source, "layout_upstream")
        self.assertIsNotNone(func_source, "layout_upstream not found in node_layout.py")

        self.assertIn(
            "with current_group:",
            func_source,
            "layout_upstream() must wrap its work inside 'with current_group:'",
        )

    def test_layout_upstream_undo_begin_before_with(self):
        """In layout_upstream(), nuke.Undo.begin() must appear before 'with current_group:'."""
        source = self._read_source()
        func_source = _get_function_source(source, "layout_upstream")
        self.assertIsNotNone(func_source, "layout_upstream not found in node_layout.py")

        undo_begin_text = "nuke.Undo.begin()"
        with_text = "with current_group:"

        self.assertIn(undo_begin_text, func_source, f"'{undo_begin_text}' not found in layout_upstream()")
        self.assertIn(with_text, func_source, f"'{with_text}' not found in layout_upstream()")

        undo_begin_index = func_source.index(undo_begin_text)
        with_index = func_source.index(with_text)
        self.assertLess(
            undo_begin_index,
            with_index,
            f"'{undo_begin_text}' (at {undo_begin_index}) must appear before "
            f"'{with_text}' (at {with_index}) in layout_upstream()",
        )

    def test_layout_selected_captures_current_group_first(self):
        """layout_selected() must capture current_group = nuke.thisGroup() before nuke.selectedNodes()."""
        source = self._read_source()
        func_source = _get_function_source(source, "layout_selected")
        self.assertIsNotNone(func_source, "layout_selected not found in node_layout.py")

        capture_text = "current_group = nuke.thisGroup()"
        selected_nodes_text = "nuke.selectedNodes()"

        self.assertIn(
            capture_text,
            func_source,
            f"layout_selected() must contain '{capture_text}'",
        )
        capture_index = func_source.index(capture_text)
        selected_nodes_index = func_source.index(selected_nodes_text)
        self.assertLess(
            capture_index,
            selected_nodes_index,
            f"'{capture_text}' (at {capture_index}) must appear before "
            f"'{selected_nodes_text}' (at {selected_nodes_index}) in layout_selected()",
        )

    def test_layout_selected_uses_with_current_group(self):
        """layout_selected() body must contain 'with current_group:'."""
        source = self._read_source()
        func_source = _get_function_source(source, "layout_selected")
        self.assertIsNotNone(func_source, "layout_selected not found in node_layout.py")

        self.assertIn(
            "with current_group:",
            func_source,
            "layout_selected() must wrap its work inside 'with current_group:'",
        )

    def test_push_nodes_has_current_group_param(self):
        """push_nodes_to_make_room() must have 'current_group' as a parameter."""
        source = self._read_source()
        tree = ast.parse(source)
        for ast_node in ast.walk(tree):
            if isinstance(ast_node, ast.FunctionDef) and ast_node.name == "push_nodes_to_make_room":
                arg_names = [arg.arg for arg in ast_node.args.args]
                self.assertIn(
                    "current_group",
                    arg_names,
                    f"push_nodes_to_make_room() must have 'current_group' parameter; got: {arg_names}",
                )
                return
        self.fail("push_nodes_to_make_room not found in node_layout.py")

    def test_push_nodes_uses_group_nodes(self):
        """push_nodes_to_make_room() must use current_group.nodes() for scoped iteration."""
        source = self._read_source()
        func_source = _get_function_source(source, "push_nodes_to_make_room")
        self.assertIsNotNone(func_source, "push_nodes_to_make_room not found in node_layout.py")

        self.assertIn(
            "current_group.nodes()",
            func_source,
            "push_nodes_to_make_room() must call current_group.nodes() to iterate group-scoped nodes",
        )

    def test_push_nodes_nuke_allnodes_as_fallback(self):
        """push_nodes_to_make_room() must retain nuke.allNodes() as the fallback branch."""
        source = self._read_source()
        func_source = _get_function_source(source, "push_nodes_to_make_room")
        self.assertIsNotNone(func_source, "push_nodes_to_make_room not found in node_layout.py")

        self.assertIn(
            "nuke.allNodes()",
            func_source,
            "push_nodes_to_make_room() must keep nuke.allNodes() as fallback when current_group is None",
        )


if __name__ == "__main__":
    unittest.main()

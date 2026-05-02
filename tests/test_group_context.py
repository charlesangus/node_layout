"""AST tests verifying that push_nodes_to_make_room threads current_group correctly.

- push_nodes_to_make_room() accepts a current_group parameter
- push_nodes_to_make_room() uses current_group.nodes() when current_group provided
- push_nodes_to_make_room() still has nuke.allNodes() as the fallback branch
"""
import ast
import os
import unittest

NODE_LAYOUT_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")


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
                    f"push_nodes_to_make_room() must have 'current_group' parameter;"
                    f" got: {arg_names}",
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
            "push_nodes_to_make_room() must call current_group.nodes() to iterate"
            " group-scoped nodes",
        )

    def test_push_nodes_nuke_allnodes_as_fallback(self):
        """push_nodes_to_make_room() must retain nuke.allNodes() as the fallback branch."""
        source = self._read_source()
        func_source = _get_function_source(source, "push_nodes_to_make_room")
        self.assertIsNotNone(func_source, "push_nodes_to_make_room not found in node_layout.py")

        self.assertIn(
            "nuke.allNodes()",
            func_source,
            "push_nodes_to_make_room() must keep nuke.allNodes() as fallback when"
            " current_group is None",
        )


if __name__ == "__main__":
    unittest.main()

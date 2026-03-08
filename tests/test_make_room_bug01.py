"""Tests for BUG-01: make_room() undefined variable risk.

These tests use AST analysis to verify that x_amount and y_amount are
initialized before any conditional branches in make_room(). This approach
is used because the code imports `nuke` which is only available inside Nuke.
"""

import ast
import sys
import unittest


MAKE_ROOM_PATH = "/workspace/make_room.py"


def _get_make_room_function_body():
    with open(MAKE_ROOM_PATH) as source_file:
        source = source_file.read()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "make_room":
            return node.body
    raise RuntimeError("make_room() function not found in make_room.py")


class TestMakeRoomVariableInitialization(unittest.TestCase):

    def test_x_amount_initialized_before_conditionals(self):
        """x_amount must be assigned 0 before any if/elif branch."""
        body = _get_make_room_function_body()
        initialized_names = set()
        for stmt in body:
            if isinstance(stmt, ast.If):
                # Hit the first if-statement; x_amount must already be initialized
                self.assertIn(
                    "x_amount",
                    initialized_names,
                    "x_amount = 0 must appear before the first if-branch in make_room()",
                )
                break
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        initialized_names.add(target.id)

    def test_y_amount_initialized_before_conditionals(self):
        """y_amount must be assigned 0 before any if/elif branch."""
        body = _get_make_room_function_body()
        initialized_names = set()
        for stmt in body:
            if isinstance(stmt, ast.If):
                # Hit the first if-statement; y_amount must already be initialized
                self.assertIn(
                    "y_amount",
                    initialized_names,
                    "y_amount = 0 must appear before the first if-branch in make_room()",
                )
                break
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        initialized_names.add(target.id)

    def test_x_amount_default_is_zero(self):
        """The default initialization value for x_amount must be 0."""
        body = _get_make_room_function_body()
        for stmt in body:
            if isinstance(stmt, ast.If):
                break
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == "x_amount":
                        value = stmt.value
                        self.assertIsInstance(value, ast.Constant)
                        self.assertEqual(
                            value.value,
                            0,
                            "x_amount must be initialized to 0",
                        )

    def test_y_amount_default_is_zero(self):
        """The default initialization value for y_amount must be 0."""
        body = _get_make_room_function_body()
        for stmt in body:
            if isinstance(stmt, ast.If):
                break
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == "y_amount":
                        value = stmt.value
                        self.assertIsInstance(value, ast.Constant)
                        self.assertEqual(
                            value.value,
                            0,
                            "y_amount must be initialized to 0",
                        )

    def test_file_parses_without_syntax_errors(self):
        """make_room.py must be valid Python syntax."""
        with open(MAKE_ROOM_PATH) as source_file:
            source = source_file.read()
        try:
            ast.parse(source)
        except SyntaxError as error:
            self.fail(f"make_room.py has a syntax error: {error}")


if __name__ == "__main__":
    unittest.main()

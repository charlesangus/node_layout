"""AST structural tests verifying Shift+E leader mode wiring in menu.py.

These tests verify menu.py's structure without loading Nuke or PySide6,
making them runnable in CI environments.

Verifies (LEAD-01):
- Layout (Leader Mode) command present with node_layout_leader.arm() callback
- shift+e assigned exactly once (on leader mode, not Layout Upstream)
- Layout Upstream still exists (shortcut removed, command retained)
- No top-level import of node_layout_leader (inline import pattern only)
- Layout (Leader Mode) appears before Layout Upstream in source
"""
import ast
import os
import unittest

MENU_PATH = os.path.join(os.path.dirname(__file__), "..", "menu.py")


def _load_menu_source():
    """Return the source code of menu.py as a string."""
    with open(MENU_PATH, "r") as menu_file:
        return menu_file.read()


def _parse_menu_ast():
    """Return the AST of menu.py."""
    return ast.parse(_load_menu_source())


class TestMenuLeaderWiring(unittest.TestCase):
    """AST tests verifying Shift+E leader mode wiring in menu.py -- LEAD-01."""

    def test_leader_mode_command_present(self):
        """menu.py must contain addCommand with 'Layout (Leader Mode)' string."""
        source = _load_menu_source()
        self.assertIn("Layout (Leader Mode)", source)

    def test_shift_e_assigned_once(self):
        """'shift+e' must appear exactly once in menu.py (on leader mode, not Layout Upstream)."""
        source = _load_menu_source()
        count = source.count("'shift+e'")
        self.assertEqual(count, 1, f"Expected 'shift+e' once, found {count} times")

    def test_leader_mode_callback_is_arm(self):
        """The leader mode command callback must call node_layout_leader.arm()."""
        source = _load_menu_source()
        self.assertIn("import node_layout_leader; node_layout_leader.arm()", source)

    def test_layout_upstream_still_exists(self):
        """'Layout Upstream' command must still be registered (without shortcut)."""
        source = _load_menu_source()
        self.assertIn("'Layout Upstream'", source)

    def test_no_toplevel_leader_import(self):
        """menu.py must NOT have a top-level import of node_layout_leader."""
        tree = _parse_menu_ast()
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotEqual(alias.name, "node_layout_leader",
                        "Top-level 'import node_layout_leader' found -- must use inline import only")
            elif isinstance(node, ast.ImportFrom):
                self.assertNotEqual(getattr(node, 'module', ''), "node_layout_leader",
                    "Top-level 'from node_layout_leader' found -- must use inline import only")

    def test_leader_mode_before_layout_upstream(self):
        """'Layout (Leader Mode)' must appear before 'Layout Upstream' in the source."""
        source = _load_menu_source()
        leader_position = source.index("Layout (Leader Mode)")
        upstream_position = source.index("Layout Upstream")
        self.assertLess(leader_position, upstream_position,
            "'Layout (Leader Mode)' must appear before 'Layout Upstream' in menu.py")


if __name__ == "__main__":
    unittest.main()

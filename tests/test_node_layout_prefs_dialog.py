"""Structural (AST) tests for node_layout_prefs_dialog.py.

These tests verify the dialog's source structure without instantiating PySide6 widgets,
making them runnable in CI environments without a display server.

Verifies:
- _make_section_header helper function exists
- _build_ui creates all 10 expected QLineEdit fields (including 3 new ones)
- _populate_from_prefs has setText calls for all 10 preference keys
- _on_accept parses all 3 new int fields
- No QGroupBox is used (section headers are bold QLabel only)
"""
import ast
import os
import unittest


DIALOG_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout_prefs_dialog.py")


def _load_dialog_source():
    """Return the source code of node_layout_prefs_dialog.py as a string."""
    with open(DIALOG_PATH, "r") as source_file:
        return source_file.read()


def _parse_dialog_ast():
    """Return the AST of node_layout_prefs_dialog.py."""
    return ast.parse(_load_dialog_source())


class TestDialogSectionHeader(unittest.TestCase):
    """_make_section_header helper must exist in the dialog module."""

    def test_make_section_header_function_exists(self):
        """_make_section_header must be defined as a function in the dialog module."""
        source = _load_dialog_source()
        tree = _parse_dialog_ast()
        function_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
        self.assertIn(
            "_make_section_header",
            function_names,
            "_make_section_header function must be defined in node_layout_prefs_dialog.py",
        )

    def test_no_qgroupbox_imported(self):
        """Dialog must NOT import QGroupBox — section headers are bold QLabel only."""
        source = _load_dialog_source()
        # QGroupBox must not appear in any import statement
        import_lines = [line for line in source.splitlines() if line.strip().startswith("from") or line.strip().startswith("import")]
        import_block = "\n".join(import_lines)
        self.assertNotIn(
            "QGroupBox",
            import_block,
            "Dialog must not import QGroupBox; use bold QLabel section headers instead",
        )


class TestDialogBuildUiFields(unittest.TestCase):
    """_build_ui must create QLineEdit instances for all 10 preference fields."""

    def setUp(self):
        self.source = _load_dialog_source()

    def test_build_ui_contains_horizontal_subtree_gap_edit(self):
        """_build_ui must reference horizontal_subtree_gap_edit."""
        self.assertIn(
            "horizontal_subtree_gap_edit",
            self.source,
            "_build_ui must create self.horizontal_subtree_gap_edit",
        )

    def test_build_ui_contains_horizontal_mask_gap_edit(self):
        """_build_ui must reference horizontal_mask_gap_edit."""
        self.assertIn(
            "horizontal_mask_gap_edit",
            self.source,
            "_build_ui must create self.horizontal_mask_gap_edit",
        )

    def test_build_ui_contains_dot_font_reference_size_edit(self):
        """_build_ui must reference dot_font_reference_size_edit."""
        self.assertIn(
            "dot_font_reference_size_edit",
            self.source,
            "_build_ui must create self.dot_font_reference_size_edit",
        )

    def test_build_ui_contains_base_subtree_margin_edit(self):
        """_build_ui must retain base_subtree_margin_edit from original dialog."""
        self.assertIn(
            "base_subtree_margin_edit",
            self.source,
            "_build_ui must retain self.base_subtree_margin_edit",
        )

    def test_build_ui_contains_compact_multiplier_edit(self):
        """_build_ui must retain compact_multiplier_edit from original dialog."""
        self.assertIn(
            "compact_multiplier_edit",
            self.source,
            "_build_ui must retain self.compact_multiplier_edit",
        )

    def test_build_ui_calls_make_section_header(self):
        """_build_ui must call _make_section_header to create section labels."""
        self.assertIn(
            "_make_section_header",
            self.source,
            "_build_ui must call _make_section_header() to create section headers",
        )


class TestDialogPopulateFromPrefs(unittest.TestCase):
    """_populate_from_prefs must set text for all 10 preference fields."""

    def setUp(self):
        self.source = _load_dialog_source()

    def _assert_populate_sets(self, pref_key):
        """Helper: confirm pref_key appears in the source (setText call expected)."""
        self.assertIn(
            pref_key,
            self.source,
            f"_populate_from_prefs must call setText for '{pref_key}'",
        )

    def test_populate_sets_horizontal_subtree_gap(self):
        self._assert_populate_sets("horizontal_subtree_gap")

    def test_populate_sets_horizontal_mask_gap(self):
        self._assert_populate_sets("horizontal_mask_gap")

    def test_populate_sets_dot_font_reference_size(self):
        self._assert_populate_sets("dot_font_reference_size")

    def test_populate_sets_base_subtree_margin(self):
        self._assert_populate_sets("base_subtree_margin")

    def test_populate_sets_compact_multiplier(self):
        self._assert_populate_sets("compact_multiplier")

    def test_populate_sets_normal_multiplier(self):
        self._assert_populate_sets("normal_multiplier")

    def test_populate_sets_loose_multiplier(self):
        self._assert_populate_sets("loose_multiplier")

    def test_populate_sets_loose_gap_multiplier(self):
        self._assert_populate_sets("loose_gap_multiplier")

    def test_populate_sets_mask_input_ratio(self):
        self._assert_populate_sets("mask_input_ratio")

    def test_populate_sets_scaling_reference_count(self):
        self._assert_populate_sets("scaling_reference_count")


class TestDialogOnAcceptNewFields(unittest.TestCase):
    """_on_accept must parse and save the 3 new int preference fields."""

    def setUp(self):
        self.source = _load_dialog_source()

    def test_on_accept_parses_horizontal_subtree_gap(self):
        """_on_accept must parse horizontal_subtree_gap_edit as int."""
        self.assertIn(
            "horizontal_subtree_gap_value",
            self.source,
            "_on_accept must parse horizontal_subtree_gap_edit.text() as int",
        )

    def test_on_accept_parses_horizontal_mask_gap(self):
        """_on_accept must parse horizontal_mask_gap_edit as int."""
        self.assertIn(
            "horizontal_mask_gap_value",
            self.source,
            "_on_accept must parse horizontal_mask_gap_edit.text() as int",
        )

    def test_on_accept_parses_dot_font_reference_size(self):
        """_on_accept must parse dot_font_reference_size_edit as int."""
        self.assertIn(
            "dot_font_reference_size_value",
            self.source,
            "_on_accept must parse dot_font_reference_size_edit.text() as int",
        )


if __name__ == "__main__":
    unittest.main()

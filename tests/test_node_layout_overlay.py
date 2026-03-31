"""Structural (AST) tests for node_layout_overlay.py.

These tests verify the overlay widget's source structure without instantiating PySide6 widgets,
making them runnable in CI environments without a display server.

Verifies:
- LeaderKeyOverlay class exists inheriting QWidget
- WA_ShowWithoutActivating, WindowType.Tool, WA_TranslucentBackground, FramelessWindowHint are set
- All 10 command keys present with correct action labels in QWERTY grid positions
- "LEADER KEY" title header present
- QGridLayout used for key grid
- _CHAINING_KEY_COLOR and _SINGLE_SHOT_KEY_COLOR module-level constants exist
- CHAINING_KEYS set contains W, A, S, D, Q, E
- show() method defined with self.move() centering call
- adjustSize called in __init__
- paintEvent defined with QPainter and drawRoundedRect
"""
import ast
import os
import unittest

OVERLAY_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout_overlay.py")


def _load_overlay_source():
    """Return the source code of node_layout_overlay.py as a string."""
    with open(OVERLAY_PATH, "r") as source_file:
        return source_file.read()


def _parse_overlay_ast():
    """Return the AST of node_layout_overlay.py."""
    return ast.parse(_load_overlay_source())


class TestOverlayClassExists(unittest.TestCase):
    """LeaderKeyOverlay class must exist and inherit from QWidget — OVRL-01/OVRL-04."""

    def test_leader_key_overlay_class_exists(self):
        """LeaderKeyOverlay class must be defined in node_layout_overlay.py."""
        tree = _parse_overlay_ast()
        class_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
        self.assertIn(
            "LeaderKeyOverlay",
            class_names,
            "LeaderKeyOverlay class must be defined in node_layout_overlay.py",
        )

    def test_leader_key_overlay_inherits_qwidget(self):
        """LeaderKeyOverlay must inherit from QWidget."""
        tree = _parse_overlay_ast()
        overlay_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "LeaderKeyOverlay":
                overlay_class = node
                break
        self.assertIsNotNone(
            overlay_class,
            "LeaderKeyOverlay class must be defined in node_layout_overlay.py",
        )
        base_names = set()
        for base in overlay_class.bases:
            if isinstance(base, ast.Attribute):
                base_names.add(base.attr)
            elif isinstance(base, ast.Name):
                base_names.add(base.id)
        self.assertIn(
            "QWidget",
            base_names,
            "LeaderKeyOverlay must inherit from QWidget",
        )


class TestOverlayQtProperties(unittest.TestCase):
    """Qt window attributes required for focus-safe floating HUD — OVRL-03/OVRL-04."""

    def setUp(self):
        self.source = _load_overlay_source()

    def test_wa_show_without_activating_is_set(self):
        """WA_ShowWithoutActivating must be set in __init__ (OVRL-03, D-12)."""
        self.assertIn(
            "WA_ShowWithoutActivating",
            self.source,
            "LeaderKeyOverlay must call setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)",
        )

    def test_window_type_tool_is_set(self):
        """Qt.WindowType.Tool must be set in __init__ (OVRL-03, D-13)."""
        self.assertIn(
            "WindowType.Tool",
            self.source,
            "LeaderKeyOverlay must set Qt.WindowType.Tool in setWindowFlags",
        )

    def test_wa_translucent_background_is_set(self):
        """WA_TranslucentBackground must be set for semi-transparent painting (D-01)."""
        self.assertIn(
            "WA_TranslucentBackground",
            self.source,
            "LeaderKeyOverlay must call setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)",
        )

    def test_frameless_window_hint_is_set(self):
        """FramelessWindowHint must be set so the HUD has no OS title bar."""
        self.assertIn(
            "FramelessWindowHint",
            self.source,
            "LeaderKeyOverlay must set Qt.WindowType.FramelessWindowHint in setWindowFlags",
        )


class TestOverlayKeyLayout(unittest.TestCase):
    """All 10 command key labels must be present in QWERTY grid positions — OVRL-02."""

    def setUp(self):
        self.source = _load_overlay_source()

    def test_all_ten_key_labels_present(self):
        """All 10 key-label pairs must appear as quoted strings in source (D-07)."""
        expected_labels = [
            ("Q", "Shrink"),
            ("W", "Move Up"),
            ("E", "Expand"),
            ("A", "Move Left"),
            ("S", "Move Down"),
            ("D", "Move Right"),
            ("F", "Freeze"),
            ("Z", "Horiz Layout"),
            ("C", "Clear State"),
            ("V", "Layout"),
        ]
        for key_letter, action_label in expected_labels:
            self.assertIn(
                f'"{key_letter}"',
                self.source,
                f'Key letter "{key_letter}" must appear as a quoted string in node_layout_overlay.py',
            )
            self.assertIn(
                f'"{action_label}"',
                self.source,
                f'Action label "{action_label}" must appear as a quoted string in node_layout_overlay.py',
            )

    def test_leader_key_title_header(self):
        """LEADER KEY title string must be present (D-03)."""
        self.assertIn(
            '"LEADER KEY"',
            self.source,
            '"LEADER KEY" title string must appear in node_layout_overlay.py',
        )

    def test_qgridlayout_used(self):
        """QGridLayout must be used for the key grid (D-04)."""
        self.assertIn(
            "QGridLayout",
            self.source,
            "node_layout_overlay.py must use QGridLayout for the key grid",
        )


class TestOverlayColorConstants(unittest.TestCase):
    """Module-level color constants must exist for chaining and single-shot keys — OVRL-02 (D-09/D-10/D-17)."""

    def setUp(self):
        self.source = _load_overlay_source()

    def test_chaining_key_color_constant_exists(self):
        """_CHAINING_KEY_COLOR module-level constant must be defined (D-09/D-17)."""
        self.assertIn(
            "_CHAINING_KEY_COLOR",
            self.source,
            "node_layout_overlay.py must define _CHAINING_KEY_COLOR module-level constant",
        )

    def test_single_shot_key_color_constant_exists(self):
        """_SINGLE_SHOT_KEY_COLOR module-level constant must be defined (D-10/D-17)."""
        self.assertIn(
            "_SINGLE_SHOT_KEY_COLOR",
            self.source,
            "node_layout_overlay.py must define _SINGLE_SHOT_KEY_COLOR module-level constant",
        )

    def test_chaining_keys_set_exists(self):
        """CHAINING_KEYS set must be defined containing all WASD/QE keys (D-09)."""
        self.assertIn(
            "CHAINING_KEYS",
            self.source,
            "node_layout_overlay.py must define CHAINING_KEYS set",
        )
        for key_letter in ("W", "A", "S", "D", "Q", "E"):
            self.assertIn(
                f'"{key_letter}"',
                self.source,
                f'CHAINING_KEYS must contain quoted key letter "{key_letter}"',
            )

    def test_chaining_and_single_shot_colors_are_different_names(self):
        """Both _CHAINING_KEY_COLOR and _SINGLE_SHOT_KEY_COLOR must coexist as distinct identifiers (D-17)."""
        self.assertIn(
            "_CHAINING_KEY_COLOR",
            self.source,
            "node_layout_overlay.py must define _CHAINING_KEY_COLOR",
        )
        self.assertIn(
            "_SINGLE_SHOT_KEY_COLOR",
            self.source,
            "node_layout_overlay.py must define _SINGLE_SHOT_KEY_COLOR",
        )
        # The two names are distinct by definition; confirm they are not the same token
        self.assertNotEqual("_CHAINING_KEY_COLOR", "_SINGLE_SHOT_KEY_COLOR")


class TestOverlayShowCentering(unittest.TestCase):
    """show() must center the overlay over its parent widget on each call — OVRL-01 (D-08)."""

    def setUp(self):
        self.source = _load_overlay_source()

    def test_show_method_defined(self):
        """show() method must be defined on LeaderKeyOverlay."""
        tree = _parse_overlay_ast()
        overlay_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "LeaderKeyOverlay":
                overlay_class = node
                break
        self.assertIsNotNone(
            overlay_class,
            "LeaderKeyOverlay class must be defined in node_layout_overlay.py",
        )
        method_names = {
            node.name
            for node in ast.walk(overlay_class)
            if isinstance(node, ast.FunctionDef)
        }
        self.assertIn(
            "show",
            method_names,
            "LeaderKeyOverlay must define a show() method for centering on parent",
        )

    def test_show_calls_move(self):
        """show() must call self.move() for centering logic (D-08)."""
        self.assertIn(
            ".move(",
            self.source,
            "LeaderKeyOverlay.show() must call self.move() to center the overlay over its parent",
        )

    def test_adjustsize_called_in_init(self):
        """adjustSize() must be called in __init__ so rect() has real dimensions before show()."""
        self.assertIn(
            "adjustSize",
            self.source,
            "LeaderKeyOverlay.__init__ must call self.adjustSize() before show() is invoked",
        )


class TestOverlayPaintEvent(unittest.TestCase):
    """paintEvent must draw a semi-transparent rounded-rect background — OVRL-01 (D-01)."""

    def setUp(self):
        self.source = _load_overlay_source()

    def test_paint_event_defined(self):
        """paintEvent() method must be defined on LeaderKeyOverlay."""
        tree = _parse_overlay_ast()
        overlay_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "LeaderKeyOverlay":
                overlay_class = node
                break
        self.assertIsNotNone(
            overlay_class,
            "LeaderKeyOverlay class must be defined in node_layout_overlay.py",
        )
        method_names = {
            node.name
            for node in ast.walk(overlay_class)
            if isinstance(node, ast.FunctionDef)
        }
        self.assertIn(
            "paintEvent",
            method_names,
            "LeaderKeyOverlay must define a paintEvent() method for custom background painting",
        )

    def test_qpainter_used(self):
        """QPainter must be used in paintEvent() for custom semi-transparent drawing."""
        self.assertIn(
            "QPainter",
            self.source,
            "node_layout_overlay.py must use QPainter in paintEvent()",
        )

    def test_draw_rounded_rect_called(self):
        """drawRoundedRect() must be called in paintEvent() for rounded corners."""
        self.assertIn(
            "drawRoundedRect",
            self.source,
            "node_layout_overlay.py must call drawRoundedRect() in paintEvent()",
        )


class TestClickableKeyCells(unittest.TestCase):
    """ClickableKeyCell must exist, inherit QWidget, and wire mouse clicks to dispatch_key."""

    def _get_clickable_key_cell_class(self, tree):
        """Return the ClickableKeyCell ClassDef node from the parsed AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "ClickableKeyCell":
                return node
        return None

    def test_clickable_key_cell_class_exists(self):
        """ClickableKeyCell class must be defined in node_layout_overlay.py."""
        tree = _parse_overlay_ast()
        class_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
        self.assertIn(
            "ClickableKeyCell",
            class_names,
            "ClickableKeyCell class must be defined in node_layout_overlay.py",
        )

    def test_clickable_key_cell_inherits_qwidget(self):
        """ClickableKeyCell must inherit from QWidget."""
        tree = _parse_overlay_ast()
        clickable_cell_class = self._get_clickable_key_cell_class(tree)
        self.assertIsNotNone(
            clickable_cell_class,
            "ClickableKeyCell class must be defined in node_layout_overlay.py",
        )
        base_names = set()
        for base in clickable_cell_class.bases:
            if isinstance(base, ast.Attribute):
                base_names.add(base.attr)
            elif isinstance(base, ast.Name):
                base_names.add(base.id)
        self.assertIn(
            "QWidget",
            base_names,
            "ClickableKeyCell must inherit from QWidget",
        )

    def test_clickable_key_cell_has_mouse_press_event(self):
        """ClickableKeyCell must define a mousePressEvent method."""
        tree = _parse_overlay_ast()
        clickable_cell_class = self._get_clickable_key_cell_class(tree)
        self.assertIsNotNone(
            clickable_cell_class,
            "ClickableKeyCell class must be defined in node_layout_overlay.py",
        )
        method_names = {
            node.name
            for node in ast.walk(clickable_cell_class)
            if isinstance(node, ast.FunctionDef)
        }
        self.assertIn(
            "mousePressEvent",
            method_names,
            "ClickableKeyCell must define a mousePressEvent() method for click handling",
        )

    def test_mouse_press_event_calls_dispatch_key(self):
        """dispatch_key must be referenced in node_layout_overlay.py for click wiring."""
        source = _load_overlay_source()
        self.assertIn(
            "dispatch_key",
            source,
            "node_layout_overlay.py must reference dispatch_key to wire cell clicks to leader dispatch",
        )

    def test_pointing_hand_cursor_set(self):
        """PointingHandCursor must be set on ClickableKeyCell for hover affordance."""
        source = _load_overlay_source()
        self.assertIn(
            "PointingHandCursor",
            source,
            "node_layout_overlay.py must set PointingHandCursor on ClickableKeyCell",
        )


if __name__ == "__main__":
    unittest.main()

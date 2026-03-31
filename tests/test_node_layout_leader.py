"""Structural (AST) tests for node_layout_leader.py.

These tests verify the event filter's source structure without instantiating PySide6,
making them runnable in CI environments without a display server.

Verifies:
- LeaderKeyFilter class exists and subclasses QObject
- eventFilter method is defined on LeaderKeyFilter
- arm module-level function exists
- _disarm module-level function exists
- Dispatch table covers V, Z, F, C keys
- Auto-repeat guard present (isAutoRepeat)
- Mouse event cancellation present (MouseButtonPress)
- Timer cancellation present (stop)
- installEventFilter and removeEventFilter calls present
"""
import ast
import os
import unittest

LEADER_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout_leader.py")


def _load_leader_source():
    """Return the source code of node_layout_leader.py as a string."""
    with open(LEADER_PATH, "r") as source_file:
        return source_file.read()


def _parse_leader_ast():
    """Return the AST of node_layout_leader.py."""
    return ast.parse(_load_leader_source())


class TestLeaderFilterClassExists(unittest.TestCase):
    """LeaderKeyFilter class must exist and inherit from QObject — LEAD-02/LEAD-03 infrastructure."""

    def test_leader_key_filter_class_exists(self):
        """LeaderKeyFilter class must be defined in node_layout_leader.py."""
        tree = _parse_leader_ast()
        class_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
        self.assertIn(
            "LeaderKeyFilter",
            class_names,
            "LeaderKeyFilter class must be defined in node_layout_leader.py",
        )

    def test_leader_key_filter_inherits_qobject(self):
        """LeaderKeyFilter must inherit from QObject."""
        tree = _parse_leader_ast()
        leader_filter_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "LeaderKeyFilter":
                leader_filter_class = node
                break
        self.assertIsNotNone(
            leader_filter_class,
            "LeaderKeyFilter class must be defined in node_layout_leader.py",
        )
        base_names = set()
        for base in leader_filter_class.bases:
            if isinstance(base, ast.Attribute):
                base_names.add(base.attr)
            elif isinstance(base, ast.Name):
                base_names.add(base.id)
        self.assertIn(
            "QObject",
            base_names,
            "LeaderKeyFilter must inherit from QObject",
        )

    def test_event_filter_method_defined(self):
        """eventFilter method must be defined on LeaderKeyFilter."""
        tree = _parse_leader_ast()
        leader_filter_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "LeaderKeyFilter":
                leader_filter_class = node
                break
        self.assertIsNotNone(
            leader_filter_class,
            "LeaderKeyFilter class must be defined in node_layout_leader.py",
        )
        method_names = {
            node.name
            for node in ast.walk(leader_filter_class)
            if isinstance(node, ast.FunctionDef)
        }
        self.assertIn(
            "eventFilter",
            method_names,
            "LeaderKeyFilter must define an eventFilter() method",
        )


class TestModuleFunctionsExist(unittest.TestCase):
    """arm and _disarm module-level functions must exist."""

    def test_arm_function_exists(self):
        """arm() must be defined as a top-level module function."""
        tree = _parse_leader_ast()
        top_level_function_names = {
            node.name
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
        }
        self.assertIn(
            "arm",
            top_level_function_names,
            "arm() must be defined as a top-level function in node_layout_leader.py",
        )

    def test_disarm_function_exists(self):
        """_disarm() must be defined as a top-level module function."""
        tree = _parse_leader_ast()
        top_level_function_names = {
            node.name
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
        }
        self.assertIn(
            "_disarm",
            top_level_function_names,
            "_disarm() must be defined as a top-level function in node_layout_leader.py",
        )


class TestDispatchTableKeys(unittest.TestCase):
    """Dispatch table must cover all four leader key commands — DISP-01 through DISP-04."""

    def setUp(self):
        self.source = _load_leader_source()

    def test_dispatch_key_v_present(self):
        """Key_V must be referenced in source for layout command."""
        self.assertIn(
            "Key_V",
            self.source,
            "Dispatch table must reference Qt.Key.Key_V for layout command (DISP-01)",
        )

    def test_dispatch_key_z_present(self):
        """Key_Z must be referenced in source for horizontal layout."""
        self.assertIn(
            "Key_Z",
            self.source,
            "Dispatch table must reference Qt.Key.Key_Z for horizontal layout (DISP-02)",
        )

    def test_dispatch_key_f_present(self):
        """Key_F must be referenced in source for freeze toggle."""
        self.assertIn(
            "Key_F",
            self.source,
            "Dispatch table must reference Qt.Key.Key_F for freeze toggle (DISP-03)",
        )

    def test_dispatch_key_c_present(self):
        """Key_C must be referenced in source for clear freeze."""
        self.assertIn(
            "Key_C",
            self.source,
            "Dispatch table must reference Qt.Key.Key_C for clear freeze (DISP-04)",
        )


class TestAutoRepeatGuard(unittest.TestCase):
    """eventFilter must guard against OS key-hold auto-repeat — D-16."""

    def test_is_auto_repeat_check_present(self):
        """isAutoRepeat() must be checked in eventFilter to guard against OS key-hold."""
        source = _load_leader_source()
        self.assertIn(
            "isAutoRepeat",
            source,
            "eventFilter must check isAutoRepeat() to guard against OS key-hold (D-16)",
        )


class TestMouseCancellation(unittest.TestCase):
    """eventFilter must cancel the leader sequence on mouse button press — LEAD-03."""

    def test_mouse_button_press_check_present(self):
        """MouseButtonPress must be checked to cancel leader mode on mouse click."""
        source = _load_leader_source()
        self.assertIn(
            "MouseButtonPress",
            source,
            "eventFilter must check QEvent.Type.MouseButtonPress for mouse cancellation (LEAD-03)",
        )


class TestTimerCancellation(unittest.TestCase):
    """_disarm must cancel any pending overlay display timer — D-07."""

    def test_timer_stop_present(self):
        """timer.stop() must be called in _disarm to cancel pending overlay display."""
        source = _load_leader_source()
        self.assertIn(
            ".stop()",
            source,
            "_disarm must call timer.stop() to cancel pending overlay display (D-07)",
        )


class TestFilterLifecycle(unittest.TestCase):
    """arm() and _disarm() must install and remove the event filter on QApplication."""

    def test_install_event_filter_present(self):
        """installEventFilter must be called in arm() to register the filter."""
        source = _load_leader_source()
        self.assertIn(
            "installEventFilter",
            source,
            "arm() must call installEventFilter to register the filter on QApplication",
        )

    def test_remove_event_filter_present(self):
        """removeEventFilter must be called in _disarm() to deregister the filter."""
        source = _load_leader_source()
        self.assertIn(
            "removeEventFilter",
            source,
            "_disarm() must call removeEventFilter to deregister the filter",
        )


class TestChainingDispatchTableKeys(unittest.TestCase):
    """Chaining dispatch table must cover W/A/S/D/Q/E keys -- DISP-05/DISP-06/DISP-07."""

    def setUp(self):
        self.source = _load_leader_source()

    def test_dispatch_key_w_present(self):
        """Key_W must be referenced in source for move up command."""
        self.assertIn("Key_W", self.source,
            "Chaining dispatch table must reference Qt.Key.Key_W for move up (DISP-05)")

    def test_dispatch_key_a_present(self):
        """Key_A must be referenced in source for move left command."""
        self.assertIn("Key_A", self.source,
            "Chaining dispatch table must reference Qt.Key.Key_A for move left (DISP-05)")

    def test_dispatch_key_s_present(self):
        """Key_S must be referenced in source for move down command."""
        self.assertIn("Key_S", self.source,
            "Chaining dispatch table must reference Qt.Key.Key_S for move down (DISP-05)")

    def test_dispatch_key_d_present(self):
        """Key_D must be referenced in source for move right command."""
        self.assertIn("Key_D", self.source,
            "Chaining dispatch table must reference Qt.Key.Key_D for move right (DISP-05)")

    def test_dispatch_key_q_present(self):
        """Key_Q must be referenced in source for shrink command."""
        self.assertIn("Key_Q", self.source,
            "Chaining dispatch table must reference Qt.Key.Key_Q for shrink (DISP-06)")

    def test_dispatch_key_e_present(self):
        """Key_E must be referenced in source for expand command."""
        self.assertIn("Key_E", self.source,
            "Chaining dispatch table must reference Qt.Key.Key_E for expand (DISP-07)")


class TestChainingDispatchHelpers(unittest.TestCase):
    """All six chaining dispatch helper functions must be top-level in the module."""

    def setUp(self):
        tree = _parse_leader_ast()
        self.top_level_function_names = {
            node.name for node in tree.body if isinstance(node, ast.FunctionDef)
        }

    def test_dispatch_move_up_exists(self):
        """_dispatch_move_up must be a top-level function."""
        self.assertIn("_dispatch_move_up", self.top_level_function_names)

    def test_dispatch_move_down_exists(self):
        """_dispatch_move_down must be a top-level function."""
        self.assertIn("_dispatch_move_down", self.top_level_function_names)

    def test_dispatch_move_left_exists(self):
        """_dispatch_move_left must be a top-level function."""
        self.assertIn("_dispatch_move_left", self.top_level_function_names)

    def test_dispatch_move_right_exists(self):
        """_dispatch_move_right must be a top-level function."""
        self.assertIn("_dispatch_move_right", self.top_level_function_names)

    def test_dispatch_shrink_exists(self):
        """_dispatch_shrink must be a top-level function."""
        self.assertIn("_dispatch_shrink", self.top_level_function_names)

    def test_dispatch_expand_exists(self):
        """_dispatch_expand must be a top-level function."""
        self.assertIn("_dispatch_expand", self.top_level_function_names)


class TestChainingDispatchTable(unittest.TestCase):
    """_CHAINING_DISPATCH_TABLE must be a module-level dict assignment."""

    def test_chaining_dispatch_table_exists(self):
        """_CHAINING_DISPATCH_TABLE must be assigned at module level."""
        source = _load_leader_source()
        self.assertIn("_CHAINING_DISPATCH_TABLE", source,
            "_CHAINING_DISPATCH_TABLE must be defined in node_layout_leader.py (D-07)")


if __name__ == "__main__":
    unittest.main()

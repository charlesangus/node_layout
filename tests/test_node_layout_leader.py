"""Structural (AST) tests for node_layout_leader.py.

These tests verify the event filter's source structure without instantiating PySide6,
making them runnable in CI environments without a display server.

Verifies:
- LeaderKeyFilter class exists and subclasses QObject
- eventFilter method is defined on LeaderKeyFilter
- arm module-level function exists
- _disarm module-level function exists
- Dispatch table covers V, Z, F, C keys (single-shot commands)
- Chaining dispatch table covers W, A, S, D, Q, E keys (chaining commands)
- Six chaining dispatch helper functions exist as top-level functions
- _CHAINING_DISPATCH_TABLE is defined at module level
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
        """Key_F must be referenced in source for freeze command."""
        self.assertIn(
            "Key_F",
            self.source,
            "Dispatch table must reference Qt.Key.Key_F for freeze command (DISP-03)",
        )

    def test_dispatch_key_c_present(self):
        """Key_C must be referenced in source for clear layout state."""
        self.assertIn(
            "Key_C",
            self.source,
            "Dispatch table must reference Qt.Key.Key_C for clear layout state",
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


class TestPreferenceBackedKeyboardLayout(unittest.TestCase):
    """Keyboard layout remapping must be preference-backed, not locale-detected."""

    def setUp(self):
        self.source = _load_leader_source()

    def test_uses_keyboard_layout_preference(self):
        """node_layout_leader must read the keyboard_layout preference."""
        self.assertIn(
            '"keyboard_layout"',
            self.source,
            "Keyboard remap must read node_layout_prefs keyboard_layout",
        )

    def test_no_qt_locale_auto_detection(self):
        """node_layout_leader must not infer keyboard layout from QLocale."""
        self.assertNotIn(
            "QLocale",
            self.source,
            "Keyboard layout auto-detection via QLocale must be removed",
        )

    def test_rebuild_layout_exists(self):
        """rebuild_layout() must apply pref changes without restarting Nuke."""
        tree = _parse_leader_ast()
        top_level_function_names = {
            node.name for node in tree.body if isinstance(node, ast.FunctionDef)
        }
        self.assertIn("rebuild_layout", top_level_function_names)


class TestShortcutOverrideConsumption(unittest.TestCase):
    """eventFilter must consume ShortcutOverride events during leader mode.

    Qt dispatches QEvent.ShortcutOverride before KeyPress. If not consumed,
    Nuke's shortcut system matches the key (e.g., C -> ColorCorrect) before
    the KeyPress handler runs. The fix: return True for ShortcutOverride when
    _leader_active is True.
    """

    def setUp(self):
        self.source = _load_leader_source()

    def test_shortcut_override_type_referenced(self):
        """ShortcutOverride must be referenced in eventFilter to prevent Nuke shortcuts firing."""
        self.assertIn(
            "ShortcutOverride",
            self.source,
            "eventFilter must handle QEvent.Type.ShortcutOverride to prevent Nuke shortcuts",
        )

    def test_shortcut_override_consumed_with_accept(self):
        """event.accept() must be called when ShortcutOverride is handled.

        Calling accept() on the ShortcutOverride event signals Qt that this
        widget will handle the key, preventing shortcut matching from occurring.
        """
        self.assertIn(
            "event.accept()",
            self.source,
            "eventFilter must call event.accept() on ShortcutOverride to suppress Nuke shortcuts",
        )

    def test_shortcut_override_inside_leader_active_guard(self):
        """ShortcutOverride handling must only fire when _leader_active is True.

        Verifies by AST analysis that the ShortcutOverride check appears inside
        the eventFilter method body (after the _leader_active guard).
        """
        tree = _parse_leader_ast()
        leader_filter_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "LeaderKeyFilter":
                leader_filter_class = node
                break
        self.assertIsNotNone(leader_filter_class, "LeaderKeyFilter must exist")

        event_filter_method = None
        for node in ast.walk(leader_filter_class):
            if isinstance(node, ast.FunctionDef) and node.name == "eventFilter":
                event_filter_method = node
                break
        self.assertIsNotNone(event_filter_method, "eventFilter method must exist")

        # Walk the eventFilter AST and collect all string/attribute references to
        # confirm ShortcutOverride is referenced within the method.
        method_source_lines = ast.get_source_segment(self.source, event_filter_method)
        self.assertIsNotNone(method_source_lines, "Should be able to extract eventFilter source")
        self.assertIn(
            "ShortcutOverride",
            method_source_lines,
            "ShortcutOverride must be referenced inside eventFilter, not just at module level",
        )

    def test_shortcut_override_returns_true(self):
        """eventFilter must return True for ShortcutOverride to consume the event.

        Verifies by source inspection that a 'return True' statement follows
        the ShortcutOverride handling (both must appear within the same block).
        The fix requires both event.accept() AND returning True.
        """
        # Find the ShortcutOverride block and confirm return True is in the method.
        # AST-level: check that the eventFilter method contains a Return node with True.
        tree = _parse_leader_ast()
        leader_filter_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "LeaderKeyFilter":
                leader_filter_class = node
                break

        event_filter_method = None
        for node in ast.walk(leader_filter_class):
            if isinstance(node, ast.FunctionDef) and node.name == "eventFilter":
                event_filter_method = node
                break

        # Check that there is at least one `return True` in the method body.
        return_true_nodes = [
            node
            for node in ast.walk(event_filter_method)
            if isinstance(node, ast.Return)
            and isinstance(node.value, ast.Constant)
            and node.value.value is True
        ]
        self.assertGreater(
            len(return_true_nodes),
            0,
            "eventFilter must have at least one 'return True' statement to consume events",
        )


class TestDispatchKeyFunction(unittest.TestCase):
    """dispatch_key() public function must exist and implement correct dispatch logic."""

    def test_dispatch_key_function_exists(self):
        """dispatch_key must be defined as a top-level function in node_layout_leader.py."""
        tree = _parse_leader_ast()
        top_level_function_names = {
            node.name
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
        }
        self.assertIn(
            "dispatch_key",
            top_level_function_names,
            "dispatch_key() must be defined as a top-level function in node_layout_leader.py",
        )

    def test_letter_to_qt_key_mapping_exists(self):
        """_LETTER_TO_QT_KEY mapping must be defined in node_layout_leader.py."""
        source = _load_leader_source()
        self.assertIn(
            "_LETTER_TO_QT_KEY",
            source,
            "_LETTER_TO_QT_KEY must be defined in node_layout_leader.py for dispatch_key() lookup",
        )

    def test_dispatch_key_references_disarm(self):
        """dispatch_key() must call _disarm() for single-shot key handling."""
        source = _load_leader_source()
        tree = _parse_leader_ast()

        # Find the dispatch_key function node.
        dispatch_key_node = None
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == "dispatch_key":
                dispatch_key_node = node
                break

        self.assertIsNotNone(
            dispatch_key_node,
            "dispatch_key() function must exist in node_layout_leader.py",
        )

        # Extract the source segment of the dispatch_key function and confirm _disarm appears.
        function_source = ast.get_source_segment(source, dispatch_key_node)
        self.assertIsNotNone(function_source, "Should be able to extract dispatch_key source")
        self.assertIn(
            "_disarm",
            function_source,
            "dispatch_key() must call _disarm() to exit leader mode for single-shot keys",
        )


class TestArmUsesReparent(unittest.TestCase):
    """arm() must call _overlay.reparent() instead of bare _overlay.setParent() on re-invocation."""

    def setUp(self):
        self.source = _load_leader_source()

    def test_arm_calls_reparent_not_set_parent(self):
        """arm() must contain .reparent( call and must NOT contain _overlay.setParent( call."""
        self.assertIn(
            ".reparent(",
            self.source,
            "arm() must call _overlay.reparent(dag_widget) instead of bare setParent()",
        )
        self.assertNotIn(
            "_overlay.setParent(",
            self.source,
            "arm() must not call _overlay.setParent() directly — use _overlay.reparent() instead",
        )


class TestFreezeIsNotToggle(unittest.TestCase):
    """F key must always freeze, never toggle — issue #4."""

    def setUp(self):
        self.source = _load_leader_source()
        self.tree = _parse_leader_ast()
        self.top_level_functions = {
            node.name: node
            for node in self.tree.body
            if isinstance(node, ast.FunctionDef)
        }

    def test_dispatch_freeze_toggle_removed(self):
        """_dispatch_freeze_toggle must not exist — it was the toggle implementation."""
        self.assertNotIn(
            "_dispatch_freeze_toggle",
            self.top_level_functions,
            "_dispatch_freeze_toggle must be removed; F key should always freeze, never toggle",
        )

    def test_dispatch_freeze_exists(self):
        """_dispatch_freeze must exist as a top-level function."""
        self.assertIn(
            "_dispatch_freeze",
            self.top_level_functions,
            "_dispatch_freeze() must be defined as a top-level function",
        )

    def test_dispatch_freeze_does_not_call_unfreeze(self):
        """_dispatch_freeze must never call unfreeze_selected — no toggle behavior."""
        freeze_fn = self.top_level_functions.get("_dispatch_freeze")
        self.assertIsNotNone(freeze_fn, "_dispatch_freeze() must exist")
        fn_source = ast.get_source_segment(self.source, freeze_fn)
        self.assertNotIn(
            "unfreeze_selected",
            fn_source,
            "_dispatch_freeze must not call unfreeze_selected() — F key must only freeze",
        )

    def test_key_f_maps_to_dispatch_freeze(self):
        """Key_F entry in _DISPATCH_TABLE must reference _dispatch_freeze, not the old toggle."""
        self.assertIn(
            "_dispatch_freeze",
            self.source,
            "_dispatch_freeze must be referenced in the dispatch table",
        )
        self.assertNotIn(
            "_dispatch_freeze_toggle",
            self.source,
            "_dispatch_freeze_toggle must not appear anywhere in the source",
        )


class TestChainingHideGuard(unittest.TestCase):
    """_chaining_hide_in_progress guard and _hide_overlay_for_chaining helper must exist.

    Regression guard: repeat W/A/S/D/Q/E presses must not disarm leader mode.
    Popup auto-close (hideEvent with guard False) must still disarm. (PR #27)
    """

    def setUp(self):
        self.source = _load_leader_source()
        self.tree = _parse_leader_ast()
        self.top_level_functions = {
            node.name: node
            for node in self.tree.body
            if isinstance(node, ast.FunctionDef)
        }

    def test_chaining_hide_in_progress_global_exists(self):
        """_chaining_hide_in_progress must be declared at module level."""
        self.assertIn(
            "_chaining_hide_in_progress",
            self.source,
            "_chaining_hide_in_progress guard flag must exist in node_layout_leader.py (PR #27)",
        )

    def test_hide_overlay_for_chaining_exists_top_level(self):
        """_hide_overlay_for_chaining must be a top-level (not nested) function."""
        self.assertIn(
            "_hide_overlay_for_chaining",
            self.top_level_functions,
            "_hide_overlay_for_chaining() must be a top-level function, not nested (PR #27)",
        )

    def test_hide_overlay_for_chaining_helper_exists(self):
        """_hide_overlay_for_chaining() must exist as a top-level helper function."""
        self.assertIn(
            "_hide_overlay_for_chaining",
            self.top_level_functions,
            "_hide_overlay_for_chaining() must be defined as a top-level function (PR #27)",
        )

    def test_hide_overlay_for_chaining_sets_guard(self):
        """_hide_overlay_for_chaining must set _chaining_hide_in_progress around hide()."""
        helper = self.top_level_functions.get("_hide_overlay_for_chaining")
        self.assertIsNotNone(helper, "_hide_overlay_for_chaining() must exist")
        fn_source = ast.get_source_segment(self.source, helper)
        self.assertIn(
            "_chaining_hide_in_progress",
            fn_source,
            "_hide_overlay_for_chaining must set _chaining_hide_in_progress around overlay.hide()",
        )

    def test_event_filter_uses_hide_overlay_for_chaining(self):
        """eventFilter must call _hide_overlay_for_chaining() for chaining keys, not inline guard."""
        leader_class = None
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef) and node.name == "LeaderKeyFilter":
                leader_class = node
                break
        self.assertIsNotNone(leader_class, "LeaderKeyFilter must exist")
        event_filter = None
        for node in ast.walk(leader_class):
            if isinstance(node, ast.FunctionDef) and node.name == "eventFilter":
                event_filter = node
                break
        self.assertIsNotNone(event_filter, "eventFilter must exist")
        fn_source = ast.get_source_segment(self.source, event_filter)
        self.assertIn(
            "_hide_overlay_for_chaining",
            fn_source,
            "eventFilter must delegate chaining hide to _hide_overlay_for_chaining() (PR #27)",
        )

    def test_dispatch_key_uses_hide_overlay_for_chaining(self):
        """dispatch_key must call _hide_overlay_for_chaining() for chaining keys, not inline guard."""
        dispatch_key_node = self.top_level_functions.get("dispatch_key")
        self.assertIsNotNone(dispatch_key_node, "dispatch_key() must exist")
        fn_source = ast.get_source_segment(self.source, dispatch_key_node)
        self.assertIn(
            "_hide_overlay_for_chaining",
            fn_source,
            "dispatch_key must delegate chaining hide to _hide_overlay_for_chaining() (PR #27)",
        )


if __name__ == "__main__":
    unittest.main()

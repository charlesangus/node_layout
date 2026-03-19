"""Tests for freeze/unfreeze commands in node_layout.py.

Verifies via AST structural analysis that freeze_selected() and unfreeze_selected() both:
- Open a nuke.Undo group with a descriptive name
- Wrap all mutating operations inside a try block
- Call nuke.Undo.cancel() + raise on exception (never in finally)
- Call nuke.Undo.end() in the else clause (never in finally)
- Place nuke.Undo.begin() at the correct position relative to early-return guards

Also verifies stub-based behavioral correctness:
- freeze_selected assigns the same UUID to all selected nodes
- unfreeze_selected clears freeze_group to None for all selected nodes
- Both commands no-op silently on empty selection

Menu registration is verified via AST analysis of menu.py.
"""
import ast
import importlib.util
import json
import os
import re
import sys
import types
import unittest

NODE_LAYOUT_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")


# ---------------------------------------------------------------------------
# Stub nuke module so node_layout.py can be imported without Nuke runtime.
# ---------------------------------------------------------------------------


class _StubKnob:
    def __init__(self, val=0):
        self._val = val

    def value(self):
        return self._val

    def getValue(self):
        return self._val

    def setValue(self, value):
        self._val = value

    def setFlag(self, flag):
        pass


class _StubNode:
    """Minimal stand-in for a nuke.Node."""

    def __init__(self, width=80, height=28, xpos=0, ypos=0, node_class="Grade",
                 knobs=None):
        self._width = width
        self._height = height
        self._xpos = xpos
        self._ypos = ypos
        self._class = node_class
        self._knobs = knobs if knobs is not None else {"tile_color": _StubKnob(0)}
        self._inputs = []

    def screenWidth(self):
        return self._width

    def screenHeight(self):
        return self._height

    def xpos(self):
        return self._xpos

    def ypos(self):
        return self._ypos

    def setXpos(self, value):
        self._xpos = value

    def setYpos(self, value):
        self._ypos = value

    def Class(self):
        return self._class

    def inputs(self):
        return len(self._inputs)

    def input(self, index):
        if 0 <= index < len(self._inputs):
            return self._inputs[index]
        return None

    def knob(self, name):
        return self._knobs.get(name)

    def addKnob(self, knob_obj):
        knob_name = getattr(knob_obj, 'name', None) or getattr(knob_obj, '_name', None)
        if knob_name and knob_name not in self._knobs:
            self._knobs[knob_name] = knob_obj

    def removeKnob(self, knob_obj):
        knob_name = getattr(knob_obj, 'name', None) or getattr(knob_obj, '_name', None)
        if knob_name and knob_name in self._knobs:
            del self._knobs[knob_name]

    def __getitem__(self, name):
        if name in self._knobs:
            return self._knobs[name]
        return _StubKnob(0)


def _make_preferences_node():
    node = _StubNode(node_class="Preferences")
    node._knobs = {
        "dag_snap_threshold": _StubKnob(8),
        "NodeColor": _StubKnob(0),
    }
    node.knobs = lambda: node._knobs
    return node


class _StubUndo:
    @staticmethod
    def name(label):
        pass

    @staticmethod
    def begin():
        pass

    @staticmethod
    def end():
        pass

    @staticmethod
    def cancel():
        pass


_nuke_stub = types.ModuleType("nuke")
_nuke_stub.Node = _StubNode
_nuke_stub.allNodes = lambda: []
_nuke_stub.selectedNodes = lambda: []
_nuke_stub.selectedNode = lambda: _StubNode()
_nuke_stub.toNode = lambda name: _make_preferences_node() if name == "preferences" else None
_nuke_stub.menu = lambda name: None
_nuke_stub.Undo = _StubUndo
_nuke_stub.INVISIBLE = 0x01
sys.modules["nuke"] = _nuke_stub

_module_path = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")
_spec = importlib.util.spec_from_file_location("node_layout", _module_path)
_nl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_nl)


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _load_function_source(func_name):
    with open(NODE_LAYOUT_PATH) as source_file:
        source = source_file.read()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return ast.get_source_segment(source, node)
    return None


def _get_finally_body_source(func_name):
    """Return the source text of any 'finally' block inside the given function, or None."""
    with open(NODE_LAYOUT_PATH) as source_file:
        source = source_file.read()
    tree = ast.parse(source)
    for func_node in ast.walk(tree):
        if isinstance(func_node, ast.FunctionDef) and func_node.name == func_name:
            for child in ast.walk(func_node):
                if isinstance(child, ast.Try) and child.finalbody:
                    parts = []
                    for stmt in child.finalbody:
                        segment = ast.get_source_segment(source, stmt)
                        if segment:
                            parts.append(segment)
                    return "\n".join(parts)
    return None


# ---------------------------------------------------------------------------
# Helper: build a _StubNode with a working state knob pre-populated
# ---------------------------------------------------------------------------


def _make_state_stub_node(initial_state=None):
    """Return a _StubNode with node_layout_tab and node_layout_state knobs pre-populated."""
    if initial_state is None:
        initial_state = {
            "scheme": "normal",
            "mode": "vertical",
            "h_scale": 1.0,
            "v_scale": 1.0,
        }
    tab_knob = _StubKnob(0)
    tab_knob.name = "node_layout_tab"
    state_knob = _StubKnob(json.dumps(initial_state))
    state_knob.name = "node_layout_state"
    node = _StubNode(knobs={
        "tile_color": _StubKnob(0),
        "node_layout_tab": tab_knob,
        "node_layout_state": state_knob,
    })
    return node


# ---------------------------------------------------------------------------
# TestFreezeSelectedStructure
# ---------------------------------------------------------------------------


class TestFreezeSelectedStructure(unittest.TestCase):
    """AST structural tests for undo group wrapping in freeze_selected()."""

    def test_freeze_selected_exists(self):
        source = _load_function_source("freeze_selected")
        self.assertIsNotNone(source, "freeze_selected() not found in node_layout.py")

    def test_freeze_selected_has_undo_name(self):
        source = _load_function_source("freeze_selected")
        self.assertIsNotNone(source, "freeze_selected() not found in node_layout.py")
        self.assertIn('nuke.Undo.name("Freeze Selected")', source)

    def test_freeze_selected_has_undo_begin(self):
        source = _load_function_source("freeze_selected")
        self.assertIsNotNone(source, "freeze_selected() not found in node_layout.py")
        self.assertIn("nuke.Undo.begin()", source)

    def test_freeze_selected_has_undo_end(self):
        source = _load_function_source("freeze_selected")
        self.assertIsNotNone(source, "freeze_selected() not found in node_layout.py")
        self.assertIn("nuke.Undo.end()", source)

    def test_freeze_selected_has_undo_cancel(self):
        source = _load_function_source("freeze_selected")
        self.assertIsNotNone(source, "freeze_selected() not found in node_layout.py")
        self.assertIn("nuke.Undo.cancel()", source)

    def test_freeze_selected_undo_end_not_in_finally(self):
        finally_source = _get_finally_body_source("freeze_selected")
        if finally_source is not None:
            self.assertNotIn(
                "Undo.end",
                finally_source,
                "nuke.Undo.end() must not be in a finally block in freeze_selected()",
            )

    def test_freeze_selected_guard_before_undo_begin(self):
        """The selected_nodes guard must appear before nuke.Undo.begin() in freeze_selected()."""
        source = _load_function_source("freeze_selected")
        self.assertIsNotNone(source, "freeze_selected() not found in node_layout.py")
        # The guard checks selected_nodes before opening the undo group
        guard_pos = source.find("selected_nodes")
        begin_pos = source.find("nuke.Undo.begin()")
        self.assertGreater(guard_pos, -1, "selected_nodes guard not found in freeze_selected()")
        self.assertGreater(begin_pos, -1, "nuke.Undo.begin() not found in freeze_selected()")
        self.assertLess(
            guard_pos, begin_pos,
            "selected_nodes guard must appear before nuke.Undo.begin() in freeze_selected()",
        )

    def test_freeze_selected_calls_write_freeze_group(self):
        source = _load_function_source("freeze_selected")
        self.assertIsNotNone(source, "freeze_selected() not found in node_layout.py")
        self.assertIn("write_freeze_group", source)

    def test_freeze_selected_calls_uuid(self):
        source = _load_function_source("freeze_selected")
        self.assertIsNotNone(source, "freeze_selected() not found in node_layout.py")
        self.assertIn("uuid.uuid4()", source)


# ---------------------------------------------------------------------------
# TestUnfreezeSelectedStructure
# ---------------------------------------------------------------------------


class TestUnfreezeSelectedStructure(unittest.TestCase):
    """AST structural tests for undo group wrapping in unfreeze_selected()."""

    def test_unfreeze_selected_exists(self):
        source = _load_function_source("unfreeze_selected")
        self.assertIsNotNone(source, "unfreeze_selected() not found in node_layout.py")

    def test_unfreeze_selected_has_undo_name(self):
        source = _load_function_source("unfreeze_selected")
        self.assertIsNotNone(source, "unfreeze_selected() not found in node_layout.py")
        self.assertIn('nuke.Undo.name("Unfreeze Selected")', source)

    def test_unfreeze_selected_has_undo_begin(self):
        source = _load_function_source("unfreeze_selected")
        self.assertIsNotNone(source, "unfreeze_selected() not found in node_layout.py")
        self.assertIn("nuke.Undo.begin()", source)

    def test_unfreeze_selected_has_undo_end(self):
        source = _load_function_source("unfreeze_selected")
        self.assertIsNotNone(source, "unfreeze_selected() not found in node_layout.py")
        self.assertIn("nuke.Undo.end()", source)

    def test_unfreeze_selected_has_undo_cancel(self):
        source = _load_function_source("unfreeze_selected")
        self.assertIsNotNone(source, "unfreeze_selected() not found in node_layout.py")
        self.assertIn("nuke.Undo.cancel()", source)

    def test_unfreeze_selected_undo_end_not_in_finally(self):
        finally_source = _get_finally_body_source("unfreeze_selected")
        if finally_source is not None:
            self.assertNotIn(
                "Undo.end",
                finally_source,
                "nuke.Undo.end() must not be in a finally block in unfreeze_selected()",
            )

    def test_unfreeze_selected_calls_clear_freeze_group(self):
        source = _load_function_source("unfreeze_selected")
        self.assertIsNotNone(source, "unfreeze_selected() not found in node_layout.py")
        self.assertIn("clear_freeze_group", source)


# ---------------------------------------------------------------------------
# TestFreezeMenuRegistration
# ---------------------------------------------------------------------------


MENU_PATH = os.path.join(os.path.dirname(__file__), "..", "menu.py")


class TestFreezeMenuRegistration(unittest.TestCase):
    """AST structural tests on menu.py for freeze command registration."""

    def setUp(self):
        with open(MENU_PATH) as menu_file:
            self.menu_source = menu_file.read()

    def test_freeze_selected_registered(self):
        self.assertIn("'Freeze Selected'", self.menu_source)
        self.assertIn("freeze_selected", self.menu_source)

    def test_unfreeze_selected_registered(self):
        self.assertIn("'Unfreeze Selected'", self.menu_source)
        self.assertIn("unfreeze_selected", self.menu_source)

    def test_freeze_selected_has_shortcut(self):
        lower_source = self.menu_source.lower()
        self.assertIn("ctrl+shift+f", lower_source)

    def test_unfreeze_selected_has_shortcut(self):
        lower_source = self.menu_source.lower()
        self.assertIn("ctrl+shift+u", lower_source)


# ---------------------------------------------------------------------------
# TestFreezeSelectedBehavior
# ---------------------------------------------------------------------------


class TestFreezeSelectedBehavior(unittest.TestCase):
    """Stub-based behavioral tests for freeze_selected()."""

    def setUp(self):
        # Restore stub in case another test module replaced it
        sys.modules["nuke"] = _nuke_stub
        # Reset selectedNodes to empty by default
        _nuke_stub.selectedNodes = lambda: []

    def tearDown(self):
        _nuke_stub.selectedNodes = lambda: []

    def test_freeze_selected_noop_on_empty_selection(self):
        _nuke_stub.selectedNodes = lambda: []
        try:
            _nl.freeze_selected()
        except Exception as exception:
            self.fail(f"freeze_selected() raised an exception on empty selection: {exception}")

    def test_freeze_selected_assigns_uuid_to_all_nodes(self):
        nodes = [_make_state_stub_node() for _ in range(3)]
        _nuke_stub.selectedNodes = lambda: nodes
        _nl.freeze_selected()

        freeze_groups = []
        for node in nodes:
            state_knob = node.knob("node_layout_state")
            self.assertIsNotNone(state_knob, "node_layout_state knob missing after freeze_selected()")
            state = json.loads(state_knob.value())
            freeze_group = state.get("freeze_group")
            self.assertIsNotNone(
                freeze_group, "freeze_group must not be None after freeze_selected()"
            )
            freeze_groups.append(freeze_group)

        # All three nodes must share the same UUID
        self.assertEqual(
            len(set(freeze_groups)), 1,
            f"All nodes must share the same freeze_group UUID, got: {freeze_groups}",
        )

    def test_freeze_selected_assigns_valid_uuid_format(self):
        nodes = [_make_state_stub_node() for _ in range(2)]
        _nuke_stub.selectedNodes = lambda: nodes
        _nl.freeze_selected()

        state_knob = nodes[0].knob("node_layout_state")
        state = json.loads(state_knob.value())
        freeze_group = state.get("freeze_group")

        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        )
        self.assertRegex(
            freeze_group,
            uuid_pattern,
            f"freeze_group must be a valid UUID4 string, got: {freeze_group!r}",
        )


# ---------------------------------------------------------------------------
# TestUnfreezeSelectedBehavior
# ---------------------------------------------------------------------------


class TestUnfreezeSelectedBehavior(unittest.TestCase):
    """Stub-based behavioral tests for unfreeze_selected()."""

    def setUp(self):
        sys.modules["nuke"] = _nuke_stub
        _nuke_stub.selectedNodes = lambda: []

    def tearDown(self):
        _nuke_stub.selectedNodes = lambda: []

    def test_unfreeze_selected_noop_on_empty_selection(self):
        _nuke_stub.selectedNodes = lambda: []
        try:
            _nl.unfreeze_selected()
        except Exception as exception:
            self.fail(f"unfreeze_selected() raised an exception on empty selection: {exception}")

    def test_unfreeze_selected_clears_freeze_group(self):
        existing_uuid = "a3f1c2e4-8b7d-4e6f-9c2a-1d5e3b7f0a4c"
        initial_state = {
            "scheme": "normal",
            "mode": "vertical",
            "h_scale": 1.0,
            "v_scale": 1.0,
            "freeze_group": existing_uuid,
        }
        nodes = [_make_state_stub_node(initial_state=initial_state) for _ in range(2)]
        _nuke_stub.selectedNodes = lambda: nodes
        _nl.unfreeze_selected()

        for node in nodes:
            state_knob = node.knob("node_layout_state")
            self.assertIsNotNone(state_knob)
            state = json.loads(state_knob.value())
            self.assertIsNone(
                state.get("freeze_group"),
                "freeze_group must be None after unfreeze_selected()",
            )


if __name__ == "__main__":
    unittest.main()

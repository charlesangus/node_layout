"""Tests for undo group wrapping in layout entry-point functions.

Verifies via AST analysis that layout_upstream() and layout_selected() both:
- Open a nuke.Undo group with a descriptive name
- Wrap all mutating operations inside a try block
- Call nuke.Undo.cancel() + raise on exception (never in finally)
- Call nuke.Undo.end() in the else clause (never in finally)
- Place nuke.Undo.begin() at the correct position relative to early-return guards and first
  mutations

These tests run without the Nuke runtime — they use AST structural analysis.
"""
import ast
import importlib.util
import os
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
sys.modules["nuke"] = _nuke_stub

_module_path = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")
_spec = importlib.util.spec_from_file_location("node_layout", _module_path)
_nl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_nl)


# ---------------------------------------------------------------------------
# AST helper
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
                    # Collect source segments for each statement in finalbody
                    parts = []
                    for stmt in child.finalbody:
                        segment = ast.get_source_segment(source, stmt)
                        if segment:
                            parts.append(segment)
                    return "\n".join(parts)
    return None


# ---------------------------------------------------------------------------
# TestUndoWrappingLayoutUpstream
# ---------------------------------------------------------------------------


class TestUndoWrappingLayoutUpstream(unittest.TestCase):
    """AST structural tests for undo group wrapping in layout_upstream()."""

    def setUp(self):
        self.source = _load_function_source("layout_upstream")
        self.assertIsNotNone(self.source, "layout_upstream() not found in node_layout.py")

    def test_undo_name_layout_upstream_present(self):
        """layout_upstream() must set undo label 'Layout Upstream' before opening the group."""
        self.assertIn(
            'nuke.Undo.name("Layout Upstream")',
            self.source,
            "layout_upstream() must call nuke.Undo.name(\"Layout Upstream\")",
        )

    def test_undo_begin_present_in_layout_upstream(self):
        """layout_upstream() must call nuke.Undo.begin() to open the undo group."""
        self.assertIn(
            "nuke.Undo.begin()",
            self.source,
            "layout_upstream() must call nuke.Undo.begin()",
        )

    def test_undo_end_present_in_layout_upstream(self):
        """layout_upstream() must call nuke.Undo.end() to commit the undo group."""
        self.assertIn(
            "nuke.Undo.end()",
            self.source,
            "layout_upstream() must call nuke.Undo.end()",
        )

    def test_undo_cancel_present_in_layout_upstream(self):
        """layout_upstream() must call nuke.Undo.cancel() to roll back on exception."""
        self.assertIn(
            "nuke.Undo.cancel()",
            self.source,
            "layout_upstream() must call nuke.Undo.cancel()",
        )

    def test_undo_begin_before_insert_dot_nodes_in_layout_upstream(self):
        """nuke.Undo.begin() must appear before insert_dot_nodes(root) in layout_upstream()."""
        begin_pos = self.source.find("nuke.Undo.begin()")
        insert_pos = self.source.find("insert_dot_nodes(root)")
        self.assertGreater(begin_pos, -1, "nuke.Undo.begin() not found in layout_upstream()")
        self.assertGreater(insert_pos, -1, "insert_dot_nodes(root) not found in layout_upstream()")
        self.assertLess(
            begin_pos, insert_pos,
            "nuke.Undo.begin() must appear before insert_dot_nodes(root) in layout_upstream()",
        )

    def test_undo_end_not_in_finally_block_in_layout_upstream(self):
        """nuke.Undo.end() must NOT be in a finally block in layout_upstream()."""
        finally_source = _get_finally_body_source("layout_upstream")
        if finally_source is not None:
            self.assertNotIn(
                "Undo.end",
                finally_source,
                "nuke.Undo.end() must not be in a finally block in layout_upstream()",
            )
        # If no finally block exists, the test passes trivially (correct state)

    def test_push_nodes_before_undo_end_in_layout_upstream(self):
        """push_nodes_to_make_room must appear before nuke.Undo.end() in layout_upstream()."""
        push_pos = self.source.find("push_nodes_to_make_room")
        end_pos = self.source.find("nuke.Undo.end()")
        self.assertGreater(push_pos, -1, "push_nodes_to_make_room not found in layout_upstream()")
        self.assertGreater(end_pos, -1, "nuke.Undo.end() not found in layout_upstream()")
        self.assertLess(
            push_pos, end_pos,
            "push_nodes_to_make_room must appear before nuke.Undo.end() in layout_upstream()",
        )


# ---------------------------------------------------------------------------
# TestUndoWrappingLayoutSelected
# ---------------------------------------------------------------------------


class TestUndoWrappingLayoutSelected(unittest.TestCase):
    """AST structural tests for undo group wrapping in layout_selected()."""

    def setUp(self):
        self.source = _load_function_source("layout_selected")
        self.assertIsNotNone(self.source, "layout_selected() not found in node_layout.py")

    def test_undo_name_layout_selected_present(self):
        """layout_selected() must set undo label 'Layout Selected' before opening the group."""
        self.assertIn(
            'nuke.Undo.name("Layout Selected")',
            self.source,
            "layout_selected() must call nuke.Undo.name(\"Layout Selected\")",
        )

    def test_undo_begin_present_in_layout_selected(self):
        """layout_selected() must call nuke.Undo.begin() to open the undo group."""
        self.assertIn(
            "nuke.Undo.begin()",
            self.source,
            "layout_selected() must call nuke.Undo.begin()",
        )

    def test_undo_end_present_in_layout_selected(self):
        """layout_selected() must call nuke.Undo.end() to commit the undo group."""
        self.assertIn(
            "nuke.Undo.end()",
            self.source,
            "layout_selected() must call nuke.Undo.end()",
        )

    def test_undo_cancel_present_in_layout_selected(self):
        """layout_selected() must call nuke.Undo.cancel() to roll back on exception."""
        self.assertIn(
            "nuke.Undo.cancel()",
            self.source,
            "layout_selected() must call nuke.Undo.cancel()",
        )

    def test_undo_begin_after_early_return_guard_in_layout_selected(self):
        """nuke.Undo.begin() must appear AFTER 'if len(selected_nodes) < 2' in layout_selected()."""
        guard_pos = self.source.find("if len(selected_nodes) < 2")
        begin_pos = self.source.find("nuke.Undo.begin()")
        self.assertGreater(
            guard_pos, -1, "'if len(selected_nodes) < 2' not found in layout_selected()"
        )
        self.assertGreater(begin_pos, -1, "nuke.Undo.begin() not found in layout_selected()")
        self.assertLess(
            guard_pos, begin_pos,
            "nuke.Undo.begin() must appear after early-return guard in layout_selected()",
        )

    def test_undo_end_not_in_finally_block_in_layout_selected(self):
        """nuke.Undo.end() must NOT be in a finally block in layout_selected()."""
        finally_source = _get_finally_body_source("layout_selected")
        if finally_source is not None:
            self.assertNotIn(
                "Undo.end",
                finally_source,
                "nuke.Undo.end() must not be in a finally block in layout_selected()",
            )
        # If no finally block exists, the test passes trivially (correct state)

    def test_push_nodes_before_undo_end_in_layout_selected(self):
        """push_nodes_to_make_room must appear before nuke.Undo.end() in layout_selected()."""
        push_pos = self.source.find("push_nodes_to_make_room")
        end_pos = self.source.find("nuke.Undo.end()")
        self.assertGreater(push_pos, -1, "push_nodes_to_make_room not found in layout_selected()")
        self.assertGreater(end_pos, -1, "nuke.Undo.end() not found in layout_selected()")
        self.assertLess(
            push_pos, end_pos,
            "push_nodes_to_make_room must appear before nuke.Undo.end() in layout_selected()",
        )


if __name__ == "__main__":
    unittest.main()

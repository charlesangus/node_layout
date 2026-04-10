"""Tests for issue #10: Layout Selected must not push newly created routing Dots.

When place_subtree() inserts a routing Dot for a side input (e.g. a source node
wired as input[1] of a two-input node), that Dot is absent from the original
node_filter.  push_nodes_to_make_room() must NOT push it — the fix is to use
collect_subtree_nodes() (no filter) after layout so new Dots appear in the skip
set.

These tests use AST analysis and a nuke stub — no Nuke runtime required.
"""
import ast
import importlib.util
import os
import sys
import types
import unittest

NODE_LAYOUT_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")


# ---------------------------------------------------------------------------
# Stub nuke module
# ---------------------------------------------------------------------------

class _StubKnob:
    def __init__(self, val=0):
        self._val = val

    def value(self):
        return self._val

    def getValue(self):
        return self._val

    def setValue(self, val):
        self._val = val


_created_dots = []   # track Dots created by nuke.nodes.Dot()


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

    def setInput(self, index, node):
        while len(self._inputs) <= index:
            self._inputs.append(None)
        self._inputs[index] = node

    def knob(self, name):
        return self._knobs.get(name)

    def addKnob(self, knob):
        pass

    def __getitem__(self, name):
        if name in self._knobs:
            return self._knobs[name]
        return _StubKnob(0)


def _make_dot_node():
    dot = _StubNode(width=12, height=12, node_class="Dot",
                    knobs={"tile_color": _StubKnob(0)})
    dot._inputs = [None]   # Dot has one input slot
    _created_dots.append(dot)
    return dot


class _StubNodesModule:
    Dot = staticmethod(_make_dot_node)


def _make_preferences_node():
    node = _StubNode(node_class="Preferences")
    node._knobs = {
        "dag_snap_threshold": _StubKnob(8),
        "NodeColor": _StubKnob(0),
    }
    node.knobs = lambda: node._knobs
    return node


if "nuke" not in sys.modules:
    _nuke_stub = types.ModuleType("nuke")
    _nuke_stub.Node = _StubNode
    _nuke_stub.nodes = _StubNodesModule()
    _nuke_stub.allNodes = lambda: []
    _nuke_stub.selectedNodes = lambda: []
    _nuke_stub.selectedNode = lambda: _StubNode()
    _nuke_stub.toNode = (
        lambda name: _make_preferences_node() if name == "preferences" else None
    )
    _nuke_stub.menu = lambda name: None
    sys.modules["nuke"] = _nuke_stub
else:
    sys.modules["nuke"].nodes = _StubNodesModule()

if "node_layout_prefs" not in sys.modules:
    _prefs_path = os.path.join(os.path.dirname(__file__), "..", "node_layout_prefs.py")
    _prefs_spec = importlib.util.spec_from_file_location("node_layout_prefs", _prefs_path)
    _prefs_mod = importlib.util.module_from_spec(_prefs_spec)
    _prefs_spec.loader.exec_module(_prefs_mod)
    sys.modules["node_layout_prefs"] = _prefs_mod

if "node_layout_state" not in sys.modules:
    _state_path = os.path.join(os.path.dirname(__file__), "..", "node_layout_state.py")
    _state_spec = importlib.util.spec_from_file_location("node_layout_state", _state_path)
    _state_mod = importlib.util.module_from_spec(_state_spec)
    _state_spec.loader.exec_module(_state_mod)
    sys.modules["node_layout_state"] = _state_mod

_module_path = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")
_spec = importlib.util.spec_from_file_location("node_layout", _module_path)
_nl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_nl)


# ---------------------------------------------------------------------------
# AST structural tests
# ---------------------------------------------------------------------------

class TestLayoutSelectedRoutingDotStructure(unittest.TestCase):
    """AST checks verifying the fix is present in layout_selected()."""

    def _load_source(self):
        with open(NODE_LAYOUT_PATH) as fh:
            return fh.read()

    def _get_function_source(self, source, function_name):
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                return ast.get_source_segment(source, node)
        return None

    def test_layout_selected_uses_collect_subtree_nodes_without_filter(self):
        """layout_selected() must call collect_subtree_nodes(layout_root) with no filter
        when building final_selected_ids, so newly created routing Dots are included."""
        source = self._load_source()
        fn_source = self._get_function_source(source, "layout_selected")
        self.assertIsNotNone(fn_source, "layout_selected() not found")
        # The fix uses a loop variable 'layout_root' to collect post-layout nodes.
        self.assertIn(
            "collect_subtree_nodes(layout_root)",
            fn_source,
            "layout_selected() must call collect_subtree_nodes(layout_root) with no "
            "node_filter so newly inserted routing Dots are included in the push skip-set",
        )

    def test_layout_selected_does_not_build_final_ids_from_node_filter_only(self):
        """After the fix, layout_selected() must NOT build final_selected_ids purely
        from node_filter (which excludes newly created routing Dots)."""
        source = self._load_source()
        fn_source = self._get_function_source(source, "layout_selected")
        self.assertIsNotNone(fn_source)
        self.assertNotIn(
            "final_selected_ids = {id(n) for n in node_filter}",
            fn_source,
            "layout_selected() must not set final_selected_ids = {id(n) for n in "
            "node_filter} — this misses newly created routing Dots",
        )

    def test_file_parses_without_syntax_errors(self):
        source = self._load_source()
        try:
            ast.parse(source)
        except SyntaxError as error:
            self.fail(f"node_layout.py has a syntax error: {error}")


# ---------------------------------------------------------------------------
# Runtime geometry tests
# ---------------------------------------------------------------------------

class TestRoutingDotNotPushedByMakeRoom(unittest.TestCase):
    """Verify that push_nodes_to_make_room skips routing Dots created by place_subtree.

    Graph:  consumer (primary input: chain_node, side input: source_node)
    place_subtree inserts a routing Dot between consumer and source_node.
    After layout the routing Dot must stay at its calculated position.
    """

    def setUp(self):
        _created_dots.clear()

    def _build_graph(self, consumer_x=-3595, consumer_y=3607):
        """
        consumer
          input[0] = chain_node   (centered above — will be placed in a left column)
          input[1] = source_node  (side input — place_subtree creates a routing Dot)
        """
        consumer = _StubNode(width=80, height=28, xpos=consumer_x, ypos=consumer_y,
                             node_class="Grade")
        chain_node = _StubNode(width=80, height=28, xpos=consumer_x,
                               ypos=consumer_y - 100)
        # Source node with 0 input slots (leaf — triggers routing Dot creation)
        source_node = _StubNode(width=80, height=28, xpos=consumer_x - 200,
                                ypos=consumer_y - 200, node_class="Constant")
        source_node._inputs = []   # no input slots

        consumer._inputs = [chain_node, source_node]
        chain_node._inputs = []

        return consumer, chain_node, source_node

    def test_routing_dot_position_not_displaced(self):
        """The routing Dot created for a side input must not be pushed further right."""
        consumer, chain_node, source_node = self._build_graph(
            consumer_x=0, consumer_y=400
        )
        all_nodes = [consumer, chain_node, source_node]
        node_filter = set(all_nodes)

        # Compute bbox_before (simulating what layout_selected captures).
        bbox_before = _nl.compute_node_bounding_box(all_nodes)
        self.assertIsNotNone(bbox_before)

        memo = {}
        snap = 8
        _nl.compute_dims(consumer, memo, snap, len(all_nodes),
                         node_filter=node_filter)
        _nl.place_subtree(consumer, consumer.xpos(), consumer.ypos(),
                          memo, snap, len(all_nodes),
                          node_filter=node_filter)

        # One routing Dot must have been created for source_node.
        self.assertEqual(len(_created_dots), 1,
                         "Expected exactly one routing Dot to be created")
        routing_dot = _created_dots[0]

        # Record the dot's position immediately after place_subtree.
        dot_x_after_place = routing_dot.xpos()
        dot_y_after_place = routing_dot.ypos()

        # Simulate push_nodes_to_make_room using collect_subtree_nodes (the fix).
        # final_selected_ids built WITHOUT filter — includes the routing dot.
        final_selected_ids = set()
        for post_node in _nl.collect_subtree_nodes(consumer):  # no filter
            final_selected_ids.add(id(post_node))

        # The routing dot must be in final_selected_ids (the fix ensures this).
        self.assertIn(
            id(routing_dot), final_selected_ids,
            "Routing Dot created by place_subtree must appear in collect_subtree_nodes"
            "(root) result so push_nodes_to_make_room skips it",
        )

        # Now simulate push_nodes_to_make_room.
        all_post_nodes = [
            n for n in [consumer, chain_node, source_node, routing_dot]
        ]
        bbox_after = _nl.compute_node_bounding_box(all_post_nodes)

        # Record external node positions before push.
        external = _StubNode(width=80, height=28,
                             xpos=bbox_before[2] + 10,   # just right of original bbox
                             ypos=consumer.ypos())
        # Only external nodes should be pushed; routing_dot must stay put.
        all_dag = all_post_nodes + [external]
        sys.modules["nuke"].allNodes = lambda: all_dag

        _nl.push_nodes_to_make_room(final_selected_ids, bbox_before, bbox_after)

        # The routing Dot must not have moved.
        self.assertEqual(routing_dot.xpos(), dot_x_after_place,
                         "Routing Dot xpos must not be changed by push_nodes_to_make_room")
        self.assertEqual(routing_dot.ypos(), dot_y_after_place,
                         "Routing Dot ypos must not be changed by push_nodes_to_make_room")

    def test_routing_dot_absent_from_original_node_filter(self):
        """The routing Dot is NOT in node_filter — this is the root cause scenario."""
        consumer, chain_node, source_node = self._build_graph(
            consumer_x=0, consumer_y=400
        )
        all_nodes = [consumer, chain_node, source_node]
        node_filter = set(all_nodes)

        memo = {}
        snap = 8
        _nl.compute_dims(consumer, memo, snap, len(all_nodes),
                         node_filter=node_filter)
        _nl.place_subtree(consumer, consumer.xpos(), consumer.ypos(),
                          memo, snap, len(all_nodes),
                          node_filter=node_filter)

        self.assertEqual(len(_created_dots), 1)
        routing_dot = _created_dots[0]

        # Confirm the routing dot is absent from the original node_filter.
        self.assertNotIn(
            routing_dot, node_filter,
            "Routing Dot must not be in original node_filter — confirms root cause",
        )

        # But it MUST appear in collect_subtree_nodes(consumer) without filter.
        all_post = _nl.collect_subtree_nodes(consumer)
        post_ids = {id(n) for n in all_post}
        self.assertIn(
            id(routing_dot), post_ids,
            "Routing Dot must be reachable via collect_subtree_nodes(consumer) "
            "with no filter after place_subtree inserts it",
        )


if __name__ == "__main__":
    unittest.main()

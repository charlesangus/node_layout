"""Tests for freeze group preprocessing in node_layout.py.

Verifies via stub-based behavioral tests that:
- _detect_freeze_groups returns correct freeze_group_map and node_freeze_uuid dicts
- Auto-join assigns an unfrozen node sandwiched between frozen group members
- Group merge generates a new UUID when a node bridges two different groups and
  persists via write_freeze_group
- _expand_scope_for_freeze_groups expands a partial selection to full group membership

Expected RED state for Task 1: ALL tests FAIL with AttributeError because
_detect_freeze_groups and _expand_scope_for_freeze_groups do not exist yet.
"""
import importlib.util
import json
import os
import sys
import types
import unittest

NODE_LAYOUT_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")
NODE_LAYOUT_PREFS_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout_prefs.py")
NODE_LAYOUT_STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout_state.py")


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


class _StubContextManager:
    """Context manager stub for nuke.lastHitGroup()."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def nodes(self):
        return []


class _StubTab_Knob:
    def __init__(self, name='', label=''):
        self.name = name

    def setFlag(self, flag):
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
_nuke_stub.lastHitGroup = lambda: _StubContextManager()
_nuke_stub.Tab_Knob = _StubTab_Knob
_nuke_stub.String_Knob = lambda name='', label='': _StubKnob(0)
sys.modules["nuke"] = _nuke_stub

# Load node_layout_prefs first (no Nuke dependency).
_prefs_spec = importlib.util.spec_from_file_location("node_layout_prefs", NODE_LAYOUT_PREFS_PATH)
_node_layout_prefs_module = importlib.util.module_from_spec(_prefs_spec)
_prefs_spec.loader.exec_module(_node_layout_prefs_module)
sys.modules["node_layout_prefs"] = _node_layout_prefs_module

# Load node_layout_state so write_freeze_group is available.
if "node_layout_state" not in sys.modules:
    _state_spec = importlib.util.spec_from_file_location(
        "node_layout_state", NODE_LAYOUT_STATE_PATH
    )
    _node_layout_state_module = importlib.util.module_from_spec(_state_spec)
    sys.modules["node_layout_state"] = _node_layout_state_module
    sys.modules["nuke"] = _nuke_stub
    _state_spec.loader.exec_module(_node_layout_state_module)
else:
    _node_layout_state_module = sys.modules["node_layout_state"]

sys.modules["nuke"] = _nuke_stub

# Load node_layout using a unique alias to avoid sys.modules collisions.
_spec = importlib.util.spec_from_file_location("node_layout_freeze", NODE_LAYOUT_PATH)
_nl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_nl)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _wire(upstream, downstream, slot=0):
    """Connect *upstream* as input *slot* of *downstream*."""
    while len(downstream._inputs) <= slot:
        downstream._inputs.append(None)
    downstream._inputs[slot] = upstream


def _set_freeze_group(node, uuid_str):
    """Write a freeze group UUID to *node* via node_layout_state."""
    _node_layout_state_module.write_freeze_group(node, uuid_str)


def _make_state_stub_node(freeze_group=None):
    """Return a _StubNode with state knob pre-populated (required for write_freeze_group)."""
    initial_state = {
        "scheme": "normal",
        "mode": "vertical",
        "h_scale": 1.0,
        "v_scale": 1.0,
        "freeze_group": freeze_group,
    }
    tab_knob = _StubTab_Knob("node_layout_tab", "Node Layout")
    state_knob = _StubKnob(json.dumps(initial_state))
    state_knob.name = "node_layout_state"
    node = _StubNode(knobs={
        "tile_color": _StubKnob(0),
        "node_layout_tab": tab_knob,
        "node_layout_state": state_knob,
    })
    return node


# ---------------------------------------------------------------------------
# TestFreezePreprocessing
# ---------------------------------------------------------------------------


class TestFreezePreprocessing(unittest.TestCase):
    """Tests that _detect_freeze_groups correctly maps nodes to their freeze UUIDs."""

    def test_detect_groups_returns_maps(self):
        """Two nodes sharing a UUID appear together in freeze_group_map."""
        node_a = _make_state_stub_node(freeze_group="group-aaa")
        node_b = _make_state_stub_node(freeze_group="group-aaa")
        node_c = _make_state_stub_node(freeze_group=None)
        _wire(node_a, node_b)
        _wire(node_b, node_c)

        freeze_group_map, node_freeze_uuid = _nl._detect_freeze_groups([node_a, node_b, node_c])

        self.assertIn("group-aaa", freeze_group_map)
        self.assertEqual(len(freeze_group_map["group-aaa"]), 2)
        self.assertEqual(node_freeze_uuid.get(id(node_a)), "group-aaa")
        self.assertEqual(node_freeze_uuid.get(id(node_b)), "group-aaa")
        self.assertNotIn(id(node_c), node_freeze_uuid)

    def test_no_frozen_nodes_returns_empty(self):
        """When no nodes have a freeze group, both maps are empty."""
        node_a = _make_state_stub_node()
        node_b = _make_state_stub_node()
        node_c = _make_state_stub_node()

        freeze_group_map, node_freeze_uuid = _nl._detect_freeze_groups([node_a, node_b, node_c])

        self.assertEqual(freeze_group_map, {})
        self.assertEqual(node_freeze_uuid, {})

    def test_multiple_groups_detected(self):
        """Four nodes in two different groups produce two keys in freeze_group_map."""
        node_a = _make_state_stub_node(freeze_group="group-aaa")
        node_b = _make_state_stub_node(freeze_group="group-aaa")
        node_c = _make_state_stub_node(freeze_group="group-bbb")
        node_d = _make_state_stub_node(freeze_group="group-bbb")

        freeze_group_map, node_freeze_uuid = _nl._detect_freeze_groups(
            [node_a, node_b, node_c, node_d]
        )

        self.assertIn("group-aaa", freeze_group_map)
        self.assertIn("group-bbb", freeze_group_map)
        self.assertEqual(len(freeze_group_map), 2)
        self.assertEqual(len(freeze_group_map["group-aaa"]), 2)
        self.assertEqual(len(freeze_group_map["group-bbb"]), 2)


# ---------------------------------------------------------------------------
# TestFreezeAutoJoin
# ---------------------------------------------------------------------------


class TestFreezeAutoJoin(unittest.TestCase):
    """Tests that _detect_freeze_groups auto-joins nodes sandwiched between frozen members."""

    def test_node_between_frozen_nodes_joins(self):
        """An unfrozen node between two frozen nodes in the same group auto-joins."""
        # Chain: C -> B -> A (A is upstream)
        node_a = _make_state_stub_node(freeze_group="group-aaa")  # upstream
        node_b = _make_state_stub_node(freeze_group=None)          # middle, unfrozen
        node_c = _make_state_stub_node(freeze_group="group-aaa")  # downstream
        _wire(node_a, node_b)   # node_b takes node_a as input
        _wire(node_b, node_c)   # node_c takes node_b as input

        freeze_group_map, node_freeze_uuid = _nl._detect_freeze_groups([node_a, node_b, node_c])

        self.assertIn(id(node_b), node_freeze_uuid,
                      "node_b (between two group-aaa members) should auto-join group-aaa")
        self.assertEqual(node_freeze_uuid[id(node_b)], "group-aaa")

    def test_node_only_downstream_does_not_join(self):
        """An unfrozen node downstream of a frozen node (no frozen descendants) does NOT join."""
        # Chain: B -> A (A is upstream/frozen, B is downstream/unfrozen with no frozen consumers)
        node_a = _make_state_stub_node(freeze_group="group-aaa")
        node_b = _make_state_stub_node(freeze_group=None)
        _wire(node_a, node_b)

        freeze_group_map, node_freeze_uuid = _nl._detect_freeze_groups([node_a, node_b])

        self.assertNotIn(id(node_b), node_freeze_uuid,
                         "node_b (only downstream of frozen, no frozen descendants) must not join")

    def test_mixed_inputs_with_frozen_descendant_joins(self):
        """A merge node with one frozen input and a frozen descendant joins that group."""
        # Merge has input_0=A (frozen "group-aaa"), input_1=D (unfrozen)
        # Merge feeds into C (frozen "group-aaa")
        node_a = _make_state_stub_node(freeze_group="group-aaa")
        node_d = _make_state_stub_node(freeze_group=None)
        node_merge = _make_state_stub_node(freeze_group=None)
        node_c = _make_state_stub_node(freeze_group="group-aaa")

        _wire(node_a, node_merge, slot=0)
        _wire(node_d, node_merge, slot=1)
        _wire(node_merge, node_c)

        freeze_group_map, node_freeze_uuid = _nl._detect_freeze_groups(
            [node_a, node_d, node_merge, node_c]
        )

        self.assertIn(id(node_merge), node_freeze_uuid,
                      "node_merge (frozen input + frozen downstream) should join group-aaa")
        self.assertEqual(node_freeze_uuid[id(node_merge)], "group-aaa")


# ---------------------------------------------------------------------------
# TestFreezeGroupMerge
# ---------------------------------------------------------------------------


class TestFreezeGroupMerge(unittest.TestCase):
    """Tests that a node bridging two freeze groups causes a merge with a new UUID."""

    def test_bridging_node_merges_two_groups(self):
        """A node between group-1 and group-2 causes all three to share a new UUID."""
        # Chain: C("group-2") -> B(unfrozen) -> A("group-1")
        node_a = _make_state_stub_node(freeze_group="group-1")
        node_b = _make_state_stub_node(freeze_group=None)
        node_c = _make_state_stub_node(freeze_group="group-2")
        _wire(node_a, node_b)
        _wire(node_b, node_c)

        freeze_group_map, node_freeze_uuid = _nl._detect_freeze_groups([node_a, node_b, node_c])

        # All three must share a single UUID
        uuid_a = node_freeze_uuid.get(id(node_a))
        uuid_b = node_freeze_uuid.get(id(node_b))
        uuid_c = node_freeze_uuid.get(id(node_c))

        self.assertIsNotNone(uuid_a, "node_a must have a freeze UUID after merge")
        self.assertIsNotNone(uuid_b, "node_b must have a freeze UUID after merge")
        self.assertIsNotNone(uuid_c, "node_c must have a freeze UUID after merge")
        self.assertEqual(uuid_a, uuid_b,
                         "node_a and node_b must share the same merged UUID")
        self.assertEqual(uuid_b, uuid_c,
                         "node_b and node_c must share the same merged UUID")

        # The new UUID must not be either original UUID
        self.assertNotEqual(uuid_a, "group-1",
                            "merged UUID must not be the original group-1")
        self.assertNotEqual(uuid_a, "group-2",
                            "merged UUID must not be the original group-2")

    def test_merge_persists_via_write_freeze_group(self):
        """After merge, all affected nodes have the new UUID persisted in their state."""
        node_a = _make_state_stub_node(freeze_group="group-1")
        node_b = _make_state_stub_node(freeze_group=None)
        node_c = _make_state_stub_node(freeze_group="group-2")
        _wire(node_a, node_b)
        _wire(node_b, node_c)

        _nl._detect_freeze_groups([node_a, node_b, node_c])

        # Read persisted state directly from knobs
        persisted_a = _node_layout_state_module.read_freeze_group(node_a)
        persisted_b = _node_layout_state_module.read_freeze_group(node_b)
        persisted_c = _node_layout_state_module.read_freeze_group(node_c)

        self.assertIsNotNone(persisted_a)
        self.assertIsNotNone(persisted_b)
        self.assertIsNotNone(persisted_c)
        self.assertEqual(persisted_a, persisted_b,
                         "All merged nodes must persist the same UUID")
        self.assertEqual(persisted_b, persisted_c,
                         "All merged nodes must persist the same UUID")
        self.assertNotEqual(persisted_a, "group-1")
        self.assertNotEqual(persisted_a, "group-2")


# ---------------------------------------------------------------------------
# TestFreezeScopeExpansion
# ---------------------------------------------------------------------------


class TestFreezeScopeExpansion(unittest.TestCase):
    """Tests that _expand_scope_for_freeze_groups expands partial selections."""

    def test_partial_selection_expands_to_full_group(self):
        """When only node_a is selected but A, B, C share a group, all three are returned."""
        node_a = _make_state_stub_node(freeze_group="group-aaa")
        node_b = _make_state_stub_node(freeze_group="group-aaa")
        node_c = _make_state_stub_node(freeze_group="group-aaa")

        # current_group context stub with all three nodes
        context_stub = _StubContextManager()
        context_stub.nodes = lambda: [node_a, node_b, node_c]

        selected = [node_a]
        expanded = _nl._expand_scope_for_freeze_groups(selected, context_stub)

        expanded_ids = {id(n) for n in expanded}
        self.assertIn(id(node_a), expanded_ids)
        self.assertIn(id(node_b), expanded_ids)
        self.assertIn(id(node_c), expanded_ids)

    def test_no_expansion_when_no_frozen_nodes(self):
        """When selected nodes have no freeze groups, no expansion occurs."""
        node_d = _make_state_stub_node(freeze_group=None)
        node_e = _make_state_stub_node(freeze_group=None)

        context_stub = _StubContextManager()
        context_stub.nodes = lambda: [node_d, node_e]

        selected = [node_d, node_e]
        expanded = _nl._expand_scope_for_freeze_groups(selected, context_stub)

        expanded_ids = {id(n) for n in expanded}
        self.assertIn(id(node_d), expanded_ids)
        self.assertIn(id(node_e), expanded_ids)
        self.assertEqual(len(expanded_ids), 2,
                         "No extra nodes should be added when none are frozen")


if __name__ == "__main__":
    unittest.main()

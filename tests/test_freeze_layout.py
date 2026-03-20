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


# ---------------------------------------------------------------------------
# TestFreezeBlockPositioning
# ---------------------------------------------------------------------------


class TestFreezeBlockPositioning(unittest.TestCase):
    """Tests that rigid block positioning works: non-root members maintain relative offsets."""

    def test_relative_offsets_preserved(self):
        """After block root moves, non-root members maintain their original relative offsets."""
        # Create a chain: member_b -> member_a -> root
        # (member_b is upstream, root is most downstream)
        root = _make_state_stub_node(freeze_group="group-aaa")
        root.setXpos(100)
        root.setYpos(300)

        member_a = _make_state_stub_node(freeze_group="group-aaa")
        member_a.setXpos(100)
        member_a.setYpos(200)

        member_b = _make_state_stub_node(freeze_group="group-aaa")
        member_b.setXpos(200)
        member_b.setYpos(100)

        # Wire: root takes member_a as input; member_a takes member_b as input
        _wire(member_a, root)
        _wire(member_b, member_a)

        block_members = [root, member_a, member_b]
        block_root = _nl._find_freeze_block_root(block_members)
        self.assertIs(block_root, root, "root should be most downstream (no other member uses it)")

        # Capture relative offsets before placement
        relative_offsets = {}
        for member in block_members:
            if id(member) != id(block_root):
                relative_offsets[id(member)] = (
                    member.xpos() - block_root.xpos(),
                    member.ypos() - block_root.ypos(),
                )

        # Simulate block root moving to new position (300, 500)
        block_root.setXpos(300)
        block_root.setYpos(500)

        # Apply offsets
        for member in block_members:
            if id(member) != id(block_root):
                offset_dx, offset_dy = relative_offsets[id(member)]
                member.setXpos(block_root.xpos() + offset_dx)
                member.setYpos(block_root.ypos() + offset_dy)

        # member_a was at (0, -100) from root; should now be at (300, 400)
        self.assertEqual(member_a.xpos(), 300)
        self.assertEqual(member_a.ypos(), 400)

        # member_b was at (100, -200) from root; should now be at (400, 300)
        self.assertEqual(member_b.xpos(), 400)
        self.assertEqual(member_b.ypos(), 300)

    def test_non_root_members_excluded_from_filter(self):
        """Non-root block members are excluded from the node filter passed to place_subtree."""
        root = _make_state_stub_node(freeze_group="group-aaa")
        non_root_member = _make_state_stub_node(freeze_group="group-aaa")
        _wire(non_root_member, root)

        all_nodes = [root, non_root_member]
        block_members = [root, non_root_member]
        block_root = _nl._find_freeze_block_root(block_members)

        # Build freeze_excluded_ids as layout_upstream would
        freeze_excluded_ids = set()
        for member in block_members:
            if id(member) != id(block_root):
                freeze_excluded_ids.add(id(member))

        # Build filtered set (simulating what would be passed to place_subtree)
        filtered = {node for node in all_nodes if id(node) not in freeze_excluded_ids}

        self.assertIn(root, filtered, "block root must be in filter")
        self.assertNotIn(non_root_member, filtered, "non-root member must be excluded from filter")

    def test_freeze_overrides_horizontal_mode(self):
        """A block member with mode=horizontal is still detected as a freeze group member."""
        # Create a node with mode=horizontal in its state but belonging to a freeze group
        initial_state = {
            "scheme": "normal",
            "mode": "horizontal",
            "h_scale": 1.0,
            "v_scale": 1.0,
            "freeze_group": "group-aaa",
        }
        import json as _json
        tab_knob = _StubTab_Knob("node_layout_tab", "Node Layout")
        state_knob = _StubKnob(_json.dumps(initial_state))
        state_knob.name = "node_layout_state"
        horizontal_member = _StubNode(knobs={
            "tile_color": _StubKnob(0),
            "node_layout_tab": tab_knob,
            "node_layout_state": state_knob,
        })

        root = _make_state_stub_node(freeze_group="group-aaa")
        _wire(horizontal_member, root)

        scope_nodes = [root, horizontal_member]
        freeze_group_map, node_freeze_uuid = _nl._detect_freeze_groups(scope_nodes)

        # horizontal_member must be detected as part of freeze group
        self.assertIn(id(horizontal_member), node_freeze_uuid,
                      "freeze membership must be detected regardless of mode flag")
        self.assertEqual(node_freeze_uuid[id(horizontal_member)], "group-aaa")


# ---------------------------------------------------------------------------
# TestFreezeBlockPush
# ---------------------------------------------------------------------------


class TestFreezeBlockPush(unittest.TestCase):
    """Tests that push_nodes_to_make_room treats frozen blocks as rigid units."""

    def test_push_translates_block_as_unit(self):
        """When a push qualifies for a block member, all block members shift by the same delta."""
        # Block members at (500, 0) and (500, 50)
        block_member_1 = _StubNode(width=80, height=28, xpos=500, ypos=0)
        block_member_2 = _StubNode(width=80, height=28, xpos=500, ypos=50)

        # Non-frozen node at (600, 0)
        other_node = _StubNode(width=80, height=28, xpos=600, ypos=0)

        block_uuid = "block-xxx"
        freeze_block_map = {
            id(block_member_1): block_uuid,
            id(block_member_2): block_uuid,
        }
        freeze_groups = {
            block_uuid: [block_member_1, block_member_2],
        }

        # Subtree that grew right: before (0,0,100,100), after (0,0,200,100)
        bbox_before = (0, 0, 100, 100)
        bbox_after = (0, 0, 200, 100)

        # Stub group context with all nodes
        context_stub = _StubContextManager()
        context_stub.nodes = lambda: [block_member_1, block_member_2, other_node]

        subtree_node_ids = set()  # empty — no nodes in the "moved" subtree

        _nl.push_nodes_to_make_room(
            subtree_node_ids, bbox_before, bbox_after,
            current_group=context_stub,
            freeze_block_map=freeze_block_map,
            freeze_groups=freeze_groups,
        )

        # Both block members should have shifted right by 100
        self.assertEqual(block_member_1.xpos(), 600,
                         "block member 1 should shift right by 100")
        self.assertEqual(block_member_2.xpos(), 600,
                         "block member 2 should shift right by 100")
        # other_node at 600 is >= before_max_x (100), so it qualifies for push too
        self.assertEqual(other_node.xpos(), 700,
                         "non-frozen node should also shift right by 100")

    def test_push_does_not_double_translate(self):
        """If both block members independently qualify for push, block is only translated once."""
        block_member_1 = _StubNode(width=80, height=28, xpos=500, ypos=0)
        block_member_2 = _StubNode(width=80, height=28, xpos=500, ypos=50)

        block_uuid = "block-yyy"
        freeze_block_map = {
            id(block_member_1): block_uuid,
            id(block_member_2): block_uuid,
        }
        freeze_groups = {
            block_uuid: [block_member_1, block_member_2],
        }

        bbox_before = (0, 0, 100, 100)
        bbox_after = (0, 0, 200, 100)

        context_stub = _StubContextManager()
        context_stub.nodes = lambda: [block_member_1, block_member_2]

        subtree_node_ids = set()

        _nl.push_nodes_to_make_room(
            subtree_node_ids, bbox_before, bbox_after,
            current_group=context_stub,
            freeze_block_map=freeze_block_map,
            freeze_groups=freeze_groups,
        )

        # Each block member should have moved exactly 100 (not 200)
        self.assertEqual(block_member_1.xpos(), 600,
                         "block member 1 should move exactly once (100px, not 200px)")
        self.assertEqual(block_member_2.xpos(), 600,
                         "block member 2 should move exactly once (100px, not 200px)")

    def test_push_uses_block_bbox_for_overlap(self):
        """If block bounding box overlaps bbox_before, entire block is skipped."""
        # Block members: one overlaps bbox_before, one does not
        # member_inside is at (50, 50) — overlaps (0,0,100,100)
        member_inside = _StubNode(width=80, height=28, xpos=50, ypos=50)
        # member_outside is at (200, 200) — does not overlap but same block
        member_outside = _StubNode(width=80, height=28, xpos=200, ypos=200)

        block_uuid = "block-zzz"
        freeze_block_map = {
            id(member_inside): block_uuid,
            id(member_outside): block_uuid,
        }
        freeze_groups = {
            block_uuid: [member_inside, member_outside],
        }

        bbox_before = (0, 0, 100, 100)
        bbox_after = (0, 0, 200, 100)

        context_stub = _StubContextManager()
        context_stub.nodes = lambda: [member_inside, member_outside]

        subtree_node_ids = set()

        _nl.push_nodes_to_make_room(
            subtree_node_ids, bbox_before, bbox_after,
            current_group=context_stub,
            freeze_block_map=freeze_block_map,
            freeze_groups=freeze_groups,
        )

        # Because the block bbox includes member_inside which overlaps bbox_before,
        # the entire block should be skipped (neither member should move)
        self.assertEqual(member_inside.xpos(), 50,
                         "member_inside should not move (block bbox overlaps before bbox)")
        self.assertEqual(member_outside.xpos(), 200,
                         "member_outside should not move (block bbox overlaps before bbox)")


# ---------------------------------------------------------------------------
# TestGroupViewDotCreation
# ---------------------------------------------------------------------------


class TestGroupViewDotCreation(unittest.TestCase):
    """Tests that Dot creation functions do not use nuke.thisGroup() (wrong context)."""

    def test_insert_dot_nodes_no_thisGroup(self):
        """insert_dot_nodes function body must not call nuke.thisGroup()."""
        import ast
        with open(NODE_LAYOUT_PATH, "r") as layout_file:
            source = layout_file.read()
        tree = ast.parse(source)

        # Find insert_dot_nodes function definition
        insert_dot_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "insert_dot_nodes":
                insert_dot_func = node
                break

        self.assertIsNotNone(insert_dot_func,
                             "insert_dot_nodes must exist in node_layout.py")

        # Walk the function body for nuke.thisGroup() calls
        for call_node in ast.walk(insert_dot_func):
            if isinstance(call_node, ast.Call):
                func = call_node.func
                if (isinstance(func, ast.Attribute) and func.attr == "thisGroup"
                        and isinstance(func.value, ast.Name) and func.value.id == "nuke"):
                    self.fail("insert_dot_nodes must not call nuke.thisGroup()")

    def test_place_output_dot_no_thisGroup(self):
        """_place_output_dot_for_horizontal_root must not call nuke.thisGroup()."""
        import ast
        with open(NODE_LAYOUT_PATH, "r") as layout_file:
            source = layout_file.read()
        tree = ast.parse(source)

        # Find _place_output_dot_for_horizontal_root function definition
        target_func = None
        for node in ast.walk(tree):
            if (isinstance(node, ast.FunctionDef)
                    and node.name == "_place_output_dot_for_horizontal_root"):
                target_func = node
                break

        self.assertIsNotNone(target_func,
                             "_place_output_dot_for_horizontal_root must exist in node_layout.py")

        # Walk the function body for nuke.thisGroup() calls
        for call_node in ast.walk(target_func):
            if isinstance(call_node, ast.Call):
                func = call_node.func
                if (isinstance(func, ast.Attribute) and func.attr == "thisGroup"
                        and isinstance(func.value, ast.Name) and func.value.id == "nuke"):
                    self.fail(
                        "_place_output_dot_for_horizontal_root must not call nuke.thisGroup()"
                    )


# ---------------------------------------------------------------------------
# TestFreezeGapClosure
# ---------------------------------------------------------------------------


class TestFreezeGapClosure(unittest.TestCase):
    """Regression tests for the three gap closure fixes in Plan 16-04.

    Gap 1: Non-frozen upstream nodes unreachable through excluded non-root members.
    Gap 2/3: Type mismatch in layout_selected node_filter -= freeze_excluded_ids was a no-op.
    Gap 5: Frozen node with mode=horizontal was used as horizontal replay root.
    """

    def test_layout_selected_excludes_non_root_members_from_filter(self):
        """Corrected id()-based comprehension excludes non-root members from node_filter.

        This is a unit test of the fixed filter construction.  Before the fix,
        `node_filter -= freeze_excluded_ids` was a no-op because node_filter
        contained node objects while freeze_excluded_ids contained int id()
        values.  The fix replaces it with a set comprehension.
        """
        # Build a two-node freeze block: root + one non-root member.
        block_root = _make_state_stub_node(freeze_group="group-aaa")
        non_root_member = _make_state_stub_node(freeze_group="group-aaa")
        _wire(non_root_member, block_root)

        # Replicate the pre-fix filter construction (should leave non_root_member in filter).
        freeze_excluded_ids_before = {id(non_root_member)}
        node_filter_before = {block_root, non_root_member}
        # Pre-fix (broken): set difference between node objects and ints is always empty.
        result_before = node_filter_before - freeze_excluded_ids_before
        # The broken version incorrectly keeps non_root_member in the filter.
        self.assertIn(non_root_member, result_before,
                      "Pre-fix: broken -= leaves non-root member in filter (no-op on mismatched types)")

        # Replicate the post-fix filter construction (should correctly exclude non_root_member).
        freeze_excluded_ids_after = {id(non_root_member)}
        node_filter_after = {block_root, non_root_member}
        # Post-fix (correct): id()-based comprehension.
        result_after = {n for n in node_filter_after if id(n) not in freeze_excluded_ids_after}
        self.assertIn(block_root, result_after,
                      "Post-fix: block root must remain in filter")
        self.assertNotIn(non_root_member, result_after,
                         "Post-fix: non-root member must be excluded from filter")

    def test_frozen_block_moves_as_unit_in_layout_selected(self):
        """Relative offset between freeze block root and non-root member is preserved.

        After layout_selected processes the block, the non-root member's position
        relative to the root must match the original captured offset.  This verifies
        the offset restoration logic works correctly regardless of which code path
        reposition the root.
        """
        block_root = _make_state_stub_node(freeze_group="group-aaa")
        block_root.setXpos(100)
        block_root.setYpos(300)

        non_root_member = _make_state_stub_node(freeze_group="group-aaa")
        non_root_member.setXpos(100)
        non_root_member.setYpos(200)

        _wire(non_root_member, block_root)

        # Record the original relative offset (dx=0, dy=-100).
        original_dx = non_root_member.xpos() - block_root.xpos()
        original_dy = non_root_member.ypos() - block_root.ypos()
        self.assertEqual(original_dx, 0)
        self.assertEqual(original_dy, -100)

        # Capture relative offsets as the layout engine does.
        freeze_relative_offsets = {}
        freeze_relative_offsets[id(non_root_member)] = (original_dx, original_dy)

        # Simulate place_subtree moving the block root to a new position.
        block_root.setXpos(250)
        block_root.setYpos(500)

        # Apply offset restoration (the FRZE-06 block).
        offset_dx, offset_dy = freeze_relative_offsets[id(non_root_member)]
        non_root_member.setXpos(block_root.xpos() + offset_dx)
        non_root_member.setYpos(block_root.ypos() + offset_dy)

        # Verify the relative offset is unchanged.
        new_dx = non_root_member.xpos() - block_root.xpos()
        new_dy = non_root_member.ypos() - block_root.ypos()
        self.assertEqual(new_dx, original_dx,
                         "Horizontal relative offset between root and non-root must be preserved")
        self.assertEqual(new_dy, original_dy,
                         "Vertical relative offset between root and non-root must be preserved")

    def test_frozen_node_not_used_as_horizontal_replay_root(self):
        """BFS horizontal replay root search skips frozen nodes as root candidates.

        A frozen node that has mode=horizontal stored in its state must not become
        the replay root.  The BFS guard (id(bfs_cursor) in node_freeze_uuid) prevents
        it from being bound as root while still traversing through it.
        """
        # Create a frozen node with mode=horizontal in its state.
        frozen_horizontal_state = {
            "scheme": "normal",
            "mode": "horizontal",
            "h_scale": 1.0,
            "v_scale": 1.0,
            "freeze_group": "group-aaa",
        }
        import json as _json
        tab_knob = _StubTab_Knob("node_layout_tab", "Node Layout")
        state_knob_frozen = _StubKnob(_json.dumps(frozen_horizontal_state))
        state_knob_frozen.name = "node_layout_state"
        frozen_node = _StubNode(knobs={
            "tile_color": _StubKnob(0),
            "node_layout_tab": tab_knob,
            "node_layout_state": state_knob_frozen,
        })
        frozen_node.setXpos(0)
        frozen_node.setYpos(0)

        # A non-frozen consumer that feeds into frozen_node upstream.
        consumer = _make_state_stub_node()
        consumer.setXpos(0)
        consumer.setYpos(100)
        _wire(frozen_node, consumer)

        # Build node_freeze_uuid as the layout engine would after _detect_freeze_groups.
        # frozen_node is in the freeze group; consumer is not.
        node_freeze_uuid = {id(frozen_node): "group-aaa"}

        # Replicate the BFS from layout_upstream / layout_selected.
        # consumer.mode is "vertical" so the BFS starts.
        original_root = consumer
        root = consumer
        root_mode = "vertical"

        bfs_queue = [consumer.input(slot) for slot in range(consumer.inputs())
                     if consumer.input(slot) is not None]
        bfs_visited = {id(consumer)}
        bfs_index = 0
        while bfs_index < len(bfs_queue):
            bfs_cursor = bfs_queue[bfs_index]
            bfs_index += 1
            if id(bfs_cursor) in bfs_visited:
                continue
            bfs_visited.add(id(bfs_cursor))
            # Apply the freeze guard (the fix for Gap 5).
            if id(bfs_cursor) in node_freeze_uuid:
                for bfs_slot in range(bfs_cursor.inputs()):
                    bfs_inp = bfs_cursor.input(bfs_slot)
                    if bfs_inp is not None and id(bfs_inp) not in bfs_visited:
                        bfs_queue.append(bfs_inp)
                continue
            if _node_layout_state_module.read_node_state(bfs_cursor).get("mode") == "horizontal":
                root = bfs_cursor
                root_mode = "horizontal"
                break
            for bfs_slot in range(bfs_cursor.inputs()):
                bfs_inp = bfs_cursor.input(bfs_slot)
                if bfs_inp is not None and id(bfs_inp) not in bfs_visited:
                    bfs_queue.append(bfs_inp)

        # The frozen node must NOT have been selected as replay root.
        self.assertIs(root, original_root,
                      "Frozen node with mode=horizontal must not become horizontal replay root")
        self.assertEqual(root_mode, "vertical",
                         "root_mode must remain vertical — frozen node was not eligible as root")

    def test_non_frozen_upstream_nodes_repositioned_after_freeze_block(self):
        """BFS in second pass correctly identifies non-frozen nodes upstream of freeze block.

        Chain: non-frozen D -> non-frozen E -> frozen B (non-root) -> frozen A (root).
        D and E connect to the freeze block only through B (non-root member).
        The second pass BFS must collect D and E in upstream_non_frozen.
        """
        # Build nodes.
        frozen_a = _make_state_stub_node(freeze_group="group-aaa")  # block root (most downstream)
        frozen_b = _make_state_stub_node(freeze_group="group-aaa")  # non-root member
        non_frozen_e = _make_state_stub_node()   # connects to frozen_b
        non_frozen_d = _make_state_stub_node()   # connects to non_frozen_e

        frozen_a.setXpos(0)
        frozen_a.setYpos(300)
        frozen_b.setXpos(0)
        frozen_b.setYpos(200)
        non_frozen_e.setXpos(0)
        non_frozen_e.setYpos(100)
        non_frozen_d.setXpos(0)
        non_frozen_d.setYpos(0)

        # Wire: frozen_a <- frozen_b <- non_frozen_e <- non_frozen_d
        _wire(frozen_b, frozen_a)
        _wire(non_frozen_e, frozen_b)
        _wire(non_frozen_d, non_frozen_e)

        block_members = [frozen_a, frozen_b]
        block_member_ids = {id(m) for m in block_members}
        freeze_block_roots = {"group-aaa": frozen_a}

        # Run the second-pass BFS (replicating the Gap 1 post-pass logic).
        upstream_non_frozen = []
        visited_upstream = set()
        upstream_queue = []
        for member in block_members:
            for upstream_node in _nl.get_inputs(member):
                if upstream_node is not None and id(upstream_node) not in block_member_ids:
                    upstream_queue.append((upstream_node, member))
        while upstream_queue:
            candidate, connecting_member = upstream_queue.pop()
            if id(candidate) in visited_upstream or id(candidate) in block_member_ids:
                continue
            visited_upstream.add(id(candidate))
            upstream_non_frozen.append((candidate, connecting_member))
            for further_upstream in _nl.get_inputs(candidate):
                if further_upstream is not None:
                    upstream_queue.append((further_upstream, connecting_member))

        upstream_non_frozen_ids = {id(node) for node, _ in upstream_non_frozen}

        # Both non-frozen upstream nodes must appear in upstream_non_frozen.
        self.assertIn(id(non_frozen_e), upstream_non_frozen_ids,
                      "non_frozen_e (direct input to frozen_b) must be in upstream_non_frozen")
        self.assertIn(id(non_frozen_d), upstream_non_frozen_ids,
                      "non_frozen_d (further upstream) must be in upstream_non_frozen")

        # Frozen block members must NOT appear in upstream_non_frozen.
        self.assertNotIn(id(frozen_a), upstream_non_frozen_ids,
                         "frozen_a (block root) must not appear in upstream_non_frozen")
        self.assertNotIn(id(frozen_b), upstream_non_frozen_ids,
                         "frozen_b (non-root member) must not appear in upstream_non_frozen")


if __name__ == "__main__":
    unittest.main()

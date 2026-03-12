"""RED test scaffold for fan alignment and mask side-swap in node_layout.py (09-01 TDD).

These tests verify the Phase 9 contract (LAYOUT-01, LAYOUT-02):
- _is_fan_active(input_slot_pairs, consumer_node) activates when 3+ non-mask inputs
- compute_dims() uses max(child_heights) not sum for fan-active consumers
- place_subtree() places all fan roots at the same Y level
- Routing Dots for fan inputs all land at a uniform Y row
- Mask input is placed LEFT of the consumer when fan is active
- Existing staircase behaviour for n==2 is unchanged (regression guards)

Expected RED state: 6 tests FAIL, 2 tests PASS (the two regression guards).
  - test_two_input_no_fan_regression: PASS RED (staircase for n==2 is unchanged)
  - test_mask_right_when_no_fan_regression: PASS RED (mask stays right for n==2)
"""
import sys
import types
import importlib.util
import os
import unittest


NODE_LAYOUT_PATH = "/workspace/node_layout.py"
NODE_LAYOUT_PREFS_PATH = "/workspace/node_layout_prefs.py"
NODE_LAYOUT_STATE_PATH = "/workspace/node_layout_state.py"


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
                 knobs=None, num_inputs=0):
        self._width = width
        self._height = height
        self._xpos = xpos
        self._ypos = ypos
        self._class = node_class
        self._knobs = knobs if knobs is not None else {"tile_color": _StubKnob(0)}
        self._inputs = [None] * num_inputs if num_inputs > 0 else []

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

    def setInput(self, slot, node):
        while len(self._inputs) <= slot:
            self._inputs.append(None)
        self._inputs[slot] = node

    def knob(self, name):
        return self._knobs.get(name)

    def inputLabel(self, index):
        return ""

    def __getitem__(self, name):
        if name in self._knobs:
            return self._knobs[name]
        return _StubKnob(0)


class _StubMergeNode(_StubNode):
    """A Merge2-class node where slot 2 is the mask input.

    inputLabel mimics the real Merge2 label convention so _is_mask_input
    correctly classifies slot 2 as a mask slot.
    """

    def __init__(self, **kwargs):
        super().__init__(node_class="Merge2", **kwargs)

    def inputLabel(self, index):
        return {0: "B", 1: "A", 2: "M"}.get(index, "A{}".format(index))


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
_nuke_stub.nodes = types.SimpleNamespace(
    Dot=lambda: _StubNode(node_class="Dot", width=12, height=12)
)
_nuke_stub.selectedNodes = lambda: []

# Load node_layout_prefs first (no Nuke dependency).
_prefs_spec = importlib.util.spec_from_file_location("node_layout_prefs", NODE_LAYOUT_PREFS_PATH)
_node_layout_prefs_module = importlib.util.module_from_spec(_prefs_spec)
_prefs_spec.loader.exec_module(_node_layout_prefs_module)
sys.modules["node_layout_prefs"] = _node_layout_prefs_module

# Provide a minimal node_layout_state stub so node_layout.py can import it.
if "node_layout_state" not in sys.modules:
    _state_spec = importlib.util.spec_from_file_location("node_layout_state", NODE_LAYOUT_STATE_PATH)
    _node_layout_state_module = importlib.util.module_from_spec(_state_spec)
    sys.modules["node_layout_state"] = _node_layout_state_module
    sys.modules["nuke"] = _nuke_stub
    _state_spec.loader.exec_module(_node_layout_state_module)

sys.modules["nuke"] = _nuke_stub

# Load node_layout using a unique alias to avoid sys.modules collisions.
_spec = importlib.util.spec_from_file_location(
    "node_layout_fan_alignment", NODE_LAYOUT_PATH
)
nl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nl)


def _reset_prefs():
    """Restore prefs to DEFAULTS without touching any file."""
    singleton = _node_layout_prefs_module.prefs_singleton
    for key, default_value in _node_layout_prefs_module.DEFAULTS.items():
        singleton.set(key, default_value)


# ---------------------------------------------------------------------------
# TestFanActivePredicate — 2 tests for _is_fan_active()
# ---------------------------------------------------------------------------


class TestFanActivePredicate(unittest.TestCase):
    """Tests for nl._is_fan_active(input_slot_pairs, consumer_node)."""

    def setUp(self):
        _reset_prefs()

    def test_fan_active_predicate_three_non_mask(self):
        """3 non-mask inputs triggers fan mode (_is_fan_active returns True)."""
        consumer = _StubNode(node_class="Grade")
        input_b = _StubNode(width=80, height=28)
        input_a1 = _StubNode(width=80, height=28)
        input_a2 = _StubNode(width=80, height=28)
        # All three are non-mask for a generic Grade node.
        input_slot_pairs = [(0, input_b), (1, input_a1), (2, input_a2)]
        result = nl._is_fan_active(input_slot_pairs, consumer)
        self.assertTrue(result, "_is_fan_active must return True for 3 non-mask inputs")

    def test_fan_active_predicate_two_non_mask(self):
        """2 non-mask inputs does NOT trigger fan mode (_is_fan_active returns False)."""
        consumer = _StubNode(node_class="Grade")
        input_b = _StubNode(width=80, height=28)
        input_a = _StubNode(width=80, height=28)
        input_slot_pairs = [(0, input_b), (1, input_a)]
        result = nl._is_fan_active(input_slot_pairs, consumer)
        self.assertFalse(result, "_is_fan_active must return False for only 2 non-mask inputs")


# ---------------------------------------------------------------------------
# TestComputeDimsFanHeight — 1 test for fan height formula in compute_dims()
# ---------------------------------------------------------------------------


class TestComputeDimsFanHeight(unittest.TestCase):
    """compute_dims() must use max(child_heights) not sum for fan-active consumers."""

    def setUp(self):
        _reset_prefs()
        self.memo = {}
        self.snap_threshold = 8
        self.node_count = 5

    def test_compute_dims_fan_height_uses_max_not_sum(self):
        """Fan-active consumer: total height = max(child_heights)+gaps, not sum."""
        # Each subtree input has height 100; staircase gives H >> 300, fan gives H < 200.
        input_b = _StubNode(width=80, height=100)
        input_a1 = _StubNode(width=80, height=100)
        input_a2 = _StubNode(width=80, height=100)
        consumer = _StubMergeNode(width=80, height=28, xpos=500, ypos=500)
        # slot 0=B, slot 1=A1, slot 3=A2 (slot 2 reserved for mask, left None)
        consumer._inputs = [input_b, input_a1, None, input_a2]

        width, height = nl.compute_dims(
            consumer, self.memo, self.snap_threshold, self.node_count
        )
        # Staircase would give H >= 3*100 + gaps > 300.
        # Fan mode must give H < 200 (max(100) + gaps + consumer_height).
        self.assertLess(
            height, 200,
            "fan mode should use max(child_heights), not sum — "
            f"got height={height}, expected < 200"
        )


# ---------------------------------------------------------------------------
# TestPlaceSubtreeFanRoots — 2 tests for fan root and Dot row Y placement
# ---------------------------------------------------------------------------


class TestPlaceSubtreeFanRoots(unittest.TestCase):
    """place_subtree() must place all fan roots at the same Y level."""

    def setUp(self):
        _reset_prefs()
        self.memo = {}
        self.snap_threshold = 8
        self.node_count = 5

    def _build_three_input_consumer(self):
        """Return (consumer, [input_b, input_a1, input_a2], [slot_b, slot_a1, slot_a2])."""
        input_b = _StubNode(width=80, height=28)
        input_a1 = _StubNode(width=80, height=28)
        input_a2 = _StubNode(width=80, height=28)
        consumer = _StubMergeNode(width=80, height=28, xpos=500, ypos=500)
        # slot 0=B, slot 1=A1, slot 3=A2; slot 2 is mask (left None for these tests)
        consumer._inputs = [input_b, input_a1, None, input_a2]
        return consumer, [input_b, input_a1, input_a2], [0, 1, 3]

    def test_fan_roots_same_y(self):
        """All 3 fan-input subtree roots must share the same Y coordinate after placement."""
        consumer, inputs, non_mask_slots = self._build_three_input_consumer()
        nl.place_subtree(
            consumer, 500, 500, self.memo, self.snap_threshold, self.node_count
        )
        # Read the ypos of the actual input stubs (not the Dots that may have replaced them).
        # After place_subtree, consumer._inputs[slot] may be a Dot; walk through to the root.
        def _root_ypos(slot):
            node_at_slot = consumer._inputs[slot]
            if node_at_slot is not None and node_at_slot.Class() == "Dot":
                upstream = node_at_slot.input(0)
                if upstream is not None:
                    return upstream.ypos()
                return node_at_slot.ypos()
            return inputs[non_mask_slots.index(slot)].ypos()

        y_positions = [_root_ypos(slot) for slot in non_mask_slots]
        self.assertEqual(
            len(set(y_positions)), 1,
            "all fan roots must share the same Y — "
            f"got y_positions={y_positions}"
        )

    def test_fan_dot_row_uniform_y(self):
        """Routing Dots inserted for fan inputs must all be at the same Y row."""
        consumer, inputs, non_mask_slots = self._build_three_input_consumer()
        nl.place_subtree(
            consumer, 500, 500, self.memo, self.snap_threshold, self.node_count
        )
        # Collect Dot nodes that place_subtree inserted into consumer._inputs for non-mask slots.
        dot_nodes = []
        for slot in non_mask_slots:
            node_at_slot = consumer._inputs[slot]
            if node_at_slot is not None and node_at_slot.Class() == "Dot":
                dot_nodes.append(node_at_slot)

        self.assertGreaterEqual(
            len(dot_nodes), 3,
            "all 3 fan inputs (including B at slot 0) must have routing Dots — "
            f"found only {len(dot_nodes)} Dots"
        )
        dot_y_values = [dot.ypos() for dot in dot_nodes]
        self.assertEqual(
            len(set(dot_y_values)), 1,
            "all fan routing Dots must share the same Y row — "
            f"got dot_y_values={dot_y_values}"
        )


# ---------------------------------------------------------------------------
# TestMaskSideSwap — 3 tests for mask placement (left when fan, right when not)
# ---------------------------------------------------------------------------


class TestMaskSideSwap(unittest.TestCase):
    """Mask input is placed LEFT of the consumer when fan is active, RIGHT otherwise."""

    def setUp(self):
        _reset_prefs()
        self.memo = {}
        self.snap_threshold = 8
        self.node_count = 5

    def test_two_input_no_fan_regression(self):
        """n==2 (B + A): staircase is unchanged — A (input[1]) must be BELOW B (input[0]).

        In Nuke's DAG positive Y is down, so 'below' means higher Y value.
        This test is expected to PASS RED (regression guard — staircase for n==2
        is unchanged by Phase 9).
        """
        input_b = _StubNode(width=80, height=28)
        input_a = _StubNode(width=80, height=28)
        consumer = _StubMergeNode(width=80, height=28, xpos=500, ypos=500)
        # slot 0=B, slot 1=A; no mask slot populated
        consumer._inputs = [input_b, input_a]
        nl.place_subtree(
            consumer, 500, 500, self.memo, self.snap_threshold, self.node_count
        )
        # After placement: A (slot 1) must be BELOW B (slot 0), i.e. A.ypos > B.ypos
        # (because in staircase layout B is topmost / farthest from root).
        # Note: place_subtree may have inserted a Dot for slot 1 (A); walk through it.
        node_at_slot_1 = consumer._inputs[1]
        if node_at_slot_1 is not None and node_at_slot_1.Class() == "Dot":
            # The Dot is between consumer and A; A is upstream of the Dot.
            y_a_side = node_at_slot_1.ypos()
        else:
            y_a_side = input_a.ypos()
        y_b = input_b.ypos()
        self.assertGreater(
            y_a_side, y_b,
            "staircase: A-side (slot 1) must be BELOW B (slot 0) in Y — "
            f"y_b={y_b}, y_a_side={y_a_side}"
        )

    def test_mask_left_of_consumer_when_fan_active(self):
        """Fan active (3 non-mask inputs): mask input must be placed LEFT of consumer.

        'Left' means mask_xpos < consumer_xpos.
        """
        input_b = _StubNode(width=80, height=28)
        input_a1 = _StubNode(width=80, height=28)
        input_a2 = _StubNode(width=80, height=28)
        mask_input = _StubNode(width=80, height=28)
        consumer = _StubMergeNode(width=80, height=28, xpos=500, ypos=500)
        # slot 0=B, slot 1=A1, slot 2=mask, slot 3=A2
        consumer._inputs = [input_b, input_a1, mask_input, input_a2]
        consumer_xpos = 500
        nl.place_subtree(
            consumer, consumer_xpos, 500, self.memo, self.snap_threshold, self.node_count
        )
        # Read the xpos of whatever is in the mask slot after placement (may be a Dot).
        node_at_mask_slot = consumer._inputs[2]
        if node_at_mask_slot is not None and node_at_mask_slot.Class() == "Dot":
            # Walk through to the actual mask input upstream node.
            upstream = node_at_mask_slot.input(0)
            if upstream is not None:
                mask_xpos = upstream.xpos()
            else:
                mask_xpos = node_at_mask_slot.xpos()
        else:
            mask_xpos = mask_input.xpos()
        self.assertLess(
            mask_xpos, consumer_xpos,
            "when fan is active, mask must be placed LEFT of consumer — "
            f"mask_xpos={mask_xpos}, consumer_xpos={consumer_xpos}"
        )

    def test_mask_right_when_no_fan_regression(self):
        """n==2 (1 non-mask + mask): mask must stay RIGHT of consumer (no fan).

        This test is expected to PASS RED (regression guard — existing mask placement
        for n==2 is unchanged by Phase 9).
        """
        input_b = _StubNode(width=80, height=28)
        mask_input = _StubNode(width=80, height=28)
        consumer = _StubMergeNode(width=80, height=28, xpos=500, ypos=500)
        # slot 0=B, slot 1=A (None), slot 2=mask
        consumer._inputs = [input_b, None, mask_input]
        consumer_xpos = 500
        nl.place_subtree(
            consumer, consumer_xpos, 500, self.memo, self.snap_threshold, self.node_count
        )
        # Read the xpos of what is in the mask slot after placement.
        node_at_mask_slot = consumer._inputs[2]
        if node_at_mask_slot is not None and node_at_mask_slot.Class() == "Dot":
            upstream = node_at_mask_slot.input(0)
            if upstream is not None:
                mask_xpos = upstream.xpos()
            else:
                mask_xpos = node_at_mask_slot.xpos()
        else:
            mask_xpos = mask_input.xpos()
        self.assertGreater(
            mask_xpos, consumer_xpos,
            "when no fan (n==2), mask must stay RIGHT of consumer — "
            f"mask_xpos={mask_xpos}, consumer_xpos={consumer_xpos}"
        )


if __name__ == "__main__":
    unittest.main()

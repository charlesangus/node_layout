import json
import sys
import types
import unittest

# ---------------------------------------------------------------------------
# Minimal Nuke stub — injected before importing node_layout_state
# ---------------------------------------------------------------------------

nuke_stub = types.ModuleType('nuke')
nuke_stub.INVISIBLE = 0x01  # arbitrary non-zero flag value


class FakeKnob:
    def __init__(self, kind, name, label=''):
        self.kind = kind
        self.name = name
        self._value = ''
        self._flags = 0

    def value(self):
        return self._value

    def setValue(self, v):
        self._value = v

    def setFlag(self, flag):
        self._flags |= flag


class FakeNode:
    def __init__(self):
        self._knobs = {}
        self._added_knobs = []  # ordered list of knob objects

    def knob(self, name):
        return self._knobs.get(name)

    def addKnob(self, k):
        if k.name not in self._knobs:
            self._knobs[k.name] = k
            self._added_knobs.append(k)

    def removeKnob(self, k):
        if k.name in self._knobs:
            del self._knobs[k.name]
            self._added_knobs.remove(k)

    def __getitem__(self, name):
        return self._knobs[name]


def _make_tab(name='node_layout_tab', label='Node Layout'):
    return FakeKnob('Tab_Knob', name, label)


def _make_state_knob(name='node_layout_state', label='Node Layout State'):
    return FakeKnob('String_Knob', name, label)


def _make_diamond_knob(name='node_layout_diamond_dot', label='Diamond Dot Marker'):
    return FakeKnob('Int_Knob', name, label)


# Inject stub factories into nuke stub
nuke_stub.Tab_Knob = _make_tab
nuke_stub.String_Knob = _make_state_knob

sys.modules['nuke'] = nuke_stub

import node_layout_state  # noqa: E402 — must come after stub injection


def _restore_nuke_stub():
    """Re-inject our nuke stub into sys.modules in case other test files replaced it."""
    sys.modules['nuke'] = nuke_stub


# ---------------------------------------------------------------------------
# FakePrefs helper for scheme resolution tests
# ---------------------------------------------------------------------------

class FakePrefs:
    """Simple dict-backed prefs object with a .get(key) method."""

    def __init__(self, data):
        self._data = data

    def get(self, key):
        return self._data[key]


_STANDARD_PREFS = FakePrefs({
    "compact_multiplier": 0.7,
    "normal_multiplier": 1.0,
    "loose_multiplier": 1.5,
})


# ---------------------------------------------------------------------------
# TestReadNodeState
# ---------------------------------------------------------------------------

class TestReadNodeState(unittest.TestCase):

    def test_returns_defaults_when_knob_absent(self):
        node = FakeNode()
        result = node_layout_state.read_node_state(node)
        self.assertEqual(result, {
            "scheme": "normal",
            "mode": "vertical",
            "h_scale": 1.0,
            "v_scale": 1.0,
        })

    def test_returns_defaults_when_knob_empty(self):
        node = FakeNode()
        # Add a state knob with empty value
        knob = _make_state_knob()
        knob.setValue('')
        node._knobs['node_layout_state'] = knob
        result = node_layout_state.read_node_state(node)
        self.assertEqual(result, {
            "scheme": "normal",
            "mode": "vertical",
            "h_scale": 1.0,
            "v_scale": 1.0,
        })

    def test_merges_stored_with_defaults(self):
        """Partial JSON fills in missing keys from defaults."""
        node = FakeNode()
        knob = _make_state_knob()
        knob.setValue(json.dumps({"scheme": "compact"}))
        node._knobs['node_layout_state'] = knob
        result = node_layout_state.read_node_state(node)
        self.assertEqual(result, {
            "scheme": "compact",
            "mode": "vertical",
            "h_scale": 1.0,
            "v_scale": 1.0,
        })

    def test_returns_defaults_on_malformed_json(self):
        node = FakeNode()
        knob = _make_state_knob()
        knob.setValue("not-json")
        node._knobs['node_layout_state'] = knob
        result = node_layout_state.read_node_state(node)
        self.assertEqual(result, {
            "scheme": "normal",
            "mode": "vertical",
            "h_scale": 1.0,
            "v_scale": 1.0,
        })


# ---------------------------------------------------------------------------
# TestWriteNodeState
# ---------------------------------------------------------------------------

class TestWriteNodeState(unittest.TestCase):

    def setUp(self):
        # Other test files may replace sys.modules['nuke'] with their own stubs.
        # Re-inject our stub before each test that exercises write/clear code paths.
        _restore_nuke_stub()

    def test_creates_tab_and_state_knob_when_absent(self):
        node = FakeNode()
        state = {"scheme": "compact", "mode": "vertical", "h_scale": 1.0, "v_scale": 1.0}
        node_layout_state.write_node_state(node, state)
        self.assertIsNotNone(node.knob('node_layout_tab'))
        self.assertIsNotNone(node.knob('node_layout_state'))

    def test_does_not_duplicate_knobs_on_second_call(self):
        node = FakeNode()
        state = {"scheme": "compact", "mode": "vertical", "h_scale": 1.0, "v_scale": 1.0}
        node_layout_state.write_node_state(node, state)
        node_layout_state.write_node_state(node, state)
        # tab + state knob only — no duplicates
        self.assertEqual(len(node._added_knobs), 2)

    def test_sets_invisible_flag_on_state_knob(self):
        node = FakeNode()
        state = {"scheme": "normal", "mode": "vertical", "h_scale": 1.0, "v_scale": 1.0}
        node_layout_state.write_node_state(node, state)
        state_knob = node.knob('node_layout_state')
        self.assertIsNotNone(state_knob)
        # INVISIBLE flag must be set
        self.assertTrue(state_knob._flags & nuke_stub.INVISIBLE)

    def test_json_value_roundtrips(self):
        node = FakeNode()
        state = {"scheme": "loose", "mode": "horizontal", "h_scale": 0.8, "v_scale": 1.2}
        node_layout_state.write_node_state(node, state)
        raw_value = node.knob('node_layout_state').value()
        self.assertEqual(json.loads(raw_value), state)


# ---------------------------------------------------------------------------
# TestClearNodeState
# ---------------------------------------------------------------------------

class TestClearNodeState(unittest.TestCase):

    def setUp(self):
        _restore_nuke_stub()

    def _node_with_state_only(self):
        """Return a node that has tab + state knob but no diamond dot."""
        node = FakeNode()
        tab = _make_tab()
        state_knob = _make_state_knob()
        node._knobs['node_layout_tab'] = tab
        node._knobs['node_layout_state'] = state_knob
        node._added_knobs = [tab, state_knob]
        return node

    def _node_with_state_and_diamond(self):
        """Return a node that has tab + state knob + diamond dot."""
        node = FakeNode()
        tab = _make_tab()
        state_knob = _make_state_knob()
        diamond = _make_diamond_knob()
        node._knobs['node_layout_tab'] = tab
        node._knobs['node_layout_state'] = state_knob
        node._knobs['node_layout_diamond_dot'] = diamond
        node._added_knobs = [tab, state_knob, diamond]
        return node

    def test_removes_state_knob(self):
        node = self._node_with_state_only()
        node_layout_state.clear_node_state(node)
        self.assertIsNone(node.knob('node_layout_state'))

    def test_removes_tab_when_diamond_dot_absent(self):
        node = self._node_with_state_only()
        node_layout_state.clear_node_state(node)
        self.assertIsNone(node.knob('node_layout_tab'))

    def test_preserves_tab_when_diamond_dot_present(self):
        node = self._node_with_state_and_diamond()
        node_layout_state.clear_node_state(node)
        # state knob removed, but tab must stay because diamond dot is still there
        self.assertIsNone(node.knob('node_layout_state'))
        self.assertIsNotNone(node.knob('node_layout_tab'))


# ---------------------------------------------------------------------------
# TestSchemeResolution
# ---------------------------------------------------------------------------

class TestSchemeResolution(unittest.TestCase):

    def test_scheme_name_to_multiplier_compact(self):
        result = node_layout_state.scheme_name_to_multiplier("compact", _STANDARD_PREFS)
        self.assertEqual(result, 0.7)

    def test_scheme_name_to_multiplier_normal(self):
        result = node_layout_state.scheme_name_to_multiplier("normal", _STANDARD_PREFS)
        self.assertEqual(result, 1.0)

    def test_scheme_name_to_multiplier_loose(self):
        result = node_layout_state.scheme_name_to_multiplier("loose", _STANDARD_PREFS)
        self.assertEqual(result, 1.5)

    def test_scheme_name_to_multiplier_unknown_fallback(self):
        result = node_layout_state.scheme_name_to_multiplier("unknown", _STANDARD_PREFS)
        self.assertEqual(result, 1.0)  # falls back to normal_multiplier

    def test_multiplier_to_scheme_name_roundtrip(self):
        for name in ("compact", "normal", "loose"):
            multiplier = node_layout_state.scheme_name_to_multiplier(name, _STANDARD_PREFS)
            result = node_layout_state.multiplier_to_scheme_name(multiplier, _STANDARD_PREFS)
            self.assertEqual(result, name, f"Round-trip failed for {name}")

    def test_multiplier_to_scheme_name_no_match_returns_normal(self):
        result = node_layout_state.multiplier_to_scheme_name(99.9, _STANDARD_PREFS)
        self.assertEqual(result, "normal")


# ---------------------------------------------------------------------------
# TestScaleAccumulation
# ---------------------------------------------------------------------------

class TestScaleAccumulation(unittest.TestCase):

    def setUp(self):
        _restore_nuke_stub()

    def test_scale_accumulates_without_drift(self):
        """round(0.8 * 0.8, 10) must equal 0.64 with no float drift."""
        self.assertEqual(round(0.8 * 0.8, 10), 0.64)

    def test_two_shrink_sequence_stores_correct_value(self):
        """Simulate two consecutive 0.8 shrink calls on h_scale."""
        node = FakeNode()
        # First shrink: h_scale 1.0 -> 0.8
        state_after_first = {"scheme": "normal", "mode": "vertical", "h_scale": 0.8, "v_scale": 1.0}
        node_layout_state.write_node_state(node, state_after_first)
        read_back = node_layout_state.read_node_state(node)
        self.assertAlmostEqual(read_back["h_scale"], 0.8, places=9)

        # Second shrink: h_scale 0.8 -> 0.64
        new_h_scale = round(read_back["h_scale"] * 0.8, 10)
        state_after_second = {
            "scheme": "normal", "mode": "vertical", "h_scale": new_h_scale, "v_scale": 1.0,
        }
        node_layout_state.write_node_state(node, state_after_second)
        final = node_layout_state.read_node_state(node)
        self.assertAlmostEqual(final["h_scale"], 0.64, places=9)


# ---------------------------------------------------------------------------
# TestFreezeGroupState
# ---------------------------------------------------------------------------

class TestFreezeGroupState(unittest.TestCase):

    def setUp(self):
        _restore_nuke_stub()

    def test_default_state_contains_freeze_group_key(self):
        self.assertIn("freeze_group", node_layout_state._DEFAULT_STATE)
        self.assertIsNone(node_layout_state._DEFAULT_STATE["freeze_group"])

    def test_read_node_state_returns_freeze_group_none_for_new_node(self):
        node = FakeNode()
        result = node_layout_state.read_node_state(node)
        self.assertIn("freeze_group", result)
        self.assertIsNone(result["freeze_group"])

    def test_read_node_state_returns_freeze_group_none_for_old_node_without_key(self):
        """Simulate an old node whose JSON has no freeze_group key."""
        node = FakeNode()
        knob = _make_state_knob()
        knob.setValue(json.dumps({"scheme": "compact", "mode": "vertical", "h_scale": 1.0, "v_scale": 1.0}))
        node._knobs['node_layout_state'] = knob
        result = node_layout_state.read_node_state(node)
        self.assertIn("freeze_group", result)
        self.assertIsNone(result["freeze_group"])

    def test_freeze_group_roundtrips_through_write_and_read(self):
        node = FakeNode()
        test_uuid = "a3f1c2e4-8b7d-4e6f-9c2a-1d5e3b7f0a4c"
        state = dict(node_layout_state._DEFAULT_STATE)
        state["freeze_group"] = test_uuid
        node_layout_state.write_node_state(node, state)
        result = node_layout_state.read_node_state(node)
        self.assertEqual(result["freeze_group"], test_uuid)

    def test_read_freeze_group_returns_none_for_unfrozen_node(self):
        node = FakeNode()
        result = node_layout_state.read_freeze_group(node)
        self.assertIsNone(result)

    def test_write_freeze_group_and_read_freeze_group_roundtrip(self):
        node = FakeNode()
        test_uuid = "b4c2d3e5-9a8b-4f7c-0d1e-2f3a4b5c6d7e"
        node_layout_state.write_freeze_group(node, test_uuid)
        result = node_layout_state.read_freeze_group(node)
        self.assertEqual(result, test_uuid)

    def test_clear_freeze_group_sets_none(self):
        node = FakeNode()
        node_layout_state.write_freeze_group(node, "some-uuid-value")
        node_layout_state.clear_freeze_group(node)
        result = node_layout_state.read_freeze_group(node)
        self.assertIsNone(result)

    def test_freeze_group_does_not_affect_other_state_keys(self):
        node = FakeNode()
        node_layout_state.write_freeze_group(node, "test-uuid")
        result = node_layout_state.read_node_state(node)
        self.assertEqual(result["scheme"], "normal")
        self.assertEqual(result["mode"], "vertical")
        self.assertEqual(result["h_scale"], 1.0)
        self.assertEqual(result["v_scale"], 1.0)


if __name__ == '__main__':
    unittest.main()

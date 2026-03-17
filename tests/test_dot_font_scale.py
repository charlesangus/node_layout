"""RED test scaffold for _dot_font_scale() in node_layout.py (08-01 TDD).

These tests verify the dot font-size margin scaling contract (LAYOUT-03):
- _dot_font_scale(node, slot) returns a float multiplier based on the first
  labeled Dot found by walking upstream from node.input(slot)
- _subtree_margin() and _horizontal_margin() incorporate the font multiplier
- Default-font Dots (font_size == reference_size) produce no change (multiplier 1.0)

All 11 tests in this file MUST FAIL RED before any production code is written.
"""
import importlib.util
import os
import sys
import types
import unittest

NODE_LAYOUT_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")
NODE_LAYOUT_PREFS_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout_prefs.py")


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

    def inputLabel(self, index):
        return ""

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

# Load node_layout_prefs (no Nuke dependency) so node_layout.py import resolves it.
_prefs_spec = importlib.util.spec_from_file_location("node_layout_prefs", NODE_LAYOUT_PREFS_PATH)
_node_layout_prefs_module = importlib.util.module_from_spec(_prefs_spec)
_prefs_spec.loader.exec_module(_node_layout_prefs_module)
sys.modules["node_layout_prefs"] = _node_layout_prefs_module

_module_path = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")
_spec = importlib.util.spec_from_file_location("node_layout_dot_font_scale", _module_path)
_nl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_nl)


def _reset_prefs():
    """Restore prefs to DEFAULTS without touching any file."""
    singleton = _node_layout_prefs_module.prefs_singleton
    for key, default_value in _node_layout_prefs_module.DEFAULTS.items():
        singleton.set(key, default_value)


# ---------------------------------------------------------------------------
# Stub specialisations for Dot nodes
# ---------------------------------------------------------------------------


class _StubDotNode(_StubNode):
    """A Dot node stub with label and note_font_size knobs.

    Args:
        label: The label knob value (empty string = unlabeled Dot).
        font_size: The note_font_size knob value.
        upstream: Another node returned by input(0), or None.
    """

    def __init__(self, label="", font_size=20, upstream=None):
        super().__init__(node_class="Dot")
        self._knobs["label"] = _StubKnob(label)
        self._knobs["note_font_size"] = _StubKnob(font_size)
        self._upstream = upstream

    def Class(self):
        return "Dot"

    def input(self, index):
        if index == 0:
            return self._upstream
        return None


class _StubDotNodeMissingFontKnob(_StubDotNode):
    """A Dot node where reading the note_font_size knob raises KeyError.

    The label knob is present and non-empty so the walker finds this Dot and
    attempts to read the font size — at which point it must fall back gracefully.
    """

    def __getitem__(self, name):
        if name == "note_font_size":
            raise KeyError(name)
        return super().__getitem__(name)


class _StubNonDotNode(_StubNode):
    """A non-Dot node that breaks the upstream Dot walk."""

    def __init__(self):
        super().__init__(node_class="Grade")

    def Class(self):
        return "Grade"


# ---------------------------------------------------------------------------
# TestDotFontScaleUnit — 8 tests that exercise _dot_font_scale directly
# ---------------------------------------------------------------------------


class TestDotFontScaleUnit(unittest.TestCase):
    """Unit tests for _dot_font_scale(node, slot)."""

    def setUp(self):
        _reset_prefs()

    def test_no_dot_returns_1(self):
        """When slot input is None, _dot_font_scale returns 1.0."""
        node = _StubNode(node_class="Grade")
        # input(0) returns None (default _inputs is empty)
        result = _nl._dot_font_scale(node, 0)
        self.assertEqual(result, 1.0,
                         f"Expected 1.0 when slot input is None, got {result}")

    def test_unlabeled_dot_chain_returns_1(self):
        """A chain of unlabeled Dots produces a multiplier of 1.0."""
        dot2 = _StubDotNode(label="", font_size=40, upstream=None)
        dot1 = _StubDotNode(label="", font_size=40, upstream=dot2)
        node = _StubNode(node_class="Grade")
        node._inputs = [dot1]
        result = _nl._dot_font_scale(node, 0)
        self.assertEqual(result, 1.0,
                         f"Expected 1.0 for all-unlabeled Dot chain, got {result}")

    def test_labeled_dot_font_40_reference_20(self):
        """Labeled Dot with font_size=40 and reference=20 gives multiplier 2.0."""
        dot = _StubDotNode(label="BG elements", font_size=40, upstream=None)
        node = _StubNode(node_class="Grade")
        node._inputs = [dot]
        result = _nl._dot_font_scale(node, 0)
        self.assertEqual(result, 2.0,
                         f"Expected 2.0 for font_size=40 / reference=20, got {result}")

    def test_floor_at_1(self):
        """Labeled Dot with font_size=10 (below reference 20) produces multiplier 1.0 (floor)."""
        dot = _StubDotNode(label="BG elements", font_size=10, upstream=None)
        node = _StubNode(node_class="Grade")
        node._inputs = [dot]
        result = _nl._dot_font_scale(node, 0)
        self.assertEqual(result, 1.0,
                         f"Expected 1.0 floor for font_size=10 / reference=20, got {result}")

    def test_cap_at_4(self):
        """Labeled Dot with font_size=200 (very large) produces multiplier capped at 4.0."""
        dot = _StubDotNode(label="BG elements", font_size=200, upstream=None)
        node = _StubNode(node_class="Grade")
        node._inputs = [dot]
        result = _nl._dot_font_scale(node, 0)
        self.assertEqual(result, 4.0,
                         f"Expected 4.0 cap for font_size=200 / reference=20, got {result}")

    def test_walk_skips_unlabeled_finds_labeled(self):
        """Walker skips unlabeled Dot1, finds labeled Dot2, returns 2.0."""
        dot2 = _StubDotNode(label="BG elements", font_size=40, upstream=None)
        dot1 = _StubDotNode(label="", font_size=99, upstream=dot2)
        node = _StubNode(node_class="Grade")
        node._inputs = [dot1]
        result = _nl._dot_font_scale(node, 0)
        self.assertEqual(result, 2.0,
                         f"Expected 2.0 from Dot2 after skipping unlabeled Dot1, got {result}")

    def test_walk_stops_at_non_dot(self):
        """Chain breaks at a non-Dot node; labeled Dot3 beyond it is not reachable."""
        dot3 = _StubDotNode(label="BG elements", font_size=40, upstream=None)
        grade = _StubNonDotNode()
        grade._inputs = [dot3]
        dot1 = _StubDotNode(label="", font_size=99, upstream=grade)
        node = _StubNode(node_class="Grade")
        node._inputs = [dot1]
        result = _nl._dot_font_scale(node, 0)
        self.assertEqual(
            result, 1.0,
            f"Expected 1.0 when chain broke at Grade before labeled Dot3, got {result}",
        )

    def test_missing_knob_fallback(self):
        """When note_font_size knob raises KeyError, _dot_font_scale returns 1.0."""
        dot = _StubDotNodeMissingFontKnob(label="BG elements", font_size=40, upstream=None)
        node = _StubNode(node_class="Grade")
        node._inputs = [dot]
        result = _nl._dot_font_scale(node, 0)
        self.assertEqual(result, 1.0,
                         f"Expected 1.0 fallback when note_font_size knob is absent, got {result}")


# ---------------------------------------------------------------------------
# TestSubtreeMarginFontScale — 1 integration test
# ---------------------------------------------------------------------------


class TestSubtreeMarginFontScale(unittest.TestCase):
    """Integration: _subtree_margin() must scale up for a labeled Dot with large font."""

    def setUp(self):
        _reset_prefs()

    def test_font_scale_applies(self):
        """_subtree_margin with a 40px-font labeled Dot must exceed the 20px-font baseline."""
        # Baseline: node whose slot 0 input is a Dot with default font size (= reference)
        baseline_dot = _StubDotNode(label="BG elements", font_size=20, upstream=None)
        node_baseline = _StubNode(node_class="Grade")
        node_baseline._inputs = [baseline_dot]

        # Scaled: same setup but font_size = 40 (2× reference)
        scaled_dot = _StubDotNode(label="BG elements", font_size=40, upstream=None)
        node_scaled = _StubNode(node_class="Grade")
        node_scaled._inputs = [scaled_dot]

        node_count = 9
        mode_multiplier = 1.0

        baseline_margin = _nl._subtree_margin(node_baseline, 0, node_count,
                                               mode_multiplier=mode_multiplier)
        scaled_margin = _nl._subtree_margin(node_scaled, 0, node_count,
                                             mode_multiplier=mode_multiplier)

        self.assertGreater(
            scaled_margin,
            baseline_margin,
            f"Expected scaled_margin ({scaled_margin}) > baseline_margin ({baseline_margin}) "
            f"when font_size=40 vs font_size=20 at reference=20",
        )


# ---------------------------------------------------------------------------
# TestHorizontalMarginFontScale — 1 integration test
# ---------------------------------------------------------------------------


class TestHorizontalMarginFontScale(unittest.TestCase):
    """Integration: _horizontal_margin() must scale up for a labeled Dot with large font."""

    def setUp(self):
        _reset_prefs()

    def test_font_scale_applies(self):
        """_horizontal_margin with a 40px-font labeled Dot must exceed the 20px-font baseline."""
        baseline_dot = _StubDotNode(label="BG elements", font_size=20, upstream=None)
        node_baseline = _StubNode(node_class="Grade")
        node_baseline._inputs = [baseline_dot]

        scaled_dot = _StubDotNode(label="BG elements", font_size=40, upstream=None)
        node_scaled = _StubNode(node_class="Grade")
        node_scaled._inputs = [scaled_dot]

        baseline_margin = _nl._horizontal_margin(node_baseline, 0)
        scaled_margin = _nl._horizontal_margin(node_scaled, 0)

        self.assertGreater(
            scaled_margin,
            baseline_margin,
            f"Expected scaled_margin ({scaled_margin}) > baseline_margin ({baseline_margin}) "
            f"when font_size=40 vs font_size=20 at reference=20",
        )


# ---------------------------------------------------------------------------
# TestNoRegression — 1 regression test
# ---------------------------------------------------------------------------


class TestNoRegression(unittest.TestCase):
    """A Dot at the reference font size must not change margins vs. no-Dot baseline."""

    def setUp(self):
        _reset_prefs()

    def test_default_font_no_change(self):
        """Dot with font_size == reference_size (20) produces identical margins to
        no-Dot baseline."""
        # No-Dot baseline: slot input is a plain Grade node (not a Dot)
        grade_input = _StubNonDotNode()
        node_no_dot = _StubNode(node_class="Grade")
        node_no_dot._inputs = [grade_input]

        # Reference-size Dot: font_size equals reference (multiplier should be 1.0)
        reference_dot = _StubDotNode(label="BG elements", font_size=20, upstream=None)
        node_ref_dot = _StubNode(node_class="Grade")
        node_ref_dot._inputs = [reference_dot]

        node_count = 9
        mode_multiplier = 1.0

        baseline_subtree = _nl._subtree_margin(node_no_dot, 0, node_count,
                                                mode_multiplier=mode_multiplier)
        ref_subtree = _nl._subtree_margin(node_ref_dot, 0, node_count,
                                           mode_multiplier=mode_multiplier)

        baseline_horizontal = _nl._horizontal_margin(node_no_dot, 0)
        ref_horizontal = _nl._horizontal_margin(node_ref_dot, 0)

        self.assertEqual(
            ref_subtree,
            baseline_subtree,
            f"_subtree_margin changed with reference-size Dot: "
            f"ref={ref_subtree}, baseline={baseline_subtree}",
        )
        self.assertEqual(
            ref_horizontal,
            baseline_horizontal,
            f"_horizontal_margin changed with reference-size Dot: "
            f"ref={ref_horizontal}, baseline={baseline_horizontal}",
        )


if __name__ == "__main__":
    unittest.main()

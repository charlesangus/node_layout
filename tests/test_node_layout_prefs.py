"""Tests for NodeLayoutPrefs — JSON-backed preferences singleton.

Verifies:
- Default values returned when no prefs file exists
- Round-trip persistence: set() -> save() -> reload new instance -> get() returns saved value
- Partial file fallback: missing keys in saved file fall back to DEFAULTS
- File-not-found at init: no FileNotFoundError, returns DEFAULTS
- set() + save() writes valid JSON readable by json.load()
- reload() picks up changes written to the prefs file since last load

All tests use temporary files and never touch ~/.nuke/node_layout_prefs.json.

NOTE: If you have an existing ~/.nuke/node_layout_prefs.json from v1.0, delete it to see
the rebalanced defaults (base_subtree_margin=200, loose_gap_multiplier=8.0).
"""
import json
import os
import tempfile
import unittest

NODE_LAYOUT_PREFS_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout_prefs.py")


def _import_prefs_module():
    """Import node_layout_prefs from its absolute path without going through sys.path."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("node_layout_prefs", NODE_LAYOUT_PREFS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestNodeLayoutPrefsDefaults(unittest.TestCase):
    """Default values returned when no prefs file exists."""

    def setUp(self):
        self.prefs_module = _import_prefs_module()
        # Use a path that does not exist so _load() falls back to DEFAULTS
        self.nonexistent_path = "/tmp/node_layout_prefs_test_nonexistent_DONOTCREATE.json"
        self.instance = self.prefs_module.NodeLayoutPrefs(prefs_file=self.nonexistent_path)

    def tearDown(self):
        # Ensure the test never created the file
        if os.path.exists(self.nonexistent_path):
            os.remove(self.nonexistent_path)

    def test_default_base_subtree_margin(self):
        """get('base_subtree_margin') returns 200 when no prefs file exists."""
        self.assertEqual(self.instance.get("base_subtree_margin"), 200)

    def test_default_compact_multiplier(self):
        """get('compact_multiplier') returns 0.6 when no prefs file exists."""
        self.assertAlmostEqual(self.instance.get("compact_multiplier"), 0.6)

    def test_default_normal_multiplier(self):
        """get('normal_multiplier') returns 1.0 when no prefs file exists."""
        self.assertAlmostEqual(self.instance.get("normal_multiplier"), 1.0)

    def test_default_loose_multiplier(self):
        """get('loose_multiplier') returns 1.5 when no prefs file exists."""
        self.assertAlmostEqual(self.instance.get("loose_multiplier"), 1.5)

    def test_default_loose_gap_multiplier(self):
        """get('loose_gap_multiplier') returns 8.0 when no prefs file exists."""
        self.assertAlmostEqual(self.instance.get("loose_gap_multiplier"), 8.0)

    def test_default_mask_input_ratio(self):
        """get('mask_input_ratio') is approximately 0.333 when no prefs file exists."""
        self.assertAlmostEqual(self.instance.get("mask_input_ratio"), 0.333, places=3)

    def test_default_scaling_reference_count(self):
        """get('scaling_reference_count') returns 150 when no prefs file exists."""
        self.assertEqual(self.instance.get("scaling_reference_count"), 150)

    def test_default_horizontal_subtree_gap(self):
        """get('horizontal_subtree_gap') returns 250 when no prefs file exists."""
        self.assertEqual(self.instance.get("horizontal_subtree_gap"), 250)

    def test_default_horizontal_mask_gap(self):
        """get('horizontal_mask_gap') returns 50 when no prefs file exists."""
        self.assertEqual(self.instance.get("horizontal_mask_gap"), 50)

    def test_default_dot_font_reference_size(self):
        """get('dot_font_reference_size') returns 20 when no prefs file exists."""
        self.assertEqual(self.instance.get("dot_font_reference_size"), 20)

    def test_no_file_not_found_error_on_init(self):
        """Creating NodeLayoutPrefs with a nonexistent file raises no exception."""
        # setUp already created it; if we get here, no exception was raised
        self.assertIsNotNone(self.instance)

    def test_default_hint_popup_delay_ms(self):
        """get('hint_popup_delay_ms') returns 0 when no prefs file exists."""
        self.assertEqual(self.instance.get("hint_popup_delay_ms"), 0)

    def test_default_keyboard_layout(self):
        """get('keyboard_layout') returns qwerty when no prefs file exists."""
        self.assertEqual(self.instance.get("keyboard_layout"), "qwerty")


class TestNodeLayoutPrefsDefaults_DictContents(unittest.TestCase):
    """DEFAULTS dict must contain all expected keys."""

    def setUp(self):
        self.prefs_module = _import_prefs_module()

    def test_defaults_contains_all_thirteen_keys(self):
        """DEFAULTS must contain exactly the 13 required preference keys."""
        required_keys = {
            "base_subtree_margin",
            "horizontal_subtree_gap",
            "horizontal_side_vertical_gap",
            "horizontal_mask_gap",
            "dot_font_reference_size",
            "compact_multiplier",
            "normal_multiplier",
            "loose_multiplier",
            "loose_gap_multiplier",
            "mask_input_ratio",
            "scaling_reference_count",
            "hint_popup_delay_ms",
            "keyboard_layout",
        }
        actual_keys = set(self.prefs_module.DEFAULTS.keys())
        missing_keys = required_keys - actual_keys
        self.assertEqual(
            missing_keys,
            set(),
            f"DEFAULTS is missing required keys: {missing_keys}",
        )
        self.assertEqual(
            len(actual_keys),
            13,
            f"DEFAULTS should have exactly 13 keys, got {len(actual_keys)}: {actual_keys}",
        )


class TestNodeLayoutPrefsRoundTrip(unittest.TestCase):
    """Round-trip persistence: set -> save -> reload from same file -> get."""

    def setUp(self):
        self.prefs_module = _import_prefs_module()
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, prefix="test_node_layout_prefs_"
        ) as temp_file:
            self.temp_path = temp_file.name

    def tearDown(self):
        if os.path.exists(self.temp_path):
            os.remove(self.temp_path)

    def test_round_trip_base_subtree_margin(self):
        """set('base_subtree_margin', 200) -> save() -> new instance -> get() returns 200."""
        first_instance = self.prefs_module.NodeLayoutPrefs(prefs_file=self.temp_path)
        first_instance.set("base_subtree_margin", 200)
        first_instance.save()

        second_instance = self.prefs_module.NodeLayoutPrefs(prefs_file=self.temp_path)
        self.assertEqual(second_instance.get("base_subtree_margin"), 200)

    def test_round_trip_compact_multiplier(self):
        """set('compact_multiplier', 0.8) -> save() -> new instance -> get() returns 0.8."""
        first_instance = self.prefs_module.NodeLayoutPrefs(prefs_file=self.temp_path)
        first_instance.set("compact_multiplier", 0.8)
        first_instance.save()

        second_instance = self.prefs_module.NodeLayoutPrefs(prefs_file=self.temp_path)
        self.assertAlmostEqual(second_instance.get("compact_multiplier"), 0.8)

    def test_save_writes_valid_json(self):
        """save() writes a file that json.load() can read without error."""
        instance = self.prefs_module.NodeLayoutPrefs(prefs_file=self.temp_path)
        instance.set("base_subtree_margin", 500)
        instance.save()

        with open(self.temp_path, "r") as saved_file:
            loaded_data = json.load(saved_file)

        self.assertEqual(loaded_data.get("base_subtree_margin"), 500)

    def test_reload_picks_up_external_changes(self):
        """reload() picks up changes written to the prefs file since last load."""
        instance = self.prefs_module.NodeLayoutPrefs(prefs_file=self.temp_path)
        # Externally write a new value to the file
        external_data = {"base_subtree_margin": 999}
        with open(self.temp_path, "w") as prefs_file:
            json.dump(external_data, prefs_file)

        instance.reload()
        self.assertEqual(instance.get("base_subtree_margin"), 999)


class TestNewPrefsRoundTrip(unittest.TestCase):
    """Round-trip tests for the three new preference keys added in v1.1 Phase 6."""

    def setUp(self):
        self.prefs_module = _import_prefs_module()
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, prefix="test_node_layout_prefs_new_"
        ) as temp_file:
            self.temp_path = temp_file.name

    def tearDown(self):
        if os.path.exists(self.temp_path):
            os.remove(self.temp_path)

    def test_round_trip_horizontal_subtree_gap(self):
        """set('horizontal_subtree_gap', 200) -> save() -> reload() -> get() returns 200."""
        instance = self.prefs_module.NodeLayoutPrefs(prefs_file=self.temp_path)
        instance.set("horizontal_subtree_gap", 200)
        instance.save()
        instance.reload()
        self.assertEqual(instance.get("horizontal_subtree_gap"), 200)

    def test_round_trip_horizontal_mask_gap(self):
        """set('horizontal_mask_gap', 75) -> save() -> new instance -> get() returns 75."""
        first_instance = self.prefs_module.NodeLayoutPrefs(prefs_file=self.temp_path)
        first_instance.set("horizontal_mask_gap", 75)
        first_instance.save()

        second_instance = self.prefs_module.NodeLayoutPrefs(prefs_file=self.temp_path)
        self.assertEqual(second_instance.get("horizontal_mask_gap"), 75)

    def test_round_trip_dot_font_reference_size(self):
        """set('dot_font_reference_size', 24) -> save() -> new instance -> get() returns 24."""
        first_instance = self.prefs_module.NodeLayoutPrefs(prefs_file=self.temp_path)
        first_instance.set("dot_font_reference_size", 24)
        first_instance.save()

        second_instance = self.prefs_module.NodeLayoutPrefs(prefs_file=self.temp_path)
        self.assertEqual(second_instance.get("dot_font_reference_size"), 24)

    def test_round_trip_hint_popup_delay_ms(self):
        """set('hint_popup_delay_ms', 500) -> save() -> new instance -> get() returns 500."""
        first_instance = self.prefs_module.NodeLayoutPrefs(prefs_file=self.temp_path)
        first_instance.set("hint_popup_delay_ms", 500)
        first_instance.save()
        second_instance = self.prefs_module.NodeLayoutPrefs(prefs_file=self.temp_path)
        self.assertEqual(second_instance.get("hint_popup_delay_ms"), 500)

    def test_round_trip_keyboard_layout(self):
        """set('keyboard_layout', 'azerty') -> save() -> new instance -> get() returns azerty."""
        first_instance = self.prefs_module.NodeLayoutPrefs(prefs_file=self.temp_path)
        first_instance.set("keyboard_layout", "azerty")
        first_instance.save()
        second_instance = self.prefs_module.NodeLayoutPrefs(prefs_file=self.temp_path)
        self.assertEqual(second_instance.get("keyboard_layout"), "azerty")

    def test_invalid_keyboard_layout_falls_back_to_qwerty(self):
        """Unknown keyboard_layout values in JSON are ignored."""
        with open(self.temp_path, "w") as prefs_file:
            json.dump({"keyboard_layout": "dvorak"}, prefs_file)
        instance = self.prefs_module.NodeLayoutPrefs(prefs_file=self.temp_path)
        self.assertEqual(instance.get("keyboard_layout"), "qwerty")


class TestNodeLayoutPrefsPartialFileFallback(unittest.TestCase):
    """Missing keys in a saved file fall back to DEFAULTS values, not KeyError."""

    def setUp(self):
        self.prefs_module = _import_prefs_module()
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, prefix="test_node_layout_prefs_partial_"
        ) as temp_file:
            self.temp_path = temp_file.name

    def tearDown(self):
        if os.path.exists(self.temp_path):
            os.remove(self.temp_path)

    def test_missing_keys_fall_back_to_defaults(self):
        """A file with only one key still returns DEFAULTS for all other keys."""
        # Write a partial file with only one key
        partial_data = {"base_subtree_margin": 400}
        with open(self.temp_path, "w") as prefs_file:
            json.dump(partial_data, prefs_file)

        instance = self.prefs_module.NodeLayoutPrefs(prefs_file=self.temp_path)

        # The saved key is loaded correctly
        self.assertEqual(instance.get("base_subtree_margin"), 400)

        # All other keys fall back to DEFAULTS (no KeyError)
        self.assertAlmostEqual(instance.get("compact_multiplier"), 0.6)
        self.assertAlmostEqual(instance.get("normal_multiplier"), 1.0)
        self.assertAlmostEqual(instance.get("loose_multiplier"), 1.5)
        self.assertAlmostEqual(instance.get("loose_gap_multiplier"), 8.0)
        self.assertAlmostEqual(instance.get("mask_input_ratio"), 0.333, places=3)
        self.assertEqual(instance.get("scaling_reference_count"), 150)

        # New keys also fall back to DEFAULTS
        self.assertEqual(instance.get("horizontal_subtree_gap"), 250)
        self.assertEqual(instance.get("horizontal_side_vertical_gap"), 150)
        self.assertEqual(instance.get("horizontal_mask_gap"), 50)
        self.assertEqual(instance.get("dot_font_reference_size"), 20)
        self.assertEqual(instance.get("hint_popup_delay_ms"), 0)
        self.assertEqual(instance.get("keyboard_layout"), "qwerty")


class TestNodeLayoutPrefsExports(unittest.TestCase):
    """Module-level exports: NodeLayoutPrefs, DEFAULTS, PREFS_FILE, prefs_singleton."""

    def setUp(self):
        self.prefs_module = _import_prefs_module()

    def test_module_exports_node_layout_prefs_class(self):
        """node_layout_prefs module must export NodeLayoutPrefs class."""
        self.assertTrue(
            hasattr(self.prefs_module, "NodeLayoutPrefs"),
            "node_layout_prefs must export NodeLayoutPrefs",
        )

    def test_module_exports_defaults(self):
        """node_layout_prefs module must export DEFAULTS dict."""
        self.assertTrue(
            hasattr(self.prefs_module, "DEFAULTS"),
            "node_layout_prefs must export DEFAULTS",
        )
        self.assertIsInstance(self.prefs_module.DEFAULTS, dict)

    def test_module_exports_prefs_file(self):
        """node_layout_prefs module must export PREFS_FILE path string."""
        self.assertTrue(
            hasattr(self.prefs_module, "PREFS_FILE"),
            "node_layout_prefs must export PREFS_FILE",
        )
        self.assertIsInstance(self.prefs_module.PREFS_FILE, str)

    def test_module_exports_prefs_singleton(self):
        """node_layout_prefs module must export prefs_singleton instance."""
        self.assertTrue(
            hasattr(self.prefs_module, "prefs_singleton"),
            "node_layout_prefs must export prefs_singleton",
        )
        self.assertIsInstance(
            self.prefs_module.prefs_singleton,
            self.prefs_module.NodeLayoutPrefs,
        )

    def test_prefs_file_points_to_nuke_dir(self):
        """PREFS_FILE must point into the user's ~/.nuke directory."""
        expected_dir = os.path.join(os.path.expanduser("~"), ".nuke")
        self.assertTrue(
            self.prefs_module.PREFS_FILE.startswith(expected_dir),
            f"PREFS_FILE should be inside {expected_dir}, got: {self.prefs_module.PREFS_FILE}",
        )

    def test_prefs_singleton_returns_default_base_subtree_margin(self):
        """prefs_singleton.get('base_subtree_margin') returns 200 (new default)."""
        # prefs_singleton may have loaded from ~/.nuke/node_layout_prefs.json if it exists.
        # We test the default fallback only if the file is absent.
        nuke_prefs_path = os.path.join(
            os.path.expanduser("~"), ".nuke", "node_layout_prefs.json"
        )
        if not os.path.exists(nuke_prefs_path):
            self.assertEqual(
                self.prefs_module.prefs_singleton.get("base_subtree_margin"), 200
            )


if __name__ == "__main__":
    unittest.main()

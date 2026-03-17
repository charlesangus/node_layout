import json
import os

PREFS_FILE = os.path.join(os.path.expanduser("~"), ".nuke", "node_layout_prefs.json")

DEFAULTS = {
    "base_subtree_margin": 200,           # rebalanced: was 300, now 200 (less tall)
    "horizontal_subtree_gap": 250,        # H-axis spine-to-spine gap (px)
    "horizontal_side_vertical_gap": 150,  # H-axis gap between spine and first node of side subtree (px)
    "horizontal_mask_gap": 50,            # H-axis mask input gap (px)
    "dot_font_reference_size": 20,        # NEW: stub for Phase 8 font-margin scaling
    "compact_multiplier": 0.6,
    "normal_multiplier": 1.0,
    "loose_multiplier": 1.5,
    "loose_gap_multiplier": 8.0,          # rebalanced: was 12.0, now 8.0 (less tall)
    "mask_input_ratio": 0.333,
    "scaling_reference_count": 150,
}


class NodeLayoutPrefs:
    def __init__(self, prefs_file=PREFS_FILE):
        self._prefs_file = prefs_file
        self._prefs = self._load()

    def _load(self):
        if os.path.exists(self._prefs_file):
            with open(self._prefs_file, "r") as prefs_file_handle:
                raw_content = prefs_file_handle.read().strip()
            if raw_content:
                loaded = json.loads(raw_content)
                return {**DEFAULTS, **loaded}
        return dict(DEFAULTS)

    def get(self, key):
        return self._prefs.get(key, DEFAULTS.get(key))

    def set(self, key, value):
        self._prefs[key] = value

    def save(self):
        with open(self._prefs_file, "w") as prefs_file_handle:
            json.dump(self._prefs, prefs_file_handle, indent=2)

    def reload(self):
        self._prefs = self._load()


prefs_singleton = NodeLayoutPrefs()

"""
node_layout_state.py — Per-node state helpers for node_layout.py.

This module is intentionally kept importable without a live Nuke runtime.
The only Nuke API calls are inside write_node_state() and clear_node_state(),
which use a deferred ``import nuke`` so tests can inject a stub before import.
"""

import json

_DEFAULT_STATE = {
    "scheme": "normal",
    "mode": "vertical",
    "h_scale": 1.0,
    "v_scale": 1.0,
}

# Name constants used for the per-node knobs.
_TAB_KNOB_NAME = "node_layout_tab"
_STATE_KNOB_NAME = "node_layout_state"
_DIAMOND_KNOB_NAME = "node_layout_diamond_dot"

# Mapping from scheme name to prefs key.
_SCHEME_TO_PREF_KEY = {
    "compact": "compact_multiplier",
    "normal": "normal_multiplier",
    "loose": "loose_multiplier",
}


def read_node_state(node):
    """Return the per-node layout state dict for *node*.

    Always returns a dict with all four keys (scheme, mode, h_scale, v_scale).
    Missing keys are filled in from _DEFAULT_STATE.  If the knob is absent,
    empty, or contains malformed JSON, the full default dict is returned.
    """
    state_knob = node.knob(_STATE_KNOB_NAME)
    if state_knob is None:
        return dict(_DEFAULT_STATE)

    raw = state_knob.value()
    if not raw:
        return dict(_DEFAULT_STATE)

    try:
        stored = json.loads(raw)
    except (ValueError, TypeError):
        return dict(_DEFAULT_STATE)

    merged = dict(_DEFAULT_STATE)
    merged.update(stored)
    return merged


def write_node_state(node, state):
    """Write *state* dict to *node* as a hidden JSON string knob.

    Creates the ``node_layout_tab`` Tab_Knob and ``node_layout_state``
    String_Knob if they are absent.  Never duplicates knobs.
    """
    import nuke  # deferred import — keeps module importable without Nuke runtime

    if node.knob(_TAB_KNOB_NAME) is None:
        node.addKnob(nuke.Tab_Knob(_TAB_KNOB_NAME, "Node Layout"))

    if node.knob(_STATE_KNOB_NAME) is None:
        state_knob = nuke.String_Knob(_STATE_KNOB_NAME, "Node Layout State")
        state_knob.setFlag(nuke.INVISIBLE)
        node.addKnob(state_knob)

    node[_STATE_KNOB_NAME].setValue(json.dumps(state))


def clear_node_state(node):
    """Remove the per-node state knob from *node*.

    Also removes the ``node_layout_tab`` knob unless the node still has a
    ``node_layout_diamond_dot`` knob (which uses the same tab).
    """
    import nuke  # deferred import — keeps module importable without Nuke runtime

    state_knob = node.knob(_STATE_KNOB_NAME)
    if state_knob is not None:
        node.removeKnob(state_knob)

    # Only remove the shared tab when the diamond-dot knob is also gone.
    if node.knob(_DIAMOND_KNOB_NAME) is None:
        tab_knob = node.knob(_TAB_KNOB_NAME)
        if tab_knob is not None:
            node.removeKnob(tab_knob)


def scheme_name_to_multiplier(scheme_name, prefs):
    """Return the numeric multiplier for *scheme_name* from *prefs*.

    Falls back to the normal_multiplier for unknown scheme names.
    """
    pref_key = _SCHEME_TO_PREF_KEY.get(scheme_name, "normal_multiplier")
    return prefs.get(pref_key)


def multiplier_to_scheme_name(scheme_multiplier, prefs):
    """Return the scheme name whose pref multiplier matches *scheme_multiplier*.

    Comparison uses a tolerance of 1e-9 to avoid float precision issues.
    Returns ``"normal"`` when no scheme matches.
    """
    for scheme_name, pref_key in _SCHEME_TO_PREF_KEY.items():
        if abs(scheme_multiplier - prefs.get(pref_key)) < 1e-9:
            return scheme_name
    return "normal"

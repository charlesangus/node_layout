"""Hidden state write-back.

Converts ``LayoutResult`` plus ``PreparedScope`` into persisted state on
every node touched by the layout. Per-command policy lives here so the
geometry engine never decides what gets persisted.
"""
from __future__ import annotations

import node_layout_prefs
import node_layout_state
from layout_contracts import PACKER_HORIZONTAL, LayoutResult, PreparedScope


def sync_layout_state(result: LayoutResult, prepared: PreparedScope):
    """Persist scheme/mode updates for every node touched by the layout.

    Policy per command:
      * ``layout_upstream`` / ``layout_selected`` — persist the actual
        per-node mode reported in ``result.mode_assignments``, defaulting
        to ``"vertical"``.
      * ``layout_selected_horizontal[_place_only]`` — persist
        ``"horizontal"`` for spine nodes, ``"vertical"`` for selected
        non-spine nodes, and leave unselected upstream side nodes
        untouched.
    """
    request = prepared.request
    prefs = node_layout_prefs.prefs_singleton
    state_nodes = set(prepared.state_nodes) | result.placed_nodes

    if request.scope_kind == "selected_horizontal":
        horizontal_params = prepared.packer_params.get(PACKER_HORIZONTAL)
        spine_set = set(horizontal_params.spine_ids) if horizontal_params is not None else set()
        # state_nodes from prep = initial selection (post-non-root filter).
        selected_ids = {id(n) for n in prepared.state_nodes}

        def _mode_for(node):
            if id(node) in spine_set:
                return "horizontal"
            if id(node) in selected_ids:
                return "vertical"
            return None

        _write_state(state_nodes, prepared.per_node_scheme, prefs, mode_for_node=_mode_for)
        return

    mode_assignments = result.mode_assignments
    _write_state(
        state_nodes, prepared.per_node_scheme, prefs,
        mode_for_node=lambda n: mode_assignments.get(id(n), "vertical"),
    )


def _write_state(nodes, scheme_map, prefs, mode_for_node):
    """Write scheme + mode back to each node's hidden state knob.

    ``mode_for_node`` is a callable returning either ``"horizontal"`` /
    ``"vertical"`` (or any other registered mode), or ``None`` to leave
    the existing mode untouched.
    """
    for node in nodes:
        stored = node_layout_state.read_node_state(node)
        n_scheme = scheme_map.get(id(node), prefs.get("normal_multiplier"))
        stored["scheme"] = node_layout_state.multiplier_to_scheme_name(
            n_scheme, prefs,
        )
        new_mode = mode_for_node(node)
        if new_mode is not None:
            stored["mode"] = new_mode
        node_layout_state.write_node_state(node, stored)

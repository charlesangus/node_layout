"""Single command pipeline shared by every layout entry point.

The orchestrator is the only place that runs the full

    build_scope -> prepare_graph -> layout -> apply -> state-sync -> push

sequence. Each public command in ``node_layout`` constructs a
``LayoutRequest``, gathers ``initial_nodes`` from the live Nuke selection,
and calls ``run_layout``. The differences between commands live entirely in
``LayoutRequest`` and the scope-builder branch they hit.
"""
from __future__ import annotations

import node_layout
import node_layout_prefs
from layout_contracts import (
    LayoutRequest,
    LayoutResult,
    PreparedScope,
)
from layout_prepare import prepare_graph
from layout_scope import build_scope
from node_layout_bbox import (
    LayoutContext,
    _apply_subtree_anchored_at,
    _push_after,
    _resolve_side_dot_gap,
    _undo_block,
    _write_state,
)
from node_layout_bbox import (
    layout as _engine_layout,
)
from node_layout_bbox import (
    layout_horizontal as _engine_layout_horizontal,
)

# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------

def run_layout(request: LayoutRequest, initial_nodes, current_group):
    """Run the full layout pipeline for ``request``.

    ``initial_nodes`` is whatever the public command extracted from the live
    Nuke selection. ``current_group`` is ``nuke.lastHitGroup()`` captured
    before any other Nuke API call.
    """
    node_layout._clear_color_cache()
    with _undo_block(request.undo_label), current_group:
        return _run_pipeline(request, initial_nodes, current_group)


def _run_pipeline(request: LayoutRequest, initial_nodes, current_group):
    scope = build_scope(request, initial_nodes, current_group)
    if scope is None or not scope.roots:
        return None
    prepared = prepare_graph(scope, current_group)
    ctx = _layout_context_from_prepared(prepared)
    result = _run_engine(prepared, ctx)
    _apply_layout_result(result, prepared)
    _sync_layout_state(result, prepared)
    _push_layout(result, prepared, current_group)
    return result


# ---------------------------------------------------------------------------
# Layout — turn PreparedScope into a LayoutContext and run the engine.
# ---------------------------------------------------------------------------

def _layout_context_from_prepared(prepared: PreparedScope) -> LayoutContext:
    from layout_contracts import PACKER_HORIZONTAL, HorizontalParams  # noqa: PLC0415

    snap = node_layout.get_dag_snap_threshold()
    packer_params: dict = {}
    if "spine_set" in prepared.packer_params:
        packer_params[PACKER_HORIZONTAL] = HorizontalParams(
            spine_ids=frozenset(prepared.packer_params["spine_set"]),
            root_id=prepared.packer_params.get("horizontal_root_id"),
            side_layout_mode=prepared.packer_params.get(
                "side_layout_mode", "recursive",
            ),
        )
    return LayoutContext(
        snap_threshold=snap,
        node_count=len(prepared.layout_nodes) or 1,
        node_filter=prepared.node_filter,
        per_node_scheme=prepared.per_node_scheme,
        per_node_h_scale=prepared.per_node_h_scale,
        per_node_v_scale=prepared.per_node_v_scale,
        dimension_overrides=prepared.freeze_dimension_overrides,
        all_member_ids=prepared.freeze_member_ids,
        side_dot_gap=_resolve_side_dot_gap(snap, prepared.request.scheme_multiplier),
        packer_params=packer_params,
    )


def _run_engine(prepared: PreparedScope, ctx: LayoutContext) -> LayoutResult:
    request = prepared.request
    subtrees: list = []
    placed_nodes: set = set()
    mode_assignments: dict = {}

    if request.scope_kind == "selected_horizontal":
        # Force the chain root through the horizontal packer regardless of
        # its stored mode — the user explicitly asked for a horizontal chain.
        subtree = _engine_layout_horizontal(prepared.roots[0], ctx)
        subtrees.append(subtree)
        placed_nodes.update(subtree.nodes.keys())
        mode_assignments.update(subtree.mode_assignments)
    else:
        for root in prepared.roots:
            subtree = _engine_layout(root, ctx)
            subtrees.append(subtree)
            placed_nodes.update(subtree.nodes.keys())
            mode_assignments.update(subtree.mode_assignments)

    return LayoutResult(
        subtrees=subtrees,
        placed_nodes=placed_nodes,
        mode_assignments=mode_assignments,
    )


# ---------------------------------------------------------------------------
# Apply / state-sync / push — final mutation stages.
# ---------------------------------------------------------------------------

def _apply_layout_result(result: LayoutResult, prepared: PreparedScope):
    for subtree, root in zip(result.subtrees, prepared.roots, strict=False):
        _apply_subtree_anchored_at(subtree, root)


def _sync_layout_state(result: LayoutResult, prepared: PreparedScope):
    request = prepared.request
    prefs = node_layout_prefs.prefs_singleton
    state_nodes = set(prepared.state_nodes) | result.placed_nodes

    if request.scope_kind == "selected_horizontal":
        spine_set = prepared.packer_params.get("spine_set", set())
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


def _push_layout(result: LayoutResult, prepared: PreparedScope, current_group):
    push_set = set(prepared.push_subject_nodes) | result.placed_nodes
    _push_after(push_set, prepared.bbox_before, current_group, prepared.freeze_blocks)

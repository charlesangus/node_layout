"""Single command pipeline shared by every layout entry point.

The orchestrator is the only place that runs the full

    build_scope -> prepare_graph -> layout -> apply -> state-sync -> push

sequence. Each public command in ``node_layout`` constructs a
``LayoutRequest``, gathers ``initial_nodes`` from the live Nuke selection,
and calls ``run_layout``. The differences between commands live entirely in
``LayoutRequest`` and the scope-builder branch they hit.
"""
from __future__ import annotations

import contextlib

import nuke

import node_layout
from layout_apply import apply_layout
from layout_contracts import (
    LayoutRequest,
    LayoutResult,
    PreparedScope,
)
from layout_prepare import prepare_graph
from layout_push import push_surrounding_nodes
from layout_scope import build_scope
from layout_state_sync import sync_layout_state
from node_layout_bbox import (
    LayoutContext,
    _resolve_side_dot_gap,
)
from node_layout_bbox import (
    layout as _engine_layout,
)
from node_layout_bbox import (
    layout_horizontal as _engine_layout_horizontal,
)


@contextlib.contextmanager
def _undo_block(label: str):
    """Wrap a block in a Nuke undo group, cancelling on exception."""
    nuke.Undo.name(label)
    nuke.Undo.begin()
    try:
        yield
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()

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
    apply_layout(result, prepared)
    sync_layout_state(result, prepared)
    push_surrounding_nodes(result, prepared, current_group)
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



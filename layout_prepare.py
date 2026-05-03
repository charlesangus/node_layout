"""Topology preparation — the only stage allowed to mutate graph topology.

``prepare_graph(scope, current_group)`` calls ``prepare_layout_graph`` to
insert routing dots, then re-collects the post-mutation node set and
re-resolves per-node scheme/scale tables. The returned ``PreparedScope`` is
the authoritative input to layout, apply, state-sync, and push.
"""
from __future__ import annotations

import node_layout
import node_layout_prefs
from layout_contracts import LayoutScope, PreparedScope
from node_layout_bbox import (
    LayoutContext,
    _resolve_per_node_state,
    _resolve_side_dot_gap,
    _walk_mutable_graph,
    prepare_layout_graph,
)


def prepare_graph(scope: LayoutScope, current_group) -> PreparedScope:
    """Mutate topology for ``scope`` and return the post-mutation ``PreparedScope``.

    Inserts routing dots via ``prepare_layout_graph``, re-collects the
    layout node set, and re-resolves per-node scheme/scale tables for every
    node the engine will see.
    """
    prefs = node_layout_prefs.prefs_singleton
    snap = node_layout.get_dag_snap_threshold()
    request = scope.request

    # Resolve per-node state for the initial scope so the prep helpers and
    # the post-mutation re-resolve start from a consistent base.
    per_node_scheme: dict = {}
    per_node_h_scale: dict = {}
    per_node_v_scale: dict = {}
    initial_state_pool = scope.initial_nodes
    if scope.node_filter is not None:
        initial_state_pool = initial_state_pool | scope.node_filter
    _resolve_per_node_state(
        initial_state_pool, request.scheme_multiplier, prefs,
        per_node_scheme, per_node_h_scale, per_node_v_scale,
    )

    # Build a transient context for the prep helpers. They only read
    # node_filter, dimension_overrides, all_member_ids, and (for horizontal
    # routing) the horizontal packer params — scheme/scale tables are
    # unused at this stage.
    prep_ctx = LayoutContext(
        snap_threshold=snap,
        node_count=len(scope.initial_nodes) or 1,
        node_filter=scope.node_filter,
        per_node_scheme=per_node_scheme,
        per_node_h_scale=per_node_h_scale,
        per_node_v_scale=per_node_v_scale,
        dimension_overrides=scope.freeze_dimension_overrides,
        all_member_ids=scope.freeze_member_ids,
        side_dot_gap=_resolve_side_dot_gap(snap, request.scheme_multiplier),
        packer_params=dict(scope.packer_params),
    )

    prepare_layout_graph(
        scope.roots, prep_ctx, current_group,
        routing_mode=request.routing_mode,
    )

    # Re-collect layout_nodes after mutation in the same shape the engine
    # will traverse for this command.
    layout_nodes = _collect_layout_nodes(scope, prep_ctx)

    # Re-resolve per-node state with newly inserted nodes included.
    _resolve_per_node_state(
        layout_nodes, request.scheme_multiplier, prefs,
        per_node_scheme, per_node_h_scale, per_node_v_scale,
    )

    # ``layout_upstream`` re-derives node_filter post-mutation when freeze
    # blocks contribute non-root members; the other commands keep the
    # pre-mutation filter (it already reflects their declared scope).
    if request.scope_kind == "upstream" and scope.freeze_non_root_ids:
        node_filter = {
            n for n in layout_nodes if id(n) not in scope.freeze_non_root_ids
        }
    else:
        node_filter = scope.node_filter

    # state_nodes / push_subject_nodes — per-command write/push targets
    # before the engine result is folded in. The state-sync and push stages
    # union these with ``result.placed_nodes``. The shape per command
    # mirrors the legacy entry-point behaviour:
    #
    #   upstream:            result.placed_nodes only.
    #   selected:            initial selection ∪ post-mutation layout set.
    #   selected_horizontal: initial selection only (placed-from-result
    #                        contains the chain and its side subtrees).
    if request.scope_kind == "upstream":
        state_nodes: set = set()
    elif request.scope_kind == "selected":
        state_nodes = set(scope.initial_nodes) | layout_nodes
    elif request.scope_kind == "selected_horizontal":
        state_nodes = set(scope.initial_nodes)
    else:
        state_nodes = set()
    push_subject_nodes = set(state_nodes)

    return PreparedScope(
        request=request,
        roots=list(scope.roots),
        node_filter=node_filter,
        layout_nodes=layout_nodes,
        state_nodes=state_nodes,
        push_subject_nodes=push_subject_nodes,
        bbox_before=scope.bbox_before,
        freeze_blocks=scope.freeze_blocks,
        freeze_dimension_overrides=scope.freeze_dimension_overrides,
        freeze_member_ids=scope.freeze_member_ids,
        per_node_scheme=per_node_scheme,
        per_node_h_scale=per_node_h_scale,
        per_node_v_scale=per_node_v_scale,
        packer_params=dict(scope.packer_params),
    )


def _collect_layout_nodes(scope: LayoutScope, ctx: LayoutContext) -> set:
    """Return the node set the engine will traverse after preparation."""
    request = scope.request
    if request.scope_kind == "upstream":
        return set(node_layout.collect_subtree_nodes(scope.roots[0]))
    if request.scope_kind == "selected":
        result: set = set()
        for root in scope.roots:
            result.update(
                node_layout.collect_subtree_nodes(root, ctx.node_filter)
            )
        return result
    if request.scope_kind == "selected_horizontal":
        return set(_walk_mutable_graph(scope.roots, ctx))
    return set()

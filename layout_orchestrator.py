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
    LayoutScope,
    PreparedScope,
)
from node_layout_bbox import (
    LayoutContext,
    _apply_subtree_anchored_at,
    _push_after,
    _resolve_per_node_state,
    _resolve_side_dot_gap,
    _setup_freeze,
    _undo_block,
    _walk_mutable_graph,
    _write_state,
    prepare_layout_graph,
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
    scope = _build_scope(request, list(initial_nodes), current_group)
    if scope is None or not scope.roots:
        return None
    prepared = _prepare_graph(scope, current_group)
    ctx = _layout_context_from_prepared(prepared)
    result = _run_engine(prepared, ctx)
    _apply_layout_result(result, prepared)
    _sync_layout_state(result, prepared)
    _push_layout(result, prepared, current_group)
    return result


# ---------------------------------------------------------------------------
# Scope construction.
#
# Each scope_kind produces a LayoutScope describing the resolved participating
# set before topology mutation. Anything here that can be invalidated by
# routing-dot insertion is re-resolved during ``_prepare_graph``.
# ---------------------------------------------------------------------------

def _build_scope(request, initial_nodes, current_group):
    if request.scope_kind == "upstream":
        return _build_scope_upstream(request, initial_nodes, current_group)
    if request.scope_kind == "selected":
        return _build_scope_selected(request, initial_nodes, current_group)
    if request.scope_kind == "selected_horizontal":
        return _build_scope_selected_horizontal(request, initial_nodes, current_group)
    raise ValueError(f"Unknown scope_kind: {request.scope_kind!r}")


def _build_scope_upstream(request, initial_nodes, current_group):
    if not initial_nodes:
        return None
    root = initial_nodes[0]
    all_upstream = node_layout.collect_subtree_nodes(root)
    bbox_before = node_layout.compute_node_bounding_box(all_upstream)

    _, freeze_blocks, dimension_overrides, all_non_root_ids, all_member_ids = (
        _setup_freeze(all_upstream, current_group)
    )

    node_filter = (
        {n for n in all_upstream if id(n) not in all_non_root_ids}
        if all_non_root_ids else None
    )

    return LayoutScope(
        request=request,
        roots=[root],
        initial_nodes=set(all_upstream),
        node_filter=node_filter,
        bbox_before=bbox_before,
        freeze_blocks=freeze_blocks,
        freeze_dimension_overrides=dimension_overrides,
        freeze_non_root_ids=all_non_root_ids,
        freeze_member_ids=all_member_ids,
        packer_params={},
    )


def _build_scope_selected(request, initial_nodes, current_group):
    if len(initial_nodes) < 2:
        return None
    expanded, freeze_blocks, dimension_overrides, all_non_root_ids, all_member_ids = (
        _setup_freeze(initial_nodes, current_group)
    )
    bbox_before = node_layout.compute_node_bounding_box(expanded)

    node_filter = set(expanded)
    selected = list(node_filter)
    if all_non_root_ids:
        node_filter = {n for n in node_filter if id(n) not in all_non_root_ids}
        selected = [n for n in selected if id(n) not in all_non_root_ids]

    roots = node_layout.find_selection_roots(selected)
    roots.sort(key=lambda n: n.xpos())

    return LayoutScope(
        request=request,
        roots=roots,
        initial_nodes=set(selected),
        node_filter=node_filter,
        bbox_before=bbox_before,
        freeze_blocks=freeze_blocks,
        freeze_dimension_overrides=dimension_overrides,
        freeze_non_root_ids=all_non_root_ids,
        freeze_member_ids=all_member_ids,
        packer_params={},
    )


def _build_scope_selected_horizontal(request, initial_nodes, current_group):
    if not initial_nodes:
        return None
    # Pass 1: detect freeze groups in the selection so we can identify
    # non-root members and pick a chain root that isn't one of them.
    expanded, _, _, sel_non_root_ids, _ = _setup_freeze(initial_nodes, current_group)
    bbox_before = node_layout.compute_node_bounding_box(expanded)

    selection_filter = set(expanded)
    selected = list(selection_filter)
    if sel_non_root_ids:
        selection_filter = {
            n for n in selection_filter if id(n) not in sel_non_root_ids
        }
        selected = [n for n in selected if id(n) not in sel_non_root_ids]

    roots = node_layout.find_selection_roots(selected)
    if not roots:
        return None
    roots.sort(key=lambda n: -n.xpos())  # rightmost wins as chain root
    chain_root = roots[0]

    # Build the spine: walk input(0) through the selection.
    spine_set: set = set()
    cursor = chain_root
    while cursor is not None and cursor in selection_filter:
        spine_set.add(id(cursor))
        cursor = cursor.input(0)

    # Expand scope to the spine's full upstream so side inputs and the
    # leftmost spine node's input(0) get laid out by the recursion.
    wider_scope = set(selection_filter)
    for spine_node_id in spine_set:
        spine_node_obj = next((n for n in selected if id(n) == spine_node_id), None)
        if spine_node_obj is not None:
            wider_scope.update(node_layout.collect_subtree_nodes(spine_node_obj))

    # Pass 2: re-detect freeze groups against the wider scope. Blocks living
    # entirely upstream of the spine were invisible to pass 1 but must be
    # folded as opaque leaves so the recursion preserves rigid offsets.
    wider_filter, freeze_blocks, dim_overrides, all_non_root_ids, all_member_ids = (
        _setup_freeze(wider_scope, current_group)
    )
    wider_filter = set(wider_filter)
    if all_non_root_ids:
        wider_filter = {
            n for n in wider_filter if id(n) not in all_non_root_ids
        }
        selected = [n for n in selected if id(n) not in all_non_root_ids]

    return LayoutScope(
        request=request,
        roots=[chain_root],
        initial_nodes=set(selected),
        node_filter=wider_filter,
        bbox_before=bbox_before,
        freeze_blocks=freeze_blocks,
        freeze_dimension_overrides=dim_overrides,
        freeze_non_root_ids=all_non_root_ids,
        freeze_member_ids=all_member_ids,
        packer_params={
            "spine_set": spine_set,
            "horizontal_root_id": id(chain_root),
            "side_layout_mode": request.selected_horizontal_side_mode or "recursive",
        },
    )


# ---------------------------------------------------------------------------
# Topology preparation.
#
# Calls ``prepare_layout_graph`` (the only stage allowed to mutate topology),
# then re-collects layout_nodes and re-resolves per-node scheme/scale tables
# so the engine's view is fully post-mutation.
# ---------------------------------------------------------------------------

def _prepare_graph(scope: LayoutScope, current_group) -> PreparedScope:
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
    # routing) spine_set — scheme/scale tables are unused at this stage.
    spine_set = scope.packer_params.get("spine_set")
    horizontal_root_id = scope.packer_params.get("horizontal_root_id")
    side_layout_mode = scope.packer_params.get("side_layout_mode", "recursive")
    prep_ctx = LayoutContext(
        snap_threshold=snap,
        node_count=len(scope.initial_nodes) or 1,
        node_filter=scope.node_filter,
        per_node_scheme=per_node_scheme,
        per_node_h_scale=per_node_h_scale,
        per_node_v_scale=per_node_v_scale,
        dimension_overrides=scope.freeze_dimension_overrides,
        spine_set=spine_set,
        horizontal_root_id=horizontal_root_id,
        side_layout_mode=side_layout_mode,
        all_member_ids=scope.freeze_member_ids,
        side_dot_gap=_resolve_side_dot_gap(snap, request.scheme_multiplier),
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

    # state_nodes / push_subject_nodes — the per-command write/push targets
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


# ---------------------------------------------------------------------------
# Layout — turn PreparedScope into a LayoutContext and run the engine.
# ---------------------------------------------------------------------------

def _layout_context_from_prepared(prepared: PreparedScope) -> LayoutContext:
    snap = node_layout.get_dag_snap_threshold()
    spine_set = prepared.packer_params.get("spine_set")
    horizontal_root_id = prepared.packer_params.get("horizontal_root_id")
    side_layout_mode = prepared.packer_params.get("side_layout_mode", "recursive")
    return LayoutContext(
        snap_threshold=snap,
        node_count=len(prepared.layout_nodes) or 1,
        node_filter=prepared.node_filter,
        per_node_scheme=prepared.per_node_scheme,
        per_node_h_scale=prepared.per_node_h_scale,
        per_node_v_scale=prepared.per_node_v_scale,
        dimension_overrides=prepared.freeze_dimension_overrides,
        spine_set=spine_set,
        horizontal_root_id=horizontal_root_id,
        side_layout_mode=side_layout_mode,
        all_member_ids=prepared.freeze_member_ids,
        side_dot_gap=_resolve_side_dot_gap(snap, prepared.request.scheme_multiplier),
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

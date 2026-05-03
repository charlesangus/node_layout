"""Pre-preparation scope resolution.

``build_scope`` decides which nodes participate in a layout run for a given
``LayoutRequest``. It owns selection-root rules, upstream collection,
selected-horizontal spine discovery, freeze expansion, and the pre-mutation
``bbox_before`` snapshot.

It does NOT mutate graph topology. Anything that can be invalidated by
routing-dot insertion (final node sets, scale tables) is re-resolved by
``layout_prepare.prepare_graph`` after preparation.
"""
from __future__ import annotations

import node_layout
from layout_contracts import LayoutRequest, LayoutScope
from node_layout_bbox import _setup_freeze


def build_scope(request: LayoutRequest, initial_nodes, current_group):
    """Return a ``LayoutScope`` for ``request``, or ``None`` if the command is a no-op.

    ``initial_nodes`` is what the caller extracted from the live Nuke
    selection — one node for ``layout_upstream``, the multi-selection for
    ``layout_selected`` / ``layout_selected_horizontal*``.
    """
    initial_nodes = list(initial_nodes)
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

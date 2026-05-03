"""Room-push stage.

Computes the post-layout bounding box and shoves any surrounding DAG nodes
to make room. The bbox-before snapshot lives on ``PreparedScope`` so the
push correctly accounts for growth in either direction.
"""
from __future__ import annotations

import node_layout
from layout_contracts import LayoutResult, PreparedScope


def push_surrounding_nodes(
    result: LayoutResult, prepared: PreparedScope, current_group,
):
    """Push surrounding DAG nodes outward to make room for the new layout."""
    push_set = set(prepared.push_subject_nodes) | result.placed_nodes
    _push_after(push_set, prepared.bbox_before, current_group, prepared.freeze_blocks)


def _push_after(all_after_nodes, bbox_before, current_group, freeze_blocks):
    """Run ``push_nodes_to_make_room`` for the post-layout bounding box.

    ``all_after_nodes`` is augmented with any freeze-block members that
    weren't part of the recursion result so the push correctly skips over
    rigid block geometry.
    """
    augmented = set(all_after_nodes)
    for block in freeze_blocks:
        augmented.update(block.members)
    bbox_after = node_layout.compute_node_bounding_box(list(augmented))
    if bbox_before is None or bbox_after is None:
        return
    node_layout.push_nodes_to_make_room(
        {id(n) for n in augmented}, bbox_before, bbox_after,
        current_group=current_group,
        freeze_blocks=freeze_blocks,
    )

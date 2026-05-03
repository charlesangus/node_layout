"""Final position mutation.

Translates each ``Subtree`` so its root lands at the anchor node's current
DAG position, then writes the new ``xpos``/``ypos`` to every Nuke node in
the subtree. This is the only stage allowed to call ``setXpos`` / ``setYpos``.
"""
from __future__ import annotations

from layout_contracts import LayoutResult, PreparedScope


def apply_layout(result: LayoutResult, prepared: PreparedScope):
    """Apply each subtree in ``result`` anchored at its corresponding root."""
    for subtree, root in zip(result.subtrees, prepared.roots, strict=False):
        _apply_subtree_anchored_at(subtree, root)


def _apply_subtree_anchored_at(subtree, anchor_node):
    """Translate ``subtree`` so ``anchor_node`` ends at its current xpos/ypos.

    Falls back to ``subtree.anchor_out`` when the anchor isn't in the node
    dict (defensive — every recursion path returns the anchor in nodes).
    """
    local_x, local_y = subtree.nodes.get(anchor_node, subtree.anchor_out)
    dx = anchor_node.xpos() - local_x
    dy = anchor_node.ypos() - local_y
    for obj, (lx, ly) in subtree.nodes.items():
        obj.setXpos(lx + dx)
        obj.setYpos(ly + dy)

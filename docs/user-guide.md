---
title: "Node Layout — User Guide"
author: "Charles Angus"
header-includes:
  - \department{Node Layout}
---

Node Layout is a toolset for Nuke that automatically arranges nodes in the
DAG, saving artists from manually dragging nodes into tidy, readable
layouts. It provides commands to lay out upstream trees, selections, and
freeform arrangements, along with a set of preferences for tuning spacing
and behavior.

## Make Room

Make Room opens empty space in the DAG by shifting nodes out of the way, so
you can slot new nodes into a crowded graph without manually dragging
everything aside first.

If you have a selection, only the selected nodes move, by a fixed amount in
the chosen direction. With nothing selected, the vertical commands act on
the whole graph relative to a reference point: "Above" shifts every node
above it, and "Below" shifts every node below it, opening a gap across the
entire tree. The horizontal commands (Left/Right) always require a
selection and do nothing if none is made.

Remember that in Nuke's DAG, up is toward the upstream/input side of the
graph. So Make Room Above pushes nodes up, toward their inputs, while Make
Room Below pushes nodes down, toward their outputs.

![A tightly packed DAG with no room to insert a node between the upstream reads and the downstream Merge/Write.](docs/images/make_room_before.png)

![After running Make Room Below on the Merge/Write, a clear gap opens between the upstream nodes and the pushed-down Merge/Write, ready for a new node.](docs/images/make_room_after.png)

The commands live in the Node Layout menu:

| Command | Shortcut | Amount |
|---|---|---|
| Make Room Above | `[` | 1600 |
| Make Room Below | `]` | 1600 |
| Make Room Above (smaller) | `Ctrl+[` | 800 |
| Make Room Below (smaller) | `Ctrl+]` | 800 |
| Make Room Left | `{` | 800 |
| Make Room Right | `}` | 800 |

The amounts are DAG units; the bracket shortcuts open a large gap, and their
`Ctrl` variants open a smaller one for finer adjustments.

## Layout Upstream

Layout Upstream tidies the entire tree feeding into one node, turning a
tangled upstream graph into a clean, readable stack in a single keystroke.

Select the node at the bottom of the branch you want to clean up. Its whole
upstream subtree — every node that feeds into it, directly or indirectly — is
collected and arranged automatically; you only ever select the one downstream
node. That node stays put as the root, and its inputs are laid out above it,
because in Nuke's DAG upstream is up, toward the inputs. Nodes elsewhere in
the script are left where they are.

![A branch with several Reads, Grades, and a Merge feeding a Write, arranged untidily by hand.](docs/images/layout_upstream_before.png)

![After Layout Upstream on the Write, the whole feeding tree is stacked neatly above it while the Write stays in place.](docs/images/layout_upstream_after.png)

| Command | Shortcut |
|---|---|
| Layout Upstream | `Shift+E` |

The shortcut is active in the DAG. It lays out the last selected node's
upstream tree.

## Layout Selected

Layout Selected arranges only the nodes you have selected, leaving the rest of
the script untouched — useful for tidying one cluster without reflowing the
whole graph.

Select two or more nodes; the command does nothing with fewer than two. Only
the selected nodes move, even if unselected nodes sit between them. Node
Layout finds the *roots* of your selection — the most downstream selected
nodes, the ones no other selected node feeds into — and stacks each root's
selected inputs above it. If the selection contains several independent roots,
they are arranged side by side, ordered left to right.

![A loose selection of nodes across two small branches, positioned by hand.](docs/images/layout_selected_before.png)

![After Layout Selected, only the selected nodes are tidied into clean stacks; everything else stays put.](docs/images/layout_selected_after.png)

| Command | Shortcut |
|---|---|
| Layout Selected | *(none — run from the Node Layout menu)* |

## Layout Selected Horizontal

Layout Selected Horizontal arranges the selected nodes along a left-to-right
spine instead of a vertical stack, for branches you would rather read across
the screen than down it.

Select the nodes to arrange. The most downstream selected node anchors the
right end of the spine, and its `input(0)` chain extends leftward from there,
so the primary pipe flows left to right into that root. Each spine node's side
inputs — its second and later inputs — stack vertically above their point on
the spine. As with Layout Selected, unselected nodes are left alone.

![A chain of nodes selected in their default vertical arrangement.](docs/images/layout_selected_horizontal_before.png)

![After Layout Selected Horizontal, the main chain runs left to right along a spine with side inputs stacked above it.](docs/images/layout_selected_horizontal_after.png)

| Command | Shortcut |
|---|---|
| Layout Selected Horizontal | *(none — run from the Node Layout menu)* |

## Freeze / Unfreeze

Freeze locks the internal shape of a hand-arranged block so that later layout
commands move the block as a rigid unit without disturbing its relative
positions.

Freezing tags the selected nodes with a shared group ID; nothing moves at the
moment you freeze. The effect appears on the next layout: a frozen block of
two or more nodes keeps its internal offsets — the exact relative positions
you set by hand — while the surrounding graph is tidied around it as one solid
piece. Freezing a single node on its own is a no-op, because a lone node has
no internal offsets to preserve. Unfreeze removes the tag so the nodes flow
with the layout again.

![A Grade and Merge frozen together as a two-node block, with the Merge deliberately nudged to one side by hand.](docs/images/freeze_before.png)

![After a layout, the unfrozen nodes tidy up while the frozen Grade+Merge block keeps its hand-set side offset intact.](docs/images/freeze_after.png)

| Command | Shortcut |
|---|---|
| Freeze Selected | `Ctrl+Shift+F` |
| Unfreeze Selected | `Ctrl+Shift+U` |

## Shrink / Expand

Shrink and Expand tighten or loosen the spacing of a selection without
changing its shape, so you can compact a sprawling tree or give a cramped one
more room to breathe.

Select two or more nodes. The most downstream selected node acts as the
anchor and stays fixed; every other node moves toward it (Shrink) or away from
it (Expand), scaling all the gaps by a constant factor. Because the scale is
anchored on that downstream node rather than the selection's midpoint, the
tree holds its position at the bottom and contracts or grows upward. Each
press applies one step — Shrink multiplies spacing by 0.8, Expand by 1.25 —
so repeat the shortcut to compact or spread further.

![A tidy two-branch tree: Reads into Grades into a Merge into a Write.](docs/images/shrink_before.png)

![After one Shrink step, the same tree is pulled in tighter around the downstream Write, which has not moved.](docs/images/shrink_after.png)

| Command | Shortcut |
|---|---|
| Shrink Selected | `Ctrl+,` |
| Expand Selected | `Ctrl+.` |

## Leader Window

## Preferences

## Other Features

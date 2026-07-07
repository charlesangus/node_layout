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

## Layout Selected

## Layout Selected Horizontal

## Freeze / Unfreeze

## Shrink / Expand

## Leader Window

## Preferences

## Other Features

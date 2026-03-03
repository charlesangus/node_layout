# C_NodeLayout

A plugin for [The Foundry's Nuke](https://www.foundry.com/products/nuke-family/nuke) that automatically arranges node graphs into clean, readable hierarchies. Instead of manually dragging nodes around your DAG, you select a node and let the plugin lay out its entire upstream tree — with intelligent spacing, color-aware grouping, automatic Dot node insertion, and collision avoidance for surrounding nodes.

---

## Installation

1. Place the four Python files together in a folder of your choice:

   ```
   node_layout.py
   menu.py
   make_room.py
   util.py
   ```

2. Add that folder to your Nuke plugin path. The most common way is to add a line like this to your `~/.nuke/init.py` (create it if it doesn't exist):

   ```python
   nuke.pluginAddPath('/path/to/your/folder')
   ```

   If you are at a studio, place the folder somewhere on your shared plugin path and add the `pluginAddPath` call to the appropriate `init.py`.

3. If you already have a `menu.py` in your Nuke path, copy the contents of this repo's `menu.py` into yours rather than replacing the file.

4. Restart Nuke. The commands will appear under **Edit → Node Layout**.

---

## Features

### Layout Upstream — `Shift+E`

Automatically lays out all visibly upstream nodes above a selected node. Nodes whose inputs are hidden (via the `hide_input` flag) act as leaves — the layout does not follow connections beyond them.

Select any node in your DAG and press `Shift+E`. Every node feeding into it — directly or through arbitrarily deep chains — is repositioned into an organized tree above it. The selected node stays exactly where it is; only its inputs move.

**How input nodes are arranged:**

- The primary input (input 0) is placed directly above the selected node in the same column.
- Additional inputs (input 1, 2, …) are stepped to the right of the node, each in its own column, with a Dot node inserted automatically on each side branch so the wire routing stays clean.
- Each input's entire upstream subtree gets its own exclusive vertical band, so no two subtrees ever overlap vertically.
- The bands stack so that the last input is closest to the root node and the first input is farthest up.

**Color-aware spacing:**

When two adjacent nodes share the same tile color *and* belong to the same toolbar category (e.g., both are Color nodes with a matching color), they are snapped together with a minimal gap. Nodes that differ in color or category get a larger gap, making visual groupings immediately readable.

**Mask input handling:**

Mask and matte inputs are detected automatically — by input label, by the presence of a `maskChannel` knob, or by node type (Merge/Dissolve input 2 is always treated as a mask). Mask inputs receive a narrower gap (roughly one-third of the normal gap) so the mask branch sits close to the node it feeds, and mask columns are always placed rightmost when there are multiple side inputs.

**Surrounding node displacement:**

After layout, the plugin compares the subtree's bounding box before and after. If the tree grew upward or rightward, any nodes that were sitting in that newly occupied space are automatically pushed out of the way. Nodes that were already overlapping the original footprint are left untouched.

---

### Layout Selected

Lays out multiple selected nodes relative to each other.

Select two or more nodes and run **Edit → Node Layout → Layout Selected**. The plugin finds the most-downstream nodes among your selection (the "roots") and lays each one's upstream selected subgraph above it. When two roots' subtrees would overlap horizontally, the second root is shifted rightward by a full subtree margin to keep everything separated.

This is useful when you have several independent trees you want to clean up at once, or when you want to organize a subset of a larger graph without disturbing the rest.

---

### Diamond Resolution (Automatic Dot Insertion)

When the same node is used as input in more than one place in a tree — a "diamond" pattern — the plugin automatically resolves it by inserting a hidden Dot node on the secondary path. This lets the layout algorithm treat the graph as a tree while keeping the actual node connections intact.

Non-mask paths are resolved first; mask paths are deferred and only get a Dot if the node they point to has already been claimed. This ensures the primary data flow takes the direct route.

---

### Select Upstream Ignoring Hidden — `E`

Select a node and press `E`. All visibly upstream nodes are selected. This is handy for grabbing an entire dependency chain before running Layout Selected, or before moving a subgraph.

---

### Sort By Filename

Select multiple Read nodes (or any nodes with a `file` knob) and run **Edit → Node Layout → Sort By Filename**. The nodes are sorted alphabetically by their file path and laid out in a horizontal row starting from the leftmost position of the selection.

---

### Make Room

A set of commands for quickly shifting nodes to create space in your DAG.

| Command | Shortcut | Effect |
|---|---|---|
| Make Room Above | `[` | Move nodes up 1600 px |
| Make Room Below | `]` | Move nodes down 1600 px |
| Make Room Above (smaller) | `Ctrl+[` | Move nodes up 800 px |
| Make Room Below (smaller) | `Ctrl+]` | Move nodes down 800 px |
| Make Room Left | `{` | Move nodes left 800 px |
| Make Room Right | `}` | Move nodes right 800 px |

**With a selection:** The selected nodes are moved by the specified amount in the specified direction.

**Without a selection (up/down only):** All nodes above or below the current cursor position are shifted. This lets you insert breathing room between two sections of a graph without selecting anything first.

---

## How Spacing Is Calculated

Spacing adapts to the snap threshold you have configured in Nuke's preferences (`dag_snap_threshold`). The base margins are:

- **Normal subtree margin:** 300 px — vertical clearance between adjacent input subtrees
- **Mask input margin:** 100 px — narrower clearance for mask/matte branches

The gap between an input node and the node it feeds into is:

- **Tight (snap\_threshold − 1 px):** when the two nodes share the same tile color and the same toolbar category
- **Loose (12 × snap\_threshold):** otherwise

This means same-color nodes snap neatly together while nodes with different colors get a visible gap.

---

## File Overview

| File | Purpose |
|---|---|
| `node_layout.py` | Core layout engine: dimension calculation, node placement, diamond resolution, collision avoidance |
| `menu.py` | Registers all commands and keyboard shortcuts in Nuke's Edit menu |
| `make_room.py` | Bulk node displacement for creating space in the DAG |
| `util.py` | Upstream selection and file-based sorting utilities |

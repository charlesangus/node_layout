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

The Leader Window is a "leader key" mode: press one shortcut to arm it, then
tap a single letter to fire a layout command, so the whole toolset is a
two-keystroke chord away without hunting through the menu.

Hover the mouse over the DAG and press `Shift+D`. A floating HUD appears at
the cursor, showing the command keys laid out in their QWERTY positions with a
matching text list on the right. The next key you press runs its command; an
unrecognised key, or a click outside the HUD, cancels leader mode and dismisses
the window. Because leader mode is armed from a menu shortcut scoped to the
DAG, the HUD only appears when the Node Graph has keyboard focus.

![The Leader Window HUD floating over the DAG, showing colour-coded key badges arranged like a QWERTY keyboard with a key list on the right.](docs/images/leader-window.png)

The badges are colour-coded by how the key behaves:

- **Teal — chaining keys** (`Q` `W` `E` `A` `S` `D`). These nudge and scale the
  selection and *keep leader mode armed* after they fire, so you can chain
  several moves in a row. Pressing the first chaining key hides the HUD, but
  leader mode stays live: keep tapping chaining keys to repeat, or press any
  one-shot key to finish.
- **Green — layout keys** (`Z` `V`). The primary "lay it out" actions.
- **Neutral — one-shot keys** (`F` `X` `C` `H` `Y`). These fire once and
  immediately exit leader mode.

Every key is also clickable: the HUD dispatches the same command when you click
a badge as when you press the corresponding key, following the same rules — a
chaining badge keeps the window armed, a one-shot or layout badge dispatches and
dismisses it.

Most commands are context-aware, acting on your selection: with one node
selected they operate on its upstream tree, and with two or more they operate on
the selection.

| Key | Action | Behaviour |
|---|---|---|
| `Q` | Shrink | chaining (teal) |
| `W` | Move Up | chaining (teal) |
| `E` | Expand | chaining (teal) |
| `A` | Move Left | chaining (teal) |
| `S` | Move Down | chaining (teal) |
| `D` | Move Right | chaining (teal) |
| `Z` | Horizontal Layout | layout (green) |
| `V` | Layout (upstream or selected) | layout (green) |
| `F` | Freeze Selected | one-shot (neutral) |
| `X` | Select Hidden Outputs | one-shot (neutral) |
| `C` | Clear Layout State | one-shot (neutral) |
| `H` | Arrange Horizontal | one-shot (neutral) |
| `Y` | Arrange Vertical | one-shot (neutral) |

| Command | Shortcut |
|---|---|
| Layout (Leader Mode) | `Shift+D` |

The badge letters follow your configured keyboard layout — on an AZERTY or
QWERTZ keyboard the affected letters are relabelled to the key in the same
physical position (see Preferences, below).

## Preferences

The Preferences dialog tunes the spacing, scaling, and leader-key behaviour of
Node Layout so you can match its output to your own graph style. Open it from
the Node Layout menu with **Node Layout Preferences…** (no shortcut). Changes
are written to `~/.nuke/node_layout_prefs.json` when you click OK, so they
persist between Nuke sessions.

![The Node Layout Preferences dialog, with fields grouped under Spacing, Scheme Multipliers, Leader Key, Behaviour, and Advanced headings.](docs/images/preferences-dialog.png)

The dialog is organised into five groups:

- **Spacing** sets the raw gaps used when nodes are placed: the horizontal
  gap between subtrees, the gap between a spine and a side input, the mask-input
  gap, the base vertical margin between stacked subtrees, and the mask input
  ratio. These feed directly into the layout maths, so larger values spread the
  graph out and smaller ones pack it tighter.
- **Scheme Multipliers** scale that base spacing for the Compact, Normal, and
  Loose layout schemes — for example the Compact and Loose menu commands simply
  apply the compact and loose multipliers. The loose gap multiplier separately
  controls how much extra room the loose scheme opens up.
- **Leader Key** controls the leader mode described above: the hint popup delay
  (in milliseconds — 0 shows the HUD immediately) before the Leader Window
  appears, and the keyboard layout (QWERTY, AZERTY, or QWERTZ) used to relabel
  and remap the command keys to their physical positions.
- **Behaviour** holds opt-in/opt-out toggles. Use Safe Delete replaces Nuke's
  stock Backspace/Delete with a guarded delete that only warns when a deletion
  would truly break dependencies.
- **Advanced** exposes the dot font reference size and the scaling reference
  count, which drive the font-based margin scaling and the
  square-root-of-node-count scaling that keeps large trees from growing without
  bound.

Values are validated on OK: non-numeric or out-of-range entries are rejected and
the dialog stays open. Saving also rebuilds the leader-key tables immediately, so
a new keyboard layout takes effect without restarting Nuke.

## Other Features

Beyond the headline layout commands, Node Layout ships a handful of smaller
utilities and behaviours. Most live in the Node Layout menu; a couple run
automatically as part of every layout.

### Compact and Loose variants

The Compact and Loose commands run the same Layout Upstream and Layout Selected
algorithms described above, but tighten or open up the spacing in one step —
handy when the default (Normal) spacing packs a tree too densely or leaves it
too airy for the shot you are working on. They are convenience shortcuts for a
one-off spacing scheme without changing your saved preferences: Compact applies
the compact multiplier (0.6) and Loose applies the loose multiplier (1.5) to the
base spacing, exactly the values documented under **Scheme Multipliers** in the
Preferences section. Adjust those multipliers there and every Compact/Loose run
follows suit.

These are menu-only; the plain Layout Upstream (`Shift+E`) and Layout Selected
commands cover the Normal scheme.

| Command | Shortcut |
|---|---|
| Layout Upstream Compact | *(none — run from the Node Layout menu)* |
| Layout Selected Compact | *(none — run from the Node Layout menu)* |
| Layout Upstream Loose | *(none — run from the Node Layout menu)* |
| Layout Selected Loose | *(none — run from the Node Layout menu)* |

### Clear Layout State

Node Layout remembers per-node settings — the scheme (Normal/Compact/Loose) and
the accumulated Shrink/Expand scale — by storing them on the nodes themselves, so
a later layout reuses your last choices. Clear Layout State wipes that stored
state, resetting the affected nodes to the default scheme and a scale of 1.0 the
next time they are laid out. Reach for it when a tree has drifted after repeated
Shrink/Expand passes, or when you want a clean baseline before re-running a
layout.

The Selected variant clears only the selected nodes; the Upstream variant clears
the selected node and its whole upstream tree. Both are wrapped in an undo group,
so a single `Ctrl+Z` restores the previous state. The command is also on the
Leader Window as the one-shot `C` key, which is context-aware like the other
leader keys: with one node selected it runs the Upstream variant, and with two
or more selected it runs the Selected variant.

| Command | Shortcut |
|---|---|
| Clear Layout State Selected | *(none — Node Layout menu, or `C` in Leader mode with two or more nodes selected)* |
| Clear Layout State Upstream | *(none — Node Layout menu, or `C` in Leader mode with one node selected)* |

### Diamond resolution

Diamond resolution is automatic — there is no command to run. Layout arranges
nodes as a tree, but real graphs contain "diamonds": a single node whose output
fans out to two or more consumers within the tree being laid out. A pure tree
cannot draw one node in two places, so before placing nodes the engine inserts a
hidden pass-through Dot on the second and later connections into any such shared
node. Each consumer then gets its own leaf to stack under, while the Dot
preserves the real DAG topology (its input still carries the shared node's
output). The inserted Dots are tagged internally and have their input hidden, so
they stay out of the way; you generally will not notice them beyond seeing the
tree lay out cleanly instead of overlapping. Non-mask connections always win the
"directly above" position over mask connections when both reach the same node.

### Select Upstream Ignoring Hidden

This selection helper walks up from the current node and selects its entire
visible upstream tree, following only ordinary input connections and skipping any
that are hidden. Use it to grab a whole branch for a follow-up operation —
layout, freeze, delete — without having to rubber-band or shift-click each node.
The starting node is included in the resulting selection along with everything
that feeds it through visible inputs.

Unlike the headline Layout Upstream (`Shift+E`), this command only *selects*
nodes; it does not move anything.

| Command | Shortcut |
|---|---|
| Select Upstream Ignoring Hidden | `E` |

### Sort by filename

Sort by filename lines the selected file-based nodes up in a single horizontal
row, left to right, in alphabetical order of their file paths — a quick way to
put a scattered set of Reads into a predictable, readable order. Only nodes that
have a `file` knob are affected; anything else in the selection is ignored. The
row starts at the top-left corner of the selection's current bounds and spaces
the nodes at a fixed 300-unit horizontal interval on a single line.

The command appears in the menu as **Arrange by Filename** and has no shortcut.

| Command | Shortcut |
|---|---|
| Arrange by Filename | *(none — run from the Node Layout menu)* |

### Safe Delete

Safe Delete replaces Nuke's stock Backspace/Delete so the "this will break
hidden-input / expression links" warning only appears when a deletion would
*actually* leave a dangling link — that is, when a deleted node still has a
dependent that is not itself being deleted in the same operation. Nuke's default
warns even when every dependent is part of the same delete, which trains you to
click straight through it; Safe Delete stays silent in that safe case and only
interrupts when it matters. Viewer nodes are always treated as harmless
dependents and never trigger the prompt.

It works on the normal Backspace/Delete keys — there is no separate menu entry —
and is governed by the **Use Safe Delete** checkbox in the Preferences dialog
(see the Behaviour group under Preferences, above). Uncheck it to fall back to
Nuke's stock delete behaviour.

| Action | Shortcut |
|---|---|
| Safe Delete | `Backspace` / `Delete` (when Use Safe Delete is enabled) |

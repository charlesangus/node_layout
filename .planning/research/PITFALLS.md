# Domain Pitfalls — node_layout v1.1

**Domain:** Nuke DAG auto-layout plugin — v1.1 feature additions
**Researched:** 2026-03-05
**Scope:** Integration pitfalls for adding per-node state knobs, horizontal B-spine mode,
multi-input fan alignment, Shrink/Expand axis modes, Dot font-size margin scaling,
Group context fix, and spacing rebalance to the existing ~4,095 LOC system.

---

## Critical Pitfalls

Mistakes that cause rewrites, silent data loss, or user-visible breakage.

---

### Pitfall 1: Dynamically Added Knobs Are Not Serialized to .nk Files

**What goes wrong:**
`node.addKnob()` in Python adds the knob to the live node object, but the knob structure
(the `addUserKnob` declaration) is NOT automatically written into the .nk save file.
When the script is saved and reopened, the knob is gone. Any values stored in it are
silently lost. The node behaves as if it was never tagged.

**Why it happens:**
Nuke only serializes knobs that were defined at node creation time (built-in knobs) or
added via the "User" knob panel in the GUI (which writes `addUserKnob` records). Python-side
`addKnob()` calls modify the in-memory node only. On file reload, those knobs do not exist,
so `.value()` calls raise `AttributeError` or return wrong defaults.

**Consequences:**
- All per-node layout state (layout_mode, scheme, scale_factor) is lost on every save/open.
- Re-layout after reload ignores the stored state — the "least surprise" re-layout feature
  becomes silent no-op.
- If the read code does not guard against missing knobs, it raises an exception inside the
  undo group and triggers `Undo.cancel()`, rolling back the entire layout.

**Prevention:**
Two legitimate patterns exist:

1. **`addUserKnob` via TCL string (preferred for simple values):** Use
   `nuke.tcl('addUserKnob {INT layout_mode_store l "Layout Mode" +HIDDEN}')` executed
   within a knob-changed or onCreate callback. Knobs added this way are written as
   `addUserKnob` records in the .nk file and survive reload.

2. **`nuke.addOnCreate` callback per class:** Register an `addOnCreate` callback that
   checks for the knob and adds it if missing. This runs at node creation AND at file
   load for every node of that class. The knob is re-created fresh each load, so the
   value stored in the .nk file (via the standard knob serialization) is still read back
   correctly because Nuke stores knob _values_ separately from knob _declarations_.

**Detection:**
Save a script with a freshly tagged node, close Nuke, reopen the script, then check
`node.knob('node_layout_mode')`. If it returns `None`, the declaration is not persisting.

**Phase that must address this:** Per-node state storage phase. This is the foundational
correctness requirement for the entire state-replay feature.

---

### Pitfall 2: Group Context — `nuke.nodes.Dot()` Creates Nodes at Root, Not in Current Group

**What goes wrong:**
When the layout plugin runs while the user has a Group node open (double-clicked into its
internal DAG), `nuke.nodes.Dot()` and `nuke.nodes.NodeClass()` create nodes at the ROOT
level of the script, NOT inside the currently open Group. The newly inserted Dot appears
in the wrong context, connects to nothing useful, and the DAG is corrupted.

**Why it happens:**
`nuke.nodes.Dot()` is a raw node factory that ignores the current DAG view context.
`nuke.createNode("Dot", inpanel=False)` respects the last-hit group view context via
`nuke.lastHitGroup()`, but `nuke.nodes.Dot()` does not. The existing code uses
`nuke.nodes.Dot()` in `insert_dot_nodes()` and `place_subtree()`.

**Consequences:**
- Diamond-resolution Dots and side-input Dots appear at root level while the operated
  nodes are inside a Group. The DAG is now in a structurally inconsistent state.
- `nuke.Undo.cancel()` will roll back position changes but NOT the misplaced Dot
  creation if the undo boundary is around only the position moves.
- `nuke.allNodes()` called inside the undo group operates on root when the user is inside
  a Group, so `push_nodes_to_make_room` pushes root-level nodes, not Group members.

**Prevention:**
Before any node creation, capture `current_group = nuke.thisGroup()` (or
`nuke.root()` when at top level). Wrap all `nuke.nodes.Dot()` calls as:
```python
current_group.begin()
dot = nuke.nodes.Dot()
current_group.end()
```
Alternatively, replace `nuke.nodes.Dot()` with `nuke.createNode("Dot", inpanel=False)`
which naturally follows the last-hit group context. The `nuke.allNodes()` call in
`push_nodes_to_make_room` must also be scoped: pass `group=current_group` as an argument.

**Detection:**
Run "Layout Upstream" while double-clicked into a Group node. Check if new Dot nodes
appear at root level (`nuke.root()`) rather than inside the Group.

**Phase that must address this:** Group context bug fix phase (standalone, low risk once
the correct API call is identified).

---

### Pitfall 3: Horizontal B-spine Mode — Axis Swap in `compute_dims` Produces Incorrect Memoized Results

**What goes wrong:**
`compute_dims` returns `(width, height)` for the vertical layout. Adding a horizontal
mode by transposing `(width, height)` to `(height, width)` inside the same function,
while sharing the same `memo` dict keyed by `id(node)`, causes silent cache collisions
when a node appears in both a vertical and horizontal subtree in the same layout pass —
or when memo is not cleared between axis passes.

**Why it happens:**
The `memo` dict is keyed by `id(node)`. If `compute_dims` is called for vertical first
and then for horizontal (or vice versa), the second call returns the cached vertical
result for a horizontal placement because the key is the same. The staircase formulas
in `place_subtree` then compute positions using width as height and vice versa, producing
overlapping or nonsensical layouts.

**Consequences:**
- Subtrees placed in horizontal mode have wrong bounding-box sizes — nodes overlap.
- The bug is intermittent: it only manifests when a node is reachable from both a
  vertical-mode and horizontal-mode root in the same layout operation, or when the memo
  dict is reused across multiple calls without clearing.
- It is invisible in isolated test cases (single-axis) and only appears in real scripts.

**Prevention:**
- Keep horizontal mode's `compute_dims` in a separate function (e.g., `compute_dims_h`)
  or pass an `axis` parameter and include it in the memo key:
  `memo_key = (id(node), axis)`.
- Never share a `memo` dict across a vertical and horizontal layout pass in the same
  operation.
- The cleanest design: the horizontal B-spine root is the _only_ entry point for the
  horizontal pass. The memo is created fresh for each `layout_upstream()` call (it
  already is), so the risk is only when horizontal and vertical modes are combined in
  one operation.

**Detection:**
Construct a DAG where one node is reachable via a vertical-mode path and a horizontal-
mode path simultaneously. After layout, check for node overlaps.

**Phase that must address this:** Horizontal B-spine layout phase (initial design).

---

### Pitfall 4: Horizontal B-spine — `place_subtree` X/Y Role Reversal Breaks Dot Insertion Logic

**What goes wrong:**
`place_subtree` has deeply interwoven X-vs-Y semantics: "above" means lower Y, side
inputs go to higher X, dots are centered on X, the staircase walks Y. Transposing the
axis for horizontal mode by swapping `x`/`y` arguments at the call site silently breaks
every helper that still references absolute X/Y in Nuke's coordinate system (`_center_x`,
`_subtree_margin`, `push_nodes_to_make_room` bounding box directions, dot centering logic).

**Why it happens:**
Nuke's DAG has immutable absolute coordinate semantics: `setXpos`/`setYpos` always refer
to screen X and Y regardless of "layout axis." A naive axis swap passes transposed values
to `setXpos`/`setYpos` which means (intended_x, intended_y) = (actual_y, actual_x) in
screen space — nodes end up in mirrored positions.

**Consequences:**
- Horizontal layout produces a mirrored vertical layout, not a horizontal one.
- Dot positioning formulas produce dots far off-screen.
- `push_nodes_to_make_room` uses `grew_up` / `grew_right` logic that assumes vertical
  expansion; horizontal mode's expansion is in the X axis ("grew_right"), which is
  handled, but the delta computation reverses the meaning of `before_min_y`.

**Prevention:**
Do not reuse `place_subtree` with swapped arguments. Design a dedicated
`place_subtree_horizontal(node, x, y, ...)` that consistently uses X for the spine axis
and Y for the branching axis. Share only the per-node knob read/write helpers and the
side-input Dot insertion mechanics. Treat it as a sibling function, not a wrapper.

**Detection:**
Run horizontal B-spine on a 3-node linear chain. Nodes should appear left-to-right at
the same Y. If they appear top-to-bottom at the same X, axis swap went through wrong path.

**Phase that must address this:** Horizontal B-spine layout phase (architecture decision).

---

### Pitfall 5: Per-Node Knob Read Inside Recursive `compute_dims` / `place_subtree` Breaks Memoization Contract

**What goes wrong:**
Reading per-node knobs (layout_mode, scheme, scale_factor) inside `compute_dims` so that
each node can override its subtree's behavior causes memoization to produce wrong cached
results. The memo is keyed by `id(node)`. If node A's dimensions depend on its own
layout_mode knob value, but a sibling subtree also reaches node A via a diamond path,
the second traversal gets the cached result from the first traversal's context — which
may have used a different effective scheme_multiplier.

**Why it happens:**
The memo key is `id(node)` only. The cached result encodes assumptions about
`scheme_multiplier` that were valid for the first traversal path but may not match the
second path's context (e.g., if one root has a custom scale_factor knob that altered the
multiplier mid-recursion).

**Consequences:**
- Diamond paths with mixed per-node overrides produce subtree bounding boxes that are
  too small or too large, causing node overlap after placement.
- Bug is non-deterministic: depends on traversal order, which depends on which root is
  processed first.

**Prevention:**
Read per-node knobs at the TOP of each `layout_upstream()` / `layout_selected()` call,
not inside the recursive functions. Resolve the effective scheme and scale for the whole
operation before recursion begins. Per-node state should determine which COMMAND to use
(e.g., dispatch to `layout_upstream` with the stored `scheme_multiplier`), not
dynamically alter multipliers mid-recursion.

**Detection:**
Create a diamond DAG where the shared upstream node has a per-node scale_factor knob
set to a non-default value. Run layout and check if the shared node's subtree bounding
box is computed consistently.

**Phase that must address this:** Per-node state storage and replay phase.

---

## Moderate Pitfalls

Mistakes that cause subtle layout quality bugs or unexpected UX, but not data loss.

---

### Pitfall 6: Fan Alignment — Same-Y Constraint Fights the Staircase Formula

**What goes wrong:**
The multi-input fan alignment feature (2+ non-mask inputs have subtree roots at same Y)
directly conflicts with the existing staircase formula in `place_subtree`. The staircase
assigns different Y positions to each input band. Forcing all non-mask inputs to the
same Y requires collapsing the inter-band vertical gaps to zero for primary inputs —
but the inter-band gaps (`side_margins_v`) are also used to separate subtrees vertically.
If gaps are zeroed, subtrees overlap.

**Why it happens:**
The staircase formula in `place_subtree` distributes vertical space to prevent subtree
overlap. Fan alignment (same Y for roots) works in horizontal mode (where the spine is X)
but is incorrect in vertical mode unless subtrees grow strictly sideways with no vertical
extent. In practice, subtrees always have vertical extent.

**Prevention:**
Fan alignment (same-Y roots) should only apply in horizontal B-spine mode where inputs
are placed left-to-right and their subtrees extend upward (negative Y). In vertical mode,
what "fan alignment" should mean is alignment of the side-input Dot nodes' vertical
position, not the subtree roots themselves. Clarify the spec before implementing.
If vertical fan alignment is required, the staircase must compute a Y that satisfies
both the subtree non-overlap constraint AND the same-Y-root constraint — potentially
requiring a max() across all subtree heights, which significantly increases total width.

**Detection:**
Layout a merge node with 3 inputs of varying subtree depths. If inputs share Y but
subtrees overlap, the staircase-vs-fan conflict has occurred.

**Phase that must address this:** Multi-input fan alignment phase (spec clarification first).

---

### Pitfall 7: Mask Side-Swap — `_is_mask_input` False Negatives on Unusual Node Classes

**What goes wrong:**
The mask-goes-left rule (when 2+ non-mask inputs are present) depends on `_is_mask_input`
correctly identifying every mask/matte slot. The current implementation has three
detection paths: class-specific hardcoding (`Merge2`, `Dissolve`), label inspection
(`inputLabel(i).lower()` contains "mask" or "matte"), and a fallback on
`maskChannelInput`/`maskChannel` knobs with last-input assumption. Nodes that have a
mask channel but label it differently (e.g., "Stencil", "Alpha", "Holdout") will be
misclassified as non-mask, placed on the wrong side, and the mask side-swap logic will
activate incorrectly.

**Prevention:**
Do not expand `_MERGE_LIKE_CLASSES` speculatively. Instead, rely on the label-inspection
path as the primary signal and document that the feature works for standard Foundry nodes.
Add a note in code comments that non-standard third-party nodes may not trigger the swap.
The fallback heuristic (last input + mask knob) is already a reasonable safety net.

**Detection:**
Test with a Merge node (2+ non-mask inputs), a Keymix node (has alpha/mask), and a
custom gizmo with an atypically labeled mask slot.

**Phase that must address this:** Multi-input fan alignment / mask side-swap phase.

---

### Pitfall 8: Expand Push-Away — Double-Push When Called After Layout

**What goes wrong:**
`expand_selected` and `expand_upstream` will gain push-away behavior (same as regular
layout). If the user runs "Layout Upstream" followed immediately by "Expand Upstream",
the push logic fires twice: once at the end of layout (which already repositioned
surrounding nodes) and again after expand. The second push uses `bbox_before` = the
layout's final bounding box and `bbox_after` = the expanded bounding box. Nodes that
were already pushed by layout may be pushed again, accumulating displacement.

**Why it happens:**
`push_nodes_to_make_room` is stateless — it pushes based purely on bounding box delta.
It does not know that some nodes were already pushed in a prior operation. Each call
is additive.

**Consequences:**
- Surrounding nodes drift further than intended with each expand operation.
- Users who habitually expand after layout will see surrounding nodes migrate across the
  DAG over time.

**Prevention:**
This is inherent to the stateless push model. Mitigate by making push-away in Expand
commands optional (off by default) or by ensuring the push amount is conservative (only
push nodes that are immediately adjacent to the expanded bounding box, not all upstream
nodes). Document the additive behavior clearly.

**Detection:**
Run Layout Upstream, then Expand Upstream three times. Measure accumulated displacement
of a node that was not in the subtree. Compare to a single Expand-only run.

**Phase that must address this:** Shrink/Expand axis modes and expand push-away phase.

---

### Pitfall 9: Shrink/Expand H/V/Both — Scale Factor Applied to Wrong Axis After Knob Read

**What goes wrong:**
Adding axis-mode commands (Shrink H, Shrink V, Shrink Both) to `_scale_selected_nodes`
and `_scale_upstream_nodes` requires making the X and Y deltas independently scaleable.
A common mistake is to apply `scale_factor` to both `dx` and `dy`, then zero out one
axis, but the snap-minimum floor (`snap_min`) is then applied on the zeroed axis too,
producing unintended minimum displacement on the axis that should be unchanged.

**Prevention:**
Apply the snap-minimum floor only on axes that are being scaled. When scaling only H
(X axis), `dy` is preserved unchanged — do NOT apply `abs(new_dy) < snap_min` logic
to `dy`. Guard the snap floor with an axis-mode check.

**Detection:**
Run Shrink H on a vertical chain. Nodes should not move vertically at all. If they
shift by `snap_min` pixels vertically, the floor is being misapplied.

**Phase that must address this:** Shrink/Expand axis modes phase.

---

### Pitfall 10: Dot Font Size — `screenHeight()` Not Updated Until Idle Time

**What goes wrong:**
Reading `note_font_size` from a Dot node to scale the subtree margin is fine as a knob
read. However, if the code also tries to use the Dot's `screenHeight()` after the font
size is set (or changed), `screenHeight()` returns a stale value. This is a documented
Nuke behavior: node screen dimensions update during idle time, not synchronously within
the same Python call stack.

**Why it happens:**
Nuke defers DAG geometry recalculation to idle time for performance. Any code that sets
a display property (like font size or label) and then immediately reads `screenHeight()`
in the same function will see the pre-change dimension.

**Consequences:**
- If the margin scaling reads `dot.screenHeight()` to determine Dot size and uses it
  as an offset, the computed margin is wrong for the current font size.
- The error corrects itself on the next layout operation (by then, idle has run), so it
  appears intermittent.

**Prevention:**
Do not use `screenHeight()` of a Dot to determine margin. Instead, compute the expected
Dot height from the font size directly (Dot height is approximately `font_size + 16px`
in standard Nuke DAG rendering, though this is empirical and not documented). Alternatively,
read `note_font_size` only and use it as a pure scaling input without relying on
`screenHeight()` for the same Dot.

**Detection:**
Immediately after setting `dot['note_font_size'].setValue(48)`, call `dot.screenHeight()`.
It will return the old height. After `nuke.updateUI()` or on next idle, it returns the
new height.

**Phase that must address this:** Dot font size margin scaling phase.

---

### Pitfall 11: Per-Node Knob Write Inside Undo Group — Knob Values Roll Back on Cancel

**What goes wrong:**
If per-node knob writes (storing layout_mode, scheme, scale_factor) happen inside the
`nuke.Undo.begin()` / `nuke.Undo.end()` block, they are recorded in the undo history.
When the user presses Ctrl+Z, the knob values revert along with the positions — which
is usually correct. However, if a layout raises an exception and `Undo.cancel()` fires,
any knob writes that happened before the exception are also rolled back. This is the
correct behavior, but it means the write-then-read pattern must be ordered carefully:
read the stored state BEFORE beginning the undo group; write (update) the state INSIDE
the undo group.

**Prevention:**
- Read knob state → resolve effective parameters → open undo group → do layout →
  write knob state → close undo group. Never read knob state inside the undo group after
  writing, as the write may have occurred on a prior run.
- If writing knob state should NOT be undoable (i.e., state should persist even if layout
  is undone), use `nuke.Undo.disable()` around the knob write — but this requires
  careful pairing with `nuke.Undo.enable()` and is rarely the right choice.

**Detection:**
Write a known state into a per-node knob inside a layout operation. Trigger an exception
mid-layout. Verify the knob value was rolled back by `Undo.cancel()`.

**Phase that must address this:** Per-node state storage phase (undo ordering design).

---

### Pitfall 12: Horizontal Spacing Preferences — `normal_multiplier` Misapplied to Horizontal Gap

**What goes wrong:**
The current `_subtree_margin` function applies `mode_multiplier` (the scheme multiplier
for compact/normal/loose) to both vertical and horizontal margin calculations. If a new
`horizontal_gap` preference is added, applying `scheme_multiplier` to it as well means
compact mode squishes horizontal spacing alongside vertical — which may be undesired.
The existing key decision (compact/loose scheme affects vertical gaps only, horizontal
is category-based) should be honored.

**Prevention:**
Store horizontal gap preferences as absolute values, not multiplier-scaled values. Read
`horizontal_gap` from prefs at call time but do NOT pass `scheme_multiplier` to the
horizontal margin path. The vertical margin already uses `scheme_multiplier`; keep that
path separate from the horizontal path.

**Detection:**
Run compact layout and measure horizontal gap between side inputs. If it is proportionally
smaller than normal layout's horizontal gap, the multiplier is being applied incorrectly.

**Phase that must address this:** Spacing rebalance phase (design decision up front).

---

## Minor Pitfalls

Issues that cause minor friction or require small fixes.

---

### Pitfall 13: Idempotency — Adding Knobs/Tabs to Nodes That Already Have Them

**What goes wrong:**
If `_ensure_node_layout_knobs(node)` is called on a node that already has the
`node_layout_tab` Tab_Knob (e.g., because the node already carries the diamond-dot
marker tab from a prior run), calling `node.addKnob(nuke.Tab_Knob('node_layout_tab', ...))`
again silently adds a duplicate tab. The node now shows two "Node Layout" tabs, and
the second set of knobs shadows or confuses the first.

**Prevention:**
Always guard with `if node.knob('node_layout_tab') is None:` before adding the tab.
Similarly guard each individual knob: `if node.knob('node_layout_mode') is None:`.
Note that `node.knob('name')` returns `None` (not raises) when the knob is absent —
this is the correct check pattern (confirmed from Nuke API docs).

**Detection:**
Open a node's properties panel after two successive layout runs. If two "Node Layout"
tabs are visible, the guard is missing.

**Phase that must address this:** Per-node state storage phase.

---

### Pitfall 14: Menu Command Renames — Keyboard Shortcut Tab-Completion Order Changes

**What goes wrong:**
Renaming "Compact Layout Upstream" → "Layout Upstream Compact" (scheme name at end)
changes the sort order in Nuke's tab-menu. Users who type "Layout" in the tab-menu will
see both "Layout Upstream" and "Layout Upstream Compact" as adjacent entries — which is
the intended improvement. However, if the shortcut context bindings are not updated
correspondingly, the old names may still appear in conflict warnings from Nuke on startup.

**Prevention:**
In `menu.py`, update both the display name string AND verify no old name persists in
any string-based `addCommand` call (there are no other callers in this codebase). Run
Nuke once after the rename and check the Script Editor for "shortcut conflict" or
"duplicate command" warnings.

**Detection:**
After rename, open Nuke and check the Nuke Script Editor output on startup for warnings.

**Phase that must address this:** Command renames phase (trivial, low risk).

---

### Pitfall 15: `nuke.allNodes()` in `push_nodes_to_make_room` Ignores Group Context

**What goes wrong:**
`push_nodes_to_make_room` calls `nuke.allNodes()` with no group argument. At root level,
this correctly returns all root-level nodes. But when layout runs inside a Group
(after the Group context fix is applied to Dot creation), `push_nodes_to_make_room`
still pushes root-level nodes because `nuke.allNodes()` defaults to the current Python
execution context, not the DAG view context.

**Prevention:**
Pass the correct group to `push_nodes_to_make_room` as a parameter:
`nuke.allNodes(group=current_group)`. Capture `current_group = nuke.thisGroup()` at
the top of `layout_upstream()` and thread it through to the push function.

**Detection:**
Run Layout Upstream inside a Group. Observe if any root-level nodes move. If they do,
the context is wrong.

**Phase that must address this:** Group context fix phase (part of the same fix as Pitfall 2).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Per-node state storage | Knobs not serialized to .nk file (Pitfall 1) | Use `addUserKnob` TCL or `addOnCreate`; always guard idempotency (Pitfall 13) |
| Per-node state storage | Knob reads inside recursion break memo (Pitfall 5) | Read state at entry points only; resolve parameters before recursion |
| Per-node state storage | Undo ordering — reads before undo group, writes inside (Pitfall 11) | Explicit ordering rule in implementation |
| Horizontal B-spine | Memo cache collision across axes (Pitfall 3) | Separate memo key includes axis, or use dedicated `compute_dims_h` |
| Horizontal B-spine | Axis swap silently breaks X/Y semantics (Pitfall 4) | Dedicated `place_subtree_horizontal` function; no shared entry point with swapped args |
| Multi-input fan alignment | Same-Y constraint fights staircase (Pitfall 6) | Clarify spec before coding; fan alignment may only be valid for horizontal B-spine mode |
| Multi-input fan alignment | Mask detection false negatives (Pitfall 7) | Rely on label inspection; document scope of detection |
| Shrink/Expand axis modes | Snap floor applied to non-scaled axis (Pitfall 9) | Axis-mode guard around snap floor logic |
| Expand push-away | Double-push accumulation (Pitfall 8) | Conservative push; document additive behavior |
| Dot font size margin | `screenHeight()` stale after font change (Pitfall 10) | Compute expected height from font size value; never rely on `screenHeight()` in same call |
| Group context fix | `nuke.nodes.Dot()` creates in wrong context (Pitfall 2) | Wrap all node creation with `current_group.begin()/end()` |
| Group context fix | `nuke.allNodes()` still uses root context (Pitfall 15) | Pass `group=current_group` to all `nuke.allNodes()` calls |
| Spacing rebalance | `scheme_multiplier` applied to horizontal gap (Pitfall 12) | Keep horizontal gap path independent of scheme multiplier |
| Command renames | Stale names in menu.py or startup warnings (Pitfall 14) | Check Script Editor output on first post-rename Nuke launch |

---

## Sources

- Foundry Nuke Python API — Tab_Knob: https://learn.foundry.com/nuke/developers/140/pythonreference/_autosummary/nuke.Tab_Knob.html
- Foundry Nuke Python API — Node.addKnob: https://learn.foundry.com/nuke/developers/140/pythonreference/_autosummary/nuke.Node.html
- Foundry Nuke Python API — allNodes: https://learn.foundry.com/nuke/developers/140/pythonreference/_autosummary/nuke.allNodes.html
- Foundry Nuke Python API — Undo: https://learn.foundry.com/nuke/developers/150/pythondevguide/_autosummary/nuke.Undo.html
- screenHeight() not updating (mailing list thread): https://www.mail-archive.com/nuke-python@support.thefoundry.co.uk/msg02764.html
- screenHeight() original report: https://www.mail-archive.com/nuke-python@support.thefoundry.co.uk/msg02763.html
- Adding knobs to existing tab: https://www.mail-archive.com/nuke-python@support.thefoundry.co.uk/msg00234.html
- addOnCreate for persistent knobs: https://benmcewan.com/blog/2018/09/10/add-new-functionality-to-default-nodes-with-addoncreate/
- nuke.nodes.X vs nuke.createNode group context: https://conradolson.com/add-nodes-inside-a-group-with-python (LOW confidence — WebSearch only)
- Group context and lastHitGroup: https://learn.foundry.com/nuke/developers/140/pythonreference/_autosummary/nuke.allNodes.html
- note_font_size knob default: WebSearch (MEDIUM confidence — community sources consistent with Nuke knob conventions)
- Custom knob serialization via addUserKnob: WebSearch + official knob docs (MEDIUM confidence)

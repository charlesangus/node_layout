---
status: resolved
trigger: "HORIZ-03 mode replay only works when selecting the exact stored root node, but not when selecting a downstream node and running Layout Upstream"
created: 2026-03-14T00:00:00Z
updated: 2026-03-14T00:00:00Z
---

## Current Focus

hypothesis: layout_upstream reads mode only from the selected node (root); if root is downstream of the horizontal chain it has mode="vertical" so the horizontal path is never taken
test: read layout_upstream lines 1186-1193 and layout_selected lines 1310-1317
expecting: confirmed — mode check is exclusively on the selected node, no upstream walk to discover horizontal-mode nodes
next_action: DONE — root cause confirmed, diagnosis returned

## Symptoms

expected: Running Layout Upstream on any downstream node of a horizontal chain replays the horizontal mode
actual: Only works if you select the exact stored root node; selecting a downstream node ignores the horizontal mode flag
errors: none (silent wrong-path: falls through to vertical layout)
reproduction: lay out a chain horizontally, select a node downstream of the horizontal root, run Layout Upstream
started: always

## Eliminated

(none — root cause found on first investigation)

## Evidence

- timestamp: 2026-03-14T00:00:00Z
  checked: layout_upstream lines 1185-1213
  found: |
    root_stored_state = node_layout_state.read_node_state(root)
    root_mode = root_stored_state.get("mode", "vertical")
    if root_mode == "horizontal": ...
  implication: mode is read exclusively from `root` (the selected node). If selected node is downstream, it was written with mode="vertical" (line 1237), so horizontal path is never entered.

- timestamp: 2026-03-14T00:00:00Z
  checked: state write-back loop lines 1226-1239
  found: |
    if root_mode == "horizontal":
        stored_state["mode"] = "horizontal" if id(state_node) in replay_spine_set else "vertical"
    else:
        stored_state["mode"] = "vertical"
  implication: Only spine nodes get mode="horizontal". Any node downstream of the spine (i.e. downstream of the original root) is NOT in the subtree at all — its mode is never written by layout_upstream. So a downstream consumer node retains whatever mode it had before, which is "vertical" by default.

- timestamp: 2026-03-14T00:00:00Z
  checked: collect_subtree_nodes — traversal direction
  found: traverses only inputs (upstream), never outputs (downstream)
  implication: When layout_upstream is called with a downstream node selected, collect_subtree_nodes walks upstream through the horizontal chain fine. But the mode check is on the selected node itself, not on any of its inputs.

- timestamp: 2026-03-14T00:00:00Z
  checked: layout_selected lines 1310-1317 (same pattern)
  found: same root_mode = root_stored_state.get("mode", "vertical") check on each root node
  implication: layout_selected has the same bug for the same reason.

## Resolution

root_cause: |
  Both layout_upstream and layout_selected read the horizontal-mode flag exclusively
  from the selected node itself. When the selected node is downstream of the horizontal
  chain, its stored mode is "vertical" (default), so the code takes the vertical path
  and never calls place_subtree_horizontal. No upstream walk is performed to discover
  whether any input of the selected node carries mode="horizontal".

fix: |
  After reading root_mode, if root_mode is NOT "horizontal", walk the selected node's
  input(0) chain (upstream through input[0]) to find the first node whose stored mode
  is "horizontal". If found, treat THAT node as the effective horizontal root for the
  replay (i.e. call place_subtree_horizontal with it as the root, building the
  spine_set starting from that node). The selected node then acts merely as the trigger
  for the walk.

  Alternatively — simpler and more targeted — change the mode check from reading the
  selected node alone to also scanning the upstream subtree nodes for any
  mode="horizontal" entry. If any spine node is found upstream, honour the horizontal
  replay regardless of what the selected node's own mode says.

verification: applied — fixed by commit 8ef07b9
files_changed:
  - node_layout.py

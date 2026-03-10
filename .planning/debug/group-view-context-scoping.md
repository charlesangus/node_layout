---
status: diagnosed
trigger: "layout commands don't correctly scope to the Group context when using Nuke's Group View mode"
created: 2026-03-07T00:00:00Z
updated: 2026-03-07T00:00:00Z
---

## Current Focus

hypothesis: nuke.thisGroup() only resolves the context established by the Python call stack (Ctrl-Enter nav), not the UI-level Group View panel context
test: code review + Nuke API research
expecting: nuke.lastHitGroup() is the correct replacement
next_action: DONE — root cause confirmed via API docs and code review

## Symptoms

expected: layout_upstream() and layout_selected() create Dot nodes inside the Group being viewed
actual: when using Group View (inline expansion), Dot nodes are created at root level
errors: no Python error — silent misbehaviour
reproduction: open a Group via Group View (not Ctrl-Enter), run layout_upstream() or layout_selected()
started: always broken for Group View mode; Ctrl-Enter path works correctly

## Eliminated

- hypothesis: bug is in place_subtree() or insert_dot_nodes() themselves
  evidence: those functions create nodes via nuke.nodes.Dot() which inherits context from the `with current_group:` block — they are correct
  timestamp: 2026-03-07

- hypothesis: the `with current_group:` context manager block is being entered incorrectly
  evidence: the block itself is fine; the problem is entirely in what object current_group holds before the block is entered
  timestamp: 2026-03-07

## Evidence

- timestamp: 2026-03-07
  checked: node_layout.py line 583 and 633
  found: both layout_upstream() and layout_selected() open with `current_group = nuke.thisGroup()`
  implication: this is the sole determination of which group context Dot creation and node enumeration will use

- timestamp: 2026-03-07
  checked: Nuke Python API docs — nuke.thisGroup()
  found: thisGroup() returns the group that is currently being executed in (the Python call-stack context), which corresponds to the group the user Ctrl-Entered into. It is NOT panel/UI aware.
  implication: when a menu command is triggered from outside a group's Python execution context, thisGroup() returns nuke.root()

- timestamp: 2026-03-07
  checked: Nuke Python API docs — nuke.lastHitGroup()
  found: "To find out the group of the last hit Group View, use nuke.lastHitGroup(). This can be used to support Group View when creating custom menu items." Official Foundry documentation explicitly calls this out as the Group View support API.
  implication: lastHitGroup() returns the Group node whose inline Group View panel was most recently interacted with (clicked into). When not in Group View (at root DAG), it returns nuke.root() — the same safe fallback as thisGroup() in that scenario.

- timestamp: 2026-03-07
  checked: nukescripts.create.createNodeLocal
  found: Foundry's own "create node in correct context" wrapper uses lastHitGroup() internally, not thisGroup(). This is the canonical pattern Foundry established for menu commands that must be Group View aware.
  implication: thisGroup() is correct for callbacks RUNNING INSIDE a group's script. lastHitGroup() is correct for menu/toolbar commands triggered from the UI.

- timestamp: 2026-03-07
  checked: push_nodes_to_make_room() signature (line 531) and call sites (lines 609, 683)
  found: current_group is passed through and used as `current_group.nodes()` to enumerate DAG nodes. If current_group is nuke.root() instead of the actual Group, this will enumerate ALL root-level nodes, silently corrupting non-subtree node positions at root level.
  implication: the bug is not just about where Dots land — push_nodes_to_make_room also operates on the wrong node set

- timestamp: 2026-03-07
  checked: `with current_group:` usage in both functions (lines 589, 641)
  found: the `with` statement calls group.begin()/group.end() which sets the active context for nuke.nodes.Dot() and all other node-creation calls inside the block
  implication: fixing current_group at capture time fixes ALL downstream effects: Dot creation location, nuke.selectedNodes() scoping, and push_nodes_to_make_room enumeration

## Resolution

root_cause: |
  nuke.thisGroup() resolves the GROUP CONTEXT FROM THE PYTHON CALL STACK — it returns the group
  that is currently being script-executed (set by Ctrl-Enter navigation). It has no awareness of
  the UI panel that triggered the menu command.

  In Group View mode the user never Ctrl-Entered the group, so the Python call stack context is
  nuke.root(). nuke.thisGroup() therefore returns nuke.root(), and `with nuke.root():` makes all
  subsequent nuke.nodes.Dot() calls land at root level.

  The correct API for menu/toolbar commands that must respect Group View is nuke.lastHitGroup().
  Foundry documents it explicitly for this purpose and their own nukescripts.createNodeLocal uses
  it internally. When the active DAG panel is the root (not a Group View), lastHitGroup() returns
  nuke.root() — the same safe result as thisGroup() in that scenario, so it is a safe universal
  replacement.

fix: |
  Replace `current_group = nuke.thisGroup()` with `current_group = nuke.lastHitGroup()` on:
  - layout_upstream()  line 583
  - layout_selected()  line 633
  No other changes required. The `with current_group:` block, push_nodes_to_make_room() call,
  and all internal helpers are correct and unaffected.

verification: N/A — diagnosis only, no code changes made
files_changed: []

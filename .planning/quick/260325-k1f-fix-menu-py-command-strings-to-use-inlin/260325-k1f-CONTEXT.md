---
name: Fix menu.py inline import strings — context
description: User decisions for converting all menu.py addCommand calls to inline import string form
type: project
---

# Quick Task 260325-k1f: Fix menu.py command strings to use inline import form — Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Task Boundary

Update `menu.py` so every `addCommand` call uses the string form `"import X; X.do_thing()"` rather than callable references. Ensure the inline import is correct for each command so no NameError can occur at invocation time.

</domain>

<decisions>
## Implementation Decisions

### Scope
- Convert ALL `addCommand` calls to inline import string form (not just the already-string ones).
- Consistent approach: every command becomes a string, reload-safe, matches Nuke best practice.

### Top-level imports
- Remove the top-level module imports that become unused after conversion (node_layout, node_layout_prefs_dialog, make_room, util).
- `import nuke` stays — still needed for `nuke.menu("Nuke")` and `m.findItem("Edit")`.

### Claude's Discretion
- Exact string form: `"import node_layout; node_layout.layout_upstream()"` pattern.
- Callable arguments (e.g. `direction='down'`, `amount=800`) stay as-is inside the string call.
- Shortcut and shortcutContext args remain unchanged.

</decisions>

<specifics>
## Specific Ideas

- Before: `node_layout.layout_upstream` (callable ref)
- After: `"import node_layout; node_layout.layout_upstream()"`

- Before: `"make_room.make_room(direction='down')"` (string, no import)
- After: `"import make_room; make_room.make_room(direction='down')"`

</specifics>

<canonical_refs>
## Canonical References

No external specs — requirements fully captured in decisions above.
</canonical_refs>

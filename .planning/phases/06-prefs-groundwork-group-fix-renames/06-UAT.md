---
status: complete
phase: 06-prefs-groundwork-group-fix-renames
source: [06-01-SUMMARY.md, 06-02-SUMMARY.md, 06-03-SUMMARY.md, 06-04-SUMMARY.md]
started: 2026-03-08T03:00:00Z
updated: 2026-03-09T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Prefs Dialog — 3 sections with bold headers
expected: Open the prefs dialog. Three sections visible with bold headers: "Spacing", "Scheme Multipliers", "Advanced". No box borders around sections.
result: pass

### 2. Prefs Dialog — new fields present and saving
expected: In the Spacing section, fields for "Horizontal Subtree Gap" (default 150) and "Horizontal Mask Gap" (default 50) are present. In the Advanced section, "Dot Font Reference Size" (default 20) is present. Change a value, click OK, reopen dialog — the changed value persists.
result: pass

### 3. Layout default spacing looks wider
expected: Run a layout on a simple node tree (2–3 nodes). Horizontal spacing between subtrees should be noticeably wider than before (driven by horizontal_subtree_gap=150 pref), while vertical spacing may feel a bit tighter (base_subtree_margin rebalanced from 300→200).
result: pass

### 4. Dot nodes land inside a Group
expected: Enter a Group node (double-click to go inside). Select some nodes and run a layout command. Any Dot nodes created during layout should appear inside the Group, not at the root script level. After layout, exit the Group — no stray Dot nodes should have appeared at root.
result: pass
note: "Fixed by Plan 06-04 — nuke.lastHitGroup() replaced nuke.thisGroup() at layout entry points; confirmed passing in Group View via UAT re-run"

### 5. Push-away stays inside a Group
expected: Inside a Group, run a layout command that triggers push_nodes_to_make_room (e.g. layout on a crowded area). Only nodes inside the Group should be displaced — nodes at root level should not move.
result: pass

### 6. Menu scheme commands end with Compact/Loose
expected: In the Nuke menu (wherever your layout commands live), the four scheme commands should be named ending with "Compact" or "Loose" — e.g. "Layout Compact", "Layout Loose", or similar. No cryptic names.
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0

## Gaps

- truth: "Dot nodes created during layout inside a Group land in the Group context regardless of how the Group is open (Ctrl-Enter or Group View)"
  status: closed
  closed_by: "06-04-PLAN.md"
  verified_by: "UAT re-run — user confirmed pass"
  test: 4

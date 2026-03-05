# Milestones

## v1.0 — Quality & Preferences

**Shipped:** 2026-03-05
**Phases:** 5 | **Plans:** 13
**Files changed:** 51 | **Lines:** 4,095 Python
**Timeline:** 2026-03-03 → 2026-03-05 (2 days)

### Delivered

Transformed node_layout from a working-but-fragile tool into a reliable, undoable, and configurable Nuke DAG layout plugin.

### Key Accomplishments

1. **Code quality pass** — removed debug artifacts, narrowed exception handlers, added per-operation caches for toolbar map and color lookups, tagged diamond Dots with a custom knob for reliable identification
2. **Five layout bugs fixed** — make_room() variable init, node filter stale refs, input-0 centering via _center_x(), secondary input margin symmetry, diamond Dot post-placement centering
3. **Full undo support** — both layout_upstream() and layout_selected() wrapped in Nuke undo groups; Ctrl+Z atomically restores all nodes
4. **Preferences system** — JSON-backed NodeLayoutPrefs singleton at ~/.nuke/node_layout_prefs.json with PySide6 dialog accessible from the Node Layout menu
5. **Sqrt-scaled subtree margins** — spacing scales with node count (backward-compatible at reference_count=150); Compact/Normal/Loose multipliers thread through the full layout pipeline
6. **7 new menu commands** — Compact Layout, Loose Layout (scheme-aware), Shrink/Expand Selected (4 variants), all with keyboard shortcuts (Ctrl+,/. and Shift variants)

### Archive

- `.planning/milestones/v1.0-ROADMAP.md` — full phase details
- `.planning/milestones/v1.0-REQUIREMENTS.md` — all 24 requirements with outcomes

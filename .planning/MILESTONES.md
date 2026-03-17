# Milestones

## v1.1 — Layout Engine & State

**Shipped:** 2026-03-17
**Phases:** 9 (6–12, incl. 3 inserted) | **Plans:** 30
**Files changed:** 133 | **Lines:** ~2,900 Python source (~11,100 incl. tests)
**Timeline:** 2026-03-05 → 2026-03-17 (12 days)

### Delivered

Transformed node_layout into a full layout engine: per-node state memory, horizontal B-spine mode, multi-input fan alignment, axis-specific scale commands, and Dot font-size margin scaling — all with 276 passing tests.

### Key Accomplishments

1. **Rebalanced spacing + horizontal gap preferences** — Separate horizontal gaps for subtrees and mask inputs; defaults rebalanced for less-cramped layouts (Phase 6)
2. **Per-node state storage** — Hidden knobs on every laid-out node store mode, scheme, and scale; survive .nk save/reload and auto-replay on re-layout (Phase 7)
3. **Dot font-size margin scaling** — Subtree margins grow with Dot font size, enabling visual section-boundary signals without extra config (Phase 8)
4. **Multi-input fan alignment + mask side-swap** — 2+ non-mask inputs align at same Y in a fan; mask input placed left of all non-mask inputs (Phase 9)
5. **Axis-specific Shrink/Expand + push-away** — H/V/Both scale modes via menu and modifier keys; Expand pushes surrounding nodes using full layout push logic (Phase 10)
6. **Horizontal B-spine layout** — Left-to-right spine with output Dot; stored in state and auto-replayed by normal layout; geometry bugs corrected in post-ship phases 11.1, 11.2, 12 (Phases 11–12)

### Archive

- `.planning/milestones/v1.1-ROADMAP.md` — full phase details
- `.planning/milestones/v1.1-REQUIREMENTS.md` — all 20 requirements with outcomes
- `.planning/milestones/v1.1-MILESTONE-AUDIT.md` — audit report (passed, 20/20 requirements)

---

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

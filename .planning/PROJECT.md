# node_layout — Quality & Preferences Milestone

## What This Is

node_layout is a Nuke plugin that automatically lays out DAG node trees with intelligent spacing: related nodes (same tile color and toolbar category) are placed tightly, while unrelated nodes get more breathing room. This milestone addresses accumulated technical debt, known bugs, missing critical features (undo/redo, user-facing errors), performance inefficiencies, and adds a user-configurable spacing preferences system following the Labelmaker pattern.

## Core Value

Layout operations must be reliable, undoable, and configurable — users need to trust the tool won't silently misbehave and need to be able to undo when the result isn't what they wanted.

## Requirements

### Validated

- ✓ Automatic upstream DAG layout (Shift+E) — existing
- ✓ Automatic selected-nodes layout (E) — existing
- ✓ Color+category-aware tight/loose vertical spacing — existing
- ✓ Mask/matte input placed rightmost with reduced gap — existing
- ✓ Diamond pattern resolution via hidden Dot insertion — existing
- ✓ Push surrounding nodes to prevent overlap on layout — existing
- ✓ Toolbar folder categorization for spacing decisions — existing
- ✓ Snap threshold integration from Nuke preferences — existing

### Active

<!-- Tech debt -->
- [ ] Toolbar folder cache is refreshable / invalidated per layout operation
- [ ] Exception handling in color/preference lookups catches specific exceptions only
- [ ] Debug print statement removed from util.py
- [ ] `== None` comparisons replaced with `is None` per PEP 8

<!-- Known bugs -->
- [ ] make_room() initializes x_amount/y_amount before conditional branches
- [ ] Node filter in layout_selected() stores node objects (not IDs) to avoid stale references

<!-- Missing critical features -->
- [ ] All layout operations are wrapped in a single Nuke undo group (Ctrl+Z undoes entire layout)
- [ ] layout_upstream() shows a user-friendly dialog when no node is selected
- [ ] layout_selected() shows a user-friendly dialog when no nodes are selected

<!-- Fragile areas -->
- [ ] Diamond-resolution Dot nodes carry an explicit custom knob marker instead of relying on hide_input flag

<!-- Performance -->
- [ ] Preference lookups (find_node_default_color) are memoized/cached per layout operation

<!-- Preferences system -->
- [ ] Spacing constants (SUBTREE_MARGIN, gap multipliers) are read from a prefs file at runtime
- [ ] A PySide6 preferences dialog (node_layout menu) lets users set spacing values and presets
- [ ] Prefs are stored at ~/.nuke/node_layout_prefs.json with sensible defaults
- [ ] Presets (Compact / Normal / Loose) set all spacing values at once
- [ ] Fine-grained controls: SUBTREE_MARGIN, tight gap multiplier, loose gap multiplier, mask input ratio

### Out of Scope

- Keyboard shortcut customization via prefs — conflicts are low probability; documented in README only
- Unit test suite for core algorithms — requires Nuke license; not feasible in CI without headless Nuke
- Spatial indexing / quadtree for large DAGs — performance acceptable up to ~500 nodes; over-engineering for now
- Nuke version compatibility layer — current users are on Nuke 11+; not worth abstracting now

## Context

Sibling project Labelmaker uses an identical prefs pattern: `labelmaker_prefs.py` (JSON-backed singleton at `~/.nuke/labelmaker_prefs.json`) + `labelmaker_prefs_dialog.py` (PySide6 QDialog launched from menu). node_layout's prefs module should follow the same structure.

Current hardcoded spacing values:
- `SUBTREE_MARGIN = 300` — vertical clearance between adjacent subtrees
- `MASK_INPUT_MARGIN = SUBTREE_MARGIN // 3` — gap for mask inputs (~100 px)
- Tight gap: `snap_threshold - 1` (same color+category)
- Loose gap: `12 * snap_threshold` (different color or category)

## Constraints

- **Tech stack**: Python, PySide6 (matches Labelmaker); JSON prefs at `~/.nuke/`
- **Compatibility**: Nuke 11+ assumed; no version guards needed
- **Pattern**: Follow Labelmaker conventions exactly for prefs module structure

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Follow Labelmaker prefs pattern | Consistency across sibling plugins; user already knows the UX | — Pending |
| Store prefs at ~/.nuke/node_layout_prefs.json | Matches Nuke convention; survives plugin reinstalls | — Pending |
| Add custom knob to diamond-resolution Dots | Safer than relying on hide_input flag which user can set manually | — Pending |
| Cache preference lookups per layout op (not globally) | Avoids stale data while still reducing repeated Nuke API calls | — Pending |

---
*Last updated: 2026-03-03 after initialization*

# node_layout

## What This Is

node_layout is a Nuke plugin that automatically lays out DAG node trees with intelligent spacing: related nodes (same tile color and toolbar category) are placed tightly, while unrelated nodes get more breathing room. Users can configure spacing values, choose compact or loose layout schemes, and scale node spacing up or down. All layout operations are fully undoable.

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
- ✓ Toolbar folder cache refreshed per layout operation — v1.0
- ✓ Exception handling catches specific exceptions only — v1.0
- ✓ Diamond-resolution Dots tagged with custom knob marker — v1.0
- ✓ Per-operation color lookup cache — v1.0
- ✓ make_room() variables always initialized before use — v1.0
- ✓ Node filter stores node objects (not IDs) to avoid stale refs — v1.0
- ✓ Input-0 always placed directly above consumer node — v1.0
- ✓ Secondary input margin symmetry (left/right consistent) — v1.0
- ✓ Diamond Dot centered under consumer post-placement — v1.0
- ✓ Layout operations wrapped in Nuke undo groups (Ctrl+Z works) — v1.0
- ✓ JSON-backed prefs module with singleton at ~/.nuke/node_layout_prefs.json — v1.0
- ✓ Subtree margin scales with sqrt(node_count) — v1.0
- ✓ Spacing constants read from prefs at runtime — v1.0
- ✓ PySide6 preferences dialog accessible from menu — v1.0
- ✓ Compact / Normal / Loose layout schemes via scheme_multiplier — v1.0
- ✓ Shrink/expand selected and upstream scaling commands — v1.0

### Active

- [ ] **SCHEME-02**: Horizontal layout scheme — input 0 goes left instead of up
- [ ] **SCHEME-03**: Fan scheme — all inputs in one row above root node
- [ ] **SCHEME-04**: Per-node layout scheme tag via custom knob
- [ ] **SCHEME-05**: Clear layout scheme tag command

### Out of Scope

| Feature | Reason |
|---------|--------|
| Error dialogs for empty selection | Annoying; fail silently instead |
| Keyboard shortcut customization | Low conflict probability; documented in README only |
| Unit test suite requiring Nuke license | Not feasible in CI without headless Nuke; AST-based tests used instead |
| Spatial indexing / quadtree | Acceptable performance up to ~500 nodes; over-engineering now |
| Nuke version compatibility layer | Users are on Nuke 11+; no abstraction needed |
| SCHEME-04 tagged layout | Out of scope until v2.0 |

## Context

**Current state:** v1.0 shipped 2026-03-05. Codebase is 4,095 Python LOC across node_layout.py, make_room.py, util.py, node_layout_prefs.py, node_layout_prefs_dialog.py, menu.py, and a test suite.

**Tech stack:** Python, PySide6 (matches sibling plugin Labelmaker); JSON prefs at ~/.nuke/; AST-based tests (nuke module unavailable outside Nuke).

**Patterns established:**
- Per-operation cache reset: module-level globals set to None at entry points
- Custom knob tagging for programmatically-created nodes
- Follow Labelmaker prefs pattern for consistency across sibling plugins
- try/except/else for Nuke undo groups (not finally)
- scheme_multiplier resolves to normal_multiplier on first None check (not at every recursive level)
- sqrt-scaled subtree margin: int(base * multiplier * sqrt(node_count) / sqrt(reference_count))

## Constraints

- **Tech stack**: Python, PySide6 (matches Labelmaker); JSON prefs at `~/.nuke/`
- **Compatibility**: Nuke 11+ assumed; no version guards needed
- **Pattern**: Follow Labelmaker conventions exactly for prefs module structure

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Follow Labelmaker prefs pattern | Consistency across sibling plugins | ✓ Good |
| Store prefs at ~/.nuke/node_layout_prefs.json | Matches Nuke convention; survives reinstalls | ✓ Good |
| Add custom knob to diamond-resolution Dots | Safer than relying on user-settable hide_input flag | ✓ Good |
| Cache preference lookups per layout op (not globally) | Avoids stale data; reduces repeated Nuke API calls | ✓ Good |
| Narrow exception handling to (KeyError, AttributeError) | Only two failure modes for nuke knob access; bare Exception swallows programmer errors | ✓ Good |
| Reset _TOOLBAR_FOLDER_MAP to None (not pass dict through chain) | Simpler; _get_toolbar_folder_map() rebuilds on first access | ✓ Good |
| Use try/except/else for undo group | nuke.Undo.end() in else, nuke.Undo.cancel() in except — correct Nuke API contract | ✓ Good |
| sqrt formula for subtree margin | Backward-compatible at reference_count=150; smaller subtrees get proportionally less clearance | ✓ Good |
| scheme_multiplier resolves at top, not each recursion level | Avoids redundant prefs reads in recursive calls | ✓ Good |
| SHRINK_FACTOR=0.8, EXPAND_FACTOR=1.25 as module constants | Not user-configurable — ratio is the meaningful unit, not the raw value | ✓ Good |
| Center-based offsets in scale functions | Dot nodes move same fractional distance as regular nodes | ✓ Good |
| snap_min floor in _scale_selected only, not _scale_upstream | Upstream trees are self-consistent layouts; floor would distort them | ✓ Good |
| Anchor tiebreaker key=(ypos, -xpos) | Deterministic anchor selection on Y tie in _scale_selected_nodes | ✓ Good |
| QLineEdit (not QSpinBox) for dialog fields | Matches Labelmaker pattern | ✓ Good |
| Validate base_subtree_margin > 0 and scaling_reference_count >= 1 | Prevents downstream ZeroDivisionError | ✓ Good |
| No keyboard shortcuts for Compact/Loose layout commands | Low usage frequency; menu-only per CONTEXT.md decision | ✓ Good |

---
*Last updated: 2026-03-05 after v1.0 milestone*

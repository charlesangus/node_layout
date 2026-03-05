# node_layout — Project

## What This Is

node_layout is a Nuke plugin that automatically lays out DAG node trees with intelligent spacing: related nodes (same tile color and toolbar category) are placed tightly, while unrelated nodes get more breathing room. The plugin is reliable, fully undoable, and user-configurable — users can adjust spacing values via a persistent preferences file and PySide6 dialog, and apply compact, normal, or loose layout schemes.

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
- ✓ Toolbar folder cache invalidated and rebuilt per layout operation — v1.0
- ✓ Exception handling in color/preference lookups catches specific exceptions only (KeyError, AttributeError) — v1.0
- ✓ Debug print removed from util.py — v1.0
- ✓ `== None` comparisons replaced with `is None` — v1.0
- ✓ Diamond-resolution Dot nodes carry `node_layout_diamond_dot` custom knob marker — v1.0
- ✓ Color lookup results memoized per layout operation, cleared between operations — v1.0
- ✓ make_room() initializes x_amount/y_amount before conditional branches — v1.0
- ✓ Node filter in layout_selected() stores node objects to avoid stale references — v1.0
- ✓ Input 0 (main/B input) always goes directly above consumer node — v1.0
- ✓ Diamond-resolution Dot nodes centered under their output node — v1.0
- ✓ A/B/mask input slot spacing consistent (same rules both sides) — v1.0
- ✓ layout_upstream() wrapped in single Nuke undo group (single Ctrl+Z) — v1.0
- ✓ layout_selected() wrapped in single Nuke undo group (single Ctrl+Z) — v1.0
- ✓ Spacing constants read from prefs at layout-operation time — v1.0
- ✓ PySide6 preferences dialog accessible from node_layout menu — v1.0
- ✓ Prefs stored at ~/.nuke/node_layout_prefs.json with sensible defaults — v1.0
- ✓ Compact, Normal, Loose layout scheme commands in menu — v1.0
- ✓ Subtree margin scales with node count via sqrt formula — v1.0
- ✓ Shrink/Expand Selected scales spacing centered on root node — v1.0
- ✓ Scale Upstream applies shrink/expand to all upstream nodes — v1.0

### Active

- [ ] Rebalance default spacing (less vertical, more horizontal) and add horizontal spacing preferences
- [ ] Differentiate horizontal gap for secondary vs mask inputs; mask input goes left when 2+ non-mask inputs present
- [ ] Subtree margin scales with font size of Dot at subtree root (section boundary signal)
- [ ] Rename Compact/Loose commands to put scheme name at end (tab-menu discoverability)
- [ ] Multi-input fan alignment: 2+ non-mask inputs have subtree roots at same Y, spread left-to-right
- [ ] Expand Selected/Upstream push surrounding nodes away (same push logic as regular layout)
- [ ] Shrink/Expand H/V/Both modes via separate commands and modifier keys
- [ ] Per-node hidden tab/knobs storing layout mode, scheme, and scale factor; replayed on re-layout
- [ ] Horizontal B-spine layout command (left→right); stored in knobs, replayed by normal layout
- [ ] Fix: Dot nodes created in correct Group context when running inside a Nuke Group

### Out of Scope

- Keyboard shortcut customization via prefs — conflicts are low probability; document in README only
- Unit test suite for core algorithms — requires Nuke license; not feasible in CI without headless Nuke
- Spatial indexing / quadtree for large DAGs — performance acceptable up to ~500 nodes; over-engineering for now
- Nuke version compatibility layer — current users are on Nuke 11+; not worth abstracting now
- Error dialogs for empty selection — fail silently; no dialog noise
- Layout scheme tag on individual nodes — moved to v1.1 as part of node state storage

## Context

**Shipped:** v1.0 Quality & Preferences (2026-03-05)
**Codebase:** ~4,095 LOC Python across node_layout.py, util.py, node_layout_prefs.py, node_layout_prefs_dialog.py, menu.py, and test suite
**Tech stack:** Python, PySide6; JSON prefs at `~/.nuke/`; AST-based structural tests (Nuke unavailable in CI)
**Test suite:** 121 tests (test_prefs_integration.py, test_node_layout_prefs.py, test_undo_wrapping.py, test_scale_nodes.py, test_layout_core.py)

Sibling project Labelmaker uses an identical prefs pattern: `labelmaker_prefs.py` (JSON-backed singleton at `~/.nuke/labelmaker_prefs.json`) + `labelmaker_prefs_dialog.py`. node_layout follows the same structure.

## Constraints

- **Tech stack**: Python, PySide6 (matches Labelmaker); JSON prefs at `~/.nuke/`
- **Compatibility**: Nuke 11+ assumed; no version guards needed
- **Pattern**: Follow Labelmaker conventions exactly for prefs module structure

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Follow Labelmaker prefs pattern | Consistency across sibling plugins; user already knows the UX | ✓ Good — clean pattern, consistent structure |
| Store prefs at ~/.nuke/node_layout_prefs.json | Matches Nuke convention; survives plugin reinstalls | ✓ Good |
| Add custom knob to diamond-resolution Dots | Safer than relying on hide_input flag which user can set manually | ✓ Good — robust identification |
| Cache preference lookups per layout op (not globally) | Avoids stale data while still reducing repeated Nuke API calls | ✓ Good |
| Use try/except/else (not finally) for undo groups | Nuke API contract: end() in else, cancel() in except only | ✓ Good — prevents partial undo state |
| Early-return guard before undo group open in layout_selected() | No empty undo entries when <2 nodes selected | ✓ Good |
| Use QLineEdit (not QSpinBox) for dialog | Matches Labelmaker pattern | ✓ Good |
| scheme_multiplier defaults None, resolved at first call site | Avoids redundant prefs reads in recursive calls | ✓ Good |
| compact/loose scheme affects vertical gaps only; horizontal unchanged | Horizontal spacing is category-based, not density-based | ✓ Good — correct semantics |
| snap_min floor in _scale_selected_nodes only, not _scale_upstream_nodes | Upstream trees are self-consistent layouts; floor would distort relative spacing | ✓ Good |
| Anchor tiebreaker key=(n.ypos(), -n.xpos()) for scale commands | Deterministic anchor selection on Y tie | ✓ Good |
| base_subtree_margin default 300 (backward-compatible) | At reference_count=150, sqrt formula returns exactly 300; small subtrees receive tighter spacing dynamically | ✓ Good — intentional design |
| No preset selector in dialog; no tight gap field | Compact/Normal/Loose are menu commands (Phase 5 design); tight gap removed in favor of multiplier scheme | ✓ Good |

## Current Milestone: v1.1 Layout Engine & State

**Goal:** Improve layout quality through spacing rebalance, multi-input fan alignment, horizontal B-spine mode, and per-node state memory for least-surprise re-layout.

**Target features:**
- Spacing rebalance + horizontal preferences
- Multi-input fan alignment + mask side-swap
- Node state storage (hidden tab/knobs)
- Horizontal B-spine layout command
- Shrink/Expand H/V/Both modes
- Expand push-away
- Command renames
- Group context bug fix

---
*Last updated: 2026-03-05 after v1.1 milestone start*

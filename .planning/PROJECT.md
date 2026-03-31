# node_layout — Project

## What This Is

node_layout is a Nuke plugin that automatically lays out DAG node trees with intelligent spacing and persistent state. Related nodes are placed tightly while unrelated nodes get breathing room. The plugin supports vertical stacking, horizontal B-spine mode, multi-input fan alignment, and axis-specific scale commands. It is fully undoable, user-configurable via a PySide6 preferences dialog, and stores per-node layout state in hidden knobs that survive script save/reload and auto-replay on re-layout. Every push is automatically linted and tested via GitHub Actions CI, and version tags produce a tested ZIP artifact published as a GitHub Release.

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
- ✓ Horizontal/mask gap prefs configurable via dialog; defaults rebalanced (less vertical cramping) — v1.1
- ✓ Dot font-size drives subtree margin scaling (section-boundary signal) — v1.1
- ✓ Scheme commands renamed: scheme name at end (tab-menu discoverability) — v1.1
- ✓ Group context: Dot nodes created inside Group, push-away scoped to Group — v1.1
- ✓ Per-node hidden state (mode, scheme, scale) persistent across save/reload and auto-replayed on re-layout — v1.1
- ✓ Multi-input fan alignment: 2+ non-mask inputs at same Y; mask placed left of all non-mask inputs — v1.1
- ✓ Shrink/Expand H/V/Both axis modes; Expand pushes surrounding nodes away — v1.1
- ✓ Horizontal B-spine layout (Layout Selected Horizontal); stored in state, auto-replayed by normal layout — v1.1
- ✓ pyproject.toml with Ruff config (line-length=100, E/F/W/B/I/SIM rules) — v1.2
- ✓ GitHub Actions CI workflow: pytest + Ruff linting on every push and PR — v1.2
- ✓ GitHub Actions release workflow: v* tag triggers test gate, versioned ZIP build, GitHub Release publish — v1.2

### Validated (continued)

<!-- v1.3 Freeze Layout — validated in Phase 15–16 -->

- ✓ User can freeze a selection of nodes into a named freeze group (shared UUID, stored in hidden layout knob) — v1.3 (Phase 15)
- ✓ User can unfreeze selected nodes, removing their freeze group membership — v1.3 (Phase 15)
- ✓ Layout engine detects freeze groups during preprocessing (same phase as horizontal block detection) and treats each group as a rigid block — v1.3 (Phase 16)
- ✓ Nodes inserted between frozen nodes in the DAG auto-join the freeze group during layout crawl (no real-time callbacks) — v1.3 (Phase 16)
- ✓ Layout positions a frozen block via its root node (most downstream); other block nodes maintain relative offsets — v1.3 (Phase 16)
- ✓ Push-away (expand) moves a frozen block rigidly as a unit using its bounding box as the obstacle — v1.3 (Phase 16)

### Active

<!-- v1.4 Leader Key -->

- [ ] Shift+E enters leader mode (replaces Layout Upstream shortcut)
- [ ] Leader mode dispatches V/Z/F/C/W/A/S/D/Q/E to existing commands
- [ ] WASD movement chains — leader mode persists between move steps
- [ ] Any unrecognized key or mouse click cancels leader mode
- ✓ Icon-style keyboard overlay (`LeaderKeyOverlay` HUD widget) implemented — v1.4 (Phase 18)
- ✓ New pref: "hint popup delay (ms)" with default 0 — v1.4 (Phase 17)
- ✓ WASD/Q/E chaining dispatch in leader mode — `_CHAINING_DISPATCH_TABLE` keeps mode active — v1.4 (Phase 20)

### Out of Scope

- Keyboard shortcut customization via prefs — conflicts are low probability; document in README only
- Unit test suite for core algorithms — requires Nuke license; not feasible in CI without headless Nuke
- Spatial indexing / quadtree for large DAGs — performance acceptable up to ~500 nodes; over-engineering for now
- Nuke version compatibility layer — current users are on Nuke 11+; not worth abstracting now
- Error dialogs for empty selection — fail silently; no dialog noise
- Layout scheme tag on individual nodes — delivered in v1.1 as per-node state storage
- PyPI publishing — not a Python package; users install manually into `~/.nuke/`
- Docker-based Nuke testing — no headless Nuke license; stub-based tests are sufficient
- Automated versioning / changelog generation — git tags + auto-release notes are sufficient

## Context

**Shipped:** v1.2 CI/CD (2026-03-18)
**Shipped:** v1.3 Freeze Layout (2026-03-19) — Phase 16 complete
**In Progress:** v1.4 Leader Key — Phase 20 complete (WASD/Q/E chaining dispatch)
**Codebase:** ~3,200 LOC Python source (node_layout.py, node_layout_state.py, util.py, node_layout_prefs.py, node_layout_prefs_dialog.py, node_layout_overlay.py, menu.py); ~12,000+ LOC total incl. tests; 81 lines GitHub Actions YAML
**Tech stack:** Python, PySide6; JSON prefs at `~/.nuke/`; AST-based structural tests + Nuke-stub unit tests; GitHub Actions CI (Ruff + pytest) and release workflow (softprops/action-gh-release@v2)
**Test suite:** 366 tests spanning prefs, state, layout core, fan alignment, horizontal spine, scale commands, freeze commands, freeze layout integration, leader key prefs/dialog, and overlay widget

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
| node_layout_state.py as separate module | Clean separation; state helpers importable without full layout engine | ✓ Good |
| Hidden tab knobs (not visible knobs) for per-node state | No clutter in node parameter panel; state is implementation detail | ✓ Good |
| compute_dims memo key extended to 5-tuple (id, scheme, h_scale, v_scale, mode) | Correctly invalidates cache when any layout parameter changes | ✓ Good |
| Horizontal mode stored per-node, replayed via BFS scan | Normal Layout Upstream auto-dispatches without requiring explicit Horizontal command — least-surprise UX | ✓ Good |
| Layout Selected Horizontal sets mode; no Layout Upstream Horizontal command | Post-UAT redesign: upstream horizontal is triggered by stored mode replay, not a separate command | ✓ Good — cleaner than two entry points |
| Fan layout: _is_fan_active() threshold is 2+ non-mask inputs | Matches actual compositor usage; 2-input trees use original stacking | ✓ Good |
| Inserted phases use decimal numbering (11.1, 11.2, 12) | Clear insertion semantics; avoids renumbering existing phases | ✓ Good |
| Phase 2 vertical pass for consumer when horizontal chain detected | Lets normal vertical tree sit correctly above/below horizontal spine without overlap | ✓ Good |
| Single sequential lint-then-test CI job (not parallel) | Lint failure fast-fails before tests run — faster feedback, avoids wasted compute | ✓ Good |
| ubuntu-24.04 explicit (not ubuntu-latest) in GitHub Actions | Reproducibility across time; ubuntu-latest changes without notice | ✓ Good |
| Hardcoded 9-file list in ZIP build (not glob) | Prevents accidental inclusion of test files or future non-distribution files | ✓ Good |
| ZIP named with github.ref_name preserving v prefix | Produces e.g. node_layout-v1.2.zip — clear version signal without extra config | ✓ Good |
| softprops/action-gh-release@v2 with generate_release_notes: true | No manual release notes authoring; auto-notes from PR/commit history | ✓ Good |

## Current Milestone: v1.4 Leader Key

**Goal:** Replace the Shift+E Layout Upstream shortcut with a modal leader key system that dispatches to existing commands via a mnemonic keymap and displays an icon-style keyboard overlay over the DAG during the modal window.

**Target features:**
- Shift+E enters leader mode; any unrecognized key or mouse click cancels it (no timeout)
- V — vertical layout (1-node selected → layout upstream, 2+ nodes → layout selection)
- Z — horizontal layout
- F — freeze/unfreeze toggle (context-aware)
- C — clear freeze group
- W/A/S/D — move selected nodes; stays in leader mode for chained movement
- Q — scale down (shrink); E — scale up (expand)
- Icon-style keyboard overlay over active DAG on leader press, showing active keys and labels
- New pref: "hint popup delay (ms)", default 0

## Completed Milestone: v1.3 Freeze Layout ✓

**Goal:** Add a freeze command that locks the relative positions of a group of nodes into a rigid block that the layout engine treats as a single unit.

**All features shipped:**
- Freeze Selected: marks selected nodes with a shared UUID in hidden layout knob
- Unfreeze Selected: removes freeze group membership
- Layout crawl detects and resolves freeze groups (preprocessing step)
- Auto-join: nodes inserted between frozen DAG nodes inherit the group during crawl
- Rigid block positioning: block anchored at root node; relative offsets preserved
- Rigid push-away: expand treats block bounding box as single obstacle

---
*Last updated: 2026-03-30 after Phase 20 WASD chaining dispatch completion*
